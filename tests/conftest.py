"""Shared pytest fixtures for the AI-Ready Data Assessment Agent test suite."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Ensure agent package is importable
sys.path.insert(0, str(Path(__file__).parent.parent / "agent"))

from agent.context import UserContext
from agent.discover import ColumnInfo, DatabaseInventory, TableInfo
from agent.suites.base import Test, TestResult


# ---------------------------------------------------------------------------
# DuckDB fixture database (session-scoped, created once)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def fixture_db_path(tmp_path_factory: pytest.TempPathFactory) -> str:
    """Create the DuckDB fixture database and return its path."""
    from tests.fixtures.create_fixture import create_fixture

    db_dir = tmp_path_factory.mktemp("fixture")
    return create_fixture(str(db_dir / "sample.duckdb"))


@pytest.fixture(scope="session")
def duckdb_conn(fixture_db_path: str):
    """Session-scoped DuckDB connection to the fixture database."""
    import duckdb

    conn = duckdb.connect(fixture_db_path)
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# Synthetic data structures (no DB required)
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_columns() -> list[ColumnInfo]:
    """A variety of columns for testing type detection and heuristics."""
    return [
        ColumnInfo(name="customer_id", data_type="integer", is_nullable=False, column_default=None, ordinal_position=1, constraints=["PRIMARY KEY"]),
        ColumnInfo(name="email", data_type="varchar", is_nullable=True, column_default=None, ordinal_position=2),
        ColumnInfo(name="phone", data_type="varchar", is_nullable=True, column_default=None, ordinal_position=3),
        ColumnInfo(name="middle_name", data_type="varchar", is_nullable=True, column_default=None, ordinal_position=4),
        ColumnInfo(name="total_amount", data_type="decimal(10,2)", is_nullable=False, column_default=None, ordinal_position=5),
        ColumnInfo(name="created_at", data_type="timestamp", is_nullable=False, column_default=None, ordinal_position=6),
        ColumnInfo(name="order_id", data_type="integer", is_nullable=False, column_default=None, ordinal_position=7),
        ColumnInfo(name="status", data_type="varchar", is_nullable=True, column_default=None, ordinal_position=8),
        ColumnInfo(name="productName", data_type="varchar", is_nullable=True, column_default=None, ordinal_position=9),
    ]


@pytest.fixture
def sample_table(sample_columns: list[ColumnInfo]) -> TableInfo:
    """A sample table with mixed columns."""
    return TableInfo(
        catalog="main",
        schema="analytics",
        name="orders",
        table_type="BASE TABLE",
        columns=sample_columns,
    )


@pytest.fixture
def sample_inventory(sample_table: TableInfo) -> DatabaseInventory:
    """A synthetic DatabaseInventory for unit testing."""
    customers = TableInfo(
        catalog="main",
        schema="analytics",
        name="customers",
        table_type="BASE TABLE",
        columns=[
            ColumnInfo(name="customer_id", data_type="integer", is_nullable=False, column_default=None, ordinal_position=1, constraints=["PRIMARY KEY"]),
            ColumnInfo(name="first_name", data_type="varchar", is_nullable=False, column_default=None, ordinal_position=2),
            ColumnInfo(name="last_name", data_type="varchar", is_nullable=False, column_default=None, ordinal_position=3),
            ColumnInfo(name="middle_name", data_type="varchar", is_nullable=True, column_default=None, ordinal_position=4),
            ColumnInfo(name="email", data_type="varchar", is_nullable=True, column_default=None, ordinal_position=5),
            ColumnInfo(name="phone", data_type="varchar", is_nullable=True, column_default=None, ordinal_position=6),
            ColumnInfo(name="created_at", data_type="timestamp", is_nullable=False, column_default=None, ordinal_position=7),
        ],
    )

    products = TableInfo(
        catalog="main",
        schema="analytics",
        name="products",
        table_type="BASE TABLE",
        columns=[
            ColumnInfo(name="product_id", data_type="integer", is_nullable=False, column_default=None, ordinal_position=1),
            ColumnInfo(name="productName", data_type="varchar", is_nullable=True, column_default=None, ordinal_position=2),
            ColumnInfo(name="product_category", data_type="varchar", is_nullable=True, column_default=None, ordinal_position=3),
            ColumnInfo(name="price", data_type="decimal", is_nullable=True, column_default=None, ordinal_position=4),
        ],
    )

    staging_table = TableInfo(
        catalog="main",
        schema="staging",
        name="tmp_orders",
        table_type="BASE TABLE",
        columns=[
            ColumnInfo(name="id", data_type="integer", is_nullable=False, column_default=None, ordinal_position=1),
            ColumnInfo(name="raw_data", data_type="varchar", is_nullable=True, column_default=None, ordinal_position=2),
        ],
    )

    return DatabaseInventory(
        tables=[sample_table, customers, products, staging_table],
        available_providers=["ansi-sql", "information-schema", "duckdb"],
        unavailable_providers=["iceberg", "otel"],
        permissions_gaps=[],
        detected_platform="duckdb",
    )


@pytest.fixture
def sample_context() -> UserContext:
    """A populated UserContext for testing context overrides."""
    return UserContext(
        target_level="L2",
        excluded_schemas=["staging", "_scratch"],
        excluded_tables=[],
        known_pii_columns=["analytics.customers.email", "analytics.customers.phone"],
        false_positive_pii=["analytics.orders.status"],
        nullable_by_design=["analytics.customers.middle_name"],
        table_criticality={"analytics.orders": "critical", "analytics.dim_country": "low"},
        freshness_slas={"analytics.orders": 2, "analytics.dim_country": 720},
        confirmed_keys=["analytics.events.event_id"],
        not_keys=["analytics.products.product_id"],
        infrastructure=set(),
        known_issues=["High null rate in orders.customer_id"],
        accepted_failures=["null_rate|analytics.customers.middle_name"],
    )


@pytest.fixture
def empty_context() -> UserContext:
    """A default UserContext with no user input."""
    return UserContext()


@pytest.fixture
def sample_test() -> Test:
    """A sample Test object for unit tests."""
    return Test(
        name="null_rate",
        factor="clean",
        requirement="null_rate",
        sql='SELECT 0.25 AS measured_value',
        target_type="column",
        platform="common",
    )


@pytest.fixture
def sample_results() -> list[TestResult]:
    """A list of TestResult objects for report-building tests."""
    return [
        TestResult(
            name="null_rate", factor="clean", requirement="null_rate",
            target="analytics.orders.customer_id", platform="common",
            levels=["L1", "L2", "L3"],
            result={"L1": "fail", "L2": "fail", "L3": "fail"},
            measured_value=0.23, thresholds={"L1": 0.10, "L2": 0.05, "L3": 0.01},
            detail="Measured 0.2300", query="SELECT ...",
        ),
        TestResult(
            name="column_comment_coverage", factor="contextual", requirement="column_comment_coverage",
            target="analytics.orders", platform="common",
            levels=["L1", "L2", "L3"],
            result={"L1": "pass", "L2": "fail", "L3": "fail"},
            measured_value=0.60, thresholds={"L1": 0.50, "L2": 0.90, "L3": 0.95},
            detail="Measured 0.6000", query="SELECT ...",
        ),
        TestResult(
            name="constraint_coverage", factor="correlated", requirement="constraint_coverage",
            target="database", platform="common",
            levels=["L1", "L2", "L3"],
            result={"L1": "pass", "L2": "pass", "L3": "fail"},
            measured_value=0.85, thresholds={"L1": 0.50, "L2": 0.80, "L3": 0.95},
            detail="Measured 0.8500", query="SELECT ...",
        ),
        TestResult(
            name="naming_consistency", factor="contextual", requirement="naming_consistency",
            target="analytics.products", platform="common",
            levels=["L1", "L2", "L3"],
            result={"L1": "pass", "L2": "pass", "L3": "pass"},
            measured_value=1.0, thresholds={"L1": 0.50, "L2": 0.80, "L3": 0.90},
            detail="Measured 1.0000", query="SELECT ...",
        ),
    ]


@pytest.fixture
def sample_report(sample_results: list[TestResult], sample_inventory: DatabaseInventory) -> dict:
    """A full report dict for testing interpretation and diffing."""
    from agent.score import build_report
    return build_report(sample_results, sample_inventory, "duckdb://test.db", "common")


@pytest.fixture
def sample_thresholds() -> dict:
    """Default thresholds for testing scoring."""
    return {
        "clean": {
            "null_rate": {"direction": "max", "L1": 0.10, "L2": 0.05, "L3": 0.01},
            "duplicate_rate": {"direction": "max", "L1": 0.05, "L2": 0.02, "L3": 0.005},
            "pii_detection_rate": {"direction": "max", "L1": None, "L2": 0.0, "L3": 0.0},
            "zero_negative_rate": {"direction": "max", "L1": 0.20, "L2": 0.10, "L3": 0.05},
        },
        "contextual": {
            "column_comment_coverage": {"direction": "min", "L1": 0.50, "L2": 0.90, "L3": 0.95},
            "table_comment_coverage": {"direction": "min", "L1": 0.50, "L2": 0.90, "L3": 0.95},
            "naming_consistency": {"direction": "min", "L1": 0.50, "L2": 0.80, "L3": 0.90},
            "foreign_key_coverage": {"direction": "min", "L1": 0.30, "L2": 0.70, "L3": 0.90},
        },
        "current": {
            "max_staleness_hours": {"direction": "max", "L1": 168, "L2": 24, "L3": 6},
        },
        "correlated": {
            "constraint_coverage": {"direction": "min", "L1": 0.50, "L2": 0.80, "L3": 0.95},
        },
        "compliant": {
            "rbac_coverage": {"direction": "min", "L1": 0.30, "L2": 0.70, "L3": 0.90},
            "pii_column_name_rate": {"direction": "max", "L1": None, "L2": 0.0, "L3": 0.0},
        },
    }
