# Remediation: Timestamp Column Coverage

**Requirement:** `timestamp_column_coverage`
**Factor:** Current
**Thresholds:** L1: ≥25%, L2: ≥50%, L3: ≥80%

## What It Means

The percentage of tables that have at least one timestamp column (created_at, updated_at, event_time, etc.). Tables without timestamps have no way to assess freshness.

## Why It Matters

- **L1 (Analytics):** Without timestamps, you can't tell when data was created or last updated. Trend analysis is impossible.
- **L2 (RAG):** Without timestamps, the system can't prioritize recent content or detect stale documents.
- **L3 (Training):** Without timestamps, you can't build time-aware features, detect distribution drift, or determine whether training data represents the current state.

## Fix Patterns

**Option 1: Add a timestamp column**

```sql
ALTER TABLE {schema}.{table} ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE {schema}.{table} ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
```

**Option 2: Add a trigger to auto-update the timestamp**

```sql
-- PostgreSQL
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_updated_at
    BEFORE UPDATE ON {schema}.{table}
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
```

## What to Generate

For each table without any timestamp column, generate an ALTER TABLE statement to add `created_at` and `updated_at` columns with appropriate defaults. Note that existing rows will have NULL for `created_at` unless the user backfills.
