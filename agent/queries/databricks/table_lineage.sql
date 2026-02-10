-- factor: correlated
-- requirement: lineage_coverage
-- requires: databricks
-- target_type: database
-- description: Checks Unity Catalog table lineage. Measures the percentage of tables that have upstream lineage tracked by Unity Catalog.

SELECT
    CAST(
        COUNT(DISTINCT target_table_full_name) AS FLOAT
    ) / NULLIF(
        (SELECT COUNT(*) FROM information_schema.tables
         WHERE table_schema NOT IN ('information_schema', 'default')
           AND table_type IN ('BASE TABLE', 'MANAGED', 'EXTERNAL')),
        0
    ) AS measured_value
FROM system.access.table_lineage
WHERE target_type = 'TABLE'
