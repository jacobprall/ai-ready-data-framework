# Remediation: Table Comment Coverage

**Requirement:** `table_comment_coverage`
**Factor:** Contextual
**Thresholds:** L1: ≥25%, L2: ≥50%, L3: ≥80%

## What It Means

The percentage of tables that have descriptions explaining their grain, purpose, and source.

## Why It Matters

- **L1 (Analytics):** Analysts waste time figuring out which table to use for which question.
- **L2 (RAG):** Without table descriptions, the system can't determine which tables are relevant to a query.
- **L3 (Training):** Feature engineering requires understanding what each table represents. Missing documentation leads to incorrect feature construction.

## Fix Patterns

```sql
COMMENT ON TABLE {schema}.{table} IS '{description}';
```

## What to Generate

For each table without a comment, generate a `COMMENT ON TABLE` statement. Infer the description from the table name, its columns, and its relationships. For example:

- `orders` -> "Customer orders. One row per order. Primary key: order_id."
- `customers` -> "Customer master data. One row per customer."
- `order_items` -> "Line items within orders. Foreign key: order_id references orders."

Include the grain (what one row represents) and the primary key in every description.
