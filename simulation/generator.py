import requests
import uuid
import time
import random
import argparse
from datetime import datetime, timezone

API_URL = "http://localhost:8000"

# --- Deterministic Seed for Repeatability ---
random.seed(42)

SERVICES = {
    "payment-service": ["/process", "/authorize"],
    "order-service": ["/create", "/update"],
    "inventory-service": ["/check", "/reserve"],
    "shipping-service": ["/label", "/track"]
}

ERROR_TYPES = ["latency_timeout", "connection_reset", "db_deadlock", "auth_failure", "rate_limit"]

def post_event(payload):
    try:
        response = requests.post(f"{API_URL}/events", json=payload)
        return response.status_code == 200
    except Exception as e:
        print(f"Connection error: {e}")
        return False

class ScenarioRunner:
    @staticmethod
    def brownian_burn(duration_min=10, service="payment-service"):
        """Gradually increase latency over time to test slow degradation detection."""
        print(f"🔥 Scenario: BROWNIAN BURN on {service} (Duration: {duration_min}m)")
        start_time = time.time()
        base_latency = 50.0
        
        # 10 events per minute
        for m in range(duration_min):
            current_latency = base_latency + (m * 25.0) # Increases by 25ms every minute
            print(f"Minute {m}: Targeting latency {current_latency}ms")
            
            for _ in range(10):
                post_event({
                    "event_id": str(uuid.uuid4()),
                    "trace_id": str(uuid.uuid4()),
                    "service_name": service,
                    "endpoint": "/process",
                    "status": "failure",
                    "retry_count": 0,
                    "max_retries": 3,
                    "is_dead": False,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "error_type": "timeout",
                    "latency_ms": current_latency + random.uniform(-5, 5) # Slight jitter
                })
            time.sleep(1) # Simulated time passage

    @staticmethod
    def retry_storm(duration_min=10, service="order-service"):
        """Gradually increase retry counts while keeping failure rate constant."""
        print(f"🌀 Scenario: RETRY STORM on {service}")
        for m in range(duration_min):
            current_retry = min(m // 2, 3) # Starts at 0, goes up to 3
            print(f"Minute {m}: Targeting avg retry {current_retry}")
            
            for _ in range(15):
                post_event({
                    "event_id": str(uuid.uuid4()),
                    "trace_id": str(uuid.uuid4()),
                    "service_name": service,
                    "endpoint": "/create",
                    "status": "failure",
                    "retry_count": current_retry,
                    "max_retries": 3,
                    "is_dead": current_retry >= 3,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "error_type": "retry_exhaustion",
                    "latency_ms": 100.0
                })
            time.sleep(1)

    @staticmethod
    def silent_failure(duration_min=5, service="inventory-service"):
        """Drop total failure volume by 50% to test traffic volatility drift."""
        print(f"🔇 Scenario: SILENT FAILURE on {service}")
        # Minute 0-2: Normal load (20 events/min)
        # Minute 2-5: Low load (5 events/min)
        for m in range(duration_min):
            count = 20 if m < 2 else 5
            print(f"Minute {m}: Emitting {count} events")
            for _ in range(count):
                post_event({
                    "event_id": str(uuid.uuid4()),
                    "trace_id": str(uuid.uuid4()),
                    "service_name": service,
                    "endpoint": "/check",
                    "status": "failure",
                    "retry_count": 0,
                    "max_retries": 3,
                    "is_dead": False,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "error_type": "db_error",
                    "latency_ms": 10.0
                })
            time.sleep(1)

    @staticmethod
    def heavy_tail(duration_min=5, service="shipping-service"):
        """95% normal events, 5% extreme latency to test p95 sensitivity."""
        print(f"📈 Scenario: HEAVY TAIL (High Intensity) on {service}")
        for m in range(duration_min):
            print(f"Minute {m}: Bursting 80 events with 10% outliers")
            for i in range(80):
                # 10% outliers (every 10th event)
                is_outlier = (i % 10 == 0) 
                latency = 10000.0 if is_outlier else 50.0
                post_event({
                    "event_id": str(uuid.uuid4()),
                    "trace_id": str(uuid.uuid4()),
                    "service_name": service,
                    "endpoint": "/label",
                    "status": "failure",
                    "retry_count": 0,
                    "max_retries": 3,
                    "is_dead": False,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "error_type": "io_delay",
                    "latency_ms": latency
                })
            time.sleep(1)

def validate_drift():
    print("\n🧐 Validating Detected Drift via AERIS Engine...")
    try:
        response = requests.get(f"{API_URL}/drift/explain?recent_min=5&baseline_min=60")
        if response.status_code == 200:
            data = response.json()
            print(f"Risk Level: {data['risk_level']} | Confidence: {data['confidence']}")
            print("Detected Signals:")
            for detail in data['details']:
                print(f"  - {detail}")
            if not data['details']:
                print("  - [!] NO DRIFT DETECTED")
        else:
            print(f"Validation failed: {response.text}")
    except Exception as e:
        print(f"Could not reach AERIS API: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AERIS V2 Deterministic Drift Generator")
    parser.add_argument("--scenario", type=str, choices=["brownian", "storm", "silent", "tail"], required=True)
    parser.add_argument("--duration", type=int, default=10, help="Duration in simulated minutes (default: 10)")
    
    args = parser.parse_args()
    
    runner = ScenarioRunner()
    scenarios = {
        "brownian": runner.brownian_burn,
        "storm": runner.retry_storm,
        "silent": runner.silent_failure,
        "tail": runner.heavy_tail
    }
    
    scenarios[args.scenario](duration_min=args.duration)
    validate_drift()
