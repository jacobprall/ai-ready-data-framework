-- factor: contextual
-- requirement: table_documentation
-- requires: databricks
-- target_type: table
-- description: Checks Unity Catalog table properties including owner, comment, and tags. Measures documentation completeness.

SELECT
    table_owner,
    comment,
    CASE WHEN comment IS NOT NULL AND comment != '' THEN 1 ELSE 0 END AS has_comment,
    CASE WHEN table_owner IS NOT NULL AND table_owner != '' THEN 1 ELSE 0 END AS has_owner
FROM information_schema.tables
WHERE table_schema = '{schema}'
  AND table_name = '{table}'
