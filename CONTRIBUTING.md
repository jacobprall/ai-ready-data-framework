# Contributing

We welcome contributions to both the framework content and the assessment agent. The most impactful contribution is **adding support for a new data platform** -- SQL or non-SQL.

## Adding a New SQL Platform

The agent ships with built-in support for Snowflake and DuckDB. Community platforms live in `examples/community-suites/`. Here's how to add a SQL-based one.

### Step 1: Create a registration file

Create `examples/community-suites/<platform>.py`. This registers your platform with the agent's platform registry:

```python
"""Register <Platform> as a community platform."""

from __future__ import annotations
from typing import Any
from agent.platforms import Platform, register_platform


def _connect_myplatform(connection_string: str) -> Any:
    """Connect to MyPlatform."""
    try:
        import mydriver
    except ImportError:
        raise ImportError("MyPlatform driver not installed. Run: pip install mydriver")
    # Parse the connection string and return a DB-API 2.0 connection
    return mydriver.connect(connection_string)


def register_myplatform() -> None:
    register_platform(Platform(
        name="myplatform",
        schemes=["myplatform"],                       # URL scheme(s)
        driver_package="mydriver",                    # PyPI package name
        driver_install="pip install mydriver",        # Install command
        connect_fn=_connect_myplatform,               # Connection function
        detect_sql="SELECT version()",                # SQL to identify this platform
        detect_match="myplatform",                    # Substring to match in result
        identifier_quote='"',                         # Quote character for identifiers
        cast_float="FLOAT",                           # CAST type for floats
        system_schemas=["information_schema"],         # Schemas to exclude from assessment
        extra_numeric_types=set(),                    # Platform-specific numeric types
        extra_string_types=set(),                     # Platform-specific string types
        extra_timestamp_types=set(),                  # Platform-specific timestamp types
        suite_class=None,                             # None = use CommonSuite
        connection_format="myplatform://user:pass@host/db",
    ))
```

That's it for basic support. The `CommonSuite` (ANSI SQL + `information_schema`) works out of the box with most SQL databases.

### Step 2 (optional): Create a platform-native suite

If your platform has capabilities beyond ANSI SQL (system tables, metadata views, lineage APIs), create a native suite:

```python
"""MyPlatform-native test suite."""

from agent.suites.common import CommonSuite
from agent.suites.base import Test
from agent.discover import DatabaseInventory, TableInfo


class MyPlatformSuite(CommonSuite):

    @property
    def platform(self) -> str:
        return "myplatform"

    @property
    def description(self) -> str:
        return "MyPlatform-native assessment using platform-specific metadata."

    def database_tests(self, inventory: DatabaseInventory) -> list[Test]:
        tests = super().database_tests(inventory)  # Inherit all common tests
        tests.extend([
            Test(
                name="my_native_test",
                factor="clean",
                requirement="my_requirement",
                target_type="database",
                platform=self.platform,
                description="What this test measures",
                query="SELECT ... FROM my_platform_system_table",
            ),
        ])
        return tests

    def table_tests(self, table: TableInfo) -> list[Test]:
        tests = super().table_tests(table)  # Inherit all common tests
        # Add platform-native table tests here
        return tests
```

Then set `suite_class` in your registration:

```python
suite_class="examples.community_suites.myplatform_suite:MyPlatformSuite",
```

---

## Adding a Non-SQL Platform (MongoDB, Elasticsearch, etc.)

The framework factors are data-source-agnostic. Non-SQL platforms participate in the same scoring and reporting pipeline -- they just use different query languages and discovery mechanisms.

### Step 1: Register a query handler

Tell the executor how to run your platform's native query language:

```python
from agent.execute import register_query_handler

def mongo_handler(conn, pipeline_json: str) -> float | None:
    """Execute a MongoDB aggregation pipeline and return measured_value."""
    import json
    pipeline = json.loads(pipeline_json)
    # pipeline[0] is the collection name, pipeline[1:] is the pipeline
    collection_name = pipeline[0]
    stages = pipeline[1:]
    db = conn.get_default_database()
    result = list(db[collection_name].aggregate(stages))
    if result:
        return float(result[0].get("measured_value", 0))
    return None

register_query_handler("mongo_agg", mongo_handler)
```

### Step 2: Register the platform with custom detection and discovery

Non-SQL platforms use `detect_fn` instead of `detect_sql`, and `discover_fn` instead of `information_schema`:

```python
from agent.platforms import Platform, register_platform
from agent.discover import ColumnInfo, DatabaseInventory, TableInfo


def _connect_mongo(connection_string: str):
    from pymongo import MongoClient
    return MongoClient(connection_string)


def _detect_mongo(conn) -> bool:
    """Return True if this connection is a MongoDB client."""
    return hasattr(conn, "server_info")


def _discover_mongo(conn, schemas, user_context) -> DatabaseInventory:
    """Discover collections and infer fields by sampling documents."""
    db = conn.get_default_database()
    inventory = DatabaseInventory()
    inventory.available_providers = ["mongodb"]

    for coll_name in db.list_collection_names():
        if user_context and user_context.is_table_excluded("default", coll_name):
            continue
        sample = db[coll_name].find_one() or {}
        columns = []
        for i, (key, val) in enumerate(sample.items()):
            columns.append(ColumnInfo(
                name=key,
                data_type=type(val).__name__,
                is_nullable=True,   # MongoDB fields are always optional
                column_default=None,
                ordinal_position=i,
            ))
        inventory.tables.append(TableInfo(
            catalog="", schema="default", name=coll_name,
            table_type="COLLECTION", columns=columns,
        ))

    return inventory


register_platform(Platform(
    name="mongodb",
    schemes=["mongodb", "mongodb+srv"],
    driver_package="pymongo",
    driver_install="pip install pymongo",
    connect_fn=_connect_mongo,
    query_type="mongo_agg",
    detect_fn=_detect_mongo,
    discover_fn=_discover_mongo,
    suite_class="examples.community_suites.mongodb:MongoDBSuite",
    connection_format="mongodb://user:pass@host:27017/dbname",
))
```

### Step 3: Create a suite

Non-SQL suites extend `Suite` directly (not `CommonSuite`):

```python
from agent.suites.base import Suite, Test
from agent.discover import ColumnInfo, DatabaseInventory, TableInfo
import json


class MongoDBSuite(Suite):

    @property
    def platform(self) -> str:
        return "mongodb"

    @property
    def description(self) -> str:
        return "MongoDB assessment using aggregation pipelines."

    def database_tests(self, inventory: DatabaseInventory) -> list[Test]:
        return []  # Add database-level tests

    def table_tests(self, table: TableInfo) -> list[Test]:
        # "table" is actually a collection in MongoDB
        pipeline = json.dumps([
            table.name,
            {"$group": {"_id": None, "total": {"$sum": 1},
                        "nulls": {"$sum": {"$cond": [{"$eq": ["$_id", None]}, 1, 0]}}}},
            {"$project": {"measured_value": {"$divide": ["$nulls", "$total"]}}}
        ])
        return [
            Test(
                name="null_rate",
                factor="clean",
                requirement="null_rate",
                query=pipeline,
                target_type="collection",
                query_type="mongo_agg",
                platform=self.platform,
            )
        ]

    def column_tests(self, table: TableInfo, column: ColumnInfo) -> list[Test]:
        return []  # Add per-field tests
```

### Key differences for non-SQL platforms

| Aspect | SQL platforms | Non-SQL platforms |
|---|---|---|
| `query_type` | `"sql"` (default) | `"mongo_agg"`, `"python"`, etc. |
| Detection | `detect_sql` + `detect_match` | `detect_fn` callable |
| Discovery | `information_schema` (automatic) | `discover_fn` callable |
| Suite base | Extend `CommonSuite` | Extend `Suite` directly |
| Read-only | SQL validation in executor | Enforce in `connect_fn` |
| `target_type` | `"database"`, `"table"`, `"column"` | Also `"collection"` |

### Step 3: Add thresholds (if new requirements)

If your native tests introduce new requirement names, add thresholds to `agent/schema/thresholds-default.json`:

```json
"my_requirement": {
    "direction": "min",
    "L1": 0.8,
    "L2": 0.9,
    "L3": 0.95
}
```

- `direction: "min"` means higher is better (most metrics)
- `direction: "max"` means lower is better (error rates, null rates)

### Step 4: Add a remediation template (optional)

Create `agent/remediation/<requirement>.md` with fix instructions. See existing templates for the format.

### Step 5: Submit a PR

Add your files to `examples/community-suites/` and submit a PR. Include:
- The registration file
- The suite file (if applicable)
- A brief section added to `skills/references/platforms.md` documenting connection format and capabilities

### Working examples

- **PostgreSQL** (registration only, uses CommonSuite): `examples/community-suites/postgresql.py`
- **Databricks** (full native suite): `examples/community-suites/databricks_register.py` + `databricks.py`

### SQL Dialect Overrides

`CommonSuite` provides overridable dialect properties so you don't need to rewrite every test. Override these in your suite if your platform's SQL differs from ANSI:

| Property | Default | Override when... |
|---|---|---|
| `quote` | `"` | Your platform uses backticks or brackets |
| `cast_float` | `FLOAT` | Your platform uses `DOUBLE`, `REAL`, etc. |
| `regex_match(col, pattern)` | `col ~ 'pattern'` | Your platform uses `REGEXP`, `RLIKE`, etc. |
| `epoch_diff(col)` | `EXTRACT(EPOCH FROM ...)` | Your platform uses `DATEDIFF`, `TIMESTAMPDIFF`, etc. |

---

## Adding Tests to an Existing Suite

1. Add `Test()` entries in the appropriate method (`database_tests`, `table_tests`, or `column_tests`). Use `query=` for the test logic and `query_type=` if not SQL.
2. Add default thresholds to `agent/schema/thresholds-default.json` with a `direction` field
3. Add a remediation template to `agent/remediation/` (optional but recommended)
4. Add test coverage

See the existing Snowflake suite (`agent/suites/snowflake.py`) for SQL patterns.

---

## Framework Content

Framework content lives in `framework/` and is licensed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).

- Write in a declarative, concrete style. No hyperbole.
- Requirements state what must be true about the data, not how to achieve it.
- The framework is vendor-agnostic. Never name a specific product as a requirement.
- Factor content should define requirements at all three workload levels (L1, L2, L3).

---

## Development

```bash
pip install -e "./agent[dev]"   # Install with dev dependencies
pytest tests/                   # Run tests
ruff check agent/               # Lint
```

## Submitting Changes

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## Code of Conduct

Be respectful. Be constructive. Focus on the work.
