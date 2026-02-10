-- factor: contextual
-- requirement: column_comment_coverage
-- requires: information-schema
-- target_type: table
-- description: Checks which columns have comments/descriptions. Implementation varies by platform; this uses the ANSI-standard COMMENT column where available.

SELECT
    column_name,
    CASE
        WHEN comment IS NOT NULL AND comment != '' THEN 1
        ELSE 0
    END AS has_comment
FROM information_schema.columns
WHERE table_schema = '{schema}'
  AND table_name = '{table}'
ORDER BY ordinal_position
