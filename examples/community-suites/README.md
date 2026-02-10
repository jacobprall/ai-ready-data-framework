# Community Platform Suites

This directory contains example platform registrations and test suites that the community has contributed. They are **not** built into the core agent -- you register them before running an assessment.

## Available Examples

| Platform | Files | Status |
|---|---|---|
| PostgreSQL | `postgresql.py` | Registration only (uses CommonSuite) |
| Databricks | `databricks_register.py` + `databricks.py` | Full native suite with Unity Catalog, Delta Lake |

## How to Use

### Option 1: Import before assessment

```python
from examples.community_suites.postgresql import register_postgresql
register_postgresql()

# Now run your assessment -- PostgreSQL will be detected and assessed
```

### Option 2: Run directly

```bash
python examples/community-suites/postgresql.py
python -m agent.cli assess --connection "postgresql://user:pass@host/db"
```

## Adding Your Own

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for a complete walkthrough.
