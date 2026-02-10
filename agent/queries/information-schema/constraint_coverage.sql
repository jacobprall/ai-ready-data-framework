-- factor: correlated
-- requirement: constraint_coverage
-- requires: information-schema
-- target_type: database
-- description: Measures the percentage of tables that have at least one primary key or unique constraint

SELECT
    CAST(
        COUNT(DISTINCT tc.table_name) AS FLOAT
    ) / NULLIF(
        (SELECT COUNT(*) FROM information_schema.tables
         WHERE table_schema NOT IN ('information_schema', 'pg_catalog', 'INFORMATION_SCHEMA')
           AND table_type IN ('BASE TABLE', 'TABLE')),
        0
    ) AS measured_value
FROM information_schema.table_constraints tc
WHERE tc.constraint_type IN ('PRIMARY KEY', 'UNIQUE')
  AND tc.table_schema NOT IN ('information_schema', 'pg_catalog', 'INFORMATION_SCHEMA')
