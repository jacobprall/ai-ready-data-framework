# Platform Connection Reference

Shared reference for all supported database platforms. Loaded by `connect/SKILL.md` when constructing connection strings.

## Built-in Platforms

The agent ships with built-in support for **Snowflake** and **DuckDB**. Community platforms (PostgreSQL, Databricks, MySQL, etc.) can be added via the platform registry -- see [CONTRIBUTING.md](../../CONTRIBUTING.md).

---

## Snowflake

**Connection format:**
```
snowflake://user:password@account/database/schema?warehouse=WH&role=ROLE
```

**Parameters:**
| Parameter | Required | Default | Env Var |
|-----------|----------|---------|---------|
| user | Yes | -- | `SNOWFLAKE_USER` |
| password | Yes | -- | `SNOWFLAKE_PASSWORD` |
| account | Yes | -- | `SNOWFLAKE_ACCOUNT` |
| database | Yes | -- | `SNOWFLAKE_DATABASE` |
| schema | No | PUBLIC | `SNOWFLAKE_SCHEMA` |
| warehouse | Yes | -- | `SNOWFLAKE_WAREHOUSE` |
| role | No | default role | `SNOWFLAKE_ROLE` |

**Driver:** `pip install snowflake-connector-python`

**Read-only enforcement:** Application-level SQL validation (no driver-level read-only mode).

**Capabilities (beyond ANSI SQL):**
- `ACCOUNT_USAGE` views for access history, query history, login history
- `COPY_HISTORY` for ingestion error rates
- `TABLE_STORAGE_METRICS` for row counts without scanning
- Dynamic table lag monitoring
- Masking policies and row access policies
- Object dependencies via `OBJECT_DEPENDENCIES`
- Table ownership via `TABLES.TABLE_OWNER`
- `TIME_TRAVEL` for point-in-time queries

**Suite:** `snowflake` (extends common with 13 platform-native tests)

**Example:**
```
snowflake://jdoe:p@ssw0rd@xy12345.us-east-1/ANALYTICS/PUBLIC?warehouse=COMPUTE_WH&role=ANALYST
```

---

## DuckDB

**Connection format:**
```
duckdb://path/to/file.db
duckdb://:memory:
```

**Parameters:**
| Parameter | Required | Default | Notes |
|-----------|----------|---------|-------|
| path | Yes | :memory: | Path to .db file, or :memory: |

**Driver:** `pip install duckdb`

**Read-only enforcement:** Application-level SQL validation.

**Capabilities:**
- Full `information_schema` support
- Constraint discovery
- Lightweight, no server required
- Good for testing and local development

**Suite:** `common` (ANSI SQL baseline)

**Example:**
```
duckdb:///Users/me/data/warehouse.db
duckdb://:memory:
```

---

## Community Platforms

The following platforms are available as community contributions in `examples/community-suites/`. To use them, register the platform before running your assessment. See [CONTRIBUTING.md](../../CONTRIBUTING.md) for details.

| Platform | Example File | Suite |
|----------|-------------|-------|
| PostgreSQL | `examples/community-suites/postgresql.py` | CommonSuite |
| Databricks | `examples/community-suites/databricks_register.py` + `databricks.py` | DatabricksSuite (native) |

---

## Environment Variables

All platforms support environment variable fallbacks. This is useful for CI/CD and when you don't want credentials in the connection string:

```bash
# Snowflake
export SNOWFLAKE_USER="jdoe"
export SNOWFLAKE_PASSWORD="secret"
export SNOWFLAKE_ACCOUNT="xy12345"
export SNOWFLAKE_DATABASE="ANALYTICS"
export SNOWFLAKE_WAREHOUSE="COMPUTE_WH"

# Assessment-specific
export AIRD_CONNECTION_STRING="snowflake://..."
export AIRD_CONTEXT="/path/to/context.yaml"
export AIRD_THRESHOLDS="/path/to/thresholds.json"
export AIRD_OUTPUT="json:report.json"
export AIRD_LOG_LEVEL="debug"
export AIRD_OTEL_ENDPOINT="http://otel-collector:4317"
```

## Required Permissions

The assessment agent needs **read-only** access to:

| Object | Minimum Permission | Purpose |
|--------|-------------------|---------|
| `information_schema.tables` | SELECT | Table inventory |
| `information_schema.columns` | SELECT | Column metadata |
| `information_schema.table_constraints` | SELECT | Constraint discovery |
| `information_schema.key_column_usage` | SELECT | FK relationships |
| `information_schema.table_privileges` | SELECT | RBAC coverage |
| Data tables | SELECT | Null rates, PII scans, freshness checks |

**Platform-specific (optional, for enhanced assessment):**

| Platform | Object | Purpose |
|----------|--------|---------|
| Snowflake | `SNOWFLAKE.ACCOUNT_USAGE.*` | Access history, query history, masking policies |
| Snowflake | `SNOWFLAKE.INFORMATION_SCHEMA.COPY_HISTORY` | Ingestion error rates |
