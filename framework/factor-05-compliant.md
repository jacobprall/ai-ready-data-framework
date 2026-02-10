# Factor 5: Compliant

**Definition:** Compliant data meets regulatory requirements with enforced access controls, clear ownership, and auditable AI-specific safeguards.

## The Shift

Traditional governance protects data at rest and in transit -- RBAC, audit logs, encryption. AI introduces entirely new governance surface area. PII can leak through embeddings. Bias can be encoded in training distributions. Model outputs can constitute regulated decisions (credit, hiring, healthcare). GDPR, CCPA, HIPAA, and emerging AI-specific regulations (EU AI Act) impose strict requirements on how data is collected, stored, processed, and used for AI. Traditional controls are necessary but insufficient.

### Level 1: Descriptive Analytics and BI

**Tolerance for compliance gaps: Moderate.** Access controls protect dashboards and reports. PII exposure is limited to analysts with appropriate access. Bias in reports is a presentation issue, not a systemic one. Regulatory risk exists but is bounded by human oversight.

### Level 2: RAG and Retrieval Systems

**Tolerance for compliance gaps: Low.** Retrieved content may be surfaced directly to end users. PII in source documents appears in responses. Biased source material is presented as authoritative. The system may serve regulated content (medical, financial, legal) without appropriate safeguards. Right-to-be-forgotten requests must reach the vector index, not just the source database.

### Level 3: ML Model Training and Fine-Tuning

**Tolerance for compliance gaps: Very low.** PII in training data gets memorized and can be reproduced at inference time. Bias in training distributions gets permanently encoded in model behavior. Model outputs may constitute regulated decisions subject to explainability requirements. Consent must be tracked at the AI use-case level, not just the dataset level. A compliance failure at this level is not a data issue -- it is a product liability.

## Requirements

What must be true about the data at each level. Each level is additive.

| Requirement | L1 | L2 | L3 |
|---|---|---|---|
| **Data ownership** | Key datasets have identified owners | Every dataset has an explicit owner and steward | Ownership is enforced programmatically -- no orphaned datasets, ownership transfers are audited |
| **Access controls** | Role-based access controls exist for sensitive data | RBAC enforced at query time for all data accessed by AI systems | RBAC enforced at query time with column-level and row-level security where required |
| **PII handling** | PII columns are identified | PII is detected and redacted before content enters retrieval indexes | PII is comprehensively redacted from all training data. Detection covers derived representations (embeddings, features, vector stores) |
| **Audit trails** | Access to sensitive data is logged | All data access by AI systems is logged with query-level detail | All data access, transformation, and model consumption is logged with full lineage |
| **Consent tracking** | Data usage policies exist | Consent is tracked per dataset | Consent is tracked at the AI use-case level -- a dataset approved for analytics may not be approved for training |
| **Bias monitoring** | -- | Source content is reviewed for representational bias before indexing | Training data is audited for demographic, categorical, and distributional bias with defined fairness thresholds |
| **Acceptable use policies** | -- | Policies define which datasets can be used for which AI applications | Acceptable use policies are enforced programmatically -- a dataset flagged as "not approved for training" cannot be included in a training pipeline |
| **Right to be forgotten** | Deletion requests are fulfilled in source systems | Deletion propagates to retrieval indexes (re-index after removal) | Deletion propagates to all AI systems including retrained models, cached features, and vector stores |

## Required Stack Capabilities

What the platform must support to consistently meet these requirements. Each level is additive.

| Capability | L1 | L2 | L3 |
|---|---|---|---|
| **Access control** | Role-based access controls on tables and schemas | RBAC enforced at query time with integration into AI serving layers | Column-level and row-level security with dynamic masking for AI workloads |
| **PII detection** | Manual identification of PII columns | Automated PII detection and masking before data enters embedding or retrieval pipelines | Automated PII detection across all representations -- source data, embeddings, features, vector stores |
| **Audit logging** | Access logs for sensitive tables | Query-level audit trails for all AI data access | Full audit trails covering access, transformation, training consumption, and model inference |
| **Data classification** | -- | Tagging and classification of datasets by sensitivity level | Automated classification with policy enforcement (tagged datasets restricted from certain pipelines) |
| **Deletion propagation** | Deletion in source systems | Deletion triggers re-indexing of affected content in retrieval systems | Deletion propagates across all downstream systems with verification |
| **Bias tooling** | -- | Content review tooling for representational bias | Bias detection and fairness metric tracking with threshold-based alerting |
| **Residency and sovereignty** | -- | Data residency controls for regulated jurisdictions | Cross-border data flow controls with automated policy enforcement |

## Key Questions

- Do you have explicit consent to use your data for AI/ML purposes?
- Can you demonstrate compliance to an auditor?
- How do you detect and mitigate bias in training data?
- Can you fulfill a "right to be forgotten" request across all AI systems?
- What percentage of your tables have explicit access controls beyond the default role?
