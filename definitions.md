# Definitions

Canonical definitions for the AI-Ready Data project. A short summary appears in the framework README; this document is the source of truth.

---

## AI-ready data

**AI-ready data** is data that meets the criteria of the six factors (Clean, Contextual, Consumable, Current, Correlated, Compliant) for the **workload (use case)** you target. The factors define what the data layer must provide so that what crosses the boundary into the AI system is fit for consumption.

Whether data is "AI-ready" is therefore relative to your use case. We use three workloads: descriptive analytics and BI, RAG and retrieval systems, and ML model training and fine-tuning. In tables and config these are referred to by the short names **L1**, **L2**, and **L3** (ordered by strictness of requirements, not by maturity). The same dataset may be ready for analytics (L1) but not yet for training (L3).

---

## Data layer and AI system boundary

An **AI system** performs inference: it accepts inputs, applies a learned function, and produces outputs. The boundary of the AI system is the model and its inference layer. Everything outside that boundary—ingestion, transformation, storage, serving—is the **data layer**. The data layer's job is to ensure that what crosses the boundary is fit for consumption. Assessment evaluates the data layer against the factors; it does not evaluate the model or inference logic.

---

## Data product

A **data product** is a named, bounded set of data assets maintained by a defined owner to serve a specific business function. It is the primary unit of assessment. The agent evaluates data products against the six factors; a platform's AI-readiness is the aggregate readiness of its data products.

A data product has a **name** (user-declared, e.g. "customer_360"), an optional **owner** (team or person), a set of **assets** (tables, schemas, or patterns), and an optional **target workload** (per-product override of L1/L2/L3). When no data products are defined, the agent treats all discovered assets as a single unnamed product.

---

## Data asset

A **data asset** is a concrete object within a data product: e.g. a table and column in a relational system, a collection and field in a document store, or an index in a search engine. Checks are run *against* data assets; results roll up to the data product level. Some checks also evaluate **platform capabilities** (e.g. whether the platform exposes lineage, masking, or freshness metadata).

---

## Workloads (use cases)

Requirements differ by **use case**: what you are building (serving  or training) determines how strict the requirements are. We define three workloads.

Requirements and thresholds are defined per factor and per workload. Meeting a stricter workload implies meeting the less strict ones for that requirement (additivity).

---

## Factor

A **factor** is one of six high-level categories of AI-readiness: Clean (0), Contextual (1), Consumable (2), Current (3), Correlated (4), Compliant (5). Each factor has a definition, capabilities per workload (L1/L2/L3), and platform-specific check operations. Checks are tagged by factor and capability.
