"""Example: Register PostgreSQL as a community platform.

This file shows how to add PostgreSQL support without modifying the core agent.
Run this before your assessment to make PostgreSQL available:

    python examples/community-suites/postgresql.py

Or import and call register_postgresql() from your own script.
"""

from __future__ import annotations

import os
from typing import Any

from agent.platforms import Platform, register_platform


def _connect_postgres(connection_string: str) -> Any:
    """Connect to PostgreSQL in read-only mode."""
    try:
        import psycopg2
    except ImportError:
        raise ImportError("PostgreSQL driver not installed. Run: pip install psycopg2-binary")
    conn = psycopg2.connect(connection_string)
    conn.set_session(readonly=True, autocommit=True)
    return conn


def register_postgresql() -> None:
    """Register PostgreSQL as a platform."""
    register_platform(Platform(
        name="postgresql",
        schemes=["postgresql", "postgres"],
        driver_package="psycopg2-binary",
        driver_install="pip install psycopg2-binary",
        connect_fn=_connect_postgres,
        detect_sql="SELECT version()",
        detect_match="postgresql",
        identifier_quote='"',
        cast_float="FLOAT",
        system_schemas=["information_schema", "pg_catalog", "INFORMATION_SCHEMA"],
        extra_numeric_types={"serial", "bigserial", "smallserial"},
        extra_string_types={"citext"},
        extra_timestamp_types={"timestamptz", "timetz"},
        suite_class=None,  # Uses CommonSuite (no platform-specific suite needed)
        connection_format="postgresql://user:pass@host:5432/dbname",
    ))


if __name__ == "__main__":
    register_postgresql()
    print("PostgreSQL registered as a community platform.")
