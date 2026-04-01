from core.calculators import ReliabilityCalculators as calc
from typing import List, Dict, Optional

class HybridDetector:
    """Implement a calibrated multi-signal detection engine that combines weighted statistical signals."""

    @staticmethod
    def detect(
        drift_type: str,
        baseline_data: List[float],
        recent_data: List[float],
        recent_value: float,
        static_limit: float = None,
        rel_slope_threshold: float = 0.01,
        absolute_floor: float = 0.0 # Prevent noise on extremely low baselines
    ) -> Dict:
        # A. Statistical Constants
        # ------------------------
        mean = calc.mean(baseline_data)
        std = calc.std_dev(baseline_data, mean)
        baseline_p95 = max(calc.p95(baseline_data), absolute_floor)
        
        baseline_count = len(baseline_data)
        recent_count = len(recent_data)

        # Handle Empty Baseline to prevent division by zero
        safe_mean = mean if mean > 0.0001 else 1.0

        # B. Individual Signal Calculation
        # --------------------------------
        
        # 1. Z-Score (Sudden Anomaly)
        z = (recent_value - mean) / std if std > 0.0001 else (3.1 if recent_value > mean else 0.0)
        z_score_val = max(0, min(100, (z / 5.0) * 100)) if z > 2.0 else 0.0

        # 2. Relative Slope (Gradual Trend)
        slope = calc.calculate_slope(recent_data)
        rel_slope = slope / safe_mean
        trend_score = max(0, min(100, (abs(rel_slope) / rel_slope_threshold) * 50)) if abs(rel_slope) > rel_slope_threshold else 0.0

        # 3. Tail Risk (% Outliers)
        # CALIBRATION: Ratio > 3% OR count > 5 to catch rare but steady extreme failures
        outliers = calc.count_above_threshold(recent_data, baseline_p95)
        outlier_pct = outliers / recent_count if recent_count > 0 else 0.0
        
        # Boosted score to ensure it crosses the 40 point drift threshold on its own
        is_tail_drift = (outlier_pct > 0.03) or (outliers >= 5)
        tail_score = 90 if is_tail_drift else 0.0

        # 4. Static Breach (Absolute Safety)
        static_score = 100 if (static_limit and recent_value > static_limit) else 0.0

        # C. Weighted Scoring & Final Verdict
        # -----------------------------------
        # Increased tail weight to ensure standalone detection
        final_score = (static_score * 1.0) + (z_score_val * 0.7) + (trend_score * 0.5) + (tail_score * 0.8)
        
        signals = []
        if z_score_val > 40: signals.append("Z_SCORE_ANOMALY")
        if trend_score > 30: signals.append("GRADUAL_TREND_DRIFT")
        if tail_score > 40: signals.append("HEAVY_TAIL_RISK")
        if static_score > 0: signals.append("ABSOLUTE_LIMIT_BREACH")

        # Force drift if any specific signal is strong enough
        is_drift = final_score > 40 or len(signals) > 0
        
        severity = "STABLE"
        if final_score > 120 or static_score > 0: severity = "CRITICAL"
        elif final_score > 80: severity = "HIGH"
        elif final_score > 40: severity = "MEDIUM"

        # D. Signal Isolation & Debug Trace
        # ----------------------------------
        debug_trace = {
            "z_actual": round(z, 2),
            "rel_slope": round(rel_slope, 4),
            "outlier_pct": round(outlier_pct, 4),
            "extreme_count": outliers,
            "recent_count": recent_count,
            "baseline_count": baseline_count,
            "p95_threshold": round(baseline_p95, 2),
            "weighted_score": round(final_score, 1)
        }

        return {
            "drift_type": drift_type,
            "recent_value": round(recent_value, 2),
            "baseline_value": round(mean, 2),
            "is_drift": is_drift,
            "severity": severity,
            "signals_detected": signals,
            "debug": debug_trace
        }

class DeploymentDetector:
    """Detects version distribution shifts to correlate operational drift with software changes."""

    @staticmethod
    def detect(
        baseline_events: List[dict],
        recent_events: List[dict]
    ) -> Dict:
        if not recent_events:
            return {"drift_type": "DEPLOYMENT", "is_drift": False, "severity": "STABLE", "signals_detected": [], "score": 0.0, "reason": ""}

        # 1. Distribution Analysis
        baseline_v_list = [e.get("version", "unknown") for e in baseline_events]
        recent_v_list = [e.get("version", "unknown") for e in recent_events]
        
        baseline_freq = calc.calculate_frequencies(baseline_v_list)
        recent_freq = calc.calculate_frequencies(recent_v_list)

        # 2. Performance Analysis per Version
        baseline_stats = calc.calculate_metrics_per_version(baseline_events)
        recent_stats = calc.calculate_metrics_per_version(recent_events)

        signals = []
        score = 0.0
        reason_parts = []

        # Find the "Stable" baseline version (most frequent in baseline)
        stable_v = max(baseline_freq, key=baseline_freq.get) if baseline_freq else None
        
        # Tracking for the actual Root Cause
        root_v = None
        worst_impact_score = -1.0

        # Check all new versions for both arrival and impact
        for v in recent_freq:
            is_new = v not in baseline_freq and recent_freq[v] > 0.05
            v_stats = recent_stats[v]
            
            # Identify Root Cause by worst performance degradation
            if stable_v and stable_v in baseline_stats:
                s_stats = baseline_stats[stable_v]
                v_lat = v_stats["avg_latency"]
                s_lat = s_stats["avg_latency"]
                v_err = v_stats["dead_ratio"]
                s_err = s_stats["dead_ratio"]

                # Causal Score: combination of latency shift and error jump
                impact_score = (v_lat / s_lat if s_lat > 0 else 1.0) + (v_err * 10.0)
                if impact_score > worst_impact_score and v != stable_v:
                    worst_impact_score = impact_score
                    root_v = v

            if is_new:
                if "DEPLOYMENT_DRIFT" not in signals:
                    signals.append("DEPLOYMENT_DRIFT")
                score = max(score, 60.0) # Base deployment signal
                reason_parts.append(f"New version {v} detected ({round(recent_freq[v]*100, 1)}% traffic)")

                # CORRELATION: Check Impact against stable baseline
                if stable_v and stable_v in baseline_stats and v in recent_stats:
                    s_stats = baseline_stats[stable_v]
                    v_lat = v_stats["avg_latency"]
                    s_lat = s_stats["avg_latency"]
                    v_err = v_stats["dead_ratio"]
                    s_err = s_stats["dead_ratio"]
                    
                    # Latency Impact (2x jump)
                    is_bad_lat = v_lat > s_lat * 2.0 and v_lat > 100
                    # Error Impact (Absolute delta > 10%)
                    is_bad_err = v_err > s_err + 0.1

                    if is_bad_lat or is_bad_err:
                        signals.append("DEPLOYMENT_IMPACT")
                        
                        # Calculate attribution certainty (0-100%)
                        conf = calc.calculate_blame_confidence(v_stats, s_stats, recent_freq[v])
                        reason_parts.append(f"Blame Confidence: {conf}%")
                        
                        if is_bad_lat:
                            factor = round(v_lat / s_lat, 1) if s_lat > 0 else 99
                            reason_parts.append(f"{v} shows {factor}x higher latency than {stable_v}")
                        if is_bad_err:
                            reason_parts.append(f"{v} error rate {round(v_err*100)}% vs {stable_v} {round(s_err*100)}%")

                        # Escalate score based on confidence
                        score = max(score, 40 + (conf * 0.6)) 

        severity = "STABLE"
        if score > 90: severity = "CRITICAL"
        elif score > 75: severity = "HIGH"
        elif score > 40: severity = "MEDIUM"

        hypothesis = DeploymentDetector._generate_hypothesis(signals, reason_parts, score)

        return {
            "drift_type": "DEPLOYMENT",
            "is_drift": len(signals) > 0,
            "root_cause_version": root_v or stable_v or "N/A",
            "severity": severity,
            "signals_detected": signals,
            "score": score,
            "reason": " | ".join(reason_parts),
            "hypothesis": hypothesis,
            "debug": {
                "per_version_recent": recent_stats,
                "stable_baseline_version": stable_v
            }
        }

    @staticmethod
    def _generate_hypothesis(signals, reasons, score) -> str:
        # Confidence Tiering
        tier = "LOW (Speculative)"
        if score > 90: tier = "HIGH (Reliable)"
        elif score > 60: tier = "MEDIUM (Probable)"

        # 1. Summary Block
        if "DEPLOYMENT_IMPACT" in signals:
            summary = "CRITICAL: A regressive deployment is actively degrading system performance."
            action = "IMMEDIATE ROLLBACK RECOMMENDED for the identifying version."
        elif "DEPLOYMENT_DRIFT" in signals:
            summary = "WARNING: Significant version distribution shift detected without immediate p95 regression."
            action = "Monitor canary progression and check service-level health."
        else:
            summary = "ANOMALY: Operational drift detected without clear deployment correlation."
            action = "Inspect downstream dependencies and database connection health."

        # 2. Confidence Explanation
        conf_explain = "Capped at 95% to allow for statistical noise."
        if score < 60:
            conf_explain = "Attribution hindered by small sample size or conflicting performance signals."
        elif score < 95:
             conf_explain = "Strong correlation, but requires manual trace validation."

        return (
            f"--- OPERATIONAL BRIEF ---\n"
            f"SUMMARY: {summary}\n"
            f"CONFIDENCE: {score}% [{tier}] - {conf_explain}\n"
            f"ACTION: {action}\n"
            f"--------------------------"
        )
