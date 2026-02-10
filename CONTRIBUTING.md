# Contributing

We welcome contributions to both the framework content and the assessment agent. The most impactful contribution is **adding support for a new database platform**.

## Adding a New Platform

The agent ships with built-in support for Snowflake and DuckDB. Community platforms live in `examples/community-suites/`. Here's how to add one.

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
                sql="SELECT ... FROM my_platform_system_table",
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

1. Add `Test()` entries in the appropriate method (`database_tests`, `table_tests`, or `column_tests`)
2. Add default thresholds to `agent/schema/thresholds-default.json` with a `direction` field
3. Add a remediation template to `agent/remediation/` (optional but recommended)
4. Add test coverage

See the existing Snowflake suite (`agent/suites/snowflake.py`) for patterns.

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
