-- factor: current
-- requirement: table_freshness
-- requires: databricks
-- target_type: table
-- description: Measures table freshness using Delta table history. Returns hours since the last write operation.

SELECT
    TIMESTAMPDIFF(
        HOUR,
        MAX(timestamp),
        CURRENT_TIMESTAMP()
    ) AS measured_value
FROM (
    DESCRIBE HISTORY "{schema}"."{table}"
)
WHERE operation IN ('WRITE', 'MERGE', 'DELETE', 'UPDATE', 'STREAMING UPDATE')
