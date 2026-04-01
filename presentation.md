# AERIS v2 - Demo Guide

## 1. What is AERIS (Simple Explanation)
AERIS is an automated Reliability Intelligence system. It monitors application performance and metadata to provide deterministic, "decision-safe" reasoning during incidents, helping SRE teams identify root causes and remediate failures instantly.

---

## 2. Demo Flow (The Sequence)

### STEP 1: Seed Baseline
**Command**:
```bash
python -m cli.main seed
```
**Talk Track**:
"We begin by seeding the platform with 60 minutes of 'healthy' baseline data (Version v2.0). This allows AERIS to learn the normal performance patterns of our checkout service."

---

### STEP 2: Simulate Failure
**Command**:
```bash
python -m cli.main simulate --scenario deployment
```
**Talk Track**:
"A new software version (v2.1) is now deployed as a canary. The simulation generates 150 events characterized by elevated latency and error rates."

---

### STEP 3: View Logs
**Command**:
```bash
python -m cli.main logs --limit 10
```
**Talk Track**:
"These are the raw events ingested. Note the coexistence of healthy v2.0 logs and degraded v2.1 logs."

---

### STEP 4: Check System Status
**Command**:
```bash
python -m cli.main status
```
**Talk Track**:
"AERIS provides a high-level health summary. We can see the risk level has escalated, and our reasoning engine has identified active signals in the environment."

---

### STEP 5: Explain Incident (MAIN PART)
**Command**:
```bash
python -m cli.main explain
```
**Talk Track**:
"AERIS generates a **Decision-Safe Brief**. It identifies **WHAT** happened (Deployment Regression), **WHY** (Version v2.1 triggered the drift), and **NEXT** (Immediate Rollback)."

---

## 3. Key Sections to Highlight (The Brief)

- **[SYSTEM STATE]**: The global risk level and the engine's confidence score.
- **[ROOT CAUSE]**: The specific software version or failure mode identified.
- **[IMPACT ANALYTICS]**: The 'Blast Radius' (percent of users affected).
- **[DECISION ENGINE]**: A policy-aware recommendation (Action + Safety Gate).
- **[SIMPLE EXPLANATION]**: A human-readable summary for non-technical stakeholders.

---

## 4. Two Scenarios to Explain

### Case 1: Known Cause (Deployment Issue)
AERIS correlates the release of v2.1 with performance degradation. It explicitly recommends a rollback of that specific version.

### Case 2: Unknown Cause (N/A)
If the metrics drift but no specific deployment is to blame, AERIS automatically switches to **Diagnostic Mode**, recommending infrastructure investigation instead of a blind rollback.

---

## 5. One-Line Summary (Closing Statement)
"AERIS transforms raw telemetry into deterministic intelligence, empowering SREs with the confidence to act during high-stakes failures."
