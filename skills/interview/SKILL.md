---
name: interview
description: "Three-phase interactive interview to gather business context. Captures domain knowledge that no SQL query can discover."
parent_skill: assess-data
---

# Interactive Interview

Gather business context through a three-phase conversation. Each phase targets a different stage of the assessment pipeline. Answers are captured in a `UserContext` and persisted for future runs.

Can be used standalone (to build context before an assessment) or invoked at specific phases by other skills.

## Forbidden Actions

- NEVER proceed past a STOP point without user confirmation
- NEVER assume answers -- always ask the user, even if you can guess
- NEVER overwrite saved context without offering to merge with existing answers
- NEVER ask all questions at once -- use progressive disclosure by priority

## When to Load

- **Phase 1**: Before connecting -- understand goals, scope, infrastructure
- **Phase 2**: After discovery -- confirm scope, validate heuristics, add business semantics
- **Phase 3**: After results -- triage failures, accept gaps, prioritize remediation
- **Standalone**: User wants to set up context for their data estate without running tests

## Prerequisites

- Phase 1: No prerequisites (runs before connection)
- Phase 2: A `DatabaseInventory` from `discover/SKILL.md`
- Phase 3: A completed assessment report from `assess/SKILL.md`

## Phase 1: Pre-Assessment Interview

**Goal:** Understand the data estate, the user's goals, and organizational context.

Ask these questions in priority order. Use progressive disclosure -- don't dump all questions at once.

### Question 1: Target Workload Level (Priority 1)

```
What are you building toward with this data?

- L1 (Analytics): Dashboards, BI, ad-hoc queries
- L2 (RAG): Retrieval-augmented generation, semantic search, AI-powered apps
- L3 (Training): Fine-tuning models, building training datasets
```

**Context field:** `target_level`
**Impact:** Determines which threshold level to focus on. Failures at the target level are prioritized in the report.

### Question 2: Data Estate Scope (Priority 1)

```
Tell me about your data estate. Are there schemas I should skip?
Common examples: staging, scratch, temp, test, or system schemas.
```

**Context field:** `excluded_schemas`, `excluded_tables`
**Impact:** Excluded schemas/tables are filtered from discovery before tests run.

### Question 3: Infrastructure Context (Priority 2)

```
Which of these tools are part of your data stack?

- dbt (I can look for dbt artifacts for lineage)
- Data catalog (Alation, Collibra, DataHub -- descriptions may live outside the DB)
- OpenTelemetry (I can assess pipeline freshness and reliability)
- Iceberg (I can assess dataset versioning and snapshot history)
- None of the above
```

**Context fields:** `has_dbt`, `has_catalog`, `has_otel`, `has_iceberg`
**Impact:** Overrides brittle probe-based detection. Unlocks additional assessments.

### Question 4: Governance Posture (Priority 2)

```
Do you have a PII classification policy or know which columns contain
sensitive data? I'll scan for PII patterns, but your domain knowledge
helps me avoid false positives and catch columns I might miss.
```

**Context field:** `known_pii_columns`
**Impact:** Enriches PII detection beyond heuristic name matching.

### Question 5: Known Pain Points (Priority 2)

```
What prompted this assessment? Are there specific data quality issues
you already know about?
```

**Context field:** `known_issues`
**Impact:** Validates that the assessment catches known problems. Prioritizes known problem areas.

**STOP**: Record answers in `UserContext`. Offer to save as `context.yaml`.

---

## Phase 2: Post-Discovery Questions

**Goal:** Correct heuristic assumptions and add business context based on what was found.

These questions are generated dynamically by `agent/interview.py:discovery_questions()` based on the inventory.

### Question 1: Scope Confirmation (Priority 1)

```
I found {N} tables and {M} columns across {K} schemas:
{schema_name} ({count} tables), ...

Should I assess all of them, or exclude any?
```

**Context field:** `excluded_schemas`, `excluded_tables`

### Question 2: Table Criticality (Priority 2, if > 5 tables)

```
Which tables are most critical for your AI workloads?
I'll weight failures on critical tables more heavily.

Candidates based on size and naming:
- schema.fact_orders (24 columns)
- schema.dim_customers (15 columns)
- schema.users (12 columns)
...

Tell me which are critical, or add others.
```

**Context field:** `table_criticality` (map of fqn -> "critical" | "standard" | "low")

### Question 3: Candidate Key Confirmation (Priority 2)

```
I detected these columns as likely unique identifiers based on
naming patterns (ending in _id or named id):
- schema.table.customer_id
- schema.table.order_id
...

Are any of these NOT actually unique keys?
Are there natural keys I'm missing (e.g., email, order_number)?
```

**Context fields:** `not_keys`, `confirmed_keys`
**Impact:** Fixes the `_id` heuristic. Prevents false duplicate detection.

### Question 4: PII Confirmation (Priority 2)

```
These columns look like they contain PII:
- schema.users.email
- schema.users.phone_number
- schema.orders.billing_address
...

Which actually contain sensitive data?
Are there PII columns I'm missing?
```

**Context fields:** `known_pii_columns`, `false_positive_pii`
**Impact:** Eliminates false positive PII flags. Catches non-obvious PII.

### Question 5: Nullable Expectations (Priority 3)

```
These columns look like they might intentionally allow nulls:
- schema.users.middle_name
- schema.products.discontinued_date
- schema.orders.notes
...

Which have nulls by design? I'll relax thresholds for those.
```

**Context field:** `nullable_by_design`
**Impact:** Prevents flagging intentionally nullable columns as data quality issues.

### Question 6: Freshness SLAs (Priority 3)

```
I'll check freshness for {N} tables with timestamp columns.
Default thresholds: L1=1 week, L2=24h, L3=6h.

Do any tables have different freshness requirements?
(e.g., transactions = hourly, dim_country = weekly)
```

**Context field:** `freshness_slas` (map of fqn -> hours)
**Impact:** Per-table staleness thresholds replace global defaults.

**STOP**: Update `UserContext` with answers. Save context.

---

## Phase 3: Post-Results Triage

**Goal:** Help the user decide which failures matter and what to fix.

These questions are generated by `agent/interview.py:results_questions()` based on the report.

### Question 1: Factor Triage (Priority 1)

```
At your target level ({target}), these factors scored below 80%:
- Clean: 62%
- Contextual: 45%
- Compliant: 71%

Are any of these expected or acceptable for your use case?
```

### Question 2: Failure Triage (Priority 1)

```
Top failures at {target}:
- schema.orders.customer_id -- null_rate: 0.2300 (threshold: 0.05)
- schema.users.email -- pii_detection_rate: 0.9500 (threshold: 0.00)
...

For each:
- Is this expected? (I'll mark as accepted)
- Should I generate a fix?
- Exclude from future assessments?
```

**Context field:** `accepted_failures`
**Impact:** Accepted failures are annotated in reports and don't re-flag on subsequent runs.

### Question 3: Not-Assessed Gaps (Priority 2)

```
These areas couldn't be assessed:
- pipeline_freshness: No OTEL data available
- dataset_versioning: No Iceberg metadata tables

Can you provide any of the missing data sources?
```

### Question 4: Remediation Priority (Priority 2)

```
Which areas do you want to tackle first?

1. Quick wins (comments, naming, constraints)
2. Data quality (nulls, duplicates, types)
3. Governance (PII, RBAC, masking)
4. Infrastructure (freshness, lineage, versioning)
5. All of the above
```

**STOP**: Update `UserContext`. Save context. Continue to `remediate/SKILL.md` for selected areas.

---

## Context Persistence

User context is saved per connection to `~/.aird/contexts/context-{hash}.yaml`. On subsequent runs:

1. **Load saved context**: "I found your context from the last assessment. You excluded `staging` and marked `orders` as critical."
2. **Offer to update**: "Want to change any previous answers?"
3. **Merge**: New answers are merged -- lists are unioned, scalars use the latest value.

Context can also be saved to an explicit path with `--context path/to/context.yaml`.

## Output

- A populated `UserContext` object
- A saved YAML context file (per-connection or explicit path)

## Next Skill

- After Phase 1: **Continue to** `connect/SKILL.md`
- After Phase 2: **Continue to** `assess/SKILL.md`
- After Phase 3: **Continue to** `remediate/SKILL.md`
