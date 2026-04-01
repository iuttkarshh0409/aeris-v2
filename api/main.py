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
            # Use a 10m recent vs 60m baseline window for the snapshot analysis
            DriftEngine.save_snapshot(recent_min=10, baseline_min=60)
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

    # Data is already formatted as dictionaries with named metrics by the Repository
    return {"events": events}


# 3. Drift Analysis
@app.get("/drift")
def get_drift(recent_min: int = 10, baseline_min: int = 60):
    result = DriftEngine.analyze_drift(recent_min, baseline_min)
    return result

@app.get("/drift/explain")
def explain_drift(recent_min: int = 10, baseline_min: int = 60):
    result = DriftEngine.explain_drift(recent_min, baseline_min)
    return result

@app.post("/drift/snapshot")
def capture_snapshot(recent_min: int = 10, baseline_min: int = 60):
    result = DriftEngine.save_snapshot(recent_min, baseline_min)
    return {"message": "Snapshot Captured", "result": result}

@app.get("/drift/history")
def get_snapshot_history(limit: int = 15):
    # Data is returned as structured dictionaries by DriftEngine.get_snapshots
    history = DriftEngine.get_snapshots(limit)
    return {"drift_history": history}

@app.get("/analytics/severity")
def severity_distribution():
    data = EventRepository.get_severity_distribution()
    return {"severity_distribution": data}

@app.get("/analytics/services")
def service_overview(minutes: int = 15):
    data = EventRepository.get_service_health_summary(minutes)
    return {"service_health": data}