-- factor: clean
-- requirement: pii_detection_rate
-- requires: ansi-sql
-- target_type: column
-- description: Scans a string column for common PII patterns (SSN, email, phone). Returns the rate of rows matching any PII pattern.

SELECT
    CAST(
        SUM(
            CASE
                WHEN "{column}" SIMILAR TO '[0-9]{3}-[0-9]{2}-[0-9]{4}' THEN 1
                WHEN "{column}" SIMILAR TO '[0-9]{9}' AND LENGTH("{column}") = 9 THEN 1
                WHEN "{column}" SIMILAR TO '%@%.%' THEN 1
                WHEN "{column}" SIMILAR TO '[0-9]{3}[-.][0-9]{3}[-.][0-9]{4}' THEN 1
                WHEN "{column}" SIMILAR TO '\+?[0-9]{10,}' THEN 1
                ELSE 0
            END
        ) AS FLOAT
    ) / NULLIF(COUNT("{column}"), 0) AS measured_value
FROM "{schema}"."{table}"
