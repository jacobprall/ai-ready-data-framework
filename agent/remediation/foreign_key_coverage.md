# Remediation: Foreign Key Coverage

**Requirement:** `foreign_key_coverage`
**Factor:** Contextual
**Thresholds:** L1: ≥10%, L2: ≥30%, L3: ≥50%

## What It Means

The percentage of columns ending in `_id` that have declared foreign key constraints. Undeclared relationships mean AI systems can't discover how tables relate to each other.

## Why It Matters

- **L1 (Analytics):** Analysts must rely on tribal knowledge to know which tables join on which keys.
- **L2 (RAG):** Without declared relationships, the system can't traverse entity graphs to find related context.
- **L3 (Training):** Feature engineering across related tables requires known relationships. Undeclared FKs lead to incorrect joins.

## Fix Patterns

```sql
ALTER TABLE {schema}.{table}
ADD CONSTRAINT fk_{table}_{column}
FOREIGN KEY ({column}) REFERENCES {referenced_schema}.{referenced_table}({referenced_column});
```

**Note:** Some platforms (Snowflake) support FK declarations for documentation purposes without enforcement. This still helps AI systems discover relationships.

## What to Generate

For each `_id` column without a FK constraint, attempt to infer the referenced table from the column name (e.g., `customer_id` likely references `customers.id`). Generate the ALTER TABLE statement. Flag cases where the reference is ambiguous and ask the user to confirm.
