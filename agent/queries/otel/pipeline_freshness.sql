-- factor: current
-- requirement: pipeline_freshness
-- requires: otel
-- target_type: database
-- description: Measures pipeline freshness from OTEL span timestamps. Shows the time since each pipeline last completed successfully. Pipelines that haven't run recently indicate stale data.

SELECT
    service_name,
    span_name,
    MAX(end_time) AS last_successful_run,
    EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - MAX(end_time))) / 3600.0 AS hours_since_last_run,
    COUNT(*) AS runs_last_7_days
FROM otel_traces
WHERE start_time >= CURRENT_TIMESTAMP - INTERVAL '7 days'
  AND status_code = 'OK'
  AND parent_span_id IS NULL
GROUP BY service_name, span_name
ORDER BY hours_since_last_run DESC
