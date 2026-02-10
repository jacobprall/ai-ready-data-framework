-- factor: compliant
-- requirement: pii_tagging
-- requires: databricks
-- target_type: table
-- description: Checks Unity Catalog column tags for PII classification. Measures whether columns with PII-suggestive names have been explicitly tagged.

SELECT
    c.column_name,
    c.data_type,
    t.tag_name,
    t.tag_value,
    CASE WHEN t.tag_name IS NOT NULL THEN 1 ELSE 0 END AS is_tagged
FROM information_schema.columns c
LEFT JOIN system.information_schema.column_tags t
    ON c.table_catalog = t.catalog_name
    AND c.table_schema = t.schema_name
    AND c.table_name = t.table_name
    AND c.column_name = t.column_name
WHERE c.table_schema = '{schema}'
  AND c.table_name = '{table}'
ORDER BY c.ordinal_position
