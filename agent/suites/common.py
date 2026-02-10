"""Common suite: ANSI SQL + information_schema baseline.

This suite works on any SQL database that supports information_schema.
Platform suites extend this with native capabilities.

The SQL dialect layer (quote, cast_float, regex_match, epoch_diff) is
overridable so that a MySQLSuite or DatabricksSuite can change quoting and
function syntax without reimplementing every test.
"""

from __future__ import annotations

from agent.discover import ColumnInfo, DatabaseInventory, TableInfo
from agent.suites.base import Suite, Test


class CommonSuite(Suite):

    @property
    def platform(self) -> str:
        return "common"

    @property
    def description(self) -> str:
        return "ANSI SQL + information_schema baseline. Works on any SQL database."

    # ------------------------------------------------------------------
    # SQL dialect layer -- override these for non-ANSI platforms
    # ------------------------------------------------------------------

    @property
    def quote(self) -> str:
        """Identifier quote character. Override for MySQL (backtick)."""
        return '"'

    @property
    def cast_float(self) -> str:
        """Float type name for CAST. Override for MySQL (DOUBLE)."""
        return "FLOAT"

    def regex_match(self, column: str, pattern: str) -> str:
        """SQL expression for regex matching. Override for MySQL (REGEXP)."""
        return f"{column} SIMILAR TO '{pattern}'"

    def epoch_diff(self, ts1: str, ts2: str) -> str:
        """SQL expression for seconds between two timestamps.

        Returns an expression that evaluates to the number of seconds
        between ts1 and ts2 (ts1 - ts2).
        Override for MySQL (TIMESTAMPDIFF), Snowflake (DATEDIFF), etc.
        """
        return f"EXTRACT(EPOCH FROM ({ts1} - {ts2}))"

    def _q(self, *parts: str) -> str:
        """Quote and join identifier parts: _q('schema', 'table') -> '"schema"."table"'."""
        q = self.quote
        return ".".join(f"{q}{p}{q}" for p in parts)

    # ------------------------------------------------------------------
    # Database-level tests
    # ------------------------------------------------------------------

    def database_tests(self, inventory: DatabaseInventory) -> list[Test]:
        return [
            # Factor 1: Contextual
            Test(
                name="table_comment_coverage",
                factor="contextual",
                requirement="table_comment_coverage",
                target_type="database",
                platform=self.platform,
                description="Percentage of tables with non-empty descriptions",
                sql=f"""
                    SELECT CAST(
                        SUM(CASE WHEN t.comment IS NOT NULL AND t.comment != '' THEN 1 ELSE 0 END) AS {self.cast_float}
                    ) / NULLIF(COUNT(*), 0) AS measured_value
                    FROM information_schema.tables t
                    WHERE t.table_schema NOT IN ('information_schema', 'pg_catalog', 'INFORMATION_SCHEMA')
                      AND t.table_type IN ('BASE TABLE', 'TABLE', 'VIEW')
                """,
            ),
            # Factor 3: Current
            Test(
                name="timestamp_column_coverage",
                factor="current",
                requirement="timestamp_column_coverage",
                target_type="database",
                platform=self.platform,
                description="Percentage of tables with at least one timestamp column",
                sql=f"""
                    SELECT CAST(
                        COUNT(DISTINCT CASE
                            WHEN c.data_type IN ('timestamp', 'datetime', 'date', 'timestamptz',
                                                 'timestamp with time zone', 'timestamp without time zone',
                                                 'TIMESTAMP_LTZ', 'TIMESTAMP_NTZ', 'TIMESTAMP_TZ')
                            THEN c.table_name END) AS {self.cast_float}
                    ) / NULLIF(COUNT(DISTINCT c.table_name), 0) AS measured_value
                    FROM information_schema.columns c
                    JOIN information_schema.tables t
                        ON c.table_schema = t.table_schema AND c.table_name = t.table_name
                    WHERE c.table_schema NOT IN ('information_schema', 'pg_catalog', 'INFORMATION_SCHEMA')
                      AND t.table_type IN ('BASE TABLE', 'TABLE')
                """,
            ),
            # Factor 4: Correlated
            Test(
                name="constraint_coverage",
                factor="correlated",
                requirement="constraint_coverage",
                target_type="database",
                platform=self.platform,
                description="Percentage of tables with PK or unique constraints",
                sql=f"""
                    SELECT CAST(
                        COUNT(DISTINCT tc.table_name) AS {self.cast_float}
                    ) / NULLIF(
                        (SELECT COUNT(*) FROM information_schema.tables
                         WHERE table_schema NOT IN ('information_schema', 'pg_catalog', 'INFORMATION_SCHEMA')
                           AND table_type IN ('BASE TABLE', 'TABLE')), 0
                    ) AS measured_value
                    FROM information_schema.table_constraints tc
                    WHERE tc.constraint_type IN ('PRIMARY KEY', 'UNIQUE')
                      AND tc.table_schema NOT IN ('information_schema', 'pg_catalog', 'INFORMATION_SCHEMA')
                """,
            ),
            # Factor 5: Compliant
            Test(
                name="rbac_coverage",
                factor="compliant",
                requirement="rbac_coverage",
                target_type="database",
                platform=self.platform,
                description="Percentage of tables with explicit access grants beyond public",
                sql=f"""
                    SELECT CAST(
                        COUNT(DISTINCT tp.table_name) AS {self.cast_float}
                    ) / NULLIF(
                        (SELECT COUNT(*) FROM information_schema.tables
                         WHERE table_schema NOT IN ('information_schema', 'pg_catalog', 'INFORMATION_SCHEMA')
                           AND table_type IN ('BASE TABLE', 'TABLE')), 0
                    ) AS measured_value
                    FROM information_schema.table_privileges tp
                    WHERE tp.table_schema NOT IN ('information_schema', 'pg_catalog', 'INFORMATION_SCHEMA')
                      AND tp.grantee NOT IN ('PUBLIC', 'public')
                """,
            ),
        ]

    # ------------------------------------------------------------------
    # Table-level tests
    # ------------------------------------------------------------------

    def table_tests(self, table: TableInfo) -> list[Test]:
        tests = [
            # Factor 1: Contextual
            Test(
                name="column_comment_coverage",
                factor="contextual",
                requirement="column_comment_coverage",
                target_type="table",
                platform=self.platform,
                description="Percentage of columns with descriptions",
                sql=f"""
                    SELECT CAST(
                        SUM(CASE WHEN comment IS NOT NULL AND comment != '' THEN 1 ELSE 0 END) AS {self.cast_float}
                    ) / NULLIF(COUNT(*), 0) AS measured_value
                    FROM information_schema.columns
                    WHERE table_schema = '{table.schema}' AND table_name = '{table.name}'
                """,
            ),
            Test(
                name="naming_consistency",
                factor="contextual",
                requirement="naming_consistency",
                target_type="table",
                platform=self.platform,
                description="Percentage of columns following the dominant naming convention",
                sql=f"""
                    SELECT CAST(MAX(convention_count) AS {self.cast_float}) / NULLIF(SUM(convention_count), 0) AS measured_value
                    FROM (
                        SELECT CASE
                            WHEN column_name = LOWER(column_name) AND column_name LIKE '%\\_%' ESCAPE '\\' THEN 'snake_case'
                            WHEN column_name = UPPER(column_name) THEN 'UPPER'
                            ELSE 'mixed'
                        END AS convention, COUNT(*) AS convention_count
                        FROM information_schema.columns
                        WHERE table_schema = '{table.schema}' AND table_name = '{table.name}'
                        GROUP BY CASE
                            WHEN column_name = LOWER(column_name) AND column_name LIKE '%\\_%' ESCAPE '\\' THEN 'snake_case'
                            WHEN column_name = UPPER(column_name) THEN 'UPPER'
                            ELSE 'mixed'
                        END
                    ) c
                """,
            ),
            # Factor 2: Consumable
            Test(
                name="ai_compatible_type_rate",
                factor="consumable",
                requirement="ai_compatible_type_rate",
                target_type="table",
                platform=self.platform,
                description="Percentage of columns using AI-compatible types",
                sql=f"""
                    SELECT CAST(SUM(CASE WHEN LOWER(data_type) IN (
                        'int','integer','bigint','smallint','tinyint','float','double','decimal',
                        'numeric','real','number','varchar','char','text','string','nvarchar',
                        'character varying','boolean','bool','timestamp','datetime','date',
                        'timestamptz','json','jsonb','variant','array','object','vector'
                    ) THEN 1 ELSE 0 END) AS {self.cast_float}) / NULLIF(COUNT(*), 0) AS measured_value
                    FROM information_schema.columns
                    WHERE table_schema = '{table.schema}' AND table_name = '{table.name}'
                """,
            ),
            # Factor 5: Compliant
            Test(
                name="pii_column_name_scan",
                factor="compliant",
                requirement="pii_column_name_rate",
                target_type="table",
                platform=self.platform,
                description="Rate of columns with PII-suggestive names",
                sql=f"""
                    SELECT CAST(SUM(CASE
                        WHEN LOWER(column_name) LIKE '%ssn%' OR LOWER(column_name) LIKE '%email%'
                          OR LOWER(column_name) LIKE '%phone%' OR LOWER(column_name) LIKE '%address%'
                          OR LOWER(column_name) LIKE '%birth%' OR LOWER(column_name) LIKE '%passport%'
                          OR LOWER(column_name) LIKE '%salary%' OR LOWER(column_name) LIKE '%credit_card%'
                          OR LOWER(column_name) LIKE '%first_name%' OR LOWER(column_name) LIKE '%last_name%'
                          OR LOWER(column_name) LIKE '%full_name%' OR LOWER(column_name) LIKE '%social_security%'
                        THEN 1 ELSE 0 END) AS {self.cast_float}) / NULLIF(COUNT(*), 0) AS measured_value
                    FROM information_schema.columns
                    WHERE table_schema = '{table.schema}' AND table_name = '{table.name}'
                """,
            ),
        ]

        # FK coverage only if table has _id columns
        id_cols = [c for c in table.columns if c.name.lower().endswith("_id") and c.name.lower() != "id"]
        if id_cols:
            tests.append(Test(
                name="foreign_key_coverage",
                factor="contextual",
                requirement="foreign_key_coverage",
                target_type="table",
                platform=self.platform,
                description="Percentage of _id columns with FK constraints",
                sql=f"""
                    SELECT CAST(
                        SUM(CASE WHEN tc.constraint_type = 'FOREIGN KEY' THEN 1 ELSE 0 END) AS {self.cast_float}
                    ) / NULLIF(COUNT(*), 0) AS measured_value
                    FROM information_schema.columns c
                    LEFT JOIN information_schema.key_column_usage kcu
                        ON c.table_schema = kcu.table_schema AND c.table_name = kcu.table_name AND c.column_name = kcu.column_name
                    LEFT JOIN information_schema.table_constraints tc
                        ON kcu.constraint_name = tc.constraint_name AND kcu.table_schema = tc.table_schema AND tc.constraint_type = 'FOREIGN KEY'
                    WHERE c.table_schema = '{table.schema}' AND c.table_name = '{table.name}'
                      AND c.column_name LIKE '%\\_id' ESCAPE '\\' AND c.column_name != 'id'
                """,
            ))

        return tests

    # ------------------------------------------------------------------
    # Column-level tests
    # ------------------------------------------------------------------

    def column_tests(self, table: TableInfo, column: ColumnInfo) -> list[Test]:
        tests: list[Test] = []
        s, t, c = table.schema, table.name, column.name
        q_table = self._q(s, t)
        q_col = self._q(c)

        # Factor 0: Clean -- all columns
        tests.append(Test(
            name="null_rate",
            factor="clean", requirement="null_rate", target_type="column", platform=self.platform,
            description="Null rate for column",
            sql=f"SELECT CAST(COUNT(*) - COUNT({q_col}) AS {self.cast_float}) / NULLIF(COUNT(*), 0) AS measured_value FROM {q_table}",
        ))

        # String columns
        if column.is_string:
            # PII pattern scan using dialect-aware regex
            ssn_match = self.regex_match(q_col, '[0-9]{3}-[0-9]{2}-[0-9]{4}')
            email_match = self.regex_match(q_col, '%@%.%')
            phone_match = self.regex_match(q_col, '[0-9]{3}[-.][0-9]{3}[-.][0-9]{4}')
            tests.append(Test(
                name="pii_pattern_scan",
                factor="clean", requirement="pii_detection_rate", target_type="column", platform=self.platform,
                description="PII pattern match rate (SSN, email, phone)",
                sql=f"""
                    SELECT CAST(SUM(CASE
                        WHEN {ssn_match} THEN 1
                        WHEN {email_match} THEN 1
                        WHEN {phone_match} THEN 1
                        ELSE 0 END) AS {self.cast_float}) / NULLIF(COUNT({q_col}), 0) AS measured_value
                    FROM {q_table}
                """,
            ))

            # Type consistency using dialect-aware regex
            numeric_pattern_match = self.regex_match(q_col, '-?[0-9]+\\.?[0-9]*')
            numeric_pattern_not = f"NOT ({numeric_pattern_match})"
            tests.append(Test(
                name="type_consistency",
                factor="clean", requirement="type_inconsistency_rate", target_type="column", platform=self.platform,
                description="Mixed type rate in string column",
                sql=f"""
                    SELECT CASE
                        WHEN SUM(CASE WHEN {numeric_pattern_match} THEN 1 ELSE 0 END) > 0
                         AND SUM(CASE WHEN {numeric_pattern_not} THEN 1 ELSE 0 END) > 0
                        THEN CAST(LEAST(
                            SUM(CASE WHEN {numeric_pattern_match} THEN 1 ELSE 0 END),
                            SUM(CASE WHEN {numeric_pattern_not} THEN 1 ELSE 0 END)
                        ) AS {self.cast_float}) / NULLIF(COUNT({q_col}), 0)
                        ELSE 0 END AS measured_value
                    FROM {q_table}
                """,
            ))

        # Numeric columns
        if column.is_numeric:
            tests.append(Test(
                name="zero_negative_check",
                factor="clean", requirement="zero_negative_rate", target_type="column", platform=self.platform,
                description="Rate of zero or negative values",
                sql=f"SELECT CAST(SUM(CASE WHEN {q_col} <= 0 THEN 1 ELSE 0 END) AS {self.cast_float}) / NULLIF(COUNT({q_col}), 0) AS measured_value FROM {q_table}",
            ))

        # Candidate key columns
        if column.is_candidate_key:
            tests.append(Test(
                name="duplicate_detection",
                factor="clean", requirement="duplicate_rate", target_type="column", platform=self.platform,
                description="Duplicate rate for candidate key",
                sql=f"SELECT 1.0 - (CAST(COUNT(DISTINCT {q_col}) AS {self.cast_float}) / NULLIF(COUNT({q_col}), 0)) AS measured_value FROM {q_table}",
            ))

        # Timestamp columns
        if column.is_timestamp:
            diff_expr = self.epoch_diff("CURRENT_TIMESTAMP", f"MAX({q_col})")
            tests.append(Test(
                name="table_freshness",
                factor="current", requirement="max_staleness_hours", target_type="column", platform=self.platform,
                description="Hours since most recent value",
                sql=f"SELECT {diff_expr} / 3600.0 AS measured_value FROM {q_table} WHERE {q_col} IS NOT NULL",
            ))

        return tests
