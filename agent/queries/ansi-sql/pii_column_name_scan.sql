-- factor: compliant
-- requirement: pii_column_name_rate
-- requires: ansi-sql
-- target_type: table
-- description: Identifies columns with PII-suggestive names (ssn, email, phone, address, etc.). Returns the rate of columns with PII-pattern names. These columns should have masking policies or explicit clearance.

SELECT
    CAST(
        SUM(CASE
            WHEN LOWER(column_name) LIKE '%ssn%'
              OR LOWER(column_name) LIKE '%social_security%'
              OR LOWER(column_name) LIKE '%email%'
              OR LOWER(column_name) LIKE '%phone%'
              OR LOWER(column_name) LIKE '%mobile%'
              OR LOWER(column_name) LIKE '%address%'
              OR LOWER(column_name) LIKE '%zip%'
              OR LOWER(column_name) LIKE '%postal%'
              OR LOWER(column_name) LIKE '%birth%'
              OR LOWER(column_name) LIKE '%dob%'
              OR LOWER(column_name) LIKE '%passport%'
              OR LOWER(column_name) LIKE '%license%'
              OR LOWER(column_name) LIKE '%salary%'
              OR LOWER(column_name) LIKE '%credit_card%'
              OR LOWER(column_name) LIKE '%card_number%'
              OR LOWER(column_name) LIKE '%bank_account%'
              OR LOWER(column_name) LIKE '%routing%'
              OR LOWER(column_name) LIKE '%national_id%'
              OR LOWER(column_name) LIKE '%tax_id%'
              OR LOWER(column_name) LIKE '%first_name%'
              OR LOWER(column_name) LIKE '%last_name%'
              OR LOWER(column_name) LIKE '%full_name%'
            THEN 1
            ELSE 0
        END) AS FLOAT
    ) / NULLIF(COUNT(*), 0) AS measured_value
FROM information_schema.columns
WHERE table_schema = '{schema}'
  AND table_name = '{table}'
