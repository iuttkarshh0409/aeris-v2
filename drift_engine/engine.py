from datetime import datetime, timedelta
from event_service.repository import EventRepository


class DriftEngine:
    

    @staticmethod
    def get_windows(window_size_minutes=10):
        now = datetime.utcnow()

        recent_start = now - timedelta(minutes=window_size_minutes)
        baseline_start = now - timedelta(minutes=2 * window_size_minutes)

        return {
            "baseline": (baseline_start, recent_start),
            "recent": (recent_start, now)
        }
    
    @staticmethod
    def fetch_window_events(window_size_minutes=10):
        windows = DriftEngine.get_windows(window_size_minutes)

        baseline_events = EventRepository.get_events_in_time_range(
            windows["baseline"][0],
            windows["baseline"][1]
        )

        recent_events = EventRepository.get_events_in_time_range(
            windows["recent"][0],
            windows["recent"][1]
        )

        return baseline_events, recent_events
    
    @staticmethod
    def _extract_metrics(events):
        if not events:
            return {
                "avg_retry": 0,
                "dead_ratio": 0,
                "count": 0
            }

        total_retry = 0
        dead_count = 0

        for e in events:
            retry_count = e[5]      # retry_count column
            is_dead = e[7]          # is_dead column

            total_retry += retry_count
            if is_dead:
                dead_count += 1

        count = len(events)

        return {
            "avg_retry": total_retry / count,
            "dead_ratio": dead_count / count,
            "count": count
        }
    
    @staticmethod
    def calculate_drift(window_size_minutes=10):
        baseline_events, recent_events = DriftEngine.fetch_window_events(window_size_minutes)

        baseline_metrics = DriftEngine._extract_metrics(baseline_events)
        recent_metrics = DriftEngine._extract_metrics(recent_events)

        drift = {
            "retry_pressure_change": recent_metrics["avg_retry"] - baseline_metrics["avg_retry"],
            "dead_ratio_change": recent_metrics["dead_ratio"] - baseline_metrics["dead_ratio"],
            "event_volume_change": recent_metrics["count"] - baseline_metrics["count"]
        }

        return {
            "baseline": baseline_metrics,
            "recent": recent_metrics,
            "drift": drift
        }
    
    @staticmethod
    def classify_drift(drift_metrics):
        retry_change = drift_metrics["retry_pressure_change"]
        dead_change = drift_metrics["dead_ratio_change"]

        # Strong degradation
        if retry_change > 1.0 or dead_change > 0.3:
            return "HIGH"

        # Moderate degradation
        if retry_change > 0.5 or dead_change > 0.15:
            return "MEDIUM"

        # Stable system
        return "LOW"
    
    @staticmethod
    def calculate_confidence(baseline_metrics, recent_metrics):
        min_events = min(baseline_metrics["count"], recent_metrics["count"])

        if min_events >= 60:
            return "HIGH"

        if min_events >= 25:
            return "MEDIUM"

        return "LOW"
    
    @staticmethod
    def analyze_drift(window_size_minutes=10):
        result = DriftEngine.calculate_drift(window_size_minutes)
        reason = []

        drift_class = DriftEngine.classify_drift(result["drift"])
        confidence = DriftEngine.calculate_confidence(
            result["baseline"],
            result["recent"]
        )

        retry_change = result["drift"]["retry_pressure_change"]
        if retry_change > 0.5:
           reason.append(f"Retry pressure increased by {round(retry_change, 2)}")

        dead_change = result["drift"]["dead_ratio_change"]
        if dead_change > 0.15:
           reason.append(f"Dead event ratio increased by {round(dead_change, 2)}")

        vol_change = result["drift"]["event_volume_change"]
        if vol_change > 10:
           reason.append(f"Event volume increased by {vol_change} units")

        return {
               "baseline": result["baseline"],
               "recent": result["recent"],
               "drift": result["drift"],
               "risk_level": drift_class,
               "confidence": confidence,
               "reason": reason
        }

    @staticmethod
    def save_snapshot(window_minutes=15):
        analysis = DriftEngine.analyze_drift(window_minutes)
        
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
    def get_snapshots(limit=10):
        from db.sqlite import get_connection
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM snapshots ORDER BY id DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        
        conn.close()
        return rows
    
    

    @staticmethod
    def explain_drift(window_size_minutes=10):
        result = DriftEngine.analyze_drift(window_size_minutes)

        drift = result["drift"]
        risk = result["risk_level"]
        confidence = result["confidence"]

        explanations = []

        if result["baseline"]["count"] == 0 or result["recent"]["count"] == 0:
           return {
        "summary": "Insufficient data to analyze system drift.",
        "risk_level": "UNKNOWN",
        "confidence": "LOW",
        "details": [],
        "raw": result
    }

        if drift["retry_pressure_change"] > 0.5:
            explanations.append(
                f"Retry pressure increased by {round(drift['retry_pressure_change'], 2)}"
            )

        if drift["dead_ratio_change"] > 0.15:
            explanations.append(
                f"Dead event ratio increased by {round(drift['dead_ratio_change'], 2)}"
            )

        if drift["event_volume_change"] > 0:
            explanations.append(
                f"Event volume increased by {drift['event_volume_change']}"
            )

        summary = (
            f"System risk is {risk} with {confidence} confidence. "
            + (" ".join(explanations) if explanations else "No significant drift detected.")
        )

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
    analysis = DriftEngine.explain_drift(window_size_minutes=15)
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

    
    