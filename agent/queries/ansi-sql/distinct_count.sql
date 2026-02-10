-- factor: clean
-- requirement: cardinality
-- requires: ansi-sql
-- target_type: column
-- description: Counts distinct values and total non-null values for a column. Used by the generator to classify column cardinality.

SELECT
    COUNT(DISTINCT "{column}") AS distinct_count,
    COUNT("{column}") AS non_null_count,
    COUNT(*) AS total_count
FROM "{schema}"."{table}"
