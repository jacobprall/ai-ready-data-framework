# Remediation: PII Detection Rate

**Requirement:** `pii_detection_rate`
**Factor:** Clean
**Thresholds:** L1: not assessed, L2: 0%, L3: 0%

## What It Means

The percentage of values in a string column that match common PII patterns (SSN, email address, phone number). Any PII in data used for RAG or training is a compliance and safety risk.

## Why It Matters

- **L2 (RAG):** PII in source documents will be surfaced verbatim to end users. This is a legal liability.
- **L3 (Training):** Models memorize training data. PII in the training set can be reproduced at inference time.

## Fix Patterns

**Option 1: Mask PII values in place**

```sql
UPDATE {schema}.{table}
SET {column} = REGEXP_REPLACE({column}, '[0-9]{3}-[0-9]{2}-[0-9]{4}', '***-**-****')
WHERE {column} SIMILAR TO '[0-9]{3}-[0-9]{2}-[0-9]{4}';
```

**Option 2: Apply a masking policy (Snowflake)**

```sql
CREATE MASKING POLICY pii_mask AS (val STRING) RETURNS STRING ->
    CASE WHEN CURRENT_ROLE() IN ('ANALYST') THEN '***MASKED***' ELSE val END;

ALTER TABLE {schema}.{table} ALTER COLUMN {column} SET MASKING POLICY pii_mask;
```

**Option 3: Hash PII values**

```sql
UPDATE {schema}.{table}
SET {column} = SHA2({column}, 256)
WHERE {column} IS NOT NULL;
```

## What to Generate

For each column with detected PII patterns, show a sample of matched values (redacted) so the user can confirm they are genuine PII. Then generate the appropriate masking approach for their platform.
