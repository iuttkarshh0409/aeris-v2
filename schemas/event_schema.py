from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime, timezone

class Event(BaseModel):
    event_id: str
    trace_id: str
    service_name: str
    endpoint: str
    status: str
    retry_count: int
    max_retries: int
    is_dead: bool
    timestamp: datetime
    error_type: Optional[str] = "unknown"
    severity: Optional[str] = None
    severity_reason: Optional[str] = None

    # Performance & Context Fields (with strict defaults)
    latency_ms: float = 0.0
    error_code: int = 0
    region: str = "unknown"
    version: str = "unknown"

    @validator("timestamp", pre=True)
    def ensure_utc(cls, v):
        if isinstance(v, datetime):
            if v.tzinfo is None:
                return v.replace(tzinfo=timezone.utc)
            return v.astimezone(timezone.utc)
        return v

    @validator("latency_ms")
    def validate_latency(cls, v):
        if v < 0:
            raise ValueError("latency_ms must be non-negative")
        return v

    @validator("retry_count")
    def validate_retry(cls, v):
        if v < 0:
            raise ValueError("retry_count must be non-negative")
        return v

    @validator("error_code")
    def validate_error_code(cls, v):
        # Allow 0 for unknown/non-HTTP, but validate HTTP ranges
        if v < 0 or v > 999:
            raise ValueError("error_code out of physical range (0-999)")
        return v