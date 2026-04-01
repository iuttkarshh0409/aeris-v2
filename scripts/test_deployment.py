# scripts/test_deployment.py
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from drift_engine.engine import DriftEngine

def test_deployment_drift():
    # 1. Simulate BASELINE (Safe v2.0)
    print("[SEEDING] BASELINE: v2.0 @ 50ms (0% Errors)")
    baseline_events = [{
        "version": "v2.0", "latency_ms": 50.0, "is_dead": False, "region": "us-east-1", "service_name": "checkout", "timestamp": "2026-04-01T00:00:00", "retry_count": 0
    } for _ in range(100)]

    # 2. Simulate RECENT (Regressive v2.1)
    print("[RELEASE] SIMULATING RELEASE: v2.1 @ 300ms (15% Errors)")
    recent_events = []
    for i in range(100):
        is_v21 = (i < 80) # 80% v2.1 canary
        v = "v2.1" if is_v21 else "v2.0"
        lat = 300.0 if is_v21 else 50.0
        err = (i % 7 == 0) if is_v21 else False 
        recent_events.append({
            "version": v, "latency_ms": lat, "is_dead": err, "region": "us-east-1", "service_name": "checkout", "timestamp": f"2026-04-01T01:0{i%10}:00", "retry_count": 0
        })

    # 3. Analyze through Decision Engine
    analysis = DriftEngine.calculate_drift_from_events(baseline_events, recent_events)
    brief = DriftEngine._generate_decision_safe_brief(analysis, recent_events)

    print(brief)

if __name__ == "__main__":
    test_deployment_drift()
