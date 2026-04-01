# scripts/test_tail.py
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from core.detectors import HybridDetector
from core.calculators import ReliabilityCalculators as calc

def test_tail_detection():
    detector = HybridDetector()

    # 1. Simulate RECENT window (10% outliers)
    recent_latencies = [50.0] * 90 + [10000.0] * 10
    recent_p95 = calc.p95(recent_latencies)

    # 2. Simulate BASELINE window (Clean)
    baseline_latencies = [50.0] * 100

    # 3. Call unified Hybrid Detector
    # absolute_floor=250.0 ensures we don't alert on 10ms noise
    result = detector.detect(
        drift_type="LATENCY_P95",
        baseline_data=baseline_latencies,
        recent_data=recent_latencies,
        recent_value=recent_p95,
        static_limit=2000.0,
        rel_slope_threshold=0.005,
        absolute_floor=250.0
    )

    print("\n" + "-"*70)
    print("AERIS TAIL-RISK VALIDATION TEST")
    print("-"*70)
    print(f"Verdict:   {result['severity']} (Drift: {result['is_drift']})")
    print(f"Signals:   {result['signals_detected']}")
    print(f"Score:     {result['debug']['weighted_score']}")
    print(f"Outliers:  {result['debug']['extreme_count']} (Ratio: {result['debug']['outlier_pct']*100}%)")
    print(f"Threshold: {result['debug']['p95_threshold']}ms")
    print("-"*70 + "\n")

if __name__ == "__main__":
    test_tail_detection()