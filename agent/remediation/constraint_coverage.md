# Remediation: Constraint Coverage

**Requirement:** `constraint_coverage`
**Factor:** Correlated
**Thresholds:** L1: ≥50%, L2: ≥70%, L3: ≥90%

## What It Means

The percentage of tables that have at least one primary key or unique constraint. Tables without constraints have no declared identity -- you can't reliably join, deduplicate, or trace records.

## Why It Matters

- **L1 (Analytics):** Without PKs, joins produce unexpected fan-outs and deduplication is guesswork.
- **L2 (RAG):** Without unique identifiers, you can't trace a retrieved chunk back to its source record.
- **L3 (Training):** Without PKs, dataset versioning and reproducibility are impossible. You can't identify which records were in which training run.

## Fix Patterns

**Option 1: Add a primary key**

```sql
ALTER TABLE {schema}.{table} ADD CONSTRAINT pk_{table} PRIMARY KEY ({column});
```

**Option 2: Add a unique constraint** (if no single column is unique)

```sql
ALTER TABLE {schema}.{table} ADD CONSTRAINT uq_{table} UNIQUE ({column1}, {column2});
```

**Option 3: Add a surrogate key** (if no natural key exists)

```sql
ALTER TABLE {schema}.{table} ADD COLUMN id SERIAL PRIMARY KEY;
```

## What to Generate

For each table without constraints, examine the columns. If a column named `id` or `*_id` exists, suggest it as the primary key. If the table has a natural composite key (order_id + line_number), suggest a composite PK. If no key is obvious, suggest a surrogate key and flag it for the user to confirm.
