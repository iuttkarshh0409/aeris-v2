# cli/commands/logs.py
from drift_engine.engine import DriftEngine

def run(limit: int):
    """Execution for the logs command."""
    # Fetch recent events (last 60 mins) with a count-based display limit
    baseline, shown_events, total_count = DriftEngine.fetch_window_events(60, 0, limit=limit)
    
    # Format and print logs with fixed width
    print("\n" + "="*80)
    print(f" AERIS v2 EVENT LOGS (Showing {len(shown_events)} of {total_count} events)")
    print("="*80)
    print(f"{'TIMESTAMP':<22} | {'VERSION':<8} | {'LAT(ms)':<8} | {'ERR':<6}")
    print("-" * 80)
    
    for e in shown_events:
        err = 1 if e["is_dead"] else 0
        ts = e.get("timestamp", "UNKNOWN")[:16]
        print(f"{ts:<22} | {e['version']:<8} | {e['latency_ms']:<8.0f} | {err:<6}")
    print("="*80 + "\n")
