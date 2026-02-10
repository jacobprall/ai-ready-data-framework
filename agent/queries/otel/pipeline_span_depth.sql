-- factor: correlated
-- requirement: lineage_depth
-- requires: otel
-- target_type: database
-- description: Measures pipeline complexity from OTEL span depth. Deeper span trees indicate more transformation stages between source and destination. Deeper pipelines need better lineage tracking to debug issues.

SELECT
    trace_id,
    COUNT(*) AS span_count,
    MAX(
        CASE
            WHEN parent_span_id IS NULL THEN 0
            ELSE 1
        END
    ) AS has_children,
    COUNT(DISTINCT service_name) AS services_involved
FROM otel_traces
WHERE start_time >= CURRENT_TIMESTAMP - INTERVAL '7 days'
GROUP BY trace_id
HAVING COUNT(*) > 1
ORDER BY span_count DESC
LIMIT 100
