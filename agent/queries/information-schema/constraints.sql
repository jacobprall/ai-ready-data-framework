-- factor: discovery
-- requirement: constraints
-- requires: information-schema
-- target_type: table
-- description: Returns primary key, foreign key, and unique constraints for a table

SELECT
    tc.constraint_name,
    tc.constraint_type,
    kcu.column_name,
    kcu.ordinal_position
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
    AND tc.table_name = kcu.table_name
WHERE tc.table_schema = '{schema}'
  AND tc.table_name = '{table}'
ORDER BY tc.constraint_type, kcu.ordinal_position
