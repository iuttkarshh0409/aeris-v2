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
        severity_reason TEXT,

        latency_ms REAL DEFAULT 0.0,
        error_code INTEGER DEFAULT 0,
        region TEXT DEFAULT 'unknown',
        version TEXT DEFAULT '1.0.0'
    )
    """)

    # --- Schema Migrations (Backward Compatibility) ---
    columns_to_add = {
        "severity_reason": "TEXT",
        "latency_ms": "REAL DEFAULT 0.0",
        "error_code": "INTEGER DEFAULT 0",
        "region": "TEXT DEFAULT 'unknown'",
        "version": "TEXT DEFAULT '1.0.0'"
    }

    for col, definition in columns_to_add.items():
        try:
            cursor.execute(f"ALTER TABLE events ADD COLUMN {col} {definition}")
        except sqlite3.OperationalError:
            # Column already exists
            pass

    # --- Performance & Data Integrity: Database Indexing ---
    # We use IF NOT EXISTS to prevent crashes on subsequent runs
    
    # 1. Index on service_name for fast lookups in drift windows
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_service ON events (service_name)")
    
    # 2. Index on timestamp for range queries in the Drift Engine
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events (timestamp)")
    
    # 3. Index on region for localized drift analysis optimization
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_region ON events (region)")

    # 4. Snapshots Table for historical auditability
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
    
    # Also index snapshots for trend querying performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_timestamp ON snapshots (timestamp)")

    conn.commit()
    conn.close()