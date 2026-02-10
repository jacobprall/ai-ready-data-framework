# Factor 0: Clean

**Definition:** Clean data is consistently accurate, complete, valid, and free of errors that would compromise downstream consumption.

## The Shift

The importance of data quality is nothing new, but the consequences of poor data quality are dramatically increased when used by AI systems.

Clean data is not perfect data. Perfection is neither achievable nor necessary. What matters is that data is clean *enough* for the workload it feeds. Different AI workloads have materially different tolerance thresholds for data quality. The demands escalate as the system's autonomy increases and as the cost of errors shifts from recoverable to permanent.

### Level 1: Descriptive Analytics and BI

**Tolerance for dirty data: Moderate.** Humans are in the loop. They interpret results, notice anomalies, and ask clarifying questions before acting. A wrong number on a chart is a nuisance, not a catastrophe.

### Level 2: RAG and Retrieval Systems

**Tolerance for dirty data: Low.** The model selects chunks from your corpus and presents them -- often verbatim -- as answers. Any individual chunk can become the basis of a response.

### Level 3: ML Model Training and Fine-Tuning

**Tolerance for dirty data: Very low.** Errors in training data are not retrieved -- they are *learned*. The model encodes patterns from the training distribution into its weights. A bias, a labeling error, or a systematic data quality issue produces a model that is structurally inclined toward wrong answers across every inference it serves. Remediation means retraining.

## Requirements

What must be true about the data at each level. Each level is additive.

| Requirement | L1 | L2 | L3 |
|---|---|---|---|
| **Format standardization** | Dates, currencies, and units of measure are consistent so aggregations are valid | Terminology, naming conventions, and document structure are consistent across the corpus to improve retrieval accuracy | Formats are rigorously normalized across the dataset so the model learns signal, not formatting noise |
| **Null handling** | Nulls are filled where business logic supports a default, flagged or categorized where it does not | -- | -- |
| **Deduplication** | Duplicate records are resolved so they do not inflate counts or skew totals | The corpus is deduplicated across documents, including near-duplicates, to prevent skewed retrieval rankings and over-indexing on repeated content | Strict deduplication prevents duplicate examples from overweighting specific patterns in the training distribution |
| **Business rule validation** | Key metrics pass validation against known rules (e.g., ship date is not earlier than purchase date) | -- | -- |
| **Documentation** | Known data quality issues are documented with their magnitude so consumers can interpret results in context | -- | -- |
| **Noise removal** | -- | Boilerplate, navigation text, headers/footers, and off-topic content are removed before embedding. Every chunk in the index carries signal | -- |
| **PII redaction** | -- | PII is redacted from all source documents. Retrieved content may be surfaced to end users with minimal transformation | PII is fully redacted. Models memorize training data and can reproduce PII at inference time |
| **Factual accuracy** | -- | Source content is factually accurate. A RAG system can surface a single wrong document as a definitive answer | -- |
| **Bias auditing** | -- | -- | The training distribution is audited for underrepresentation, skewed label distributions, and demographic imbalances before training |
| **Harmful content removal** | -- | -- | Toxic language, unsafe code patterns, and adversarial examples are absent from the training set |
| **Label validation** | -- | -- | Labels and annotations are validated. Mislabeled data teaches the model to be wrong |
| **Dataset versioning** | -- | -- | Training datasets are versioned with immutable snapshots bound to specific model versions |

## The Common Thread

Across all three levels, the same principles hold: preserve original data, document every decision, and never discard records without confidence in the decision. What changes is the rigor required and the consequences of failure.

Clean data is Factor 0 because nothing else in the framework matters without it. Context, consumability, freshness, lineage, and compliance all assume that the underlying data is trustworthy. If it isn't, you are building on a foundation that will fail -- not loudly or immediately, but quietly and pervasively.

## Required Stack Capabilities

What the platform must support to consistently meet these requirements. Each level is additive.

| Capability | L1 | L2 | L3 |
|---|---|---|---|
| **Validation & quality checks** | Schema validation enforced at ingestion (type checks, range constraints, mandatory fields) | -- | Automated quality gates that block training runs when data quality thresholds are not met |
| **Profiling & baselines** | Data profiling to establish and track quality baselines over time | -- | Distribution drift monitoring that compares incoming data against the distribution the model was trained on |
| **Deduplication** | Deduplication logic applied during ingestion or transformation | Corpus-level deduplication with similarity detection for near-duplicates across documents | -- |
| **Alerting** | Alerting on validation rule failures so issues are surfaced, not silently propagated | -- | -- |
| **PII detection** | -- | PII detection and redaction applied before content enters the embedding pipeline | -- |
| **Content versioning** | -- | Content versioning so you know exactly what is in the index at any point in time | Dataset versioning with immutable snapshots bound to specific model versions |
| **Re-indexing / reprocessing** | -- | Re-indexing workflows that allow source documents to be corrected and re-embedded without rebuilding the entire index | -- |
| **Quality monitoring** | -- | Retrieval quality monitoring -- visibility into which chunks are being surfaced, how frequently, and whether they produce satisfactory responses | -- |
| **Label validation** | -- | -- | Label validation workflows, including inter-annotator agreement metrics where human labeling is involved |
