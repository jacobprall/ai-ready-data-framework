"""Discovery module: connects to a data source and enumerates schemas, tables, and columns.

SAFETY: The assessment agent is strictly read-only. This is enforced at two layers:

    1. Connection layer: where the driver supports it, the connection is opened in
       read-only mode (e.g., PostgreSQL SET default_transaction_read_only = ON).
    2. Execution layer: for SQL platforms, every statement is validated before
       execution -- only SELECT, DESCRIBE, SHOW, EXPLAIN, and WITH are permitted
       (see execute.py). Non-SQL platforms enforce read-only via their own
       connection options (e.g., MongoDB read preference).

Users should also grant the agent a read-only database role as a third layer of defense.

For SQL platforms, the core agent uses DB-API 2.0 connections and ANSI SQL via
information_schema. For non-SQL platforms (MongoDB, Elasticsearch, etc.), the
platform registers a custom discover_fn that handles native introspection.

Built-in drivers:

    pip install snowflake-connector-python   # Snowflake
    pip install duckdb                       # DuckDB

Community platforms can be added via the platform registry -- see CONTRIBUTING.md.

The connect() function auto-detects the driver from the connection string scheme.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agent.platforms import (
    BASE_NUMERIC_TYPES,
    BASE_STRING_TYPES,
    BASE_TIMESTAMP_TYPES,
    detect_platform,
    get_platform,
    get_platform_by_scheme,
    register_platform,  # re-export for backward compat
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ColumnInfo:
    name: str
    data_type: str
    is_nullable: bool
    column_default: str | None
    ordinal_position: int
    character_max_length: int | None = None
    numeric_precision: int | None = None
    numeric_scale: int | None = None
    has_comment: bool = False
    constraints: list[str] = field(default_factory=list)

    @property
    def is_numeric(self) -> bool:
        base = BASE_NUMERIC_TYPES
        return self.data_type.lower().split("(")[0].strip() in base

    @property
    def is_string(self) -> bool:
        base = BASE_STRING_TYPES
        return self.data_type.lower().split("(")[0].strip() in base

    @property
    def is_timestamp(self) -> bool:
        base = BASE_TIMESTAMP_TYPES
        return self.data_type.lower().split("(")[0].strip() in base

    @property
    def is_candidate_key(self) -> bool:
        return (
            "PRIMARY KEY" in self.constraints
            or "UNIQUE" in self.constraints
            or self.name.lower().endswith("_id")
            or self.name.lower() == "id"
        )


@dataclass
class TableInfo:
    catalog: str
    schema: str
    name: str
    table_type: str
    columns: list[ColumnInfo] = field(default_factory=list)

    @property
    def fqn(self) -> str:
        return f"{self.schema}.{self.name}"


@dataclass
class DatabaseInventory:
    tables: list[TableInfo] = field(default_factory=list)
    available_providers: list[str] = field(default_factory=list)
    unavailable_providers: list[str] = field(default_factory=list)
    permissions_gaps: list[str] = field(default_factory=list)
    detected_platform: str = "generic"


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

# Legacy driver registry for backward compatibility.
# New code should use agent.platforms.register_platform() instead.
_DRIVERS: dict[str, Any] = {}


def register_driver(scheme: str, connect_fn: Any) -> None:
    """Register a database driver for a URL scheme (legacy API).

    Prefer agent.platforms.register_platform() for new platforms.
    """
    _DRIVERS[scheme] = connect_fn


def connect(connection_string: str) -> Any:
    """Create a database connection from a connection string.

    Auto-detects the driver from the URL scheme using the platform registry.
    Built-in schemes:

        snowflake://    requires snowflake-connector-python
        duckdb://       requires duckdb

    Community platforms can register additional schemes via register_platform().

    Returns a DB-API 2.0 compatible connection object.
    """
    scheme = connection_string.split("://")[0].lower() if "://" in connection_string else ""

    # Try legacy registered drivers first
    if scheme in _DRIVERS:
        return _DRIVERS[scheme](connection_string)

    # Use the platform registry
    from agent.platforms import get_platform_by_scheme, list_platforms
    platform = get_platform_by_scheme(scheme)
    if platform:
        return platform.connect_fn(connection_string)

    supported = list_platforms() + list(_DRIVERS.keys())
    raise ValueError(
        f"Unsupported connection scheme: '{scheme}'. "
        f"Supported: {', '.join(supported)}. "
        "Install the appropriate driver package and try again."
    )


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def _load_query(query_dir: str, filename: str) -> str:
    """Load a SQL query from the queries directory, stripping the metadata header."""
    query_path = Path(__file__).parent / "queries" / query_dir / filename
    lines = query_path.read_text().splitlines()
    sql_lines = [line for line in lines if not line.startswith("--") or line.strip() == "--"]
    while sql_lines and sql_lines[0].strip() == "":
        sql_lines.pop(0)
    return "\n".join(sql_lines)


def discover(
    conn: Any,
    schemas: list[str] | None = None,
    user_context: Any | None = None,
) -> DatabaseInventory:
    """Discover tables/collections and columns/fields in the connected data source.

    For SQL platforms: uses ANSI SQL and information_schema (works on any SQL database).
    For non-SQL platforms: delegates to the platform's registered discover_fn.

    Args:
        conn: A connection object (DB-API 2.0 for SQL, native client for others).
        schemas: Optional list of schemas/databases to assess.
        user_context: Optional UserContext with exclusions and overrides.

    Returns:
        A DatabaseInventory with all discovered tables/collections and metadata.
    """
    # Detect platform first
    platform_name = detect_platform(conn)
    platform_obj = get_platform(platform_name) if platform_name != "generic" else None

    # Non-SQL platforms with a custom discover_fn: delegate entirely
    if platform_obj and platform_obj.discover_fn is not None:
        inventory = platform_obj.discover_fn(conn, schemas, user_context)
        inventory.detected_platform = platform_name
        if platform_name not in inventory.available_providers:
            inventory.available_providers.append(platform_name)
        return inventory

    # SQL path: ANSI information_schema discovery
    return _discover_sql(conn, schemas, user_context, platform_name)


def _discover_sql(
    conn: Any,
    schemas: list[str] | None,
    user_context: Any | None,
    platform_name: str,
) -> DatabaseInventory:
    """SQL-based discovery via information_schema (original path)."""
    inventory = DatabaseInventory()
    inventory.available_providers = ["ansi-sql", "information-schema"]
    inventory.detected_platform = platform_name

    if platform_name != "generic":
        inventory.available_providers.append(platform_name)

    # Apply user-declared infrastructure context (overrides brittle probes)
    if user_context is not None:
        infra = getattr(user_context, "infrastructure", None) or set()
        # Backward compat: also check legacy boolean fields
        has_otel = "otel" in infra or getattr(user_context, "has_otel", False)
        has_iceberg = "iceberg" in infra or getattr(user_context, "has_iceberg", False)
        if has_otel and "otel" not in inventory.available_providers:
            inventory.available_providers.append("otel")
        if has_iceberg and "iceberg" not in inventory.available_providers:
            inventory.available_providers.append("iceberg")

    cursor = conn.cursor()

    # Discover tables
    table_query = _load_query("information-schema", "table_inventory.sql")
    cursor.execute(table_query)
    rows = cursor.fetchall()

    tables: list[TableInfo] = []
    for row in rows:
        catalog = row[0] or ""
        schema = row[1]
        name = row[2]
        table_type = row[3]
        if schemas and schema.lower() not in [s.lower() for s in schemas]:
            continue
        # Apply user context exclusions
        if user_context is not None and user_context.is_table_excluded(schema, name):
            continue
        tables.append(TableInfo(catalog=catalog, schema=schema, name=name, table_type=table_type))

    # Discover columns and constraints for each table
    col_query_template = _load_query("information-schema", "column_metadata.sql")
    constraint_query_template = _load_query("information-schema", "constraints.sql")

    for table in tables:
        # Columns
        col_query = col_query_template.replace("{schema}", table.schema).replace("{table}", table.name)
        try:
            cursor.execute(col_query)
            col_rows = cursor.fetchall()
        except Exception:
            col_rows = []

        columns: list[ColumnInfo] = []
        for cr in col_rows:
            columns.append(ColumnInfo(
                name=cr[0],
                data_type=cr[1] or "unknown",
                is_nullable=str(cr[2]).upper() == "YES",
                column_default=cr[3],
                ordinal_position=cr[4] or 0,
                character_max_length=cr[5],
                numeric_precision=cr[6],
                numeric_scale=cr[7],
            ))

        # Constraints
        cons_query = constraint_query_template.replace("{schema}", table.schema).replace("{table}", table.name)
        try:
            cursor.execute(cons_query)
            cons_rows = cursor.fetchall()
            for cr_row in cons_rows:
                constraint_type = cr_row[1]
                column_name = cr_row[2]
                for col in columns:
                    if col.name == column_name:
                        col.constraints.append(constraint_type)
        except Exception:
            pass  # Constraints may not be available on all platforms

        table.columns = columns

    inventory.tables = tables

    # Detect Iceberg support (skip probe if user already declared it)
    if "iceberg" not in inventory.available_providers:
        if tables:
            sample = tables[0]
            try:
                cursor.execute(f'SELECT * FROM "{sample.schema}"."{sample.name}".snapshots LIMIT 1')
                cursor.fetchone()
                inventory.available_providers.append("iceberg")
            except Exception:
                inventory.unavailable_providers.append("iceberg")
        else:
            inventory.unavailable_providers.append("iceberg")

    # Detect OTEL data (skip probe if user already declared it)
    if "otel" not in inventory.available_providers:
        otel_endpoint = os.environ.get("AIRD_OTEL_ENDPOINT")
        if otel_endpoint:
            inventory.available_providers.append("otel")
        else:
            try:
                cursor.execute("SELECT 1 FROM otel_traces LIMIT 1")
                cursor.fetchone()
                inventory.available_providers.append("otel")
            except Exception:
                inventory.unavailable_providers.append("otel")

    cursor.close()
    return inventory
