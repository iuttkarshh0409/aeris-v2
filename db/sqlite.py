import sqlite3
from datetime import datetime

DB_NAME = "aeris.db"


def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS events (
        event_id TEXT PRIMARY KEY,
        trace_id TEXT,

        service_name TEXT,
        endpoint TEXT,

        status TEXT,
        retry_count INTEGER,
        max_retries INTEGER,

        is_dead INTEGER,

        timestamp TEXT,

        error_type TEXT,
        severity TEXT,
        severity_reason TEXT
    )
    """)

    # Migration for existing users
    try:
        cursor.execute("ALTER TABLE events ADD COLUMN severity_reason TEXT")
    except:
        pass

    # Snapshots Table for historical auditability
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        risk_level TEXT,
        confidence TEXT,
        avg_retry_recent REAL,
        avg_retry_baseline REAL,
        dead_ratio_recent REAL,
        dead_ratio_baseline REAL,
        event_count INTEGER
    )
    """)

    conn.commit()
    conn.close()