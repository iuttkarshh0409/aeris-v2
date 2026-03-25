# 🛡️ AERIS V2: Intelligence-Driven Reliability Engine

**AERIS (Automated Event Reliability & Intelligence System)** is an industry-grade observability engine designed to transform static failure logs into **Deterministic Reliability Signals**. Unlike traditional monitors that alert on raw counts, AERIS reasons about the current state of a system using context-aware severity classification and windowed drift analysis.

---

### **🚀 Core Philosophy**
AERIS is built on the principle that **failures are not incidents—they are heat signatures**. By analyzing failure clusters, retry pressure, and historical baselines, AERIS provides SREs with a transition from "fighting fires" to "understanding systemic patterns."

---

### **🧠 Key Intelligence Pillars**

#### **1. Deterministic Severity (Logic Traces)**
AERIS doesn't just assign a label; it provides a **Logic Trace** for every event.
- **Base State**: Severity is initially derived from current retry progress vs. maximum limits (e.g., 2/3 retries = HIGH).
- **Intelligence Boost**: If a microservice is currently experiencing a cluster (e.g., >20 faults in 15m), severity is automatically escalated (+1, +2 levels) to signal systemic risk.

#### **2. Confidence-Aware Drift Analysis**
Using two sliding windows (**Baseline** vs. **Recent**), the Drift Engine calculates:
- **Retry Pressure Change**: $\Delta$ in average retry counts.
- **Metric Stability**: Changes in "Dead Event" (terminal failure) ratios.
- **Confidence Signal**: A dynamically calculated score (LOW/MEDIUM/HIGH) based on sample sizes (Thresholds: 25, 60 events).

#### **3. Autonomous Auditing (Heartbeat Snapshots)**
The engine features a background **Autonomous Auditor** that periodically captures persistence snapshots. This allows for historical auditing of "System Risk" over months, providing a clear picture of reliability trends regardless of short-term noise.

---

### **🏗️ Technical Architecture**

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Asynchronous, High-Performance Gateway).
- **Persistence**: SQLite (Immutable Event Store + Snapshot Audit Trail).
- **Classification Engine**: Rule-based deterministic logic (Python-native).
- **Simulation Layer**: High-Intensity Fault Generator for validation.

---

### **🛠️ Operational Setup**

#### **1. Fast-Track API Initialization**
```bash
# Install dependencies
pip install fastapi uvicorn requests

# Start the AERIS Gateway
uvicorn api.main:app --reload
```

#### **2. Local Dashboard (The Heatmap)**
View the system health dashboard directly from your terminal:
```bash
python -m drift_engine.engine
```

#### **3. Stress Testing (AERIS Simulator)**
Simulate mass failure clusters to test the intelligence layers:
```bash
python -m simulation.generator
```

---

### **📡 API Specification**

| Endpoint | Method | Purpose |
| :--- | :--- | :--- |
| `/events` | `POST` | Ingest a failure event & receive a **Logic Trace**. |
| `/drift/explain` | `GET` | Get a human-readable analysis of system deltas. |
| `/drift/history` | `GET` | Retrieve the automated auditor trail. |
| `/analytics/services` | `GET` | Observe "Service Heat" (fault clustering per service). |
| `/analytics/severity` | `GET` | Get global severity distribution heatmap data. |

---

### **📚 Logic Design (Strict TDD Compliance)**

| Intelligence Layer | Applied Logic |
| :--- | :--- |
| **Severity Escalation** | `If count > 50: +2 levels \| If count > 20: +1 level` |
| **Risk Thresholds** | `Retry > 1.0 (Pressure Change) = HIGH RISK` |
| **Confidence matrix** | `Sample < 25 (LOW) \| 25-60 (MEDIUM) \| > 60 (HIGH)` |

---

### **👥 User Testing**
For a detailed step-by-step roadmap to validating every feature (mocking historical baselines, stress clustering, and audit checking), refer to our [User Testing Guide](./doc/User_Testing_Guide.md).

---
**Status**: `v2.0-core_standard` | **Compliance**: `Strict-TDD-1.0`
