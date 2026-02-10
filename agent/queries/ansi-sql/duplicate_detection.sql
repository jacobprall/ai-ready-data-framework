-- factor: clean
-- requirement: duplicate_rate
-- requires: ansi-sql
-- target_type: column
-- description: Measures the rate of duplicate values in a candidate key column

SELECT
    1.0 - (CAST(COUNT(DISTINCT "{column}") AS FLOAT) / NULLIF(COUNT("{column}"), 0)) AS measured_value
FROM "{schema}"."{table}"
