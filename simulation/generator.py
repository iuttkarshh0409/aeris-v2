import requests
import uuid
import time
import random
from datetime import datetime

API_URL = "http://localhost:8000"

SERVICES = {
    "payment-service": ["/process", "/authorize"],
    "order-service": ["/create", "/update"],
    "inventory-service": ["/check", "/reserve"],
    "shipping-service": ["/label", "/track"]
}

ERROR_TYPES = ["timeout", "connection_reset", "db_deadlock", "auth_failure", "rate_limit"]

def generate_fault(service, endpoint, retry_count=0, max_retries=3):
    payload = {
        "event_id": str(uuid.uuid4()),
        "trace_id": str(uuid.uuid4()),
        "service_name": service,
        "endpoint": endpoint,
        "status": "failure",
        "retry_count": retry_count,
        "max_retries": max_retries,
        "is_dead": False, # Computed by engine
        "timestamp": datetime.utcnow().isoformat(),
        "error_type": random.choice(ERROR_TYPES)
    }

    try:
        response = requests.post(f"{API_URL}/events", json=payload)
        if response.status_code == 200:
            data = response.json()["event"]
            print(f"[{service}] Created Event -> Retry: {data['retry_count']}/{data['max_retries']} | Severity: {data['severity']} | Reason: {data['severity_reason']}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Connection error: {e}")

def run_simulation(duration_seconds=60):
    print(f"🚀 Starting HIGH-LOAD AERIS V2 Simulation for {duration_seconds}s...")
    start_time = time.time()
    
    while time.time() - start_time < duration_seconds:
        scenario = random.random()
        
        if scenario > 0.7:
            # 30% chance: Rapid mass cluster of failures on payment-service
            print(f"\n🔥 MASS CLUSTER STRESS EVENT on payment-service")
            for _ in range(35):
                generate_fault("payment-service", "/process", retry_count=random.randint(1, 2))
        elif scenario > 0.4:
            # 30% chance: Random medium-intensity failures
            service = random.choice(list(SERVICES.keys()))
            print(f"\n🔸 MEDIUM STRESS on {service}")
            for _ in range(15):
                generate_fault(service, random.choice(SERVICES[service]), retry_count=random.randint(0, 1))
        else:
            service = random.choice(list(SERVICES.keys()))
            generate_fault(service, random.choice(SERVICES[service]), retry_count=random.randint(0, 1))
            
        time.sleep(0.5) # Faster sleep

if __name__ == "__main__":
    run_simulation(60)
