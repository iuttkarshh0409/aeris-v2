import logging
from schemas.event_schema import Event
from event_service.repository import EventRepository
from severity_engine.engine import SeverityEngine

# Standardized logging for non-noisy ingestion monitoring
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AERIS-INGESTION")

class EventService:

    @staticmethod
    def create_event(event: Event):
        try:
            # 1. Reject impossible state exhausted by retry_count sanity
            if event.retry_count > event.max_retries and not event.is_dead:
                 logger.warning(f"Sanitization: Event {event.event_id} has invalid retry-dead coherence. Fixing...")
                 event.is_dead = True

            # 2. Compute is_dead (Deterministic logic)
            event.is_dead = event.is_dead or (event.retry_count >= event.max_retries)

            # 3. Assign intelligence-driven severity
            event.severity, event.severity_reason = SeverityEngine.classify(event)

            # 4. Storage Persistence
            EventRepository.insert_event(event)
            return event
            
        except Exception as e:
            logger.error(f"Ingest Failure: Event rejected due to payload integrity failure: {e}")
            raise