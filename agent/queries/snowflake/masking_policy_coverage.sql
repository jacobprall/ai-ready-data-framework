-- factor: compliant
-- requirement: pii_masking_coverage
-- requires: snowflake
-- target_type: database
-- description: Measures the percentage of columns with PII-suggestive names that have masking policies applied. Uses POLICY_REFERENCES to check for active masking.

SELECT
    CAST(
        COUNT(DISTINCT pr.ref_column_name) AS FLOAT
    ) / NULLIF(
        (SELECT COUNT(*) FROM information_schema.columns
         WHERE table_schema NOT IN ('INFORMATION_SCHEMA')
           AND (LOWER(column_name) LIKE '%ssn%'
             OR LOWER(column_name) LIKE '%email%'
             OR LOWER(column_name) LIKE '%phone%'
             OR LOWER(column_name) LIKE '%address%'
             OR LOWER(column_name) LIKE '%birth%'
             OR LOWER(column_name) LIKE '%passport%'
             OR LOWER(column_name) LIKE '%salary%'
             OR LOWER(column_name) LIKE '%credit_card%'
             OR LOWER(column_name) LIKE '%first_name%'
             OR LOWER(column_name) LIKE '%last_name%'
             OR LOWER(column_name) LIKE '%full_name%')),
        0
    ) AS measured_value
FROM table(information_schema.policy_references(ref_entity_domain => 'TABLE')) pr
WHERE pr.policy_kind = 'MASKING_POLICY'
