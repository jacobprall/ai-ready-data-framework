-- factor: clean
-- requirement: manifest_profiling
-- requires: iceberg
-- target_type: table
-- description: Reads Iceberg manifest-level statistics without scanning data. Provides row counts, file counts, and size information from metadata alone.

SELECT
    COUNT(*) AS manifest_count,
    SUM(added_data_files_count) AS total_data_files,
    SUM(added_rows_count) AS total_rows_added,
    SUM(existing_rows_count) AS total_rows_existing
FROM "{schema}"."{table}".manifests
WHERE content = 0
