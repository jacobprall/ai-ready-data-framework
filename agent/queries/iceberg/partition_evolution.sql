-- factor: consumable
-- requirement: partition_optimization
-- requires: iceberg
-- target_type: table
-- description: Checks Iceberg data file distribution across partitions. Skewed partitions degrade query performance for AI workloads. Measures the ratio of the largest to smallest partition by file count.

SELECT
    COUNT(*) AS total_files,
    COUNT(DISTINCT partition) AS partition_count,
    MAX(file_count) AS max_partition_files,
    MIN(file_count) AS min_partition_files,
    CASE
        WHEN MIN(file_count) > 0
        THEN CAST(MAX(file_count) AS FLOAT) / MIN(file_count)
        ELSE NULL
    END AS partition_skew_ratio
FROM (
    SELECT
        partition,
        COUNT(*) AS file_count
    FROM "{schema}"."{table}".files
    GROUP BY partition
) partition_stats
