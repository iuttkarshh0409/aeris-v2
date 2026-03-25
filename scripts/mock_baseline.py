from datetime import datetime, timedelta
import uuid
import random
from db.sqlite import get_connection

SERVICES = ["payment-service", "order-service"]

def insert_baseline_event(service, timestamp):
    conn = get_connection()
    cursor = conn.cursor()
    
    event_id = str(uuid.uuid4())
    # Baseline scenario: Stable (Retry 0-1)
    retry_count = random.randint(0, 1)
    max_retries = 3
    
    cursor.execute("""
    INSERT INTO events (
        event_id, trace_id, service_name, endpoint,
        status, retry_count, max_retries,
        is_dead, timestamp, error_type, severity, severity_reason
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        event_id, str(uuid.uuid4()), service, "/process",
        "failure", retry_count, max_retries,
        0, timestamp.isoformat(), "timeout", "LOW", "Baseline Mock"
    ))
    
    conn.commit()
    conn.close()

def mock_baseline(count=50):
    # 15 minutes ago (The T-20 to T-10 window)
    baseline_time = datetime.utcnow() - timedelta(minutes=15)
    
    print(f"📦 MOCKING BASELINE: Inserting {count} historical events around {baseline_time}...")
    
    for _ in range(count):
        service = random.choice(SERVICES)
        # Randomize timestamp slightly within the window
        ts = baseline_time + timedelta(seconds=random.randint(-120, 120))
        insert_baseline_event(service, ts)
    
    print("✅ Baseline created successfully. Now run your simulation/drift check!")

if __name__ == "__main__":
    mock_baseline()
