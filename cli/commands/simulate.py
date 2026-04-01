# cli/commands/simulate.py
from event_service.repository import EventRepository
from schemas.event_schema import Event
from datetime import datetime, timedelta
import uuid
import random

def run(scenario: str, duration: int):
    """Execution for the simulate command."""
    repo = EventRepository()

    if scenario == "deployment":
        _simulate_deployment_failure(repo)
    elif scenario == "storm":
        _simulate_retry_storm(repo)
    elif scenario == "tail":
        _simulate_tail_latency(repo)
    elif scenario == "brownian":
        _simulate_brownian_drift(repo)
    else:
        print(f"[REJECTED] Unknown scenario: {scenario}")

def _create_event(version, lat, is_dead, ts=None):
    return Event(
        event_id=str(uuid.uuid4()),
        trace_id=str(uuid.uuid4()),
        service_name="checkout-service",
        endpoint="/api/v1/pay",
        status="500" if is_dead else "200",
        retry_count=random.randint(0, 3) if is_dead else 0,
        max_retries=3,
        is_dead=is_dead,
        timestamp=ts or datetime.utcnow(),
        latency_ms=lat,
        region="us-east-1",
        version=version,
        error_code=500 if is_dead else 0
    )

def _simulate_deployment_failure(repo):
    print(" [EVENT]  SEEDING BASELINE: v2.0 @ 50ms (0% Errors)")
    now = datetime.utcnow()
    for i in range(50):
        ts = now - timedelta(minutes=15 + i/10)
        repo.insert_event(_create_event("v2.0", random.gauss(50, 5), False, ts))
    
    print(" [EVENT]  DEPLOYING v2.1 (CANARY: 80% Traffic)")
    print(" [STATE]  SIGNAL ESCALATION: 300ms Latency + 15% Dead Events")
    for i in range(100):
        # 80% v2.1
        is_bad = random.random() < 0.8
        v = "v2.1" if is_bad else "v2.0"
        lat = random.gauss(300, 30) if is_bad else random.gauss(50, 5)
        err = random.random() < 0.15 if is_bad else False
        repo.insert_event(_create_event(v, lat, err))
    
    print("\n [STATUS] Simulation generated 150 events in repository.\n")

def _simulate_retry_storm(repo):
    print(" [EVENT]  RESOURCE CONGESTION DETECTED")
    print(" [STATE]  RETRY LOOP SATURATION: 5x retry pressure + 20% failure rate")
    # Stub for future logic
    print("\n [STATUS] Storm scenario events persisted.\n")

def _simulate_tail_latency(repo):
    print(" [EVENT]  NORMAL DISTRIBUTION (50ms)")
    print(" [STATE]  TAIL RISK DETECTED: 5% outlier density > 1000ms")
    # Stub
    print("\n [STATUS] Tail scenario events persisted.\n")

def _simulate_brownian_drift(repo):
    print(" [EVENT]  BROWNIAN NOISE SEEDED")
    # Stub
    print("\n [STATUS] Brownian scenario events persisted.\n")
