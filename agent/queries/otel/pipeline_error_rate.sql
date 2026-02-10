-- factor: current
-- requirement: pipeline_reliability
-- requires: otel
-- target_type: database
-- description: Measures pipeline error rates from OTEL spans. High error rates indicate unreliable data delivery, which impacts freshness and completeness.

SELECT
    service_name,
    span_name,
    COUNT(*) AS total_runs,
    SUM(CASE WHEN status_code = 'ERROR' THEN 1 ELSE 0 END) AS error_count,
    CAST(
        SUM(CASE WHEN status_code = 'ERROR' THEN 1 ELSE 0 END) AS FLOAT
    ) / NULLIF(COUNT(*), 0) AS measured_value
FROM otel_traces
WHERE start_time >= CURRENT_TIMESTAMP - INTERVAL '7 days'
  AND parent_span_id IS NULL
GROUP BY service_name, span_name
HAVING COUNT(*) >= 3
ORDER BY measured_value DESC
