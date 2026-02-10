"""Example: Register Databricks as a community platform.

This file shows how to add Databricks support. The full Databricks suite lives in
databricks.py in this same directory.

Usage:
    from examples.community_suites.databricks_register import register_databricks
    register_databricks()
"""

from __future__ import annotations

import os
from typing import Any

from agent.platforms import Platform, register_platform


def _connect_databricks(connection_string: str) -> Any:
    """Connect to Databricks SQL warehouse."""
    try:
        from databricks import sql as databricks_sql
    except ImportError:
        raise ImportError("Databricks driver not installed. Run: pip install databricks-sql-connector")

    from urllib.parse import urlparse, parse_qs
    parsed = urlparse(connection_string)
    host = parsed.hostname or os.environ.get("DATABRICKS_HOST", "")
    token = parsed.password or os.environ.get("DATABRICKS_TOKEN", "")
    path_parts = [p for p in parsed.path.split("/") if p]
    catalog = path_parts[0] if path_parts else os.environ.get("DATABRICKS_CATALOG", "main")
    query_params = parse_qs(parsed.query)
    http_path = query_params.get("http_path", [os.environ.get("DATABRICKS_HTTP_PATH", "")])[0]

    return databricks_sql.connect(
        server_hostname=host, http_path=http_path, access_token=token, catalog=catalog,
    )


def register_databricks() -> None:
    """Register Databricks as a platform with its native suite."""
    register_platform(Platform(
        name="databricks",
        schemes=["databricks"],
        driver_package="databricks-sql-connector",
        driver_install="pip install databricks-sql-connector",
        connect_fn=_connect_databricks,
        detect_sql="SELECT current_metastore()",
        detect_match="",
        identifier_quote='`',
        cast_float="DOUBLE",
        system_schemas=["information_schema", "INFORMATION_SCHEMA"],
        extra_numeric_types={"long", "short", "byte"},
        extra_string_types={"binary"},
        extra_timestamp_types=set(),
        suite_class="examples.community_suites.databricks:DatabricksSuite",
        connection_format="databricks://token:ACCESS_TOKEN@host/catalog?http_path=...",
    ))


if __name__ == "__main__":
    register_databricks()
    print("Databricks registered as a community platform.")
