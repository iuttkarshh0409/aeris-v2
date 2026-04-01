# cli/commands/explain.py
from drift_engine.engine import DriftEngine

def run():
    """Execution for the explain command."""
    # Run the drift engine and print the summary brief
    result = DriftEngine.analyze_drift()
    report = DriftEngine.explain_drift(result)
    
    print("\n" + "="*70)
    print(" AERIS DRIFT EXPLANATION")
    print("="*70)
    print(report["summary"])
    print("="*70 + "\n")
