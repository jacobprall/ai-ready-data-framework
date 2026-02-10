"""Integration tests: discover() against DuckDB fixture database."""

import pytest

from agent.context import UserContext
from agent.discover import discover


pytestmark = pytest.mark.integration


class TestDiscoverAgainstFixture:

    def test_discovers_tables(self, duckdb_conn):
        inventory = discover(duckdb_conn)
        assert len(inventory.tables) > 0

    def test_discovers_analytics_tables(self, duckdb_conn):
        inventory = discover(duckdb_conn)
        analytics_tables = [t for t in inventory.tables if t.schema == "analytics"]
        names = {t.name for t in analytics_tables}
        assert "orders" in names
        assert "customers" in names
        assert "products" in names
        assert "events" in names
        assert "dim_country" in names

    def test_discovers_columns(self, duckdb_conn):
        inventory = discover(duckdb_conn)
        orders = next(t for t in inventory.tables if t.name == "orders" and t.schema == "analytics")
        col_names = {c.name for c in orders.columns}
        assert "order_id" in col_names
        assert "customer_id" in col_names
        assert "status" in col_names
        assert "created_at" in col_names

    def test_detects_platform(self, duckdb_conn):
        inventory = discover(duckdb_conn)
        # DuckDB's version() output varies across versions; detection may
        # return "duckdb" or "generic" depending on the version string format.
        assert inventory.detected_platform in ("duckdb", "generic")

    def test_schema_filter(self, duckdb_conn):
        inventory = discover(duckdb_conn, schemas=["analytics"])
        schemas = {t.schema for t in inventory.tables}
        assert "analytics" in schemas
        assert "staging" not in schemas

    def test_user_context_excludes_schemas(self, duckdb_conn):
        ctx = UserContext(excluded_schemas=["staging", "_scratch"])
        inventory = discover(duckdb_conn, user_context=ctx)
        schemas = {t.schema for t in inventory.tables}
        assert "staging" not in schemas
        assert "_scratch" not in schemas
        assert "analytics" in schemas

    def test_user_context_excludes_specific_table(self, duckdb_conn):
        ctx = UserContext(excluded_tables=["analytics.dim_country"])
        inventory = discover(duckdb_conn, user_context=ctx)
        names = {f"{t.schema}.{t.name}" for t in inventory.tables}
        assert "analytics.dim_country" not in names
        assert "analytics.orders" in names

    def test_column_types_detected(self, duckdb_conn):
        inventory = discover(duckdb_conn, schemas=["analytics"])
        orders = next(t for t in inventory.tables if t.name == "orders")
        customer_id_col = next(c for c in orders.columns if c.name == "customer_id")
        created_at_col = next(c for c in orders.columns if c.name == "created_at")
        status_col = next(c for c in orders.columns if c.name == "status")
        assert customer_id_col.is_numeric
        assert created_at_col.is_timestamp
        assert status_col.is_string

    def test_has_providers(self, duckdb_conn):
        inventory = discover(duckdb_conn)
        assert "ansi-sql" in inventory.available_providers
        assert "information-schema" in inventory.available_providers
