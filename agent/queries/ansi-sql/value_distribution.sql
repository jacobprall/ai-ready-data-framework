-- factor: clean
-- requirement: value_distribution
-- requires: ansi-sql
-- target_type: column
-- description: Computes distribution statistics for a numeric column

SELECT
    MIN("{column}") AS min_value,
    MAX("{column}") AS max_value,
    AVG("{column}") AS avg_value,
    STDDEV("{column}") AS stddev_value,
    COUNT("{column}") AS non_null_count
FROM "{schema}"."{table}"
