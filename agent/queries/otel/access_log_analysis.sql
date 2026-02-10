-- factor: compliant
-- requirement: access_auditing
-- requires: otel
-- target_type: database
-- description: Analyzes data access patterns from OTEL spans. Shows which services access data, how frequently, and whether access is logged with sufficient detail for compliance audits.

SELECT
    service_name,
    span_name,
    COUNT(*) AS access_count,
    COUNT(DISTINCT trace_id) AS distinct_sessions,
    MIN(start_time) AS first_access,
    MAX(start_time) AS last_access,
    COUNT(DISTINCT attributes->>'db.name') AS distinct_databases,
    COUNT(DISTINCT attributes->>'db.statement') AS distinct_queries
FROM otel_traces
WHERE start_time >= CURRENT_TIMESTAMP - INTERVAL '30 days'
  AND (
    attributes->>'db.system' IS NOT NULL
    OR span_name LIKE '%query%'
    OR span_name LIKE '%read%'
    OR span_name LIKE '%select%'
  )
GROUP BY service_name, span_name
ORDER BY access_count DESC
