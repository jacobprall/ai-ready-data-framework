# Remediation: Null Rate

**Requirement:** `null_rate`
**Factor:** Clean
**Thresholds:** L1: ≤10%, L2: ≤5%, L3: ≤1%

## What It Means

The percentage of rows where this column has no value. High null rates indicate missing data that degrades analysis accuracy, retrieval quality, or model training.

## Why It Matters

- **L1 (Analytics):** Nulls cause aggregations to silently exclude rows, producing misleading totals and averages.
- **L2 (RAG):** Missing values in indexed content create incomplete context that the model retrieves and presents as if it were complete.
- **L3 (Training):** Models trained on data with high null rates learn that "missing" is a valid pattern, degrading prediction quality.

## Fix Patterns

**Option 1: Set a default value** (when a business-appropriate default exists)

```sql
-- Add a default for future inserts
ALTER TABLE {schema}.{table} ALTER COLUMN {column} SET DEFAULT '{default_value}';

-- Backfill existing nulls
UPDATE {schema}.{table} SET {column} = '{default_value}' WHERE {column} IS NULL;
```

**Option 2: Backfill from a related table** (when the value can be derived)

```sql
UPDATE {schema}.{table} t
SET {column} = source.{column}
FROM {related_table} source
WHERE t.{join_key} = source.{join_key}
  AND t.{column} IS NULL;
```

**Option 3: Categorize as explicit unknown** (when the absence is meaningful)

```sql
UPDATE {schema}.{table} SET {column} = 'Unknown' WHERE {column} IS NULL;
```

**Option 4: Document and accept** (when nulls are expected and the rate is within tolerance)

No code change needed. Document the expected null rate and why it's acceptable.

## What to Generate

For each failing column, generate Option 1 or Option 3 with the user's actual schema, table, and column names. If the column type is numeric, suggest `0` or `-1` as defaults only if the domain supports it. If the column is a string, suggest `'Unknown'`. Always present as a suggestion for review.
