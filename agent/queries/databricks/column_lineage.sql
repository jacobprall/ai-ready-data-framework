-- factor: correlated
-- requirement: column_lineage_coverage
-- requires: databricks
-- target_type: database
-- description: Checks Unity Catalog column-level lineage. Measures whether column-level lineage is tracked, indicating fine-grained traceability.

SELECT
    COUNT(DISTINCT target_column_name) AS columns_with_lineage,
    COUNT(DISTINCT CONCAT(target_table_full_name, '.', target_column_name)) AS total_lineage_entries
FROM system.access.column_lineage
WHERE target_type = 'TABLE'
