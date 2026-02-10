---
name: interpret
description: "Read assessment results and explain findings. Walks through factors, failures, and gaps using framework content to explain consequences."
parent_skill: assess-data
---

# Interpret Results

Read an assessment report and present findings to the user. Explain what each score means, why failures matter at their target workload level, and what couldn't be assessed. This is the intelligence layer that turns measurements into actionable insights.

## Forbidden Actions

- NEVER misrepresent scores -- always show the actual measured values and thresholds
- NEVER skip the factor-by-factor walkthrough for factors below 80%
- NEVER accept failures on behalf of the user -- always ask for explicit triage decisions
- NEVER present remediation SQL in this skill -- interpretation is read-only; fixes belong in `remediate/SKILL.md`

## When to Load

- After running an assessment (from `assess/SKILL.md`)
- When the user has a report file and wants to understand it
- When presenting results interactively (paired with `interview/SKILL.md` Phase 3)
- Can be used standalone: read any JSON report file

## Prerequisites

- A JSON assessment report (from `assess/SKILL.md` or a file)
- Optional: a `UserContext` to personalize interpretation

## Workflow

### Step 1: Read the Report

Parse the JSON report. Identify the user's target level (from `user_context.target_level` in the report, or default to L2).

```python
import json
with open("report.json") as f:
    report = json.load(f)
```

### Step 2: Present Overall Readiness

Read the `summary` section. Lead with the target level score:

```
Your data scores {score}% for {level_name} readiness ({level}).

{verdict}
```

**Verdicts by score:**
- >= 95%: "Your data is ready for {workload}."
- >= 80%: "Your data is mostly ready for {workload}. A few gaps to address."
- >= 50%: "Your data has significant gaps for {workload}. Focused remediation needed."
- < 50%: "Your data has major gaps for {workload}. Foundational work required."

Show all three levels for context:

```
| Level | Pass | Fail | Skip | Score |
|-------|------|------|------|-------|
| L1 (Analytics) | 142 | 23 | 5 | 86.1% |
| L2 (RAG)       | 118 | 47 | 5 | 71.5% ← target |
| L3 (Training)  | 89  | 76 | 5 | 53.9% |
```

### Step 3: Factor-by-Factor Walkthrough

Read the `factors` section. For each factor scoring below 80% at the target level, **read the corresponding framework document** to explain what the factor means and why it matters:

| Factor | Score < 80%? | Read This |
|--------|-------------|-----------|
| Clean | Yes | `framework/factor-00-clean.md` |
| Contextual | Yes | `framework/factor-01-contextual.md` |
| Consumable | Yes | `framework/factor-02-consumable.md` |
| Current | Yes | `framework/factor-03-current.md` |
| Correlated | Yes | `framework/factor-04-correlated.md` |
| Compliant | Yes | `framework/factor-05-compliant.md` |

**For each weak factor, explain three things:**

1. **What the factor means** -- one-sentence definition from the framework
2. **The AI shift** -- how this factor's requirements change for AI workloads vs. traditional BI
3. **The specific consequence** -- what happens if the user's specific failures aren't fixed at their target level

**Example:**

```
### Contextual: 45% at L2

Your contextual score is low because 77% of your columns lack descriptions
and 60% of _id columns have no foreign key constraints.

For RAG applications, this means AI systems will have to guess at column
meanings. A column named "status" could mean order status, account status,
or subscription status -- without a description, the LLM picks one and
may be wrong. Foreign keys tell AI systems how tables relate; without
them, join paths must be inferred from naming conventions, which breaks
for non-obvious relationships.
```

### Step 4: Present Not-Assessed Gaps

Read the `not_assessed` section. These are often the most actionable findings.

For each gap, explain:
- What capability is missing
- What the user needs to provide or install
- What assessments it would unlock

```
These areas could not be assessed:

- Pipeline freshness: No OpenTelemetry data available. Without pipeline
  observability, I can't tell you whether data is fresh because it's
  being updated frequently, or stale because a pipeline silently failed.
  → Set up OTEL instrumentation or set AIRD_OTEL_ENDPOINT

- Dataset versioning: No Iceberg metadata. Without snapshot history,
  I can't verify that you can reproduce past states of your data.
  → If your tables are Iceberg-backed, let me know and I'll re-probe
```

### Step 5: Top Failures

Read the `tests` array. Sort by impact (failures at lower levels first -- L1 failures are more critical than L3-only failures).

Present the top 10 failures:

```
| # | Target | Requirement | Measured | Threshold | Levels Failed |
|---|--------|-------------|----------|-----------|---------------|
| 1 | analytics.orders.customer_id | null_rate | 0.2300 | L1:0.10, L2:0.05 | L1, L2, L3 |
| 2 | analytics.users.email | pii_detection_rate | 0.9500 | L2:0.00 | L2, L3 |
| ... |
```

For each, explain the consequence in plain language:
- "23% of customer_id values are null. This means 1 in 4 orders can't be linked to a customer. For RAG, this breaks customer context retrieval."

### Step 6: Acknowledge Context Annotations

If the report has a `user_context` section, acknowledge what context was applied:

```
Context applied:
- Relaxed null thresholds for 3 columns marked as nullable by design
- Skipped PII checks on 2 columns confirmed as not sensitive
- Used custom freshness SLA of 1h for the orders table
- 5 test results were influenced by your context
```

### Step 7: Triage (Interactive)

**Load** `interview/SKILL.md` (Phase 3) for interactive triage. Ask the user which failures are expected, which to fix, and which to accept.

**STOP**: Wait for triage decisions before proceeding to remediation.

## Output

- A clear, prioritized understanding of the data's AI readiness
- Context-aware interpretation that accounts for user decisions
- Triage decisions recorded in the `UserContext`

## Next Skill

**Continue to** `remediate/SKILL.md` for failures the user wants to fix.
