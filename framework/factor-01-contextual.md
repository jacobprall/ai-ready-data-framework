# Factor 1: Contextual

**Definition:** Contextual data carries canonical semantics -- meaning is explicit and co-located.

## The Shift

A human analyst encountering a column named "status" can ask a colleague what it means. AI systems resolve ambiguity through inference, not lookup. Without explicit semantics -- types, enums, relationships, business definitions -- the model fills gaps with priors from training data, producing plausible but wrong interpretations that are invisible at query time. AI systems need meaning to be machine-readable, not just human-readable.

The cost of missing context is different at each workload level. A BI user can check the wiki. A RAG system cannot. A training pipeline will silently encode the ambiguity as a learned pattern.

### Level 1: Descriptive Analytics and BI

**Tolerance for missing context: Moderate.** Analysts can ask questions, check documentation, and use institutional knowledge to interpret ambiguous fields. Missing context slows them down but rarely produces silently wrong results.

### Level 2: RAG and Retrieval Systems

**Tolerance for missing context: Low.** The model must interpret field names, values, and relationships without human assistance. A column named "status" with undocumented enum values will be interpreted using the model's training priors -- which may not match your business's definition.

### Level 3: ML Model Training and Fine-Tuning

**Tolerance for missing context: Very low.** Ambiguous or inconsistent semantics across training data sources produce models that learn contradictory patterns. If "active" means different things in different tables, the model has no way to resolve the conflict. The ambiguity is permanently encoded.

## Requirements

What must be true about the data at each level. Each level is additive.

| Requirement | L1 | L2 | L3 |
|---|---|---|---|
| **Column descriptions** | Key columns have human-readable descriptions so analysts know what they represent | All columns have descriptions that are machine-readable -- co-located with the data, not in a wiki | All columns have descriptions with explicit units, valid ranges, and business definitions |
| **Table descriptions** | Tables have descriptions explaining their grain and purpose | Table descriptions include grain, update frequency, and source system | Table descriptions include ownership, SLA, known limitations, and lineage context |
| **Consistent terminology** | Key terms are used consistently within a single data product | Terminology is consistent across all data products that feed the same AI system | Terminology is standardized across the entire data estate with a controlled vocabulary |
| **Typed fields** | Columns use appropriate data types (dates as dates, numbers as numbers) | Low-cardinality columns have explicit enum definitions or check constraints | All fields carry explicit types, units, valid ranges, and enum definitions |
| **Documented relationships** | Primary keys are declared | Foreign key relationships are declared and enforced | Entity relationships are documented as a graph or ontology that AI systems can traverse |
| **Schema versioning** | Schema changes are tracked in source control | Schema changes are versioned with backward compatibility guarantees | Schema evolution policies are documented with impact analysis across dependent systems |
| **Business logic location** | Business logic is documented somewhere accessible | Business logic is encoded in the data layer (views, transforms), not scattered across applications | All business logic is in the data layer with machine-readable definitions |

## Required Stack Capabilities

What the platform must support to consistently meet these requirements. Each level is additive.

| Capability | L1 | L2 | L3 |
|---|---|---|---|
| **Metadata storage** | Column and table comments supported by the platform | A data catalog or semantic layer with machine-readable definitions | Semantic layer with programmatic access (API, SDK) for AI consumers |
| **Tagging and classification** | -- | Tags and annotations co-located with data objects | Automated classification and tagging based on data content and lineage |
| **Schema management** | Schema tracked in source control | Schema evolution management with versioning | Impact analysis across dependent systems when schemas change |
| **Metadata harvesting** | -- | Automated metadata extraction from pipelines and schemas | Continuous metadata sync between the catalog and all data sources |
| **Relationship documentation** | Primary key constraints enforced | Foreign key constraints declared and queryable | Entity relationship graph or ontology accessible to AI systems |

## Key Questions

- Can a new team member understand your data without tribal knowledge?
- Is business logic encoded in the data layer or scattered across applications?
- How do you handle schema changes across dependent systems?
- What percentage of your columns have descriptions?
