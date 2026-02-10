-- factor: correlated
-- requirement: lineage_coverage
-- requires: otel
-- target_type: database
-- description: Traces data pipeline lineage from OTEL spans. Each span represents a pipeline stage. Parent-child span relationships reveal the full data flow from source to destination.

SELECT
    service_name,
    span_name,
    COUNT(*) AS execution_count,
    COUNT(DISTINCT trace_id) AS distinct_traces,
    COUNT(DISTINCT parent_span_id) AS distinct_parents,
    AVG(EXTRACT(EPOCH FROM (end_time - start_time))) AS avg_duration_seconds,
    MAX(end_time) AS last_execution
FROM otel_traces
WHERE start_time >= CURRENT_TIMESTAMP - INTERVAL '7 days'
  AND status_code != 'ERROR'
GROUP BY service_name, span_name
ORDER BY execution_count DESC
