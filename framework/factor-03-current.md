# Factor 3: Current

**Definition:** Current data reflects the present state, with freshness enforced by systems -- never assumed.

## The Shift

In traditional analytics, stale data produces a stale report -- a human notices the date and adjusts their interpretation. Models have no concept of time. They treat every input as ground truth. Stale data doesn't produce a "stale answer" -- it produces a confident, wrong one. A fraud detection model using day-old transaction data misses real-time attacks. A pricing algorithm with stale inventory data creates customer disappointment. Freshness must be enforced by infrastructure, not assumed by convention.

### Level 1: Descriptive Analytics and BI

**Tolerance for staleness: High.** Daily or weekly refreshes are acceptable for most reporting use cases. Humans check the "last updated" timestamp and adjust their interpretation accordingly. Staleness is visible and manageable.

### Level 2: RAG and Retrieval Systems

**Tolerance for staleness: Moderate.** A RAG system that retrieves outdated documentation gives wrong answers with full confidence. The user has no way to know the retrieved content is stale. Source content must be re-indexed when it changes, and the system must know when its index is out of date.

### Level 3: ML Model Training and Fine-Tuning

**Tolerance for staleness: Low.** Training data must represent the current distribution the model will encounter in production. A model trained on last quarter's data may perform well on last quarter's patterns and fail on today's. Feature drift -- where the relationship between inputs and outputs changes over time -- requires continuous monitoring and retraining triggers.

## Requirements

What must be true about the data at each level. Each level is additive.

| Requirement | L1 | L2 | L3 |
|---|---|---|---|
| **Timestamps** | Key tables have a timestamp column indicating when records were created or updated | All records carry timestamps | All records carry both creation and modification timestamps with timezone information |
| **Freshness SLAs** | Freshness expectations are documented informally | Freshness SLAs are defined per data product and communicated to consumers | Freshness SLAs are enforced programmatically with automated alerting on violations |
| **Staleness detection** | Users can check when data was last refreshed | The system detects and surfaces staleness automatically | Staleness triggers automated remediation (pipeline restart, cache invalidation, model retraining) |
| **Pipeline reliability** | Pipelines run on a schedule | Pipelines have retry and backfill mechanisms for failures | Pipelines are monitored end-to-end with guaranteed delivery and exactly-once semantics where required |
| **Historical state** | -- | Point-in-time queries are possible for key datasets | Full historical state is queryable with versioned snapshots for reproducibility |
| **Change detection** | -- | Change data capture (CDC) or event-driven updates for source content | CDC or streaming for real-time updates with sub-minute latency where required |

## Required Stack Capabilities

What the platform must support to consistently meet these requirements. Each level is additive.

| Capability | L1 | L2 | L3 |
|---|---|---|---|
| **Scheduling** | Scheduled pipeline execution (cron, orchestrator) | Automated pipelines with guaranteed refresh rates and SLA tracking | Event-driven pipelines that trigger on data changes, not just schedules |
| **Freshness monitoring** | Manual freshness checks (query MAX(updated_at)) | Automated freshness monitoring with alerting on SLA violations | Freshness dashboards with per-table, per-pipeline visibility and trend analysis |
| **Failure recovery** | Manual pipeline restart | Automated retry and backfill mechanisms | Self-healing pipelines with dead-letter queues, circuit breakers, and automatic recovery |
| **Change propagation** | Batch refresh | CDC or streaming for near-real-time updates | Streaming with sub-minute latency and exactly-once delivery guarantees |
| **Time travel** | -- | Point-in-time query capabilities | Versioned snapshots with configurable retention for historical state reconstruction |
| **Drift detection** | -- | -- | Distribution drift monitoring that compares current data against training-time distributions |

## Key Questions

- What's the maximum acceptable staleness for each data product?
- How do you know when data is stale?
- Can you recover from pipeline failures without manual intervention?
- Do your tables have timestamp columns?
