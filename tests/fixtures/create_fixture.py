"""Generate a DuckDB fixture database with intentionally messy data.

Run this script to create tests/fixtures/sample.duckdb:

    python tests/fixtures/create_fixture.py

The database has three schemas:
  - analytics: Main schema with realistic tables and deliberate quality issues
  - staging: A schema users would typically exclude from assessments
  - _scratch: Another excludable schema

Each table exercises specific test paths: null rates, PII columns, naming
inconsistency, missing comments, missing constraints, freshness issues, etc.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path


def create_fixture(db_path: str | None = None) -> str:
    """Create the fixture database and return its path."""
    import duckdb

    if db_path is None:
        db_path = str(Path(__file__).parent / "sample.duckdb")

    # Remove old fixture if it exists
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = duckdb.connect(db_path)

    # -----------------------------------------------------------------------
    # Schema: analytics (main assessment target)
    # -----------------------------------------------------------------------
    conn.execute("CREATE SCHEMA IF NOT EXISTS analytics")

    # -- orders: nulls in customer_id (23%), missing FK, status has no comment,
    #    has timestamp for freshness checks
    conn.execute("""
        CREATE TABLE analytics.orders (
            order_id INTEGER PRIMARY KEY,
            customer_id INTEGER,
            status VARCHAR,
            total_amount DECIMAL(10, 2),
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
    """)

    now = datetime.now()
    orders = []
    for i in range(100):
        cid = None if i % 4 == 0 else (i % 20) + 1  # 25% nulls
        status = ["pending", "shipped", "delivered", "cancelled"][i % 4]
        amount = round(10.0 + (i * 3.7), 2)
        created = now - timedelta(hours=i * 2)
        updated = now - timedelta(hours=i)
        orders.append((i + 1, cid, status, amount, created, updated))

    conn.executemany(
        "INSERT INTO analytics.orders VALUES (?, ?, ?, ?, ?, ?)", orders
    )

    # -- customers: has PII columns (email, phone), middle_name (nullable by design),
    #    good naming consistency (snake_case), has some comments
    conn.execute("""
        CREATE TABLE analytics.customers (
            customer_id INTEGER PRIMARY KEY,
            first_name VARCHAR,
            last_name VARCHAR,
            middle_name VARCHAR,
            email VARCHAR,
            phone VARCHAR,
            created_at TIMESTAMP
        )
    """)
    conn.execute("COMMENT ON TABLE analytics.customers IS 'Customer master data'")
    conn.execute("COMMENT ON COLUMN analytics.customers.customer_id IS 'Unique customer identifier'")
    conn.execute("COMMENT ON COLUMN analytics.customers.email IS 'Customer email address'")

    customers = []
    for i in range(20):
        mid = None if i % 3 != 0 else "M"  # ~33% null middle names
        customers.append((
            i + 1,
            f"First{i}",
            f"Last{i}",
            mid,
            f"user{i}@example.com",
            f"555-01{i:02d}",
            now - timedelta(days=i * 10),
        ))
    conn.executemany(
        "INSERT INTO analytics.customers VALUES (?, ?, ?, ?, ?, ?, ?)", customers
    )

    # -- products: mixed naming (camelCase vs snake_case), no PK, price column
    #    (should be positive but some zeros), no comments
    conn.execute("""
        CREATE TABLE analytics.products (
            product_id INTEGER,
            productName VARCHAR,
            product_category VARCHAR,
            price DECIMAL(10, 2),
            quantity_in_stock INTEGER,
            created_at TIMESTAMP
        )
    """)

    products = []
    for i in range(30):
        price = 0.0 if i % 10 == 0 else round(5.0 + i * 2.5, 2)  # 10% zero prices
        products.append((
            i + 1,
            f"Product {i}",
            ["electronics", "clothing", "food", "books"][i % 4],
            price,
            i * 5,
            now - timedelta(days=i * 5),
        ))
    conn.executemany(
        "INSERT INTO analytics.products VALUES (?, ?, ?, ?, ?, ?)", products
    )

    # -- events: high-cardinality event_id, timestamp for freshness,
    #    no comments at all, good for testing null_rate on all columns
    conn.execute("""
        CREATE TABLE analytics.events (
            event_id INTEGER,
            user_id INTEGER,
            event_type VARCHAR,
            event_data VARCHAR,
            created_at TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE UNIQUE INDEX idx_events_id ON analytics.events(event_id)
    """)

    events = []
    for i in range(200):
        events.append((
            i + 1,
            (i % 20) + 1,
            ["click", "view", "purchase", "signup"][i % 4],
            f'{{"page": "page_{i % 10}"}}',
            now - timedelta(minutes=i * 30),
        ))
    conn.executemany(
        "INSERT INTO analytics.events VALUES (?, ?, ?, ?, ?)", events
    )

    # -- dim_country: dimension table with old data (stale, but acceptable for dims)
    conn.execute("""
        CREATE TABLE analytics.dim_country (
            country_code VARCHAR PRIMARY KEY,
            country_name VARCHAR,
            region VARCHAR,
            updated_at TIMESTAMP
        )
    """)
    conn.execute("COMMENT ON TABLE analytics.dim_country IS 'Country reference dimension'")

    countries = [
        ("US", "United States", "North America", now - timedelta(days=90)),
        ("GB", "United Kingdom", "Europe", now - timedelta(days=90)),
        ("DE", "Germany", "Europe", now - timedelta(days=90)),
        ("JP", "Japan", "Asia", now - timedelta(days=90)),
        ("AU", "Australia", "Oceania", now - timedelta(days=90)),
    ]
    conn.executemany(
        "INSERT INTO analytics.dim_country VALUES (?, ?, ?, ?)", countries
    )

    # -----------------------------------------------------------------------
    # Schema: staging (should be excluded)
    # -----------------------------------------------------------------------
    conn.execute("CREATE SCHEMA IF NOT EXISTS staging")
    conn.execute("""
        CREATE TABLE staging.tmp_orders (
            id INTEGER,
            raw_data VARCHAR,
            loaded_at TIMESTAMP
        )
    """)
    conn.executemany(
        "INSERT INTO staging.tmp_orders VALUES (?, ?, ?)",
        [(i, f"raw_{i}", now) for i in range(10)],
    )

    # -----------------------------------------------------------------------
    # Schema: _scratch (should be excluded)
    # -----------------------------------------------------------------------
    conn.execute("CREATE SCHEMA IF NOT EXISTS _scratch")
    conn.execute("""
        CREATE TABLE _scratch.debug_log (
            id INTEGER,
            message VARCHAR
        )
    """)
    conn.executemany(
        "INSERT INTO _scratch.debug_log VALUES (?, ?)",
        [(i, f"debug_{i}") for i in range(5)],
    )

    conn.close()
    return db_path


if __name__ == "__main__":
    path = create_fixture()
    print(f"Fixture database created at: {path}")
