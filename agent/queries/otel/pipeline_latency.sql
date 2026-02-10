-- factor: consumable
-- requirement: pipeline_latency
-- requires: otel
-- target_type: database
-- description: Measures pipeline execution latency from OTEL spans. Shows average and p95 duration per pipeline. High latency impacts data freshness and system responsiveness.

SELECT
    service_name,
    span_name,
    COUNT(*) AS execution_count,
    AVG(EXTRACT(EPOCH FROM (end_time - start_time))) AS avg_duration_seconds,
    PERCENTILE_CONT(0.95) WITHIN GROUP (
        ORDER BY EXTRACT(EPOCH FROM (end_time - start_time))
    ) AS p95_duration_seconds,
    MAX(EXTRACT(EPOCH FROM (end_time - start_time))) AS max_duration_seconds
FROM otel_traces
WHERE start_time >= CURRENT_TIMESTAMP - INTERVAL '7 days'
  AND parent_span_id IS NULL
GROUP BY service_name, span_name
ORDER BY p95_duration_seconds DESC
