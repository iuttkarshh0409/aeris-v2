from datetime import datetime, timedelta
from event_service.repository import EventRepository
from core.calculators import ReliabilityCalculators as calc
from core.detectors import HybridDetector, DeploymentDetector

class DriftEngine:
    
    @staticmethod
    def get_windows(recent_min=10, baseline_min=60):
        now = datetime.utcnow()
        recent_start = now - timedelta(minutes=recent_min)
        # Baseline is longer window to establish statistically sound normal
        baseline_start = now - timedelta(minutes=baseline_min)

        return {
            "baseline": (baseline_start, recent_start),
            "recent": (recent_start, now)
        }
    
    @staticmethod
    def fetch_window_events(recent_min=10, baseline_min=60, limit=None):
        windows = DriftEngine.get_windows(recent_min, baseline_min)

        baseline_events = EventRepository.get_events_in_time_range(
            windows["baseline"][0],
            windows["baseline"][1]
        )

        recent_events = EventRepository.get_events_in_time_range(
            windows["recent"][0],
            windows["recent"][1]
        )

        if limit:
            return baseline_events, recent_events[:limit], len(recent_events)
        return baseline_events, recent_events, len(recent_events)
    
    @staticmethod
    def _extract_metrics(events):
        if not events:
            return {
                "avg_retry": 0.0, "dead_ratio": 0.0, "p95_latency": 0.0,
                "retry_counts": [], "dead_flags": [], "latencies": [],
                "count": 0
            }

        retry_counts = [e["retry_count"] for e in events]
        dead_flags = [1.0 if e["is_dead"] else 0.0 for e in events]
        latencies = [e["latency_ms"] for e in events]
        count = len(events)

        return {
            "avg_retry": calc.mean(retry_counts),
            "dead_ratio": calc.mean(dead_flags),
            "p95_latency": calc.p95(latencies),
            "retry_counts": retry_counts,
            "dead_flags": dead_flags,
            "latencies": latencies,
            "count": count
        }
    
    @staticmethod
    def calculate_drift_from_events(baseline_raw, recent_raw):
        baseline = DriftEngine._extract_metrics(baseline_raw)
        recent = DriftEngine._extract_metrics(recent_raw)

        # 1. Retry Pressure Drift (Metric: Avg)
        retry_report = HybridDetector.detect(
            drift_type="RETRY_PRESSURE",
            baseline_data=baseline["retry_counts"],
            recent_data=recent["retry_counts"],
            recent_value=recent["avg_retry"],
            static_limit=2.5,
            rel_slope_threshold=0.05,
            absolute_floor=1.0 
        )

        # 2. Dead Event Ratio Drift (Metric: Ratio)
        dead_report = HybridDetector.detect(
            drift_type="DEAD_EVENT_RATIO",
            baseline_data=baseline["dead_flags"],
            recent_data=recent["dead_flags"],
            recent_value=recent["dead_ratio"],
            static_limit=0.4,
            rel_slope_threshold=0.02,
            absolute_floor=0.05 
        )

        # 3. Latency Drift (Metric: p95)
        latency_report = HybridDetector.detect(
            drift_type="LATENCY_P95",
            baseline_data=baseline["latencies"],
            recent_data=recent["latencies"],
            recent_value=recent["p95_latency"],
            static_limit=2000.0,
            rel_slope_threshold=0.005,
            absolute_floor=250.0 
        )

        # 4. Deployment Drift (Version & Performance Correlation)
        deploy_report = DeploymentDetector.detect(
            baseline_events=baseline_raw,
            recent_events=recent_raw
        )

        # Aggregated Risk is the max severity among metrics
        drift_reports = [retry_report, dead_report, latency_report, deploy_report]
        
        is_drift_found = any(d["is_drift"] for d in drift_reports)
        severity_map = {"STABLE": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
        max_severity = max(drift_reports, key=lambda x: severity_map.get(x["severity"], 0))

        min_events = min(baseline["count"], recent["count"])
        conf_score = min(100.0, (min_events / 50.0) * 100.0)

        return {
            "baseline": baseline,
            "recent": recent,
            "signals": drift_reports,
            "global_risk": max_severity["severity"],
            "is_drifting": is_drift_found,
            "confidence": "HIGH" if min_events >= 50 else "MEDIUM" if min_events >= 20 else "LOW",
            "confidence_score": conf_score
        }

    @staticmethod
    def calculate_drift(recent_min=10, baseline_min=60):
        baseline_raw, recent_raw = DriftEngine.fetch_window_events(recent_min, baseline_min)
        return DriftEngine.calculate_drift_from_events(baseline_raw, recent_raw)
    
    @staticmethod
    def calculate_confidence(baseline, recent):
        # CALIBRATION: Need 50+ events for statistical stability (HIGH)
        # 20+ for MEDIUM, else LOW
        min_events = min(baseline["count"], recent["count"])
        if min_events >= 50: return "HIGH"
        if min_events >= 20: return "MEDIUM"
        return "LOW"
    
    @staticmethod
    def _get_direction(recent, baseline, threshold=0.05) -> str:
        """Helper to determine the directional trend of a metric."""
        if recent > (baseline * (1 + threshold)): return "UP"
        if recent < (baseline * (1 - threshold)): return "DOWN"
        return "STABLE"

    @staticmethod
    def _generate_decision_safe_brief(drift_data, recent_events) -> str:
        """Structured decision-support HUD for SREs. Single source of actionable truth."""
        reports = drift_data["signals"]
        count = drift_data["recent"]["count"]
        
        # 1. Component Analysis
        latencies = [e["latency_ms"] for e in recent_events]
        all_sigs = [s for r in reports if r["is_drift"] for s in r["signals_detected"]]
        
        # Deployment Stats
        deploy_rpt = next((r for r in reports if r["drift_type"] == "DEPLOYMENT"), None)
        dominance, recovery, v_tag = 0.0, {"lat_range": [0,0], "err_range": [0,0]}, "N/A"
        if deploy_rpt and deploy_rpt["is_drift"]:
            stats = deploy_rpt["debug"].get("per_version_recent", {})
            v_tag = deploy_rpt.get("root_cause_version", "v2.1")
            stable_v = deploy_rpt["debug"].get("stable_baseline_version", "v2.0")
            dominance = (stats.get(v_tag, {}).get("count", 0) / count) if count > 0 else 0.0
            recovery = calc.calculate_counterfactual_recovery(stats, stats, v_tag, stable_v)

        # Health & State Logic: Directions
        lat_dir = DriftEngine._get_direction(drift_data["recent"]["p95_latency"], drift_data["baseline"]["p95_latency"])
        err_dir = DriftEngine._get_direction(drift_data["recent"]["dead_ratio"], drift_data["baseline"]["dead_ratio"])
        ret_dir = DriftEngine._get_direction(drift_data["recent"]["avg_retry"], drift_data["baseline"]["avg_retry"])
        
        conflicts = calc.detect_conflicts(lat_dir, err_dir, ret_dir)
        has_conflicts = "DIVERGENT" in conflicts
        integrity = calc.verify_integrity(recent_events, has_conflicts)
        phase = calc.detect_drift_phase(latencies, drift_data["baseline"]["p95_latency"], dominance)
        anchors = calc.identify_stability_anchors(recent_events, ["region", "service_name"])
        
        # Confidence Cap (Safety Requirement)
        display_conf = round(min(95.0, drift_data.get("confidence_score", 0)))

        # 2. Decision Engine Logic
        blast_radius = round(dominance * 100)
        risk = drift_data['global_risk']
        conf = display_conf
        
        # A. Risk If Wrong & Experimentation Matrix
        if blast_radius >= 60 or risk == "CRITICAL":
            risk_if_wrong = "High user impact if misattributed"
            experimentation = "DISABLED"
        elif 30 <= blast_radius < 60:
            risk_if_wrong = "Moderate impact, controlled intervention advised"
            experimentation = "LIMITED (only staged rollback)"
        else:
            risk_if_wrong = "Low impact, safe to experiment"
            experimentation = "ENABLED"

        # B. Consistency Overrides
        if conf < 60:
            risk_if_wrong += " (Low confidence - validate before action)"
            
        gate = "APPROVAL REQUIRED" if (blast_radius > 60 or risk == "CRITICAL") else "PERMITTED (AUTO-SAFE)"
        reversibility = calc.calculate_reversibility("ROLLBACK" if dominance > 0 else "INSPECT")
        
        # Action Refinement
        action = "IMMEDIATE ROLLBACK" if dominance > 0 else "INSPECT INFRASTRUCTURE"
        if conf > 90 and 0 < blast_radius < 40:
            action = "SAFE AND RECOMMENDED TO ACT IMMEDIATELY"

        # C. Strict Attribution Guard (Fallback for UNKNOWN_DRIFT)
        mode = calc.classify_failure_mode(all_sigs)
        is_unknown = (v_tag == "N/A" or mode == "UNKNOWN_DRIFT")
        
        if is_unknown:
            action = "INVESTIGATE SYSTEM / INFRASTRUCTURE"
            gate = "PERMITTED (DIAGNOSTIC MODE)"
            prediction_text = "No actionable rollback target identified"
            simple_explanation = [
                f" [SIMPLE EXPLANATION]",
                f"  * WHAT:    A system anomaly has been detected.",
                f"  * WHY:     The system is experiencing abnormal behavior, but no single root cause has been confidently identified.",
                f"  * NEXT:    Investigate infrastructure, dependencies, or external factors.",
            ]
        else:
            prediction_text = f"If {v_tag} removed: {recovery['lat_range']}ms lat | {recovery['err_range']}% err"
            action_desc = "immediate rollback" if dominance > 0 else "infrastructure inspection"
            simple_explanation = [
                f" [SIMPLE EXPLANATION]",
                f"  * WHAT:    A {mode.lower().replace('_', ' ')} incident is occurring.",
                f"  * WHY:     New version {v_tag} is causing degraded performance and reliability.",
                f"  * NEXT:    Perform an {action_desc} of the primary root cause.",
            ]

        # 5. Format Structured Brief (Strict Section Order)
        w = 70
        divider = "=" * w
        sub_div = "-" * w
        
        brief = [
            f"\n{divider}",
            f" [SHIELD]  AERIS DECISION-SAFE BRIEF",
            f"{divider}",
            f" [SYSTEM STATE]      RISK: {risk:<12} | CONFIDENCE: {conf}%",
            f" [ROOT CAUSE]        VERSION: {v_tag:<9} | MODE: {mode}",
            f" [SIGNAL HEALTH]     INTEGRITY: {integrity:<8} | CONFLICTS: {conflicts}",
            f" [DRIFT PHASE]       {phase}",
            f"{sub_div}",
            f" [IMPACT ANALYTICS]",
            f"  * BLAST RADIUS:    {blast_radius}% of traffic impacted",
            f"  * ANCHORS:         {' | '.join(anchors) if anchors else 'No invariants'}",
            f"{sub_div}",
            f" [PREDICTION]",
            f"  * RECOVERY (PROJECTED): {prediction_text}",
            f"{sub_div}",
            f" [DECISION ENGINE]",
            f"  * ACTION:          {action}",
            f"  * POLICY GATE:     {gate}",
            f"  * REVERSIBILITY:   {reversibility}",
            f"  * RISK IF WRONG:   {risk_if_wrong}",
            f"  * EXPERIMENTATION: {experimentation}",
            f"{sub_div}",
        ] + simple_explanation + [
            f"{divider}",
            f" [STOP] CAUSATION DISCLAIMER: Statistical correlation based on temporal onset.",
            f"    High confidence != absolute proof. Verify before intervention.",
            f"{divider}\n"
        ]
        return "\n".join(brief)

    @staticmethod
    def analyze_drift(recent_min=10, baseline_min=60):
        baseline_raw, recent_raw, recent_total = DriftEngine.fetch_window_events(recent_min, baseline_min)
        drift_data = DriftEngine.calculate_drift_from_events(baseline_raw, recent_raw)
        
        reasons = []
        for signal in drift_data["signals"]:
            if signal["is_drift"]:
                sigs_str = ", ".join(signal["signals_detected"])
                
                if signal["drift_type"] == "DEPLOYMENT":
                    # Deployment specific formatting
                    reasons.append(
                        f"{signal['drift_type']} ({signal['severity']}) -> [{sigs_str}]: {signal['reason']}"
                    )
                else:
                    # Hybrid (Statistical) signal formatting
                    db = signal["debug"]
                    reasons.append(
                        f"{signal['drift_type']} ({signal['severity']}) -> [{sigs_str}]. "
                        f"Traces: [Z={db['z_actual']}, Slope={db['rel_slope']}, Tail={db['outlier_pct']} "
                        f"(found {db['extreme_count']} > threshold {db['p95_threshold']})]. "
                        f"Baseline={signal['baseline_value']}, Recent={signal['recent_value']}"
                    )

        return {
            "baseline": drift_data["baseline"],
            "recent": drift_data["recent"],
            "risk_level": drift_data["global_risk"],
            "confidence": drift_data["confidence"],
            "confidence_score": drift_data["confidence_score"],
            "reason": reasons,
            "signals": drift_data["signals"],
            "decision_safe_hud": DriftEngine._generate_decision_safe_brief(drift_data, recent_raw)
        }

    @staticmethod
    def save_snapshot(recent_min=15, baseline_min=60):
        analysis = DriftEngine.analyze_drift(recent_min=recent_min, baseline_min=baseline_min)
        
        from db.sqlite import get_connection
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO snapshots (
            timestamp, risk_level, confidence,
            avg_retry_recent, avg_retry_baseline,
            dead_ratio_recent, dead_ratio_baseline,
            event_count
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.utcnow().isoformat(),
            analysis["risk_level"],
            analysis["confidence"],
            analysis["recent"]["avg_retry"],
            analysis["baseline"]["avg_retry"],
            analysis["recent"]["dead_ratio"],
            analysis["baseline"]["dead_ratio"],
            analysis["recent"]["count"]
        ))
        
        conn.commit()
        conn.close()
        return analysis

    @staticmethod
    def format_snapshot(row):
        """Map database row to a structured dictionary (Named Access)"""
        return {
            "id": row[0],
            "timestamp": row[1],
            "risk_level": row[2],
            "confidence": row[3],
            "recent_metrics": {"avg_retry": row[4], "dead_ratio": row[6]},
            "baseline_metrics": {"avg_retry": row[5], "dead_ratio": row[7]},
            "event_count": row[8]
        }

    @staticmethod
    def get_snapshots(limit=10):
        from db.sqlite import get_connection
        conn = get_connection()
        cursor = conn.cursor()

        # Explicit column ordering for robust named-mapping
        columns = "id, timestamp, risk_level, confidence, avg_retry_recent, avg_retry_baseline, dead_ratio_recent, dead_ratio_baseline, event_count"
        cursor.execute(f"SELECT {columns} FROM snapshots ORDER BY id DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        
        conn.close()
        return [DriftEngine.format_snapshot(row) for row in rows]
    
    

    @staticmethod
    def explain_drift(result):
        """Translate raw drift analysis into a human-readable summary brief."""
        risk = result["risk_level"]
        confidence = result["confidence"]

        if result["baseline"]["count"] == 0 or result["recent"]["count"] == 0:
            return {
                "summary": "Insufficient data to analyze system drift.",
                "risk_level": "UNKNOWN",
                "confidence": "LOW",
                "details": [],
                "raw": result
            }

        explanations = []
        for signal in result["signals"]:
            if signal["is_drift"]:
                sigs = ", ".join(signal["signals_detected"])
                if signal["drift_type"] == "DEPLOYMENT":
                    explanations.append(f"{signal['drift_type']} ({signal['severity']}) -> [{sigs}]: {signal['reason']}")
                else:
                    db = signal["debug"]
                    explanations.append(
                        f"{signal['drift_type']} ({signal['severity']}) -> [{sigs}]. "
                        f"Traces: [Z={db['z_actual']}, Slope={db['rel_slope']}, Tail={db['outlier_pct']}]"
                    )

        summary = (
            f"System risk is {risk} with {confidence} confidence. "
            + (" ".join(explanations) if explanations else "No significant drift detected across retry, dead-event, or latency signals.")
        )
        
        brief = result.get("decision_safe_hud")
        if brief:
            summary += "\n\n" + brief

        return {
            "summary": summary,
            "risk_level": risk,
            "confidence": confidence,
            "details": explanations,
            "raw": result
        }


if __name__ == "__main__":
    import os
    from event_service.repository import EventRepository
    
    # 🎨 Visual Style
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    
    # Fetch all data
    analysis = DriftEngine.explain_drift(recent_min=15, baseline_min=60)
    sev_dist = EventRepository.get_severity_distribution()
    svc_health = EventRepository.get_service_health_summary(minutes=15)
    
    print("\n" + "═"*70)
    print(f"{BOLD}{HEADER} 🛡️  AERIS SYSTEM HEALTH DASHBOARD V2{ENDC}")
    print("═"*70)
    
    # 1. Global Risk Section
    risk_color = {"HIGH": FAIL, "MEDIUM": WARNING, "LOW": OKGREEN}.get(analysis["risk_level"], "")
    conf_color = {"HIGH": OKGREEN, "MEDIUM": WARNING, "LOW": FAIL}.get(analysis["confidence"], "")
    print(f"\n{BOLD}GLOBAL RISK ASSESSMENT:{ENDC} {risk_color}{analysis['risk_level']}{ENDC} | {BOLD}CONFIDENCE:{ENDC} {conf_color}{analysis['confidence']}{ENDC}")
    print(f"{BOLD}SUMMARY:{ENDC} {analysis['summary']}")
    
    # 2. Severity Distribution Section
    print(f"\n{OKCYAN}🧬 SEVERITY HEATMAP (All Time){ENDC}")
    for sev, count in sev_dist.items():
        color = {"CRITICAL": FAIL, "HIGH": WARNING, "MEDIUM": OKCYAN, "LOW": OKGREEN}.get(sev, "")
        bar = "█" * min(20, count)
        print(f" {sev:<9} | {color}{bar:<20}{ENDC} {count}")

    # 3. Service Context Section
    if svc_health:
        print(f"\n{OKCYAN}📊 TOP SERVICE CLUSTERS (Last 15m){ENDC}")
        print("-" * 70)
        print(f"{'Service':<25} | {'Faults':<8} | {'Avg Retry':<10} | {'Dead Events'}")
        print("-" * 70)
        for svc, stats in svc_health.items():
            f_color = FAIL if stats['faults'] > 20 else WARNING if stats['faults'] > 5 else ""
            print(f"{svc:<25} | {f_color}{stats['faults']:<8}{ENDC} | {stats['avg_retry']:<10} | {stats['dead_events']}")
    
    # 4. Drift Root Causes
    if analysis["details"]:
        print(f"\n{WARNING}🔍 DRIFT ROOT CAUSES:{ENDC}")
        for d in analysis["details"]:
            print(f"  • {d}")
    
    print("\n" + "═"*70 + "\n")

    
    