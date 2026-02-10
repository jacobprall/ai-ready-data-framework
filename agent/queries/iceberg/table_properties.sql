-- factor: contextual
-- requirement: table_documentation
-- requires: iceberg
-- target_type: table
-- description: Reads Iceberg table properties. These key-value pairs can store descriptions, ownership, classification tags, and other metadata co-located with the table.

SHOW TBLPROPERTIES "{schema}"."{table}"
