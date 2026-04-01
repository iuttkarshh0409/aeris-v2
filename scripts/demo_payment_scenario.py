# scripts/demo_payment_scenario.py
import sys
import os
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from drift_engine.engine import DriftEngine

def run_demo():
    print("\n" + "="*80)
    print(" AERIS V2: ACADEMIC DEMONSTRATION - PAYMENT SERVICE SCENARIO")
    print("="*80)
    print("\n[DATA SOURCE EXPLANATION]")
    print("This demo analyzes synthetic application events. Each event represents a ")
    print("single customer transaction log containing metadata (Version, Region) ")
    print("and performance metrics (Latency, Errors, Retries).")
    
    # 1. Simulate Normal System (Baseline)
    print("\n[STEP 1] SIMULATING NORMAL SYSTEM (Baseline)")
    print("Steady state: Version v2.0 is processing payments at ~50ms with 0% errors.")
    baseline_events = [{
        "version": "v2.0", "latency_ms": 50.0, "is_dead": False, 
        "region": "us-east-1", "service_name": "payment-api", 
        "timestamp": "2026-04-01T10:00:00", "retry_count": 0
    } for _ in range(100)]
    time.sleep(1)

    # 2. Simulate Bad Deployment
    print("\n[STEP 2] DEPLOYING NEW VERSION v2.1")
    print("A canary deployment of v2.1 begins. Traffic is being shifted...")
    time.sleep(1)
    
    print("\n[STEP 3] SYSTEM DEGRADATION DETECTED")
    print("v2.1 is exhibiting abnormal latency (350ms) and intermittent failures.")
    recent_events = []
    for i in range(100):
        is_v21 = (i < 80) # 80% v2.1 dominance
        v = "v2.1" if is_v21 else "v2.0"
        lat = 350.0 if is_v21 else 50.0
        err = (i % 8 == 0) if is_v21 else False 
        recent_events.append({
            "version": v, "latency_ms": lat, "is_dead": err, 
            "region": "us-east-1", "service_name": "payment-api", 
            "timestamp": f"2026-04-01T11:0{i%10}:00", "retry_count": 0
        })

    # 3. Aeris Analysis
    print("\n[STEP 4] RUNNING AERIS CAUSAL ANALYSIS...")
    analysis = DriftEngine.calculate_drift_from_events(baseline_events, recent_events)
    brief = DriftEngine._generate_decision_safe_brief(analysis, recent_events)
    
    print(brief)

    # 4. Comparative Evaluation
    print("\n" + "-"*80)
    print(" COMPARATIVE EVALUATION")
    print("-" * 80)
    print("\n[WITHOUT AERIS]")
    print("  * SYMPTOMS: Dashboard shows 'Latency Spike'. Engineers begin manual log traces.")
    print("  * PROCESS:  SRE must cross-reference deployment timestamps with performance graphs.")
    print("  * OUTCOME:  High Time-to-Identify (TTI). Rollback delayed by manual verification.")
    
    print("\n[WITH AERIS]")
    print("  * SYMPTOMS: Aeris automatically correlates version shift with performance drift.")
    print("  * PROCESS:  Deterministic reasoning identifies v2.1 as the causal trigger.")
    print("  * OUTCOME:  Instant 'Decision-Safe' remediation brief. Immediate confidence to rollback.")
    print("-" * 80 + "\n")

if __name__ == "__main__":
    run_demo()
