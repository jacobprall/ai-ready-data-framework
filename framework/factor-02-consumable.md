# Factor 2: Consumable

**Definition:** Consumable data is served in the right format, at the right latencies, and at the right scale for AI workloads.

## The Shift

Traditional BI workloads read data in bulk on human timescales -- a dashboard that refreshes in 5 seconds is fast. AI workloads have fundamentally different access patterns: vector retrieval, feature serving, and inference chains require sub-second latency, native format compatibility (embeddings, JSON, Parquet), and elastic throughput. A format mismatch or latency miss isn't a degraded experience -- it's a broken pipeline.

### Level 1: Descriptive Analytics and BI

**Tolerance for consumability gaps: High.** Humans wait for dashboards. Batch refresh cycles are acceptable. Format mismatches are handled by analysts or ETL processes. Latency is measured in seconds, not milliseconds.

### Level 2: RAG and Retrieval Systems

**Tolerance for consumability gaps: Moderate.** Retrieval must return relevant chunks within the latency budget of a user-facing interaction (typically under 2 seconds end-to-end). Data must be chunked, embedded, and indexed before it can be consumed. Format transformations are acceptable during indexing but not at query time.

### Level 3: ML Model Training and Fine-Tuning

**Tolerance for consumability gaps: Low.** Training pipelines consume data at scale -- terabytes across thousands of iterations. Format incompatibilities multiply across every batch. Latency matters less than throughput: the pipeline needs to read data fast enough to keep GPUs saturated. Any format transformation at read time wastes compute that should be spent on training.

## Requirements

What must be true about the data at each level. Each level is additive.

| Requirement | L1 | L2 | L3 |
|---|---|---|---|
| **Format compatibility** | Data is queryable via SQL | Data is available in formats compatible with embedding and retrieval (text, JSON, structured documents) | Data is available in formats optimized for training throughput (Parquet, Arrow, TFRecord) with zero or one format transformations from storage |
| **Access patterns** | Interactive SQL queries | Programmatic access via SDKs, REST APIs, or direct file access alongside SQL | High-throughput batch reads optimized for training pipelines (columnar scans, parallel reads) |
| **Latency** | Dashboard refresh under 30 seconds is acceptable | Retrieval latency under 2 seconds end-to-end | Training data read throughput sufficient to saturate compute (GPU/TPU utilization) |
| **Scalability** | Handles current query volume | Scales with inference volume (concurrent retrievals) | Scales with training volume (dataset size, iteration count, distributed reads) |
| **Data type support** | Standard SQL types | Vector/embedding types, JSON, semi-structured data | Native support for tensors, embeddings, and high-dimensional data alongside tabular |
| **Open format access** | -- | Data accessible via open table formats (Iceberg, Delta) for cross-engine reads | Data accessible via open formats with zero-copy reads across compute engines |
| **Discovery** | Tables and columns are browsable | Self-service data discovery for ML practitioners (search, preview, profiling) | Programmatic dataset discovery with metadata APIs |

## Required Stack Capabilities

What the platform must support to consistently meet these requirements. Each level is additive.

| Capability | L1 | L2 | L3 |
|---|---|---|---|
| **Query interface** | SQL query engine | SQL plus programmatic access (SDKs, REST, file-based reads) | High-throughput data loaders with parallel read support |
| **Format support** | Tabular (CSV, relational) | Semi-structured (JSON, text), vector types, embedding storage | Columnar (Parquet, Arrow), tensor formats, streaming reads |
| **Serving infrastructure** | Single query engine | Serving layer with caching for hot paths (feature stores, materialized views) | Elastic infrastructure that scales with training volume independently of query volume |
| **Data discovery** | Schema browser or catalog | Self-service discovery with search, preview, and profiling | Programmatic dataset registry with metadata APIs and version tracking |
| **Cross-engine access** | -- | Open table format support (Iceberg, Delta) for multi-engine reads | Zero-copy cross-engine access with consistent semantics |

## Key Questions

- What's the p99 latency for your AI data access patterns?
- Can your serving infrastructure handle 10x current load?
- How many format transformations happen between storage and model input?
- Can ML practitioners discover and access data without filing a ticket?
