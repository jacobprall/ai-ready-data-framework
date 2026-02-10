-- factor: current
-- requirement: max_staleness_hours
-- requires: ansi-sql
-- target_type: column
-- description: Measures hours since the most recent value in a timestamp column. Lower is fresher.

SELECT
    EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - MAX("{column}"))) / 3600.0 AS measured_value
FROM "{schema}"."{table}"
WHERE "{column}" IS NOT NULL
