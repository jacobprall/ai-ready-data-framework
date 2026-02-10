# Remediation: PII Column Name Rate

**Requirement:** `pii_column_name_rate`
**Factor:** Compliant
**Thresholds:** L1: ≤100% (not assessed), L2: 0%, L3: 0%

## What It Means

The percentage of columns with names that suggest PII content (ssn, email, phone, address, birth, salary, etc.). These columns should have masking policies or explicit documentation confirming they don't contain actual PII.

## Why It Matters

- **L2 (RAG):** Columns named "email" or "phone" likely contain PII that will appear in retrieved content.
- **L3 (Training):** PII-named columns in training data are high-risk for memorization and reproduction by the model.

## Fix Patterns

**Option 1: Apply masking policies (Snowflake)**

```sql
CREATE OR REPLACE MASKING POLICY mask_{column} AS (val STRING) RETURNS STRING ->
    CASE
        WHEN CURRENT_ROLE() IN ('DATA_ENGINEER', 'ADMIN') THEN val
        ELSE '***MASKED***'
    END;

ALTER TABLE {schema}.{table} ALTER COLUMN {column} SET MASKING POLICY mask_{column};
```

**Option 2: Apply column tags (Databricks)**

```sql
ALTER TABLE {schema}.{table} ALTER COLUMN {column} SET TAGS ('pii' = 'true', 'pii_type' = 'email');
```

**Option 3: Document that the column is safe** (if it doesn't actually contain PII)

```sql
COMMENT ON COLUMN {schema}.{table}.{column} IS 'Not PII: contains system-generated email aliases, not personal email addresses.';
```

## What to Generate

List every PII-named column detected. For each, generate the masking policy or tag statement appropriate for the user's platform. If the user confirms a column doesn't contain actual PII, generate Option 3.
