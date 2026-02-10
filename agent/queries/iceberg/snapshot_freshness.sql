-- factor: current
-- requirement: max_staleness_hours
-- requires: iceberg
-- target_type: table
-- description: Measures table freshness from the most recent Iceberg snapshot timestamp. More reliable than scanning the data -- this comes from metadata.

SELECT
    EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - MAX(committed_at))) / 3600.0 AS measured_value
FROM "{schema}"."{table}".snapshots
