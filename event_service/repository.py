from db.sqlite import get_connection
from schemas.event_schema import Event
from datetime import datetime, timedelta



class EventRepository:

    @staticmethod
    def get_all_events():
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM events")
        rows = cursor.fetchall()

        conn.close()
        return rows

    @staticmethod
    def insert_event(event: Event):
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO events (
            event_id, trace_id, service_name, endpoint,
            status, retry_count, max_retries,
            is_dead, timestamp, error_type, severity, severity_reason
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event.event_id,
            event.trace_id,
            event.service_name,
            event.endpoint,
            event.status,
            event.retry_count,
            event.max_retries,
            int(event.is_dead),
            event.timestamp.isoformat(),
            event.error_type,
            event.severity,
            event.severity_reason
        ))

        conn.commit()
        conn.close()

    from datetime import datetime, timedelta


    @staticmethod
    def get_events_in_time_range(start_time: datetime, end_time: datetime):
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        SELECT * FROM events
        WHERE timestamp BETWEEN ? AND ?
        """, (
            start_time.isoformat(),
            end_time.isoformat()
        ))

        rows = cursor.fetchall()
        conn.close()

        return rows
    
    @staticmethod
    def get_recent_fault_count(service_name: str, minutes: int = 10):
        conn = get_connection()
        cursor = conn.cursor()

        start_time = datetime.utcnow() - timedelta(minutes=minutes)

        cursor.execute("""
        SELECT COUNT(*) FROM events
        WHERE service_name = ? AND timestamp >= ?
        """, (service_name, start_time.isoformat()))

        count = cursor.fetchone()[0]
        conn.close()

        return count
    
    @staticmethod
    def format_event(row):
        return {
            "event_id": row[0],
            "trace_id": row[1],
            "service_name": row[2],
            "endpoint": row[3],
            "status": row[4],
            "retry_count": row[5],
            "max_retries": row[6],
            "is_dead": bool(row[7]),
            "timestamp": row[8],
            "error_type": row[9],
            "severity": row[10],
            "severity_reason": row[11] if len(row) > 11 else None
        }
    
    @staticmethod
    def get_filtered_events(service_name=None, endpoint=None):
        conn = get_connection()
        cursor = conn.cursor()

        query = "SELECT * FROM events WHERE 1=1"
        params = []

        if service_name:
            query += " AND service_name = ?"
            params.append(service_name)

        if endpoint:
            query += " AND endpoint = ?"
            params.append(endpoint)

        cursor.execute(query, params)
        rows = cursor.fetchall()

        conn.close()
        return rows
    
    @staticmethod
    def get_events_by_time_range(start_time, end_time):
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        SELECT * FROM events
        WHERE timestamp BETWEEN ? AND ?
        """, (start_time, end_time))

        rows = cursor.fetchall()
        conn.close()

        return rows
    
    @staticmethod
    def get_severity_distribution():
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        SELECT severity, COUNT(*)
        FROM events
        GROUP BY severity
        """)

        rows = cursor.fetchall()
        conn.close()

        distribution = {
            "LOW": 0,
            "MEDIUM": 0,
            "HIGH": 0,
            "CRITICAL": 0
        }

        for severity, count in rows:
            if severity in distribution:
                distribution[severity] = count

        return distribution

    @staticmethod
    def get_service_health_summary(minutes: int = 15):
        from db.sqlite import get_connection
        from datetime import datetime, timedelta
        
        conn = get_connection()
        cursor = conn.cursor()

        start_time = datetime.utcnow() - timedelta(minutes=minutes)

        cursor.execute("""
        SELECT service_name, COUNT(*), AVG(retry_count), SUM(CASE WHEN is_dead = 1 THEN 1 ELSE 0 END)
        FROM events
        WHERE timestamp >= ?
        GROUP BY service_name
        """, (start_time.isoformat(),))

        rows = cursor.fetchall()
        conn.close()

        summary = {}
        for row in rows:
            name, count, avg_retry, dead_count = row
            summary[name] = {
                "faults": count,
                "avg_retry": round(avg_retry, 2) if avg_retry else 0.0,
                "dead_events": dead_count
            }

        return summary