from pydantic import BaseModel
from typing import Optional
from datetime import datetime

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

    error_type: Optional[str]
    severity: Optional[str] = None
    severity_reason: Optional[str] = None