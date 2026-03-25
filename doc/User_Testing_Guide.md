# AERIS V2: User Testing & Validation Guide
**Objective**: To manually validate the intelligence, explainability, and auditing layers of the AERIS system.

---

## 🛠️ Phase 1: Ingestion & Individual Severity
**Goal**: Verify the "Base Severity" logic and the persistence of "Logic Traces."

#### **1.1 Low Severity Event**
Inject a fresh failure with no retries.
```bash
curl -X POST http://localhost:8000/events -H "Content-Type: application/json" -d '{
  "event_id": "test-1", "trace_id": "tr-1", "service_name": "pay-svc", "endpoint": "/pay",
  "status": "failure", "retry_count": 0, "max_retries": 3, "is_dead": false,
  "timestamp": "2026-03-25T20:00:00Z", "error_type": "timeout"
}'
```
*   **Expectation**: Severity: `LOW`. Reason: `Base (LOW)`.

#### **1.2 Critical (Dead Letter) Event**
Inject a failure that has exhausted all retries.
```bash
curl -X POST http://localhost:8000/events -H "Content-Type: application/json" -d '{
  "event_id": "test-2", "trace_id": "tr-1", "service_name": "pay-svc", "endpoint": "/pay",
  "status": "failure", "retry_count": 3, "max_retries": 3, "is_dead": false,
  "timestamp": "2026-03-25T20:01:00Z", "error_type": "exhausted"
}'
```
*   **Expectation**: Severity: `CRITICAL`. Reason: `Base (CRITICAL)`.

---

## 🧬 Phase 2: Clustering Intelligence (Severity Boost)
**Goal**: Verify the engine's ability to escalate risk based on the environment.

1.  **Clear/New Service**: Choose a new service name (e.g., `shipping-svc`).
2.  **Generate 25 events rapidly** (manually or via a loop):
    ```powershell
    # PowerShell Example to fire 25 events
    1..25 | ForEach-Object {
        curl -X POST http://localhost:8000/events -H "Content-Type: application/json" -d "{
          \"event_id\": \"$([guid]::NewGuid())\", \"trace_id\": \"tr-cluster\", \"service_name\": \"shipping-svc\", \"endpoint\": \"/label\",
          \"status\": \"failure\", \"retry_count\": 0, \"max_retries\": 3, \"is_dead\": false,
          \"timestamp\": \"$([DateTime]::UtcNow.ToString('o'))\", \"error_type\": \"load_err\"
        }"
    }
    ```
3.  **Validate**:
    *   **Expectation**: Around event #21, the `Reason` will shift from `Base (LOW)` to `Base (LOW) + Cluster Boost (+1 for >20-50 faults)`.
    *   The `Severity` will escalate from **LOW** to **MEDIUM** automatically.

---

## 📊 Phase 3: Drift Analysis & Confidence Signals
**Goal**: Compare historical vs current performance and observe confidence scaling.

1.  **Create Baseline**: Run the mock script to create "Normal" load from 15 mins ago.
    ```powershell
    python -m scripts.mock_baseline
    ```
2.  **Generate Stress**: Run the high-load simulation for 60 seconds.
    ```powershell
    python -m simulation.generator
    ```
3.  **Check Signal**:
    *   Visit: `http://localhost:8000/drift/explain`
    *   **Expectation**: Risk: `MEDIUM` or `HIGH`. Details: Should show "Retry pressure increased by X".
    *   **Confidence**: If you fired >25 but <60 events, confidence should be `MEDIUM`.

---

## 🕵️ Phase 4: Autonomous Auditing & History
**Goal**: Verify long-term trend persistence.

1.  **Wait for Auditor**: The background thread runs every **60 seconds**.
2.  **Check Audit Trail**:
    Visit: `http://localhost:8000/drift/history`
    *   **Expectation**: You will see a list of snapshots. Look for snapshots where `event_count` is > 0.
    *   Observe how `risk_level` tracked the system state change during your Phase 3 test.

---

## 🛡️ Phase 5: System Health Dashboard (CLI)
**Goal**: Use the "Heatmap" for rapid operational insight.

1.  **Run Command**:
    ```powershell
    python -m drift_engine.engine
    ```
2.  **Analyze Visuals**:
    *   **Severity Heatmap**: Are your CRITICAL and HIGH bars accurate to your injections?
    *   **Top Service Clusters**: Does your stressed service appear at the top with "Heat" indicators?
    *   **Drift Root Causes**: Are the deltas clearly explained with bullet points?

---

## 🧪 Phase 6: Service-wise Context
**Goal**: Drill down into specific service health.

1.  **API Check**: Visit `http://localhost:8000/analytics/services`.
2.  **Validation**: Verify that `avg_retry` for your stressed service is higher than the "Normal" services.

---
**Status: ALL SYSTEMS GO** 🚀
