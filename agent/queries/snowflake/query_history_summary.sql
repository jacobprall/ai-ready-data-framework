-- factor: consumable
-- requirement: access_pattern_analysis
-- requires: snowflake
-- target_type: database
-- description: Summarizes query patterns over the last 7 days from QUERY_HISTORY. Shows whether data is being accessed programmatically (connectors, APIs) vs interactively (worksheets).

SELECT
    client_application_id,
    COUNT(*) AS query_count,
    AVG(total_elapsed_time) / 1000.0 AS avg_duration_seconds,
    MAX(total_elapsed_time) / 1000.0 AS max_duration_seconds,
    SUM(rows_produced) AS total_rows_produced
FROM snowflake.account_usage.query_history
WHERE start_time >= DATEADD('day', -7, CURRENT_TIMESTAMP())
  AND query_type = 'SELECT'
  AND execution_status = 'SUCCESS'
GROUP BY client_application_id
ORDER BY query_count DESC
LIMIT 20
