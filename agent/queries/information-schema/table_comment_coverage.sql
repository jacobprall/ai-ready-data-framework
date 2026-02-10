-- factor: contextual
-- requirement: table_comment_coverage
-- requires: information-schema
-- target_type: database
-- description: Measures the percentage of tables that have non-empty comments/descriptions across assessed schemas

SELECT
    CAST(
        SUM(CASE WHEN t.comment IS NOT NULL AND t.comment != '' THEN 1 ELSE 0 END) AS FLOAT
    ) / NULLIF(COUNT(*), 0) AS measured_value
FROM information_schema.tables t
WHERE t.table_schema NOT IN ('information_schema', 'pg_catalog', 'INFORMATION_SCHEMA')
  AND t.table_type IN ('BASE TABLE', 'TABLE', 'VIEW')
