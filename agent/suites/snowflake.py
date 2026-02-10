"""Snowflake suite: full-depth assessment using Snowflake-native capabilities.

Leverages ACCOUNT_USAGE views, information_schema extensions, TIME_TRAVEL,
OBJECT_DEPENDENCIES, Dynamic Tables, Snowpipe, masking policies, and more.

Extends CommonSuite -- inherits all ANSI SQL tests and adds Snowflake-native
versions that provide deeper coverage.
"""

from __future__ import annotations

from agent.discover import ColumnInfo, DatabaseInventory, TableInfo
from agent.suites.common import CommonSuite
from agent.suites.base import Test


class SnowflakeSuite(CommonSuite):

    @property
    def platform(self) -> str:
        return "snowflake"

    @property
    def description(self) -> str:
        return "Full Snowflake-native assessment using ACCOUNT_USAGE, TIME_TRAVEL, and platform-specific metadata."

    # ------------------------------------------------------------------
    # Database-level: inherit common + add Snowflake-native
    # ------------------------------------------------------------------

    def database_tests(self, inventory: DatabaseInventory) -> list[Test]:
        tests = super().database_tests(inventory)

        tests.extend([
            # Factor 0: Clean -- ingestion quality
            Test(
                name="copy_history_error_rate",
                factor="clean", requirement="ingestion_error_rate", target_type="database",
                platform=self.platform,
                description="Ingestion error rate from COPY_HISTORY (last 30 days)",
                sql="""
                    SELECT CAST(
                        SUM(CASE WHEN status = 'LOAD_FAILED' THEN 1 ELSE 0 END) AS FLOAT
                    ) / NULLIF(COUNT(*), 0) AS measured_value
                    FROM snowflake.account_usage.copy_history
                    WHERE last_load_time >= DATEADD('day', -30, CURRENT_TIMESTAMP())
                """,
            ),
            # Factor 0: Clean -- table profiling without scanning
            Test(
                name="table_row_counts",
                factor="clean", requirement="table_profiling", target_type="database",
                platform=self.platform,
                description="Row counts from TABLE_STORAGE_METRICS (no table scan required)",
                sql="""
                    SELECT table_schema, table_name, row_count, active_bytes
                    FROM snowflake.account_usage.table_storage_metrics
                    WHERE table_catalog = CURRENT_DATABASE()
                      AND table_schema NOT IN ('INFORMATION_SCHEMA')
                      AND deleted IS NULL
                    ORDER BY active_bytes DESC
                """,
            ),
            # Factor 3: Current -- pipeline health (Snowpipe)
            Test(
                name="pipe_status",
                factor="current", requirement="pipeline_health", target_type="database",
                platform=self.platform,
                description="Snowpipe status and health",
                sql="""
                    SELECT pipe_schema, pipe_name, is_autoingest_enabled, created, last_altered
                    FROM information_schema.pipes
                    WHERE pipe_schema NOT IN ('INFORMATION_SCHEMA')
                    ORDER BY last_altered DESC
                """,
            ),
            # Factor 3: Current -- Dynamic Table freshness
            Test(
                name="dynamic_table_lag",
                factor="current", requirement="pipeline_freshness", target_type="database",
                platform=self.platform,
                description="Dynamic Table refresh status and lag",
                sql="""
                    SELECT name, schema_name, target_lag, refresh_mode, scheduling_state
                    FROM information_schema.dynamic_tables
                    WHERE schema_name NOT IN ('INFORMATION_SCHEMA')
                """,
            ),
            # Factor 2: Consumable -- access pattern analysis
            Test(
                name="access_patterns",
                factor="consumable", requirement="access_pattern_analysis", target_type="database",
                platform=self.platform,
                description="Query patterns by client application (last 7 days)",
                sql="""
                    SELECT client_application_id, COUNT(*) AS query_count,
                        AVG(total_elapsed_time)/1000.0 AS avg_duration_sec,
                        SUM(rows_produced) AS total_rows
                    FROM snowflake.account_usage.query_history
                    WHERE start_time >= DATEADD('day', -7, CURRENT_TIMESTAMP())
                      AND query_type = 'SELECT' AND execution_status = 'SUCCESS'
                    GROUP BY client_application_id
                    ORDER BY query_count DESC LIMIT 20
                """,
            ),
            # Factor 4: Correlated -- object dependencies (lineage)
            Test(
                name="object_dependency_coverage",
                factor="correlated", requirement="lineage_coverage", target_type="database",
                platform=self.platform,
                description="Object dependency graph from OBJECT_DEPENDENCIES. Measures how many objects have tracked upstream dependencies.",
                sql="""
                    SELECT
                        COUNT(DISTINCT referencing_object_name) AS objects_with_dependencies,
                        COUNT(DISTINCT referenced_object_name) AS referenced_objects,
                        COUNT(*) AS total_dependency_edges
                    FROM snowflake.account_usage.object_dependencies
                    WHERE referencing_object_domain IN ('TABLE', 'VIEW', 'MATERIALIZED VIEW')
                """,
            ),
            # Factor 4: Correlated -- access history (column-level lineage)
            Test(
                name="access_history_lineage",
                factor="correlated", requirement="column_lineage_coverage", target_type="database",
                platform=self.platform,
                description="Column-level lineage from ACCESS_HISTORY. Shows whether column-level access tracking is active.",
                sql="""
                    SELECT
                        COUNT(*) AS total_access_records,
                        COUNT(DISTINCT query_id) AS distinct_queries,
                        MIN(query_start_time) AS earliest, MAX(query_start_time) AS latest
                    FROM snowflake.account_usage.access_history
                    WHERE query_start_time >= DATEADD('day', -30, CURRENT_TIMESTAMP())
                """,
            ),
            # Factor 5: Compliant -- access auditing
            Test(
                name="access_audit_coverage",
                factor="compliant", requirement="access_auditing", target_type="database",
                platform=self.platform,
                description="Access audit log coverage from ACCESS_HISTORY (last 30 days)",
                sql="""
                    SELECT COUNT(*) AS total_events,
                        COUNT(DISTINCT user_name) AS distinct_users,
                        COUNT(DISTINCT query_id) AS distinct_queries,
                        DATEDIFF('hour', MAX(query_start_time), CURRENT_TIMESTAMP()) AS hours_since_last
                    FROM snowflake.account_usage.access_history
                    WHERE query_start_time >= DATEADD('day', -30, CURRENT_TIMESTAMP())
                """,
            ),
            # Factor 5: Compliant -- masking policy coverage
            Test(
                name="masking_policy_coverage",
                factor="compliant", requirement="pii_masking_coverage", target_type="database",
                platform=self.platform,
                description="Percentage of PII-named columns with masking policies applied",
                sql="""
                    SELECT CAST(
                        COUNT(DISTINCT pr.ref_column_name) AS FLOAT
                    ) / NULLIF(
                        (SELECT COUNT(*) FROM information_schema.columns
                         WHERE table_schema NOT IN ('INFORMATION_SCHEMA')
                           AND (LOWER(column_name) LIKE '%ssn%' OR LOWER(column_name) LIKE '%email%'
                             OR LOWER(column_name) LIKE '%phone%' OR LOWER(column_name) LIKE '%birth%'
                             OR LOWER(column_name) LIKE '%salary%' OR LOWER(column_name) LIKE '%first_name%'
                             OR LOWER(column_name) LIKE '%last_name%')), 0
                    ) AS measured_value
                    FROM table(information_schema.policy_references(ref_entity_domain => 'TABLE')) pr
                    WHERE pr.policy_kind = 'MASKING_POLICY'
                """,
            ),
            # Factor 5: Compliant -- row access policies
            Test(
                name="row_access_policy_usage",
                factor="compliant", requirement="row_level_security", target_type="database",
                platform=self.platform,
                description="Count of tables with row access policies applied",
                sql="""
                    SELECT COUNT(DISTINCT ref_entity_name) AS tables_with_row_policies
                    FROM table(information_schema.policy_references(ref_entity_domain => 'TABLE')) pr
                    WHERE pr.policy_kind = 'ROW_ACCESS_POLICY'
                """,
            ),
        ])

        return tests

    # ------------------------------------------------------------------
    # Table-level: inherit common + add Snowflake-native
    # ------------------------------------------------------------------

    def table_tests(self, table: TableInfo) -> list[Test]:
        tests = super().table_tests(table)
        s, t = table.schema, table.name

        tests.extend([
            # Factor 3: Current -- table freshness from metadata (no scan)
            Test(
                name="table_last_altered",
                factor="current", requirement="max_staleness_hours", target_type="table",
                platform=self.platform,
                description="Hours since table was last altered (from metadata, no scan)",
                sql=f"""
                    SELECT DATEDIFF('hour', last_altered, CURRENT_TIMESTAMP()) AS measured_value
                    FROM information_schema.tables
                    WHERE table_schema = '{s}' AND table_name = '{t}'
                """,
            ),
            # Factor 4: Correlated -- table dependencies
            Test(
                name="table_dependencies",
                factor="correlated", requirement="table_lineage", target_type="table",
                platform=self.platform,
                description="Upstream dependencies for this table from OBJECT_DEPENDENCIES",
                sql=f"""
                    SELECT COUNT(*) AS upstream_count,
                        COUNT(DISTINCT referenced_object_name) AS distinct_sources
                    FROM snowflake.account_usage.object_dependencies
                    WHERE referencing_object_name = '{t}'
                      AND referencing_schema_name = '{s}'
                      AND referencing_object_domain IN ('TABLE', 'VIEW', 'MATERIALIZED VIEW')
                """,
            ),
            # Factor 1: Contextual -- table ownership
            Test(
                name="table_ownership",
                factor="contextual", requirement="data_ownership", target_type="table",
                platform=self.platform,
                description="Check if table has explicit ownership assigned",
                sql=f"""
                    SELECT table_owner,
                        CASE WHEN table_owner IS NOT NULL AND table_owner != '' THEN 1 ELSE 0 END AS measured_value
                    FROM information_schema.tables
                    WHERE table_schema = '{s}' AND table_name = '{t}'
                """,
            ),
        ])

        return tests

    # ------------------------------------------------------------------
    # Column-level: inherit all common column tests (no overrides needed)
    # ------------------------------------------------------------------

    # CommonSuite.column_tests() handles all column-level tests.
    # Snowflake's column-level capabilities (masking policies, tags) are
    # assessed at the database level via POLICY_REFERENCES.
