-- factor: current
-- requirement: timestamp_column_coverage
-- requires: ansi-sql
-- target_type: database
-- description: Measures the percentage of tables that have at least one timestamp/datetime column

SELECT
    CAST(
        COUNT(DISTINCT CASE
            WHEN c.data_type IN ('timestamp', 'datetime', 'date', 'timestamptz',
                                 'timestamp with time zone', 'timestamp without time zone',
                                 'TIMESTAMP_LTZ', 'TIMESTAMP_NTZ', 'TIMESTAMP_TZ')
            THEN c.table_name
        END) AS FLOAT
    ) / NULLIF(COUNT(DISTINCT c.table_name), 0) AS measured_value
FROM information_schema.columns c
JOIN information_schema.tables t
    ON c.table_schema = t.table_schema AND c.table_name = t.table_name
WHERE c.table_schema NOT IN ('information_schema', 'pg_catalog', 'INFORMATION_SCHEMA')
  AND t.table_type IN ('BASE TABLE', 'TABLE')
