-- factor: contextual
-- requirement: schema_versioning
-- requires: iceberg
-- target_type: table
-- description: Checks Iceberg metadata log for schema evolution events. Indicates whether schema changes are tracked and versioned through the table format.

SELECT
    COUNT(*) AS metadata_log_entries,
    MIN(timestamp) AS earliest_entry,
    MAX(timestamp) AS latest_entry
FROM "{schema}"."{table}".metadata_log_entries
