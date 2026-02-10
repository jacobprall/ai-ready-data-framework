-- factor: correlated
-- requirement: dataset_versioning
-- requires: iceberg
-- target_type: table
-- description: Queries Iceberg snapshot history for a table. Each snapshot is an immutable version of the data. Measures how many snapshots exist and the time span they cover -- indicating whether versioning is active.

SELECT
    COUNT(*) AS snapshot_count,
    MIN(committed_at) AS earliest_snapshot,
    MAX(committed_at) AS latest_snapshot,
    EXTRACT(EPOCH FROM (MAX(committed_at) - MIN(committed_at))) / 86400.0 AS days_of_history
FROM "{schema}"."{table}".snapshots
