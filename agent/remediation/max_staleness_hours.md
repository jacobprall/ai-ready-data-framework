# Remediation: Max Staleness Hours

**Requirement:** `max_staleness_hours`
**Factor:** Current
**Thresholds:** L1: ≤168 hours (7 days), L2: ≤24 hours, L3: ≤6 hours

## What It Means

The number of hours since the most recent value in a timestamp column. Higher values indicate stale data.

## Why It Matters

- **L1 (Analytics):** Week-old data is acceptable for most reporting. Month-old data is not.
- **L2 (RAG):** A RAG system retrieving day-old content may present outdated information as current fact.
- **L3 (Training):** Models trained on stale data learn patterns that no longer reflect reality. The model is confident but wrong.

## Fix Patterns

**Option 1: Check pipeline status**

This is usually a pipeline problem, not a data problem. Check whether the pipeline that feeds this table is running, failing, or delayed.

```sql
-- Snowflake: Check COPY_HISTORY for recent loads
SELECT * FROM snowflake.account_usage.copy_history
WHERE table_name = '{table}' ORDER BY last_load_time DESC LIMIT 5;

-- Check the last write time
SELECT MAX({timestamp_column}) AS last_value FROM {schema}.{table};
```

**Option 2: Set up freshness monitoring**

Configure an alert when data exceeds the staleness threshold:

```sql
-- Snowflake: Create an alert
CREATE ALERT {schema}.alert_{table}_freshness
WAREHOUSE = {warehouse}
SCHEDULE = 'USING CRON 0 * * * * UTC'
IF (EXISTS (
    SELECT 1 FROM {schema}.{table}
    WHERE DATEDIFF('hour', MAX({timestamp_column}), CURRENT_TIMESTAMP()) > {threshold}
))
THEN CALL SYSTEM$SEND_EMAIL(...);
```

## What to Generate

For each table exceeding the staleness threshold, show the current staleness value and the threshold it violates. Suggest checking the upstream pipeline. If the table has no pipeline (it's manually loaded), flag that as a process issue.
