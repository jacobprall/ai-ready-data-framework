-- factor: correlated
-- requirement: schema_versioning
-- requires: databricks
-- target_type: table
-- description: Checks Delta table history for schema evolution events. Measures whether schema changes are tracked and versioned.

SELECT
    version,
    timestamp,
    operation,
    operationParameters
FROM (
    DESCRIBE HISTORY "{schema}"."{table}"
)
WHERE operation IN ('SET TBLPROPERTIES', 'CHANGE COLUMN', 'ADD COLUMNS', 'REPLACE COLUMNS')
ORDER BY version DESC
LIMIT 20
