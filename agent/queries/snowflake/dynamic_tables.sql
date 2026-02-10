-- factor: current
-- requirement: pipeline_freshness
-- requires: snowflake
-- target_type: database
-- description: Lists Dynamic Tables and their refresh status. Dynamic Tables with lag indicate freshness issues.

SELECT
    name,
    schema_name,
    target_lag,
    refresh_mode,
    scheduling_state
FROM information_schema.dynamic_tables
WHERE schema_name NOT IN ('INFORMATION_SCHEMA')
ORDER BY name
