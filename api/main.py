from fastapi import FastAPI
from schemas.event_schema import Event
from event_service.service import EventService
from event_service.repository import EventRepository
from drift_engine.engine import DriftEngine
from db.sqlite import init_db
from typing import Optional
from datetime import datetime


import threading
import time

app = FastAPI(title="AERIS V2")

# Autonomous Auditor: Snapshotting Logic (Section 14 of TDD)
def background_auditor(interval_seconds=60):
    print(f"🕵️  AERIS Autonomous Auditor Started (Interval: {interval_seconds}s)")
    while True:
        try:
            # We use a default 15m window for the snapshot analysis
            DriftEngine.save_snapshot(window_minutes=15)
        except Exception as e:
            print(f"Auditor Error: {e}")
        time.sleep(interval_seconds)

# Initialize DB and start Auditor on startup
@app.on_event("startup")
def startup():
    init_db()
    # Start the auditor in a daemon thread to not block the server
    thread = threading.Thread(target=background_auditor, daemon=True)
    thread.start()


@app.get("/")
def root():
    return {"message": "AERIS V2 is running"}


# 1. Create Event
@app.post("/events")
def create_event(event: Event):
    created_event = EventService.create_event(event)
    return {"event": created_event}


# 2. Get All Events
@app.get("/events")
def get_events(
    service_name: Optional[str] = None,
    endpoint: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None
):
    # Priority: time-based filtering
    if start_time and end_time:
        datetime.fromisoformat(start_time)
        events = EventRepository.get_events_by_time_range(start_time, end_time)

    # Otherwise use attribute filters
    elif service_name or endpoint:
        events = EventRepository.get_filtered_events(service_name, endpoint)

    else:
        events = EventRepository.get_all_events()

    formatted = [EventRepository.format_event(r) for r in events]
    return {"events": formatted}


# 3. Drift Analysis
@app.get("/drift")
def get_drift(window_size: int = 10):
    result = DriftEngine.analyze_drift(window_size)
    return result

@app.get("/drift/explain")
def explain_drift(window_size: int = 10):
    result = DriftEngine.explain_drift(window_size)
    return result

@app.post("/drift/snapshot")
def capture_snapshot(window_size: int = 15):
    result = DriftEngine.save_snapshot(window_size)
    return {"message": "Snapshot Captured", "result": result}

@app.get("/drift/history")
def get_snapshot_history(limit: int = 15):
    rows = DriftEngine.get_snapshots(limit)
    formatted = [
        {
            "id": r[0],
            "timestamp": r[1],
            "risk_level": r[2],
            "confidence": r[3],
            # Use raw column indexes based on snapshots table definition
            "recent_metrics": {"avg_retry": r[4], "dead_ratio": r[6]},
            "baseline_metrics": {"avg_retry": r[5], "dead_ratio": r[7]},
            "event_count": r[8]
        } for r in rows
    ]
    return {"drift_history": formatted}

@app.get("/analytics/severity")
def severity_distribution():
    data = EventRepository.get_severity_distribution()
    return {"severity_distribution": data}

@app.get("/analytics/services")
def service_overview(minutes: int = 15):
    data = EventRepository.get_service_health_summary(minutes)
    return {"service_health": data}