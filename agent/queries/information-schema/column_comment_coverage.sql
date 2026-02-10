-- factor: contextual
-- requirement: column_comment_coverage
-- requires: information-schema
-- target_type: table
-- description: Measures the percentage of columns that have non-empty comments/descriptions

SELECT
    CAST(
        SUM(CASE WHEN comment IS NOT NULL AND comment != '' THEN 1 ELSE 0 END) AS FLOAT
    ) / NULLIF(COUNT(*), 0) AS measured_value
FROM information_schema.columns
WHERE table_schema = '{schema}'
  AND table_name = '{table}'
