# Factor 4: Current [draft]

**Definition:** Current data reflects the present state with freshness enforced by systems, never assumed.

## Why It Matters

AI systems assume data is current. When it isn't, they make decisions based on a world that no longer exists. A fraud detection model using day-old transaction data misses real-time attacks. A pricing algorithm with stale inventory data creates customer disappointment. Staleness is often invisible until it causes failures.

## Requirements

- Freshness SLAs defined per data product
- Automated pipelines with guaranteed refresh rates
- CDC or streaming for real-time updates
- Monitoring and alerting on freshness violations
- Timestamps on all records
- Retry and backfill mechanisms for failures

## Key Questions

- What's the maximum acceptable staleness for each data product?
- How do you know when data is stale?
- Can you recover from pipeline failures without manual intervention?
