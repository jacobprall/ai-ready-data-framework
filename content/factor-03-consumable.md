# Factor 3: Consumable [draft]

**Definition:** Consumable data is served in the right format, at the right latencies, and at the right scale for AI workloads.

## Why It Matters

Data that arrives too late, in the wrong format, or can't handle load is unusable by AI systems. A recommendation engine that takes 30 seconds to respond is worthless. A vector database that can't scale with inference volume becomes a bottleneck. Format mismatches between data and model inputs create brittle integration points.

## Requirements

- APIs or serving layers optimized for AI access patterns
- Format compatibility with model input requirements (vectors, JSON, feature stores)
- Latency SLAs matched to workload needs
- Infrastructure that scales with inference volume
- Caching or pre-computation where required

## Key Questions

- What's the p99 latency for your AI data access patterns?
- Can your serving infrastructure handle 10x current load?
- How many format transformations happen between storage and model input?
