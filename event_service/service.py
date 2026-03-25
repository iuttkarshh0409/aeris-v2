from schemas.event_schema import Event
from event_service.repository import EventRepository
from severity_engine.engine import SeverityEngine

class EventService:

    @staticmethod
    def create_event(event: Event):
        if event.retry_count < 0:
            raise ValueError("retry_count cannot be negative")

        if event.max_retries <= 0:
            raise ValueError("max_retries must be positive")

        # Compute is_dead
        event.is_dead = event.retry_count >= event.max_retries

        # Assign severity and logic trace
        event.severity, event.severity_reason = SeverityEngine.classify(event)

        # Store
        EventRepository.insert_event(event)

        return event