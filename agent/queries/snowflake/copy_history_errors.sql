-- factor: clean
-- requirement: ingestion_error_rate
-- requires: snowflake
-- target_type: database
-- description: Measures ingestion error rate from COPY_HISTORY over the last 30 days. High error rates indicate data quality issues at the source.

SELECT
    CAST(
        SUM(CASE WHEN status = 'LOAD_FAILED' THEN 1 ELSE 0 END) AS FLOAT
    ) / NULLIF(COUNT(*), 0) AS measured_value,
    COUNT(*) AS total_loads,
    SUM(CASE WHEN status = 'LOAD_FAILED' THEN 1 ELSE 0 END) AS failed_loads,
    SUM(rows_loaded) AS total_rows_loaded,
    SUM(errors_seen) AS total_errors_seen
FROM snowflake.account_usage.copy_history
WHERE last_load_time >= DATEADD('day', -30, CURRENT_TIMESTAMP())
