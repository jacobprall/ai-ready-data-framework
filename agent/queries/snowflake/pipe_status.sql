-- factor: current
-- requirement: pipeline_health
-- requires: snowflake
-- target_type: database
-- description: Lists Snowpipe status for all pipes. Active pipes with recent errors indicate freshness and reliability issues.

SELECT
    pipe_catalog,
    pipe_schema,
    pipe_name,
    is_autoingest_enabled,
    notification_channel_name,
    created,
    last_altered
FROM information_schema.pipes
WHERE pipe_schema NOT IN ('INFORMATION_SCHEMA')
ORDER BY last_altered DESC
