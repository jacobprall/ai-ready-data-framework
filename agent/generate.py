"""Generator module: maps column metadata to applicable test queries.

The generator is the core mapping logic that determines which tests apply to which
data based on column metadata (type, cardinality, name patterns, constraints).

Column-level tests are generated per column. Table-level tests are generated per table.
Database-level tests are generated once per assessment run.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agent.discover import ColumnInfo, DatabaseInventory, TableInfo


@dataclass
class TestCase:
    """A generated test case ready for execution."""
    query_file: str          # Path to the .sql file (relative to queries/)
    factor: str              # e.g., "clean", "contextual"
    requirement: str         # e.g., "null_rate", "duplicate_rate"
    requires: str            # e.g., "ansi-sql", "information-schema"
    target_type: str         # "column", "table", or "database"
    target: str              # Fully qualified: schema.table or schema.table.column
    schema: str
    table: str
    column: str | None       # None for table-level and database-level tests
    description: str


def parse_query_metadata(query_path: Path) -> dict[str, str]:
    """Parse YAML metadata from SQL comment headers."""
    metadata: dict[str, str] = {}
    for line in query_path.read_text().splitlines():
        if line.startswith("-- ") and ":" in line:
            key, _, value = line[3:].partition(":")
            metadata[key.strip()] = value.strip()
        elif not line.startswith("--"):
            break
    return metadata


def generate_tests(inventory: DatabaseInventory) -> list[TestCase]:
    """Generate test cases based on discovered schema metadata.

    Three levels of test generation:
    1. Database-level: run once per assessment (coverage metrics, RBAC, etc.)
    2. Table-level: run once per table (naming consistency, AI-compatible types, etc.)
    3. Column-level: run per column based on type and metadata
    """
    tests: list[TestCase] = []
    queries_dir = Path(__file__).parent / "queries"
    providers = inventory.available_providers

    # Database-level tests (run once)
    tests.extend(_generate_database_tests(inventory, queries_dir, providers))

    # Table-level and column-level tests
    for table in inventory.tables:
        tests.extend(_generate_table_tests(table, queries_dir, providers))
        for column in table.columns:
            tests.extend(_generate_column_tests(table, column, queries_dir, providers))

    return tests


# ---------------------------------------------------------------------------
# Database-level tests
# ---------------------------------------------------------------------------

def _generate_database_tests(
    inventory: DatabaseInventory,
    queries_dir: Path,
    providers: list[str],
) -> list[TestCase]:
    """Generate tests that run once across the entire database."""
    tests: list[TestCase] = []
    db_target = "database"

    # Factor 1: Contextual -- table comment coverage
    tests.append(_make_db_test(queries_dir, "information-schema/table_comment_coverage.sql", db_target))

    # Factor 2: Consumable -- timestamp column coverage (are tables time-aware?)
    tests.append(_make_db_test(queries_dir, "ansi-sql/timestamp_column_coverage.sql", db_target))

    # Factor 4: Correlated -- constraint coverage
    tests.append(_make_db_test(queries_dir, "information-schema/constraint_coverage.sql", db_target))

    # Factor 5: Compliant -- RBAC coverage
    tests.append(_make_db_test(queries_dir, "information-schema/rbac_coverage.sql", db_target))

    # Snowflake enrichment
    if "snowflake" in providers:
        tests.append(_make_db_test(queries_dir, "snowflake/copy_history_errors.sql", db_target))
        tests.append(_make_db_test(queries_dir, "snowflake/access_history.sql", db_target))

    # Databricks enrichment
    if "databricks" in providers:
        tests.append(_make_db_test(queries_dir, "databricks/table_lineage.sql", db_target))
        tests.append(_make_db_test(queries_dir, "databricks/access_audit.sql", db_target))

    # OTEL enrichment -- pipeline-level observability
    if "otel" in providers:
        tests.append(_make_db_test(queries_dir, "otel/pipeline_lineage.sql", db_target))
        tests.append(_make_db_test(queries_dir, "otel/pipeline_freshness.sql", db_target))
        tests.append(_make_db_test(queries_dir, "otel/pipeline_error_rate.sql", db_target))
        tests.append(_make_db_test(queries_dir, "otel/pipeline_latency.sql", db_target))
        tests.append(_make_db_test(queries_dir, "otel/throughput_analysis.sql", db_target))
        tests.append(_make_db_test(queries_dir, "otel/access_log_analysis.sql", db_target))
        tests.append(_make_db_test(queries_dir, "otel/pipeline_span_depth.sql", db_target))

    return tests


# ---------------------------------------------------------------------------
# Table-level tests
# ---------------------------------------------------------------------------

def _generate_table_tests(
    table: TableInfo,
    queries_dir: Path,
    providers: list[str],
) -> list[TestCase]:
    """Generate tests that run once per table."""
    tests: list[TestCase] = []
    table_target = f"{table.schema}.{table.name}"

    # Factor 1: Contextual -- column comment coverage for this table
    tests.append(_make_table_test(
        queries_dir, "information-schema/column_comment_coverage.sql", table_target, table))

    # Factor 1: Contextual -- naming consistency
    tests.append(_make_table_test(
        queries_dir, "ansi-sql/naming_consistency.sql", table_target, table))

    # Factor 1: Contextual -- foreign key coverage (only if table has _id columns)
    id_columns = [c for c in table.columns if c.name.lower().endswith("_id") and c.name.lower() != "id"]
    if id_columns:
        tests.append(_make_table_test(
            queries_dir, "information-schema/foreign_key_coverage.sql", table_target, table))

    # Factor 2: Consumable -- AI-compatible type rate
    tests.append(_make_table_test(
        queries_dir, "ansi-sql/ai_compatible_type_rate.sql", table_target, table))

    # Factor 5: Compliant -- PII column name scan
    tests.append(_make_table_test(
        queries_dir, "ansi-sql/pii_column_name_scan.sql", table_target, table))

    # Databricks enrichment
    if "databricks" in providers:
        tests.append(_make_table_test(
            queries_dir, "databricks/table_properties.sql", table_target, table))
        tests.append(_make_table_test(
            queries_dir, "databricks/column_tags.sql", table_target, table))
        tests.append(_make_table_test(
            queries_dir, "databricks/table_freshness.sql", table_target, table))
        tests.append(_make_table_test(
            queries_dir, "databricks/schema_evolution.sql", table_target, table))

    # Iceberg enrichment -- metadata-level assessment per table
    if "iceberg" in providers:
        tests.append(_make_table_test(
            queries_dir, "iceberg/snapshot_history.sql", table_target, table))
        tests.append(_make_table_test(
            queries_dir, "iceberg/snapshot_freshness.sql", table_target, table))
        tests.append(_make_table_test(
            queries_dir, "iceberg/schema_evolution.sql", table_target, table))
        tests.append(_make_table_test(
            queries_dir, "iceberg/manifest_statistics.sql", table_target, table))
        tests.append(_make_table_test(
            queries_dir, "iceberg/column_statistics.sql", table_target, table))
        tests.append(_make_table_test(
            queries_dir, "iceberg/partition_evolution.sql", table_target, table))
        tests.append(_make_table_test(
            queries_dir, "iceberg/table_properties.sql", table_target, table))

    return tests


# ---------------------------------------------------------------------------
# Column-level tests
# ---------------------------------------------------------------------------

def _generate_column_tests(
    table: TableInfo,
    column: ColumnInfo,
    queries_dir: Path,
    providers: list[str],
) -> list[TestCase]:
    """Generate tests for a single column based on its metadata."""
    tests: list[TestCase] = []
    col_target = f"{table.schema}.{table.name}.{column.name}"

    # Factor 0: Clean -- universal (all columns)
    tests.append(_make_col_test(queries_dir, "ansi-sql/null_rate.sql", col_target, table, column))

    # Factor 0: Clean -- string columns
    if column.is_string:
        tests.append(_make_col_test(queries_dir, "ansi-sql/pii_pattern_scan.sql", col_target, table, column))
        tests.append(_make_col_test(queries_dir, "ansi-sql/type_consistency.sql", col_target, table, column))
        tests.append(_make_col_test(queries_dir, "ansi-sql/format_consistency.sql", col_target, table, column))

    # Factor 0: Clean -- numeric columns
    if column.is_numeric:
        tests.append(_make_col_test(queries_dir, "ansi-sql/value_distribution.sql", col_target, table, column))
        tests.append(_make_col_test(queries_dir, "ansi-sql/zero_negative_check.sql", col_target, table, column))

    # Factor 0: Clean -- candidate key columns
    if column.is_candidate_key:
        tests.append(_make_col_test(queries_dir, "ansi-sql/duplicate_detection.sql", col_target, table, column))

    # Factor 3: Current -- timestamp columns get freshness checks
    if column.is_timestamp:
        tests.append(_make_col_test(queries_dir, "ansi-sql/table_freshness.sql", col_target, table, column))

    return tests


# ---------------------------------------------------------------------------
# Test case constructors
# ---------------------------------------------------------------------------

def _make_col_test(
    queries_dir: Path,
    query_rel_path: str,
    target: str,
    table: TableInfo,
    column: ColumnInfo,
) -> TestCase:
    """Create a column-level TestCase."""
    query_path = queries_dir / query_rel_path
    metadata = parse_query_metadata(query_path)
    return TestCase(
        query_file=query_rel_path,
        factor=metadata.get("factor", "clean"),
        requirement=metadata.get("requirement", "unknown"),
        requires=metadata.get("requires", "ansi-sql"),
        target_type="column",
        target=target,
        schema=table.schema,
        table=table.name,
        column=column.name,
        description=metadata.get("description", ""),
    )


def _make_table_test(
    queries_dir: Path,
    query_rel_path: str,
    target: str,
    table: TableInfo,
) -> TestCase:
    """Create a table-level TestCase."""
    query_path = queries_dir / query_rel_path
    metadata = parse_query_metadata(query_path)
    return TestCase(
        query_file=query_rel_path,
        factor=metadata.get("factor", "clean"),
        requirement=metadata.get("requirement", "unknown"),
        requires=metadata.get("requires", "ansi-sql"),
        target_type="table",
        target=target,
        schema=table.schema,
        table=table.name,
        column=None,
        description=metadata.get("description", ""),
    )


def _make_db_test(
    queries_dir: Path,
    query_rel_path: str,
    target: str,
) -> TestCase:
    """Create a database-level TestCase."""
    query_path = queries_dir / query_rel_path
    metadata = parse_query_metadata(query_path)
    return TestCase(
        query_file=query_rel_path,
        factor=metadata.get("factor", "clean"),
        requirement=metadata.get("requirement", "unknown"),
        requires=metadata.get("requires", "ansi-sql"),
        target_type="database",
        target=target,
        schema="",
        table="",
        column=None,
        description=metadata.get("description", ""),
    )
