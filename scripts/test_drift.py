from datetime import datetime, timedelta
import uuid

from db.sqlite import init_db
from schemas.event_schema import Event
from event_service.service import EventService
from drift_engine.engine import DriftEngine


def create_event(trace_id, retry_count, max_retries, minutes_ago):
    return Event(
        event_id=str(uuid.uuid4()),
        trace_id=trace_id,
        service_name="order-service",
        endpoint="/create",
        status="failure",
        retry_count=retry_count,
        max_retries=max_retries,
        is_dead=False,
        timestamp=datetime.utcnow() - timedelta(minutes=minutes_ago),
        error_type="timeout"
    )


def simulate_baseline():
    print("\n📊 Generating BASELINE (stable system)...")

    for _ in range(20):
        trace_id = str(uuid.uuid4())
        event = create_event(trace_id, retry_count=0, max_retries=3, minutes_ago=15)
        EventService.create_event(event)


def simulate_recent():
    print("\n🔥 Generating RECENT (degraded system)...")

    for _ in range(30):
        trace_id = str(uuid.uuid4())
        event = create_event(trace_id, retry_count=2, max_retries=3, minutes_ago=5)
        EventService.create_event(event)

    # add some dead events
    for _ in range(10):
        trace_id = str(uuid.uuid4())
        event = create_event(trace_id, retry_count=3, max_retries=3, minutes_ago=5)
        EventService.create_event(event)


def main():
    print("\n🔧 Initializing DB...")
    init_db()

    simulate_baseline()
    simulate_recent()

    print("\n🧠 Running Drift Analysis...\n")

    result = DriftEngine.analyze_drift(window_size_minutes=10)

    print("Baseline Metrics:", result["baseline"])
    print("Recent Metrics:", result["recent"])
    print("Drift:", result["drift"])
    print("Risk Level:", result["risk_level"])
    print("Confidence:", result["confidence"])

    if "reason" in result:
        print("Reason:", result["reason"])


if __name__ == "__main__":
    main()