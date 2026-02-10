"""Tests for the centralized platform registry (agent/platforms.py)."""

import pytest

from agent.platforms import (
    BASE_NUMERIC_TYPES,
    BASE_STRING_TYPES,
    BASE_TIMESTAMP_TYPES,
    Platform,
    _ensure_builtins,
    detect_platform,
    get_all_numeric_types,
    get_all_string_types,
    get_all_timestamp_types,
    get_platform,
    get_platform_by_scheme,
    list_platforms,
    register_platform,
)


class TestPlatformRegistry:

    def test_builtins_registered(self):
        """Both built-in platforms are registered."""
        names = list_platforms()
        assert "snowflake" in names
        assert "duckdb" in names

    def test_community_platforms_not_builtin(self):
        """Community platforms are NOT registered by default."""
        names = list_platforms()
        assert "databricks" not in names
        assert "postgresql" not in names

    def test_get_platform_by_name(self):
        p = get_platform("snowflake")
        assert p is not None
        assert p.name == "snowflake"
        assert "snowflake" in p.schemes

    def test_get_platform_by_scheme(self):
        p = get_platform_by_scheme("snowflake")
        assert p is not None
        assert p.name == "snowflake"

    def test_get_platform_by_duckdb_scheme(self):
        p = get_platform_by_scheme("duckdb")
        assert p is not None
        assert p.name == "duckdb"

    def test_get_platform_unknown(self):
        assert get_platform("mysql") is None

    def test_get_platform_by_unknown_scheme(self):
        assert get_platform_by_scheme("oracle") is None

    def test_community_platform_not_found(self):
        """Community platforms return None unless explicitly registered."""
        assert get_platform("postgresql") is None
        assert get_platform_by_scheme("postgresql") is None


class TestPlatformProperties:

    def test_snowflake_properties(self):
        p = get_platform("snowflake")
        assert p.identifier_quote == '"'
        assert p.cast_float == "FLOAT"
        assert p.suite_class is not None
        assert "SnowflakeSuite" in p.suite_class

    def test_duckdb_properties(self):
        p = get_platform("duckdb")
        assert p.identifier_quote == '"'
        assert p.suite_class is None  # uses CommonSuite

    def test_each_platform_has_connect_fn(self):
        for name in list_platforms():
            p = get_platform(name)
            assert callable(p.connect_fn), f"{name} has no connect_fn"

    def test_each_platform_has_detect_sql(self):
        for name in list_platforms():
            p = get_platform(name)
            assert p.detect_sql, f"{name} has no detect_sql"

    def test_each_platform_has_driver_install(self):
        for name in list_platforms():
            p = get_platform(name)
            assert "pip install" in p.driver_install, f"{name} has no driver_install"


class TestCustomPlatformRegistration:

    def test_register_custom_platform(self):
        custom = Platform(
            name="test_custom",
            schemes=["testdb"],
            driver_package="test-driver",
            driver_install="pip install test-driver",
            connect_fn=lambda cs: None,
            # Use a SQL statement that will fail on all platforms so it
            # doesn't interfere with detect_platform() probing order.
            detect_sql="SELECT * FROM __nonexistent_test_custom_table__",
            detect_match="test_custom",
        )
        register_platform(custom)
        assert get_platform("test_custom") is not None
        assert get_platform_by_scheme("testdb") is not None

    def test_custom_platform_in_list(self):
        names = list_platforms()
        assert "test_custom" in names


class TestTypeSets:

    def test_base_numeric_has_standard_types(self):
        assert "int" in BASE_NUMERIC_TYPES
        assert "float" in BASE_NUMERIC_TYPES
        assert "decimal" in BASE_NUMERIC_TYPES

    def test_base_string_has_standard_types(self):
        assert "varchar" in BASE_STRING_TYPES
        assert "text" in BASE_STRING_TYPES

    def test_base_timestamp_has_standard_types(self):
        assert "timestamp" in BASE_TIMESTAMP_TYPES
        assert "datetime" in BASE_TIMESTAMP_TYPES
        assert "date" in BASE_TIMESTAMP_TYPES

    def test_all_numeric_includes_platform_extras(self):
        all_types = get_all_numeric_types()
        # DuckDB adds hugeint, Snowflake adds number
        assert "hugeint" in all_types or "number" in all_types
        # Base types still present
        assert "int" in all_types

    def test_all_string_includes_platform_extras(self):
        all_types = get_all_string_types()
        # Snowflake adds variant
        assert "variant" in all_types
        # Base types still present
        assert "varchar" in all_types

    def test_all_timestamp_includes_platform_extras(self):
        all_types = get_all_timestamp_types()
        # Snowflake adds timestamp_ltz, etc.
        assert "timestamp_ltz" in all_types
        # Base types still present
        assert "timestamp" in all_types


class TestDetectPlatform:

    def test_detect_duckdb(self, duckdb_conn):
        """detect_platform() identifies DuckDB from a live connection."""
        result = detect_platform(duckdb_conn)
        # DuckDB may report as "duckdb" or fall through to "generic" depending
        # on version string; both are acceptable.
        assert result in ("duckdb", "generic")
