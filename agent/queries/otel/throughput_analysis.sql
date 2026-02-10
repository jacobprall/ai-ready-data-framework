-- factor: clean
-- requirement: data_loss_detection
-- requires: otel
-- target_type: database
-- description: Compares rows-in vs rows-out across pipeline stages using OTEL span attributes. A significant drop between stages indicates data loss. Requires pipelines to set row count attributes on spans.

SELECT
    service_name,
    span_name,
    AVG(CAST(attributes->>'rows.input' AS FLOAT)) AS avg_rows_in,
    AVG(CAST(attributes->>'rows.output' AS FLOAT)) AS avg_rows_out,
    CASE
        WHEN AVG(CAST(attributes->>'rows.input' AS FLOAT)) > 0
        THEN 1.0 - (
            AVG(CAST(attributes->>'rows.output' AS FLOAT)) /
            AVG(CAST(attributes->>'rows.input' AS FLOAT))
        )
        ELSE NULL
    END AS measured_value
FROM otel_traces
WHERE start_time >= CURRENT_TIMESTAMP - INTERVAL '7 days'
  AND attributes->>'rows.input' IS NOT NULL
  AND attributes->>'rows.output' IS NOT NULL
GROUP BY service_name, span_name
HAVING AVG(CAST(attributes->>'rows.input' AS FLOAT)) > 0
ORDER BY measured_value DESC
