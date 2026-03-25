from datetime import datetime
import uuid

from db.sqlite import init_db
from schemas.event_schema import Event
from event_service.service import EventService
from event_service.repository import EventRepository


def generate_event(trace_id, retry_count, max_retries):
    return Event(
        event_id=str(uuid.uuid4()),
        trace_id=trace_id,
        service_name="payment-service",
        endpoint="/process",
        status="failure",
        retry_count=retry_count,
        max_retries=max_retries,
        is_dead=False,  # will be computed
        timestamp=datetime.utcnow(),
        error_type="timeout"
    )


def main():
    print("\n🔧 Initializing DB...")
    init_db()

    print("\n🚀 Creating test events...\n")

    trace_id = str(uuid.uuid4())

    events = [
        generate_event(trace_id, 0, 3),
        generate_event(trace_id, 1, 3),
        generate_event(trace_id, 2, 3),
        generate_event(trace_id, 3, 3),  # should be CRITICAL
    ]

    for e in events:
        created = EventService.create_event(e)
        print(f"Event Stored → Retry: {created.retry_count}, Dead: {created.is_dead}, Severity: {created.severity}")

    print("\n📊 Fetching all events from DB...\n")

    rows = EventRepository.get_all_events()

    for row in rows:
        print(row)
    print(f"\nTotal events stored: {len(rows)}")

if __name__ == "__main__":
    main()