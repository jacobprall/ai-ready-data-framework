-- factor: clean
-- requirement: null_rate
-- requires: ansi-sql
-- target_type: column
-- description: Measures the null rate for a specific column

SELECT
    CAST(COUNT(*) - COUNT("{column}") AS FLOAT) / NULLIF(COUNT(*), 0) AS measured_value
FROM "{schema}"."{table}"
