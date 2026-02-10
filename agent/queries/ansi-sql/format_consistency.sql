-- factor: clean
-- requirement: format_inconsistency_rate
-- requires: ansi-sql
-- target_type: column
-- description: For string columns, checks format consistency by measuring how many distinct patterns exist relative to distinct values. High pattern diversity relative to value count suggests inconsistent formatting.

SELECT
    COUNT(DISTINCT "{column}") AS distinct_values,
    COUNT(DISTINCT
        CASE
            WHEN "{column}" SIMILAR TO '[0-9]{4}-[0-9]{2}-[0-9]{2}' THEN 'YYYY-MM-DD'
            WHEN "{column}" SIMILAR TO '[0-9]{2}/[0-9]{2}/[0-9]{4}' THEN 'MM/DD/YYYY'
            WHEN "{column}" SIMILAR TO '[0-9]{2}-[0-9]{2}-[0-9]{4}' THEN 'DD-MM-YYYY'
            WHEN "{column}" SIMILAR TO '[0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4}' THEN 'M/D/Y_variant'
            ELSE 'other'
        END
    ) AS date_format_count,
    CASE
        WHEN COUNT(DISTINCT
            CASE
                WHEN "{column}" SIMILAR TO '[0-9]{4}-[0-9]{2}-[0-9]{2}' THEN 'YYYY-MM-DD'
                WHEN "{column}" SIMILAR TO '[0-9]{2}/[0-9]{2}/[0-9]{4}' THEN 'MM/DD/YYYY'
                WHEN "{column}" SIMILAR TO '[0-9]{2}-[0-9]{2}-[0-9]{4}' THEN 'DD-MM-YYYY'
                WHEN "{column}" SIMILAR TO '[0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4}' THEN 'M/D/Y_variant'
                ELSE 'other'
            END
        ) > 1
        THEN 1.0 - (1.0 / COUNT(DISTINCT
            CASE
                WHEN "{column}" SIMILAR TO '[0-9]{4}-[0-9]{2}-[0-9]{2}' THEN 'YYYY-MM-DD'
                WHEN "{column}" SIMILAR TO '[0-9]{2}/[0-9]{2}/[0-9]{4}' THEN 'MM/DD/YYYY'
                WHEN "{column}" SIMILAR TO '[0-9]{2}-[0-9]{2}-[0-9]{4}' THEN 'DD-MM-YYYY'
                WHEN "{column}" SIMILAR TO '[0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4}' THEN 'M/D/Y_variant'
                ELSE 'other'
            END
        ))
        ELSE 0
    END AS measured_value
FROM "{schema}"."{table}"
