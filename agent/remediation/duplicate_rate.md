# Remediation: Duplicate Rate

**Requirement:** `duplicate_rate`
**Factor:** Clean
**Thresholds:** L1: ≤5%, L2: ≤2%, L3: ≤0.1%

## What It Means

The percentage of non-unique values in a column expected to be unique (primary keys, candidate keys, `*_id` columns). Duplicates inflate counts, skew aggregations, and cause join fan-outs.

## Why It Matters

- **L1 (Analytics):** Duplicates produce inflated metrics and incorrect counts.
- **L2 (RAG):** Duplicate records in the corpus cause the model to over-index on repeated content.
- **L3 (Training):** Duplicate training examples overweight specific patterns, biasing the model.

## Fix Patterns

**Option 1: Identify and investigate duplicates**

```sql
SELECT {column}, COUNT(*) AS duplicate_count
FROM {schema}.{table}
GROUP BY {column}
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC
LIMIT 20;
```

**Option 2: Deduplicate by keeping the most recent record**

```sql
DELETE FROM {schema}.{table}
WHERE ctid NOT IN (
    SELECT DISTINCT ON ({column}) ctid
    FROM {schema}.{table}
    ORDER BY {column}, updated_at DESC
);
```

**Option 3: Add a unique constraint to prevent future duplicates**

```sql
ALTER TABLE {schema}.{table} ADD CONSTRAINT uq_{table}_{column} UNIQUE ({column});
```

**Option 4: Create a deduplicated view**

```sql
CREATE VIEW {schema}.{table}_deduped AS
SELECT DISTINCT ON ({column}) *
FROM {schema}.{table}
ORDER BY {column}, updated_at DESC;
```

## What to Generate

First generate Option 1 to help the user understand the scope. Then suggest Option 3 to prevent future duplicates. If the duplicate rate is high, suggest Option 4 as an intermediate step that doesn't require data deletion.
