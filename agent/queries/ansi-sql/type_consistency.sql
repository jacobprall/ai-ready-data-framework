-- factor: clean
-- requirement: type_inconsistency_rate
-- requires: ansi-sql
-- target_type: column
-- description: For VARCHAR/TEXT columns, checks if values that look numeric are mixed with non-numeric values. A high mix rate suggests the column has type inconsistencies.

SELECT
    CAST(
        SUM(
            CASE
                WHEN "{column}" SIMILAR TO '-?[0-9]+\.?[0-9]*' THEN 1
                ELSE 0
            END
        ) AS FLOAT
    ) / NULLIF(COUNT("{column}"), 0) AS numeric_rate,
    CASE
        WHEN SUM(CASE WHEN "{column}" SIMILAR TO '-?[0-9]+\.?[0-9]*' THEN 1 ELSE 0 END) > 0
         AND SUM(CASE WHEN "{column}" NOT SIMILAR TO '-?[0-9]+\.?[0-9]*' THEN 1 ELSE 0 END) > 0
        THEN CAST(
            LEAST(
                SUM(CASE WHEN "{column}" SIMILAR TO '-?[0-9]+\.?[0-9]*' THEN 1 ELSE 0 END),
                SUM(CASE WHEN "{column}" NOT SIMILAR TO '-?[0-9]+\.?[0-9]*' THEN 1 ELSE 0 END)
            ) AS FLOAT
        ) / NULLIF(COUNT("{column}"), 0)
        ELSE 0
    END AS measured_value
FROM "{schema}"."{table}"
