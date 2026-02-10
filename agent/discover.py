"""Discovery module: connects to a database and enumerates schemas, tables, and columns.

SAFETY: The assessment agent is strictly read-only. This is enforced at two layers:

    1. Connection layer: where the driver supports it, the connection is opened in
       read-only mode (e.g., PostgreSQL SET default_transaction_read_only = ON).
    2. Execution layer: every SQL statement is validated before execution -- only
       SELECT, DESCRIBE, SHOW, EXPLAIN, and WITH are permitted (see execute.py).

Users should also grant the agent a read-only database role as a third layer of defense.

The core agent uses DB-API 2.0 connections and ANSI SQL. It does not depend on
any specific database driver. Drivers are installed separately by the user:

    pip install snowflake-connector-python   # Snowflake
    pip install databricks-sql-connector     # Databricks
    pip install psycopg2-binary              # PostgreSQL
    pip install duckdb                       # DuckDB

The connect() function auto-detects the driver from the connection string scheme.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


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
        numeric_types = {"int", "integer", "bigint", "smallint", "tinyint", "float", "double",
                         "decimal", "numeric", "real", "number", "money"}
        return self.data_type.lower().split("(")[0].strip() in numeric_types

    @property
    def is_string(self) -> bool:
        string_types = {"varchar", "char", "text", "string", "nvarchar", "nchar", "character varying",
                        "character", "clob"}
        return self.data_type.lower().split("(")[0].strip() in string_types

    @property
    def is_timestamp(self) -> bool:
        ts_types = {"timestamp", "datetime", "date", "timestamptz", "timestamp_tz",
                    "timestamp_ltz", "timestamp_ntz", "timestamp with time zone",
                    "timestamp without time zone"}
        return self.data_type.lower().split("(")[0].strip() in ts_types

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

# Registry of supported drivers. Each entry maps a URL scheme to a connect function.
_DRIVERS: dict[str, Any] = {}


def register_driver(scheme: str, connect_fn: Any) -> None:
    """Register a database driver for a URL scheme."""
    _DRIVERS[scheme] = connect_fn


def connect(connection_string: str) -> Any:
    """Create a database connection from a connection string.

    Auto-detects the driver from the URL scheme. Supported schemes depend on
    which drivers are installed:

        snowflake://    requires snowflake-connector-python
        databricks://   requires databricks-sql-connector
        postgresql://   requires psycopg2
        duckdb://       requires duckdb

    Returns a DB-API 2.0 compatible connection object.
    """
    scheme = connection_string.split("://")[0].lower() if "://" in connection_string else ""

    # Try registered drivers first
    if scheme in _DRIVERS:
        return _DRIVERS[scheme](connection_string)

    # Built-in driver support (lazy imports -- no hard dependency on any driver)
    if scheme == "snowflake":
        return _connect_snowflake(connection_string)
    elif scheme == "databricks":
        return _connect_databricks(connection_string)
    elif scheme in ("postgresql", "postgres"):
        return _connect_postgres(connection_string)
    elif scheme == "duckdb":
        return _connect_duckdb(connection_string)
    else:
        supported = ["snowflake", "databricks", "postgresql", "duckdb"] + list(_DRIVERS.keys())
        raise ValueError(
            f"Unsupported connection scheme: '{scheme}'. "
            f"Supported: {', '.join(supported)}. "
            "Install the appropriate driver package and try again."
        )


def _connect_snowflake(connection_string: str) -> Any:
    """Connect to Snowflake. Requires: pip install snowflake-connector-python"""
    try:
        import snowflake.connector
    except ImportError:
        raise ImportError(
            "Snowflake driver not installed. Run: pip install snowflake-connector-python"
        )

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


def _connect_databricks(connection_string: str) -> Any:
    """Connect to Databricks. Requires: pip install databricks-sql-connector

    Connection string format:
        databricks://token:<access_token>@<host>:443/<catalog>?http_path=<http_path>
    Or use environment variables:
        DATABRICKS_HOST, DATABRICKS_TOKEN, DATABRICKS_HTTP_PATH, DATABRICKS_CATALOG
    """
    try:
        from databricks import sql as databricks_sql
    except ImportError:
        raise ImportError(
            "Databricks driver not installed. Run: pip install databricks-sql-connector"
        )

    from urllib.parse import urlparse, parse_qs

    parsed = urlparse(connection_string)
    host = parsed.hostname or os.environ.get("DATABRICKS_HOST", "")
    token = parsed.password or os.environ.get("DATABRICKS_TOKEN", "")

    path_parts = [p for p in parsed.path.split("/") if p]
    catalog = path_parts[0] if path_parts else os.environ.get("DATABRICKS_CATALOG", "main")

    query_params = parse_qs(parsed.query)
    http_path = query_params.get("http_path", [os.environ.get("DATABRICKS_HTTP_PATH", "")])[0]

    return databricks_sql.connect(
        server_hostname=host,
        http_path=http_path,
        access_token=token,
        catalog=catalog,
    )


def _connect_postgres(connection_string: str) -> Any:
    """Connect to PostgreSQL in read-only mode. Requires: pip install psycopg2-binary"""
    try:
        import psycopg2
    except ImportError:
        raise ImportError(
            "PostgreSQL driver not installed. Run: pip install psycopg2-binary"
        )
    conn = psycopg2.connect(connection_string)
    conn.set_session(readonly=True, autocommit=True)
    return conn


def _connect_duckdb(connection_string: str) -> Any:
    """Connect to DuckDB. Requires: pip install duckdb"""
    try:
        import duckdb
    except ImportError:
        raise ImportError(
            "DuckDB driver not installed. Run: pip install duckdb"
        )
    # duckdb://path/to/file.db or duckdb://:memory:
    path = connection_string.replace("duckdb://", "")
    if not path or path == ":memory:":
        return duckdb.connect()
    return duckdb.connect(path)


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


def _detect_platform(conn: Any) -> str:
    """Detect which database platform we're connected to."""
    cursor = conn.cursor()

    # Snowflake
    try:
        cursor.execute("SELECT CURRENT_ACCOUNT()")
        cursor.fetchone()
        cursor.close()
        return "snowflake"
    except Exception:
        pass

    # Databricks (Unity Catalog)
    try:
        cursor.execute("SELECT current_catalog()")
        cursor.fetchone()
        # Databricks supports current_catalog(); verify with a Databricks-specific function
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
    return "generic"


def discover(
    conn: Any,
    schemas: list[str] | None = None,
    user_context: Any | None = None,
) -> DatabaseInventory:
    """Discover tables and columns in the connected database.

    Uses only ANSI SQL and information_schema -- works on any SQL database.

    Args:
        conn: A DB-API 2.0 compatible connection.
        schemas: Optional list of schemas to assess. If None, discovers all non-system schemas.
        user_context: Optional UserContext with exclusions and overrides.

    Returns:
        A DatabaseInventory with all discovered tables and their column metadata.
    """
    inventory = DatabaseInventory()
    inventory.available_providers = ["ansi-sql", "information-schema"]

    # Detect platform for optional enrichment
    platform = _detect_platform(conn)
    inventory.detected_platform = platform
    if platform != "generic":
        inventory.available_providers.append(platform)

    # Apply user-declared infrastructure context (overrides brittle probes)
    if user_context is not None:
        if user_context.has_otel and "otel" not in inventory.available_providers:
            inventory.available_providers.append("otel")
        if user_context.has_iceberg and "iceberg" not in inventory.available_providers:
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
