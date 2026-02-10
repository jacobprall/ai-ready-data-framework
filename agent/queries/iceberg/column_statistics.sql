-- factor: clean
-- requirement: column_statistics_coverage
-- requires: iceberg
-- target_type: table
-- description: Checks whether Iceberg column-level statistics (null counts, lower/upper bounds) are available in the metadata. These enable profiling without scanning data.

SELECT
    COUNT(*) AS total_files,
    SUM(CASE WHEN null_value_counts IS NOT NULL THEN 1 ELSE 0 END) AS files_with_null_stats,
    SUM(CASE WHEN lower_bounds IS NOT NULL THEN 1 ELSE 0 END) AS files_with_lower_bounds,
    SUM(CASE WHEN upper_bounds IS NOT NULL THEN 1 ELSE 0 END) AS files_with_upper_bounds,
    CAST(
        SUM(CASE WHEN null_value_counts IS NOT NULL THEN 1 ELSE 0 END) AS FLOAT
    ) / NULLIF(COUNT(*), 0) AS measured_value
FROM "{schema}"."{table}".files
