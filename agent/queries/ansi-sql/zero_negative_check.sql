-- factor: clean
-- requirement: zero_negative_rate
-- requires: ansi-sql
-- target_type: column
-- description: Measures the rate of zero or negative values in a numeric column. Useful for columns expected to contain only positive values (prices, quantities, durations).

SELECT
    CAST(
        SUM(CASE WHEN "{column}" <= 0 THEN 1 ELSE 0 END) AS FLOAT
    ) / NULLIF(COUNT("{column}"), 0) AS measured_value
FROM "{schema}"."{table}"
