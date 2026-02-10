-- factor: discovery
-- requirement: table_inventory
-- requires: information-schema
-- target_type: database
-- description: Lists all tables in all schemas, excluding system schemas

SELECT
    table_catalog,
    table_schema,
    table_name,
    table_type
FROM information_schema.tables
WHERE table_schema NOT IN ('information_schema', 'pg_catalog', 'INFORMATION_SCHEMA')
  AND table_type IN ('BASE TABLE', 'TABLE', 'VIEW')
ORDER BY table_schema, table_name
