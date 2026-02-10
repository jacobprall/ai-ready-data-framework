# Remediation: Column Comment Coverage

**Requirement:** `column_comment_coverage`
**Factor:** Contextual
**Thresholds:** L1: ≥25%, L2: ≥50%, L3: ≥80%

## What It Means

The percentage of columns in a table that have descriptions (comments). Undocumented columns force AI systems to guess at meaning based on column names alone.

## Why It Matters

- **L1 (Analytics):** Analysts spend time asking colleagues what columns mean instead of analyzing data.
- **L2 (RAG):** The model infers column meaning from training priors, not your business definitions. "status" could mean anything.
- **L3 (Training):** Ambiguous feature definitions lead to models that learn the wrong relationships.

## Fix Patterns

**Generate COMMENT ON COLUMN for each undocumented column:**

```sql
COMMENT ON COLUMN {schema}.{table}.{column} IS '{description}';
```

**Snowflake syntax:**

```sql
ALTER TABLE {schema}.{table} ALTER COLUMN {column} COMMENT '{description}';
```

**Databricks syntax:**

```sql
ALTER TABLE {schema}.{table} ALTER COLUMN {column} COMMENT '{description}';
```

## What to Generate

For each table that fails this check, list every column that lacks a comment. Generate a `COMMENT ON COLUMN` statement for each, using the column name and data type to suggest a reasonable description. For example:

- `customer_id` (INTEGER) -> "Unique identifier for the customer"
- `created_at` (TIMESTAMP) -> "Timestamp when the record was created"
- `usd_price` (DECIMAL) -> "Price in US dollars"
- `status` (VARCHAR) -> "Current status of the [entity]. Valid values: [ask the user]"

For ambiguous columns (like `status`, `type`, `flag`), generate the statement with a placeholder and ask the user to fill in the business definition.
