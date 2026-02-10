-- factor: current
-- requirement: table_freshness
-- requires: snowflake
-- target_type: database
-- description: Measures table freshness using Snowflake's TABLE_STORAGE_METRICS last_altered timestamp. More reliable than querying MAX(timestamp_col) on each table.

SELECT
    table_schema,
    table_name,
    DATEDIFF('hour', last_altered, CURRENT_TIMESTAMP()) AS hours_since_last_altered,
    row_count
FROM information_schema.tables
WHERE table_schema NOT IN ('INFORMATION_SCHEMA')
  AND table_type = 'BASE TABLE'
ORDER BY last_altered DESC
