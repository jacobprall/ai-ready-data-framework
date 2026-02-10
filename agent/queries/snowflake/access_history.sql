-- factor: compliant
-- requirement: access_auditing
-- requires: snowflake
-- target_type: database
-- description: Checks Snowflake ACCESS_HISTORY for data access tracking over the last 30 days. Verifies that access events are being recorded and provides access pattern summary.

SELECT
    COUNT(*) AS total_access_events,
    COUNT(DISTINCT user_name) AS distinct_users,
    COUNT(DISTINCT query_id) AS distinct_queries,
    MIN(query_start_time) AS earliest_event,
    MAX(query_start_time) AS latest_event,
    DATEDIFF('hour', MAX(query_start_time), CURRENT_TIMESTAMP()) AS hours_since_last_access
FROM snowflake.account_usage.access_history
WHERE query_start_time >= DATEADD('day', -30, CURRENT_TIMESTAMP())
