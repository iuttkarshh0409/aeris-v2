# cli/commands/status.py
from drift_engine.engine import DriftEngine

def run():
    """Execution for the status command."""
    # Run a quick analysis to get current risk and confidence
    result = DriftEngine.analyze_drift()
    
    # Logic for Last Incident
    last_incident = "NONE"
    if result["risk_level"] != "STABLE":
        baseline, recent, total = DriftEngine.fetch_window_events(1, 0)
        if recent:
            last_incident = recent[0].get("timestamp", "UNKNOWN")[:16]

    conf_score = result.get("confidence_score", 0)
    label = "LOW"
    if conf_score > 90: label = "HIGH"
    elif conf_score >= 60: label = "MEDIUM"

    # Format and print the system state
    print("\n" + "="*50)
    print(f" AERIS v2 SYSTEM STATUS  ")
    print("="*50)
    print(f" [RISK]           {result['risk_level']}")
    print(f" [CONFIDENCE]     {round(conf_score)}% ({label})")
    print(f" [ACTIVE SIGNALS] {len(result['signals'])}")
    print(f" [LAST INCIDENT]  {last_incident}")
    print("-" * 50)
    print("="*50 + "\n")
