-- factor: discovery
-- requirement: column_metadata
-- requires: information-schema
-- target_type: table
-- description: Returns column names, types, nullability, and defaults for a table

SELECT
    column_name,
    data_type,
    is_nullable,
    column_default,
    ordinal_position,
    character_maximum_length,
    numeric_precision,
    numeric_scale
FROM information_schema.columns
WHERE table_schema = '{schema}'
  AND table_name = '{table}'
ORDER BY ordinal_position
