-- factor: consumable
-- requirement: ai_compatible_type_rate
-- requires: ansi-sql
-- target_type: table
-- description: Measures the percentage of columns using types compatible with AI workloads (numeric, string, timestamp, boolean). Types like blob, xml, binary, and geometry are less compatible.

SELECT
    CAST(
        SUM(CASE
            WHEN LOWER(data_type) IN (
                'int', 'integer', 'bigint', 'smallint', 'tinyint',
                'float', 'double', 'decimal', 'numeric', 'real', 'number', 'money',
                'varchar', 'char', 'text', 'string', 'nvarchar', 'nchar',
                'character varying', 'character', 'clob',
                'boolean', 'bool',
                'timestamp', 'datetime', 'date', 'timestamptz',
                'timestamp with time zone', 'timestamp without time zone',
                'timestamp_ltz', 'timestamp_ntz', 'timestamp_tz',
                'json', 'jsonb', 'variant', 'array', 'object',
                'vector'
            ) THEN 1
            ELSE 0
        END) AS FLOAT
    ) / NULLIF(COUNT(*), 0) AS measured_value
FROM information_schema.columns
WHERE table_schema = '{schema}'
  AND table_name = '{table}'
