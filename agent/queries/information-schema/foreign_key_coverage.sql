-- factor: contextual
-- requirement: foreign_key_coverage
-- requires: information-schema
-- target_type: table
-- description: Measures the percentage of columns ending in _id that have declared foreign key constraints

SELECT
    CAST(
        SUM(CASE WHEN tc.constraint_type = 'FOREIGN KEY' THEN 1 ELSE 0 END) AS FLOAT
    ) / NULLIF(COUNT(*), 0) AS measured_value
FROM information_schema.columns c
LEFT JOIN information_schema.key_column_usage kcu
    ON c.table_schema = kcu.table_schema
    AND c.table_name = kcu.table_name
    AND c.column_name = kcu.column_name
LEFT JOIN information_schema.table_constraints tc
    ON kcu.constraint_name = tc.constraint_name
    AND kcu.table_schema = tc.table_schema
    AND tc.constraint_type = 'FOREIGN KEY'
WHERE c.table_schema = '{schema}'
  AND c.table_name = '{table}'
  AND (c.column_name LIKE '%\_id' ESCAPE '\' OR c.column_name LIKE '%_id')
  AND c.column_name != 'id'
