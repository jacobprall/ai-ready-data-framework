"""Test suites for the AI-Ready Data Assessment Agent.

Each suite is a complete, self-contained set of tests that covers all five factors
using a specific platform's native capabilities. The common suite provides the
ANSI SQL baseline. Platform suites extend and override common tests with deeper,
platform-native assessments.

Usage:
    from agent.suites import get_suite

    suite = get_suite("snowflake")  # Returns SnowflakeSuite
    suite = get_suite("auto", conn) # Auto-detects from connection
"""

from __future__ import annotations

from typing import Any

from agent.suites.base import Suite
from agent.suites.common import CommonSuite


# Registry of platform suites -- lazy imports to avoid requiring drivers
_REGISTRY: dict[str, type[Suite]] = {
    "common": CommonSuite,
}


def register_suite(platform: str, suite_cls: type[Suite]) -> None:
    """Register a platform suite."""
    _REGISTRY[platform] = suite_cls


def get_suite(platform: str, conn: Any | None = None) -> Suite:
    """Get a suite by platform name or auto-detect from connection.

    Args:
        platform: Platform name ("snowflake", "databricks", "postgresql", "duckdb", "auto", "common").
        conn: DB-API 2.0 connection for auto-detection.

    Returns:
        An instantiated Suite.
    """
    # Lazy-register platform suites on first access
    _ensure_registered()

    if platform == "auto" and conn is not None:
        platform = _detect_platform(conn)

    if platform in _REGISTRY:
        return _REGISTRY[platform]()

    # Fall back to common if no suite exists for this platform
    return CommonSuite()


def list_suites() -> list[str]:
    """List all registered suite names."""
    _ensure_registered()
    return list(_REGISTRY.keys())


def _ensure_registered() -> None:
    """Lazy-register all built-in suites."""
    if "snowflake" not in _REGISTRY:
        from agent.suites.snowflake import SnowflakeSuite
        _REGISTRY["snowflake"] = SnowflakeSuite
    if "databricks" not in _REGISTRY:
        from agent.suites.databricks import DatabricksSuite
        _REGISTRY["databricks"] = DatabricksSuite


def _detect_platform(conn: Any) -> str:
    """Detect platform from a live connection."""
    cursor = conn.cursor()

    # Snowflake
    try:
        cursor.execute("SELECT CURRENT_ACCOUNT()")
        cursor.fetchone()
        cursor.close()
        return "snowflake"
    except Exception:
        pass

    # Databricks
    try:
        cursor.execute("SELECT current_metastore()")
        cursor.fetchone()
        cursor.close()
        return "databricks"
    except Exception:
        pass

    # PostgreSQL
    try:
        cursor.execute("SELECT version()")
        row = cursor.fetchone()
        if row and "postgresql" in str(row[0]).lower():
            cursor.close()
            return "postgresql"
    except Exception:
        pass

    # DuckDB
    try:
        cursor.execute("SELECT version()")
        row = cursor.fetchone()
        if row and "duckdb" in str(row[0]).lower():
            cursor.close()
            return "duckdb"
    except Exception:
        pass

    cursor.close()
    return "common"
