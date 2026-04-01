import math
from typing import List

class ReliabilityCalculators:
    @staticmethod
    def mean(data: List[float]) -> float:
        if not data:
            return 0.0
        return sum(data) / len(data)

    @staticmethod
    def std_dev(data: List[float], mean: float = None) -> float:
        if not data or len(data) < 2:
            return 0.0
        
        if mean is None:
            mean = ReliabilityCalculators.mean(data)
            
        variance = sum((x - mean) ** 2 for x in data) / len(data)
        return math.sqrt(variance)

    @staticmethod
    def percentile(data: List[float], p: float) -> float:
        """Calculate the p-th percentile using the nearest rank method."""
        if not data:
            return 0.0
        
        sorted_data = sorted(data)
        index = math.ceil((p / 100) * len(sorted_data)) - 1
        return sorted_data[max(0, min(index, len(sorted_data) - 1))]

    @staticmethod
    def p95(data: List[float]) -> float:
        return ReliabilityCalculators.percentile(data, 95)

    @staticmethod
    def calculate_slope(data: List[float]) -> float:
        """Calculate the average slope of a list of values over time."""
        if len(data) < 2:
            return 0.0
        
        # Simple linear fit gradient (intercept not needed for delta check)
        n = len(data)
        x = list(range(n))
        y = data
        
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(i*j for i, j in zip(x, y))
        sum_xx = sum(i*i for i in x)
        
        denominator = (n * sum_xx - sum_x**2)
        if abs(denominator) < 0.0001:
            return 0.0
            
        slope = (n * sum_xy - sum_x * sum_y) / denominator
        return slope

    @staticmethod
    def count_above_threshold(data: List[float], threshold: float) -> int:
        return sum(1 for x in data if x > threshold)

    @staticmethod
    def calculate_frequencies(data: List[str]) -> dict:
        """Calculate the percentage frequency of each unique item in the data."""
        if not data:
            return {}
        
        counts = {}
        for item in data:
            counts[item] = counts.get(item, 0) + 1
            
        total = len(data)
        return {item: count / total for item, count in counts.items()}

    @staticmethod
    def calculate_metrics_per_version(events: List[dict]) -> dict:
        """Group and calculate mean performance per version across any number of events."""
        if not events:
            return {}
        
        groups = {}
        for e in events:
            v = e.get("version", "unknown")
            if v not in groups:
                 groups[v] = {"latencies": [], "is_dead": []}
            groups[v]["latencies"].append(e["latency_ms"])
            groups[v]["is_dead"].append(1.0 if e["is_dead"] else 0.0)
            
        stats = {}
        for v, data in groups.items():
            stats[v] = {
                "avg_latency": ReliabilityCalculators.mean(data["latencies"]),
                "dead_ratio": ReliabilityCalculators.mean(data["is_dead"]),
                "count": len(data["latencies"])
            }
        return stats

    @staticmethod
    def calculate_blame_confidence(new_v_stats: dict, baseline_v_stats: dict, dominance_pct: float) -> float:
        """Calculate a 0-100 percentage of how confident we are that 'v_new' caused the drift."""
        # 1. Sample Size Weight (40%): Need at least 50 events for statistical stability
        n_count = new_v_stats.get("count", 0)
        n_weight = min(1.0, n_count / 50.0) * 40.0
        
        # 2. Deviation Magnitude Weight (40%): Size of jump (latency factor or error delta)
        n_lat = new_v_stats.get("avg_latency", 0)
        b_lat = baseline_v_stats.get("avg_latency", 1)
        lat_jump = (n_lat / max(b_lat, 1)) - 1.0 # 0.0 means no jump
        
        n_err = new_v_stats.get("dead_ratio", 0)
        b_err = baseline_v_stats.get("dead_ratio", 0)
        err_delta = (n_err - b_err)
        err_jump = err_delta * 10.0
        
        # Magnitude logic: If either jump is significant (>2x or +10%), magnitude is high
        magnitude = max(lat_jump / 1.0, err_jump) 
        m_weight = min(1.0, magnitude) * 40.0
        
        # 3. Dominance Weight (20%): If version is 80% of traffic, it's easier to blame
        d_weight = min(1.0, dominance_pct / 0.8) * 20.0
        
        score = n_weight + m_weight + d_weight

        # 4. Narrative Heuristics (Calibrations)
        # -------------------------------------
        # A. Contradiction Penalty (-15%): If Latency is bad but Errors are perfect (or vice versa)
        # This signals it might be an isolated bug, not a systemic deployment failure.
        is_bad_lat = lat_jump > 1.0
        is_bad_err = err_delta > 0.05
        if (is_bad_lat and not is_bad_err) or (is_bad_err and not is_bad_lat):
            score -= 15.0

        # B. Temporal Consistency Boost (+10%): If both signals degrade together
        if is_bad_lat and is_bad_err:
            score += 10.0

        # C. 95% Ceiling: Absolute certainty is statistically impossible
        score = min(95.0, max(0.0, score))
        
        return round(score, 1)

    @staticmethod
    def reconstruct_timeline(events: List[dict]) -> List[dict]:
        """Bin events by minute to see the temporal progression of a drift event."""
        if not events:
            return []
            
        bins = {}
        for e in events:
            # Assume timestamp is ISO or epoch, truncate to minute
            ts = e["timestamp"]
            if isinstance(ts, str):
                minute = ts[:16] # "YYYY-MM-DDTHH:MM"
            else:
                 minute = "unknown"
            
            if minute not in bins:
                bins[minute] = {"latencies": [], "versions": [], "errors": 0}
            
            bins[minute]["latencies"].append(e["latency_ms"])
            bins[minute]["versions"].append(e["version"])
            if e["is_dead"]: bins[minute]["errors"] += 1
            
        timeline = []
        for m in sorted(bins.keys()):
            b = bins[m]
            # Find dominant version
            v_counts = {}
            for v in b["versions"]: v_counts[v] = v_counts.get(v, 0) + 1
            dom_v = max(v_counts, key=v_counts.get) if v_counts else "unknown"
            
            timeline.append({
                "minute": m,
                "avg_latency": ReliabilityCalculators.mean(b["latencies"]),
                "error_rate": b["errors"] / len(b["latencies"]),
                "dominant_version": dom_v,
                "count": len(b["latencies"])
            })
        return timeline

    @staticmethod
    def detect_drift_phase(data: List[float], threshold: float, dominance: float) -> str:
        """Categorize signal progression using magnitude, slope, and dominance."""
        if not data or len(data) < 5: return "ONSET (Initializing)"
        
        recent_slope = ReliabilityCalculators.calculate_slope(data[-5:])
        avg_v = ReliabilityCalculators.mean(data[-5:])
        
        # SATURATION: High magnitude, High Traffic, Stabilized Slope
        if avg_v > threshold * 1.5 and dominance > 0.5 and abs(recent_slope) < 0.05:
            return "SATURATION (Service Plateau)"
        
        # ESCALATION: Positive Slope, Significant Traffic
        if recent_slope > 0.05 or dominance > 0.3:
            return "ESCALATION (Increasing Impact)"
            
        return "ONSET (Initial Detection)"

    @staticmethod
    def identify_stability_anchors(events: List[dict], fields: List[str]) -> List[str]:
        """Identify what did NOT change (invariants) to narrow down root cause."""
        if not events: return []
        
        anchors = []
        for f in fields:
            vals = set(e.get(f) for e in events if e.get(f) is not None)
            if len(vals) == 1:
                anchors.append(f"{f} [{list(vals)[0]}]")
        return anchors

    @staticmethod
    def calculate_counterfactual_recovery(recent_stats: dict, b_stats: dict, v_impacted: str, stable_v: str) -> dict:
        """Estimate the performance delta range if the offending version was removed."""
        if v_impacted not in recent_stats or stable_v not in b_stats:
            return {"lat_range": [0,0], "err_range": [0,0]}
            
        target_lat = b_stats[stable_v]["avg_latency"]
        current_lat = recent_stats[v_impacted]["avg_latency"]
        
        # Bounded range (0.9 to 1.1 factor)
        lat_delta = current_lat - target_lat
        err_delta = recent_stats[stable_v]["dead_ratio"] if stable_v in recent_stats else 0.0
        current_err = recent_stats[v_impacted]["dead_ratio"]
        err_reduction = (current_err - err_delta) * 100
        
        return {
            "lat_range": [round(lat_delta * 0.9, 1), round(lat_delta * 1.1, 1)],
            "err_range": [round(err_reduction * 0.9, 1), round(err_reduction * 1.1, 1)]
        }

    @staticmethod
    def calculate_anchor_confidence(events: List[dict], field: str, value: any) -> float:
        """Calculate how 'sticky' an anchor is. (95%+ across failures = highly certain)"""
        if not events: return 0.0
        failures = [e for e in events if e.get("latency_ms", 0) > 100 or e.get("is_dead")]
        if not failures: return 0.0
        counts = sum(1 for e in failures if e.get(field) == value)
        return round((counts / len(failures)) * 100, 1)

    @staticmethod
    def classify_failure_mode(signals: List[str]) -> str:
        """Deterministically classify the incident into a known SRE failure mode."""
        if "DEPLOYMENT_IMPACT" in signals: return "DEPLOYMENT_REGRESSION"
        if "RETRY_PRESSURE" in signals and "DEAD_EVENT_RATIO" in signals: return "RETRY_STORM"
        if "LATENCY_P95" in signals: return "LATENCY_EROSION"
        if "SILENT_FAILURE" in signals: return "SILENT_FAILURE"
        return "UNKNOWN_DRIFT"

    @staticmethod
    def calculate_reversibility(action: str) -> str:
        """Estimate the reversibility level of the proposed remediation."""
        if "ROLLBACK" in action: return "HIGH (Standard)"
        if "DRAIN" in action or "REDIRECTION" in action: return "MEDIUM (Traffic stateful)"
        return "LOW (State mutation)"

    @staticmethod
    def detect_conflicts(lat_dir: str, err_dir: str, ret_dir: str) -> str:
        """Detect conflicting directional trends to warn against overconfidence."""
        # 1. PRISTINE Logic: All non-STABLE signals moving in the same direction
        non_stable = []
        if lat_dir != "STABLE": non_stable.append(("LATENCY", lat_dir))
        if err_dir != "STABLE": non_stable.append(("ERROR RATE", err_dir))
        if ret_dir != "STABLE": non_stable.append(("RETRY", ret_dir))
        
        if not non_stable: return "NONE (Signals Stable)"
        
        # Check if all moving same way (e.g. all UP)
        first_dir = non_stable[0][1]
        all_aligned = all(d[1] == first_dir for d in non_stable)
        
        if all_aligned: return "NONE (Signals Align)"
        
        # 2. DIVERGENT Logic: Opposite directions detected
        # Identify the primary conflict
        conflict_msg = []
        if lat_dir == "UP" and err_dir == "STABLE": conflict_msg = "LATENCY ^ vs ERROR RATE stable"
        elif err_dir == "UP" and lat_dir == "STABLE": conflict_msg = "ERROR RATE ^ vs LATENCY stable"
        elif ret_dir == "UP" and lat_dir == "DOWN": conflict_msg = "RETRY ^ vs LATENCY v"
        else:
             conflict_msg = f"{non_stable[0][0]} {non_stable[0][1]} vs {non_stable[1][0]} {non_stable[1][1]}"
             
        return f"DIVERGENT: {conflict_msg}"

    @staticmethod
    def verify_integrity(events: List[dict], has_conflicts: bool) -> str:
        """Confirm dataset completeness for decision safety."""
        if not events: return "CRITICAL (No signal)"
        missing = [e for e in events if not e.get("version") or not e.get("region")]
        is_incomplete = len(missing) > len(events) * 0.1
        
        if is_incomplete: return "PARTIAL (Incomplete metadata)"
        if has_conflicts: return "RELIABLE (Divergent Telemetry)"
        return "PRISTINE (Aligned Signals)"
