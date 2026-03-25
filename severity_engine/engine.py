from event_service.repository import EventRepository

class SeverityEngine:

    @staticmethod
    def classify(event, window_minutes=15):
        # 1. Determine base severity solely from unit state
        severity_levels = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        current_idx = 0

        if event.retry_count >= max(1, int(event.max_retries * 0.4)):
            current_idx = 1 # MEDIUM
        if event.retry_count >= max(1, int(event.max_retries * 0.7)):
            current_idx = 2 # HIGH
        if event.is_dead or (event.retry_count >= event.max_retries):
            current_idx = 3 # CRITICAL
        
        # 🧠 Intelligence Trace Base
        base_idx = current_idx

        # 2. Extract intelligence from the cluster
        recent_failures = EventRepository.get_recent_fault_count(event.service_name, minutes=window_minutes)

        # 🚀 INTELLIGENCE BOOST: Escalation logic
        # If clustering is HIGH (>50 faults), we jump +2 severity levels
        if recent_failures > 50:
            current_idx += 2
        # If clustering is MODERATE (>20 faults), we jump +1 severity level
        elif recent_failures > 20:
            current_idx += 1

        # Final Cap
        final_idx = min(current_idx, 3)
        severity = severity_levels[final_idx]

        # 🧬 Format Reason
        reason = f"Base ({severity_levels[base_idx]})"
        if final_idx > base_idx:
            boost = final_idx - base_idx
            reason += f" + Cluster Boost (+{boost} for >20-50 faults)"
        
        return severity, reason


if __name__ == "__main__":
    from schemas.event_schema import Event
    from datetime import datetime

    # 🎨 Visual Style
    HEADER = "\033[95m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"

    print("\n" + "═"*70)
    print(f"{BOLD}{HEADER} 🧬 AERIS SEVERITY INTELLIGENCE ENGINE {ENDC}")
    print("═"*70)

    test_scenarios = [
        {"retry": 0, "max": 3, "dead": False, "desc": "Fresh failure (Clustered)", "svc": "order-service"},
        {"retry": 2, "max": 3, "dead": False, "desc": "Retry exhaustion impending", "svc": "payment-service"},
        {"retry": 3, "max": 3, "dead": True, "desc": "Terminal failure state", "svc": "order-service"},
        {"retry": 1, "max": 5, "dead": False, "desc": "Isolated service (No data)", "svc": "new-isolated-service"},
    ]

    print(f"\n{BOLD}{OKCYAN}🎯 RUNNING CLASSIFICATION TRACE (Recent Window: 30 minutes){ENDC}\n")

    for s in test_scenarios:
        event = Event(
            event_id="test", trace_id="trace", service_name=s["svc"],
            endpoint="/test", status="failure", retry_count=s["retry"],
            max_retries=s["max"], is_dead=s["dead"], timestamp=datetime.utcnow(),
            error_type="timeout"
        )
        
        recent_count = EventRepository.get_recent_fault_count(s["svc"], minutes=30)
        severity, severity_reason = SeverityEngine.classify(event, window_minutes=30)
        
        # Determine icon and color
        icon, color = {
            "CRITICAL": ("🚨", FAIL),
            "HIGH":     ("🔥", WARNING),
            "MEDIUM":   ("🔸", OKCYAN),
            "LOW":      ("✅", OKGREEN)
        }.get(severity, ("❓", ""))
        
        # Display
        print(f"{BOLD}CASE: {s['desc']}{ENDC}")
        print(f" {OKCYAN}├─{ENDC} Service Context: {s['svc']} ({recent_count} recent faults)")
        print(f" {OKCYAN}├─{ENDC} Event Metrics:   {s['retry']}/{s['max']} retries | Dead: {s['dead']}")
        print(f" {OKCYAN}├─{ENDC} Logic Trace:     {severity_reason}")
        print(f" {OKCYAN}└─{ENDC} {BOLD}FINAL VERDICT:   {color}{icon} {severity}{ENDC}\n")

    print("═"*70 + "\n")