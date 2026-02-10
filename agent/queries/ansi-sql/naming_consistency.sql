-- factor: contextual
-- requirement: naming_consistency
-- requires: ansi-sql
-- target_type: table
-- description: Measures naming convention consistency across columns. Checks whether columns follow a single convention (snake_case, camelCase, etc.). Returns the percentage that match the dominant convention.

SELECT
    CAST(
        MAX(convention_count) AS FLOAT
    ) / NULLIF(SUM(convention_count), 0) AS measured_value
FROM (
    SELECT
        CASE
            WHEN column_name = LOWER(column_name) AND column_name LIKE '%\_%' ESCAPE '\' THEN 'snake_case'
            WHEN column_name = UPPER(column_name) AND column_name LIKE '%\_%' ESCAPE '\' THEN 'UPPER_SNAKE'
            WHEN column_name = LOWER(column_name) THEN 'lowercase'
            WHEN column_name = UPPER(column_name) THEN 'UPPERCASE'
            ELSE 'mixed'
        END AS convention,
        COUNT(*) AS convention_count
    FROM information_schema.columns
    WHERE table_schema = '{schema}'
      AND table_name = '{table}'
    GROUP BY
        CASE
            WHEN column_name = LOWER(column_name) AND column_name LIKE '%\_%' ESCAPE '\' THEN 'snake_case'
            WHEN column_name = UPPER(column_name) AND column_name LIKE '%\_%' ESCAPE '\' THEN 'UPPER_SNAKE'
            WHEN column_name = LOWER(column_name) THEN 'lowercase'
            WHEN column_name = UPPER(column_name) THEN 'UPPERCASE'
            ELSE 'mixed'
        END
) conventions
