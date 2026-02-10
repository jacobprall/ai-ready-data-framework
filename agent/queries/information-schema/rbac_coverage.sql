-- factor: compliant
-- requirement: rbac_coverage
-- requires: information-schema
-- target_type: database
-- description: Measures the percentage of tables with explicit access grants beyond the default public role. Tables with only default/public access are flagged as lacking explicit RBAC.

SELECT
    CAST(
        COUNT(DISTINCT tp.table_name) AS FLOAT
    ) / NULLIF(
        (SELECT COUNT(*) FROM information_schema.tables
         WHERE table_schema NOT IN ('information_schema', 'pg_catalog', 'INFORMATION_SCHEMA')
           AND table_type IN ('BASE TABLE', 'TABLE')),
        0
    ) AS measured_value
FROM information_schema.table_privileges tp
WHERE tp.table_schema NOT IN ('information_schema', 'pg_catalog', 'INFORMATION_SCHEMA')
  AND tp.grantee NOT IN ('PUBLIC', 'public')
