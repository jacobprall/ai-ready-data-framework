# Factor 2: Contextual [draft]

**Definition:** Contextual data carries canonical semantics—meaning is explicit and co-located.

## Why It Matters

Without context, AI systems misinterpret or infer meaning based on training data. A column named "status" means nothing without knowing what entity it describes and what values are valid. When AI systems guess at meaning, they introduce subtle errors that compound across decisions.

## Requirements

- Semantic layer or data catalog with business definitions
- Metadata co-located with data
- Consistent terminology across sources
- Documented relationships between entities
- Versioned schemas with documented evolution policies

## Key Questions

- Can a new team member understand your data without tribal knowledge?
- Is business logic encoded in the data layer or scattered across applications?
- How do you handle schema changes across dependent systems?
