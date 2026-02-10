"""Platform registry: centralizes all platform-specific knowledge.

Each supported database platform is defined as a Platform dataclass and registered
in a central registry. This eliminates scattered if/elif chains and duplicated
detection logic. Both discover.py and suites/__init__.py import from here.

Built-in platforms: Snowflake and DuckDB.
Community platforms (PostgreSQL, Databricks, MySQL, etc.) can be added by calling
register_platform() -- see CONTRIBUTING.md for a complete walkthrough.

To add a new platform:
    1. Define a connect function
    2. Call register_platform() with a Platform dataclass
    3. Create a suite in agent/suites/<platform>.py (optional -- CommonSuite works)
    4. Add optional dependency to agent/pyproject.toml

External plugins can also call register_platform() to add platforms
without modifying this repo.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Callable


# ---------------------------------------------------------------------------
# Platform definition
# ---------------------------------------------------------------------------

@dataclass
class Platform:
    """Complete definition of a supported database platform.

    Centralizes driver connection, platform detection, discovery, SQL dialect
    properties, type mappings, and suite association in one place.

    For non-SQL platforms (MongoDB, Elasticsearch, etc.), set:
        query_type      -- e.g., "mongo_agg" instead of the default "sql"
        detect_fn       -- a callable(conn) -> bool instead of detect_sql
        discover_fn     -- a callable(conn, schemas, user_context) -> DatabaseInventory
                           instead of relying on information_schema
    """
    name: str                                   # "snowflake", "mongodb", etc.
    schemes: list[str]                          # URL schemes: ["mongodb", "mongodb+srv"]
    driver_package: str                         # "pymongo"
    driver_install: str                         # "pip install pymongo"
    connect_fn: Callable[[str], Any]            # function(connection_string) -> connection
    detect_sql: str = ""                        # SQL to probe for this platform (SQL platforms)
    detect_match: str = ""                      # Substring to match in probe result
    query_type: str = "sql"                     # Default query language: "sql", "mongo_agg", "python"
    detect_fn: Callable[[Any], bool] | None = None  # Non-SQL detection: callable(conn) -> bool
    discover_fn: Callable[..., Any] | None = None   # Non-SQL discovery: callable(conn, schemas, ctx) -> DatabaseInventory
    identifier_quote: str = '"'                 # Quote character for identifiers (SQL only)
    cast_float: str = "FLOAT"                   # Type name for CAST to float (SQL only)
    system_schemas: list[str] = field(default_factory=lambda: [
        "information_schema", "pg_catalog", "INFORMATION_SCHEMA",
    ])
    extra_numeric_types: set[str] = field(default_factory=set)      # Platform-specific additions
    extra_string_types: set[str] = field(default_factory=set)
    extra_timestamp_types: set[str] = field(default_factory=set)
    suite_class: str | None = None              # Lazy import path: "agent.suites.snowflake:SnowflakeSuite"
    connection_format: str = ""                 # Example format for docs
    env_vars: dict[str, str] = field(default_factory=dict)  # Env var fallbacks


# ---------------------------------------------------------------------------
# Base type sets (shared across all platforms, extended per-platform)
# ---------------------------------------------------------------------------

BASE_NUMERIC_TYPES: set[str] = {
    "int", "integer", "bigint", "smallint", "tinyint", "float", "double",
    "decimal", "numeric", "real", "number", "money",
}

BASE_STRING_TYPES: set[str] = {
    "varchar", "char", "text", "string", "nvarchar", "nchar",
    "character varying", "character", "clob",
}

BASE_TIMESTAMP_TYPES: set[str] = {
    "timestamp", "datetime", "date", "timestamptz", "timestamp_tz",
    "timestamp_ltz", "timestamp_ntz", "timestamp with time zone",
    "timestamp without time zone",
}


def get_all_numeric_types() -> set[str]:
    """Get the union of base + all registered platform numeric types."""
    types = set(BASE_NUMERIC_TYPES)
    for p in _PLATFORMS.values():
        types |= p.extra_numeric_types
    return types


def get_all_string_types() -> set[str]:
    """Get the union of base + all registered platform string types."""
    types = set(BASE_STRING_TYPES)
    for p in _PLATFORMS.values():
        types |= p.extra_string_types
    return types


def get_all_timestamp_types() -> set[str]:
    """Get the union of base + all registered platform timestamp types."""
    types = set(BASE_TIMESTAMP_TYPES)
    for p in _PLATFORMS.values():
        types |= p.extra_timestamp_types
    return types


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_PLATFORMS: dict[str, Platform] = {}
_SCHEME_INDEX: dict[str, str] = {}  # scheme -> platform name


def register_platform(platform: Platform) -> None:
    """Register a platform. Both built-in and external plugins use this."""
    _PLATFORMS[platform.name] = platform
    for scheme in platform.schemes:
        _SCHEME_INDEX[scheme.lower()] = platform.name


def get_platform(name: str) -> Platform | None:
    """Get a platform by name."""
    _ensure_builtins()
    return _PLATFORMS.get(name)


def get_platform_by_scheme(scheme: str) -> Platform | None:
    """Get a platform by URL scheme."""
    _ensure_builtins()
    name = _SCHEME_INDEX.get(scheme.lower())
    if name:
        return _PLATFORMS.get(name)
    return None


def list_platforms() -> list[str]:
    """List all registered platform names."""
    _ensure_builtins()
    return list(_PLATFORMS.keys())


def detect_platform(conn: Any) -> str:
    """Detect which platform a connection belongs to.

    Iterates through registered platforms and tries each detection probe.
    For SQL platforms, uses detect_sql. For non-SQL platforms, uses detect_fn.
    Returns the platform name, or "generic" if none match.

    This is the single source of truth -- no more duplicate detection logic.
    """
    _ensure_builtins()

    for platform in _PLATFORMS.values():
        try:
            # Non-SQL platforms use a callable detector
            if platform.detect_fn is not None:
                if platform.detect_fn(conn):
                    return platform.name
                continue

            # SQL platforms use a SQL probe
            if not platform.detect_sql:
                continue

            cursor = conn.cursor()
            try:
                cursor.execute(platform.detect_sql)
                row = cursor.fetchone()
                if platform.detect_match:
                    if row and platform.detect_match.lower() in str(row[0]).lower():
                        cursor.close()
                        return platform.name
                else:
                    # No match required -- just succeeding is enough
                    cursor.close()
                    return platform.name
            finally:
                try:
                    cursor.close()
                except Exception:
                    pass
        except Exception:
            pass

    return "generic"


# ---------------------------------------------------------------------------
# Built-in platform connect functions
# ---------------------------------------------------------------------------

def _connect_snowflake(connection_string: str) -> Any:
    """Connect to Snowflake. Requires: pip install snowflake-connector-python"""
    try:
        import snowflake.connector
    except ImportError:
        raise ImportError("Snowflake driver not installed. Run: pip install snowflake-connector-python")

    from urllib.parse import urlparse, parse_qs
    parsed = urlparse(connection_string)
    account = parsed.hostname or ""
    user = parsed.username or os.environ.get("SNOWFLAKE_USER", "")
    password = parsed.password or os.environ.get("SNOWFLAKE_PASSWORD", "")
    path_parts = [p for p in parsed.path.split("/") if p]
    database = path_parts[0] if len(path_parts) > 0 else os.environ.get("SNOWFLAKE_DATABASE", "")
    schema = path_parts[1] if len(path_parts) > 1 else os.environ.get("SNOWFLAKE_SCHEMA", "")
    query_params = parse_qs(parsed.query)
    warehouse = query_params.get("warehouse", [os.environ.get("SNOWFLAKE_WAREHOUSE", "")])[0]
    role = query_params.get("role", [os.environ.get("SNOWFLAKE_ROLE", "")])[0]

    conn_params: dict[str, Any] = {"account": account, "user": user, "password": password}
    if database:
        conn_params["database"] = database
    if schema:
        conn_params["schema"] = schema
    if warehouse:
        conn_params["warehouse"] = warehouse
    if role:
        conn_params["role"] = role
    return snowflake.connector.connect(**conn_params)


def _connect_duckdb(connection_string: str) -> Any:
    """Connect to DuckDB. Requires: pip install duckdb"""
    try:
        import duckdb
    except ImportError:
        raise ImportError("DuckDB driver not installed. Run: pip install duckdb")
    path = connection_string.replace("duckdb://", "")
    if not path or path == ":memory:":
        return duckdb.connect()
    return duckdb.connect(path)


# ---------------------------------------------------------------------------
# Built-in platform registration (lazy, called once)
# ---------------------------------------------------------------------------

_BUILTINS_REGISTERED = False


def _ensure_builtins() -> None:
    """Register all built-in platforms on first access."""
    global _BUILTINS_REGISTERED
    if _BUILTINS_REGISTERED:
        return
    _BUILTINS_REGISTERED = True

    # Built-in platforms: Snowflake + DuckDB.
    # Community can add others via register_platform() -- see CONTRIBUTING.md.
    # Order matters for detection: most specific probes first.

    register_platform(Platform(
        name="snowflake",
        schemes=["snowflake"],
        driver_package="snowflake-connector-python",
        driver_install="pip install snowflake-connector-python",
        connect_fn=_connect_snowflake,
        detect_sql="SELECT CURRENT_ACCOUNT()",
        detect_match="",  # Just succeeding is enough
        identifier_quote='"',
        cast_float="FLOAT",
        system_schemas=["information_schema", "INFORMATION_SCHEMA"],
        extra_numeric_types={"number", "float4", "float8"},
        extra_string_types={"variant", "object", "array"},
        extra_timestamp_types={"timestamp_ltz", "timestamp_ntz", "timestamp_tz"},
        suite_class="agent.suites.snowflake:SnowflakeSuite",
        connection_format="snowflake://user:pass@account/database/schema?warehouse=WH&role=ROLE",
    ))

    register_platform(Platform(
        name="duckdb",
        schemes=["duckdb"],
        driver_package="duckdb",
        driver_install="pip install duckdb",
        connect_fn=_connect_duckdb,
        detect_sql="SELECT version()",
        detect_match="duckdb",
        identifier_quote='"',
        cast_float="FLOAT",
        system_schemas=["information_schema", "pg_catalog", "INFORMATION_SCHEMA"],
        extra_numeric_types={"hugeint", "uinteger", "ubigint", "usmallint", "utinyint"},
        extra_string_types={"blob"},
        extra_timestamp_types={"timestamptz"},
        suite_class=None,  # Uses CommonSuite
        connection_format="duckdb://path/to/file.db",
    ))
