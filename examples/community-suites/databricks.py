"""Databricks suite: full-depth assessment using Unity Catalog and Delta Lake.

Leverages Unity Catalog system tables (lineage, audit, tags), Delta Lake internals
(DESCRIBE HISTORY, DESCRIBE DETAIL), and information_schema extensions.

Extends CommonSuite -- inherits all ANSI SQL tests and adds Databricks-native
versions that provide deeper coverage.
"""

from __future__ import annotations

from agent.discover import ColumnInfo, DatabaseInventory, TableInfo
from agent.suites.common import CommonSuite
from agent.suites.base import Test


class DatabricksSuite(CommonSuite):

    @property
    def platform(self) -> str:
        return "databricks"

    @property
    def description(self) -> str:
        return "Full Databricks-native assessment using Unity Catalog, Delta Lake history, and system tables."

    # ------------------------------------------------------------------
    # Database-level: inherit common + add Databricks-native
    # ------------------------------------------------------------------

    def database_tests(self, inventory: DatabaseInventory) -> list[Test]:
        tests = super().database_tests(inventory)

        tests.extend([
            # Factor 4: Correlated -- table lineage from Unity Catalog
            Test(
                name="table_lineage_coverage",
                factor="correlated", requirement="lineage_coverage", target_type="database",
                platform=self.platform,
                description="Percentage of tables with upstream lineage tracked in Unity Catalog",
                query="""
                    SELECT CAST(
                        COUNT(DISTINCT target_table_full_name) AS FLOAT
                    ) / NULLIF(
                        (SELECT COUNT(*) FROM information_schema.tables
                         WHERE table_schema NOT IN ('information_schema', 'default')
                           AND table_type IN ('BASE TABLE', 'MANAGED', 'EXTERNAL')), 0
                    ) AS measured_value
                    FROM system.access.table_lineage
                    WHERE target_type = 'TABLE'
                """,
            ),
            # Factor 4: Correlated -- column-level lineage
            Test(
                name="column_lineage_depth",
                factor="correlated", requirement="column_lineage_coverage", target_type="database",
                platform=self.platform,
                description="Column-level lineage entries in Unity Catalog",
                query="""
                    SELECT COUNT(DISTINCT CONCAT(target_table_full_name, '.', target_column_name)) AS columns_with_lineage
                    FROM system.access.column_lineage
                    WHERE target_type = 'TABLE'
                """,
            ),
            # Factor 5: Compliant -- audit log coverage
            Test(
                name="audit_log_coverage",
                factor="compliant", requirement="access_auditing", target_type="database",
                platform=self.platform,
                description="Audit log activity over the last 30 days from system.access.audit",
                query="""
                    SELECT COUNT(*) AS total_events,
                        COUNT(DISTINCT action_name) AS distinct_actions,
                        MIN(event_date) AS earliest, MAX(event_date) AS latest,
                        DATEDIFF(DAY, MAX(event_date), CURRENT_DATE()) AS days_since_last
                    FROM system.access.audit
                    WHERE event_date >= DATEADD(DAY, -30, CURRENT_DATE())
                """,
            ),
            # Factor 2: Consumable -- compute usage patterns
            Test(
                name="compute_usage_patterns",
                factor="consumable", requirement="access_pattern_analysis", target_type="database",
                platform=self.platform,
                description="Query patterns by source from system.billing.usage (last 7 days)",
                query="""
                    SELECT usage_metadata.job_id IS NOT NULL AS is_job,
                        usage_metadata.notebook_id IS NOT NULL AS is_notebook,
                        COUNT(*) AS usage_count,
                        SUM(usage_quantity) AS total_dbu
                    FROM system.billing.usage
                    WHERE usage_date >= DATEADD(DAY, -7, CURRENT_DATE())
                      AND sku_name LIKE '%SQL%'
                    GROUP BY is_job, is_notebook
                """,
            ),
            # Factor 1: Contextual -- catalog-wide tag coverage
            Test(
                name="tag_coverage",
                factor="contextual", requirement="classification_coverage", target_type="database",
                platform=self.platform,
                description="Percentage of tables with at least one tag in Unity Catalog",
                query="""
                    SELECT CAST(
                        COUNT(DISTINCT CONCAT(schema_name, '.', table_name)) AS FLOAT
                    ) / NULLIF(
                        (SELECT COUNT(*) FROM information_schema.tables
                         WHERE table_schema NOT IN ('information_schema', 'default')), 0
                    ) AS measured_value
                    FROM system.information_schema.table_tags
                """,
            ),
        ])

        return tests

    # ------------------------------------------------------------------
    # Table-level: inherit common + add Databricks-native
    # ------------------------------------------------------------------

    def table_tests(self, table: TableInfo) -> list[Test]:
        tests = super().table_tests(table)
        s, t = table.schema, table.name

        tests.extend([
            # Factor 3: Current -- Delta table freshness from DESCRIBE HISTORY
            Test(
                name="delta_freshness",
                factor="current", requirement="max_staleness_hours", target_type="table",
                platform=self.platform,
                description="Hours since last write from Delta table history",
                query=f"""
                    SELECT TIMESTAMPDIFF(HOUR, MAX(timestamp), CURRENT_TIMESTAMP()) AS measured_value
                    FROM (DESCRIBE HISTORY `{s}`.`{t}`)
                    WHERE operation IN ('WRITE', 'MERGE', 'DELETE', 'UPDATE', 'STREAMING UPDATE')
                """,
            ),
            # Factor 4: Correlated -- schema evolution from Delta history
            Test(
                name="delta_schema_evolution",
                factor="correlated", requirement="schema_versioning", target_type="table",
                platform=self.platform,
                description="Schema change events from Delta table history",
                query=f"""
                    SELECT COUNT(*) AS schema_change_count, MIN(timestamp) AS earliest, MAX(timestamp) AS latest
                    FROM (DESCRIBE HISTORY `{s}`.`{t}`)
                    WHERE operation IN ('SET TBLPROPERTIES', 'CHANGE COLUMN', 'ADD COLUMNS', 'REPLACE COLUMNS')
                """,
            ),
            # Factor 2: Consumable -- Delta file statistics
            Test(
                name="delta_file_stats",
                factor="consumable", requirement="storage_optimization", target_type="table",
                platform=self.platform,
                description="Delta table file count, size, and partitioning from DESCRIBE DETAIL",
                query=f"""
                    SELECT numFiles, sizeInBytes, numFiles AS file_count,
                        CASE WHEN numFiles > 0 THEN sizeInBytes / numFiles ELSE 0 END AS avg_file_bytes
                    FROM (DESCRIBE DETAIL `{s}`.`{t}`)
                """,
            ),
            # Factor 1: Contextual -- table properties and owner
            Test(
                name="table_metadata",
                factor="contextual", requirement="table_documentation", target_type="table",
                platform=self.platform,
                description="Table owner and comment from Unity Catalog",
                query=f"""
                    SELECT table_owner, comment,
                        CASE WHEN comment IS NOT NULL AND comment != '' THEN 1 ELSE 0 END AS has_comment,
                        CASE WHEN table_owner IS NOT NULL AND table_owner != '' THEN 1 ELSE 0 END AS has_owner
                    FROM information_schema.tables
                    WHERE table_schema = '{s}' AND table_name = '{t}'
                """,
            ),
            # Factor 5: Compliant -- column tags (PII classification)
            Test(
                name="column_tag_coverage",
                factor="compliant", requirement="pii_tagging", target_type="table",
                platform=self.platform,
                description="Percentage of columns with Unity Catalog tags",
                query=f"""
                    SELECT CAST(
                        COUNT(DISTINCT ct.column_name) AS FLOAT
                    ) / NULLIF(
                        (SELECT COUNT(*) FROM information_schema.columns
                         WHERE table_schema = '{s}' AND table_name = '{t}'), 0
                    ) AS measured_value
                    FROM system.information_schema.column_tags ct
                    WHERE ct.schema_name = '{s}' AND ct.table_name = '{t}'
                """,
            ),
            # Factor 4: Correlated -- table-level lineage
            Test(
                name="table_upstream_lineage",
                factor="correlated", requirement="table_lineage", target_type="table",
                platform=self.platform,
                description="Upstream sources for this table from Unity Catalog lineage",
                query=f"""
                    SELECT COUNT(*) AS upstream_count,
                        COUNT(DISTINCT source_table_full_name) AS distinct_sources
                    FROM system.access.table_lineage
                    WHERE target_table_full_name LIKE '%{s}.{t}'
                      AND target_type = 'TABLE'
                """,
            ),
        ])

        return tests

    # ------------------------------------------------------------------
    # Column-level: inherit all common column tests
    # ------------------------------------------------------------------

    # CommonSuite.column_tests() handles all column-level tests.
    # Databricks column-level capabilities (tags, lineage) are assessed
    # at the table and database level via Unity Catalog system tables.
