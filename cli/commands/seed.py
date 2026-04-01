# cli/commands/seed.py
from event_service.repository import EventRepository
from schemas.event_schema import Event
from datetime import datetime, timedelta
import uuid
import random

def run():
    """Execution for the seed command."""
    repo = EventRepository()
    
    print("\n" + "="*50)
    print(" AERIS BASELINE SEEDING")
    print("="*50)
    print(" [TARGET]  60 Minutes (High Fidelity)")
    print(" [PROFILE] 50ms Latency | v2.0 Version")
    
    now = datetime.utcnow()
    for i in range(200):
        # Spread 200 events over 60 mins
        ts = now - timedelta(minutes=random.randint(0, 60))
        event = Event(
            event_id=str(uuid.uuid4()),
            trace_id=str(uuid.uuid4()),
            service_name="payment-api",
            endpoint="/api/v1/charge",
            status="200",
            retry_count=0,
            max_retries=3,
            is_dead=False,
            timestamp=ts,
            latency_ms=random.gauss(50, 5),
            region="us-east-1",
            version="v2.0",
            error_code=0
        )
        repo.insert_event(event)

    print("-" * 50)
    print(" [SEED]    200 Baseline events populated.")
    print(" [STATUS]  Ready for DRIFT / ANOMALY detection.")
    print("="*50 + "\n")
