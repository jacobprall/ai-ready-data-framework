# Factor 4: Correlated

**Definition:** Correlated data is traceable from its source to every decision it informs.

## The Shift

When a BI dashboard shows a wrong number, a human traces it back through a few SQL queries. AI systems are compositional: data flows through transformations, feature engineering, model inference, and post-processing before producing an output. The path from input to decision is longer, more opaque, and non-linear. Without end-to-end lineage, a bad output is a black box -- you can't isolate whether the failure was in the source data, a transformation, or the model itself. If you can't reproduce it, you can't debug it.

### Level 1: Descriptive Analytics and BI

**Tolerance for missing lineage: High.** An analyst can manually trace a number back through views and tables. The path is short (source -> transform -> dashboard) and the analyst is familiar with the pipeline. Manual tracing is tedious but feasible.

### Level 2: RAG and Retrieval Systems

**Tolerance for missing lineage: Moderate.** When a RAG system gives a wrong answer, you need to identify which chunk was retrieved and which source document it came from. Without lineage from source document to chunk to retrieval, debugging is guesswork. The path is: source -> chunking -> embedding -> index -> retrieval -> response.

### Level 3: ML Model Training and Fine-Tuning

**Tolerance for missing lineage: Very low.** When a model produces biased or incorrect outputs, you need to trace back to the training data that caused it. Which dataset version? Which transformation pipeline? Which labeling batch? Without end-to-end lineage and dataset versioning, debugging requires retraining from scratch -- and you can't even be sure the retrained model won't have the same problem.

## Requirements

What must be true about the data at each level. Each level is additive.

| Requirement | L1 | L2 | L3 |
|---|---|---|---|
| **Table-level lineage** | Source tables for key views and transforms are documented | Source-to-destination lineage is tracked for all tables, either in a catalog or via pipeline metadata | Source-to-destination lineage is tracked automatically and queryable via API |
| **Transformation audit** | Key transformation logic is documented in SQL or code | All transformation steps are logged with input/output record counts | All transformations produce audit logs with row-level traceability where required |
| **Reproducibility** | Analysts can re-run queries to verify results | Key datasets can be reconstructed at any historical point in time | Any model output can be reproduced by reconstructing the exact dataset and pipeline state that produced it |
| **Dataset versioning** | -- | Source content is versioned so you know what was in the index at any point | Training datasets are immutably versioned with model-to-data version binding |
| **Constraint coverage** | Primary keys are declared on key tables | Primary keys and unique constraints are declared on all tables | All tables have primary keys, and referential integrity is enforced or monitored |
| **Pipeline observability** | -- | Pipeline health is monitored (success/failure, latency) | End-to-end pipeline observability with span-level tracing across all stages |

## Required Stack Capabilities

What the platform must support to consistently meet these requirements. Each level is additive.

| Capability | L1 | L2 | L3 |
|---|---|---|---|
| **Lineage tracking** | Documentation or manual tracking | Automated lineage capture from pipeline execution (catalog, orchestrator, or OTEL) | End-to-end lineage from source systems through transformations to AI outputs, queryable via API |
| **Versioning** | Source control for SQL and pipeline code | Content versioning for indexed data (know what's in the index at any time) | Immutable dataset snapshots with retention policies and model-version binding |
| **Audit logging** | -- | Transformation logs with input/output metrics | Row-level audit trails for all data transformations |
| **Pipeline monitoring** | Job success/failure alerts | Health metrics for pipelines, feature stores, and serving layers | Span-level tracing (OTEL) across batch and real-time paths with anomaly detection |
| **Determinism** | -- | -- | Deterministic pipelines that produce identical outputs from identical inputs |
| **Time travel** | -- | Point-in-time snapshots for key datasets | Full time-travel capabilities with configurable retention across all datasets |

## Key Questions

- Can you reproduce a model's output from last month with the exact data it used?
- If a prediction is wrong, how long does it take to identify the root cause?
- Do you have lineage across both batch and real-time paths?
- What percentage of your tables have primary key constraints?
