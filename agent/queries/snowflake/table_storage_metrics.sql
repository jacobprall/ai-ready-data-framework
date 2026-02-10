-- factor: clean
-- requirement: table_profiling
-- requires: snowflake
-- target_type: database
-- description: Uses ACCOUNT_USAGE.TABLE_STORAGE_METRICS for row counts and storage without scanning tables. More efficient than COUNT(*) on large tables.

SELECT
    table_catalog,
    table_schema,
    table_name,
    active_bytes,
    time_travel_bytes,
    failsafe_bytes,
    row_count
FROM snowflake.account_usage.table_storage_metrics
WHERE table_catalog = CURRENT_DATABASE()
  AND table_schema NOT IN ('INFORMATION_SCHEMA')
  AND deleted IS NULL
ORDER BY active_bytes DESC
