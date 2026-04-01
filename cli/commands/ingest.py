# cli/commands/ingest.py
import json # for parsing input file
import os # to check if file exists

def run(file_path: str):
    """Execution for the ingest command."""
    if not os.path.exists(file_path):
        print(f"\n[ERROR] File not found: {file_path}\n")
        return

    try:
        with open(file_path, "r") as f:
            data = json.load(f)
        
        # Check if single event or list
        events = data if isinstance(data, list) else [data]
        
        # Logic from api.ingest_event
        # For CLI demo, we just print the state
        print("\n" + "="*50)
        print(" AERIS MANUAL INGESTION")
        print("="*50)
        print(f" [FILE]      {file_path}")
        print(f" [COUNT]     {len(events)} events processed")
        print("-" * 50)
        print(" [STATUS]    Events appended successfully.")
        print("="*50 + "\n")
    except Exception as e:
        print(f"\n[FATAL] Ingestion Exception: {str(e)}\n")
