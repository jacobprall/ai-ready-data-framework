# Platform Connection Reference

Shared reference for all supported database platforms. Loaded by `connect/SKILL.md` when constructing connection strings.

## PostgreSQL

**Connection format:**
```
postgresql://user:password@host:port/database
```

**Parameters:**
| Parameter | Required | Default | Notes |
|-----------|----------|---------|-------|
| user | Yes | -- | Database username |
| password | Yes | -- | Database password |
| host | Yes | -- | Hostname or IP |
| port | No | 5432 | PostgreSQL port |
| database | Yes | -- | Database name |

**Driver:** `pip install psycopg2-binary`

**Read-only enforcement:** Connection is opened with `SET default_transaction_read_only = ON` and `autocommit = True`.

**Capabilities:**
- Full `information_schema` support
- Constraint discovery (PK, FK, UNIQUE)
- Column comments via `pg_catalog.pg_description`
- Table comments via `pg_catalog.pg_description`
- `pg_stat_user_tables` for access patterns

**Example:**
```
postgresql://analyst:secret@db.example.com:5432/analytics
```

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

## Databricks (Unity Catalog)

**Connection format:**
```
databricks://token:ACCESS_TOKEN@workspace-host/catalog?http_path=/sql/1.0/warehouses/abc123
```

**Parameters:**
| Parameter | Required | Default | Env Var |
|-----------|----------|---------|---------|
| host | Yes | -- | `DATABRICKS_HOST` |
| token | Yes | -- | `DATABRICKS_TOKEN` |
| catalog | No | main | `DATABRICKS_CATALOG` |
| http_path | Yes | -- | `DATABRICKS_HTTP_PATH` |

**Driver:** `pip install databricks-sql-connector`

**Read-only enforcement:** Application-level SQL validation.

**Capabilities (beyond ANSI SQL):**
- Unity Catalog lineage (`system.access.table_lineage`)
- Column-level lineage
- Audit logs (`system.access.audit`)
- Compute usage patterns
- Tag coverage (table and column tags)
- Delta Lake freshness (`DESCRIBE HISTORY`)
- Delta schema evolution tracking
- Delta file statistics
- Table metadata via `DESCRIBE DETAIL`

**Suite:** `databricks` (extends common with 11 platform-native tests)

**Example:**
```
databricks://token:dapi12345@adb-1234567890.1.azuredatabricks.net/my_catalog?http_path=/sql/1.0/warehouses/abc123
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

## Environment Variables

All platforms support environment variable fallbacks. This is useful for CI/CD and when you don't want credentials in the connection string:

```bash
# PostgreSQL
export AIRD_CONNECTION_STRING="postgresql://user:pass@host/db"

# Snowflake
export SNOWFLAKE_USER="jdoe"
export SNOWFLAKE_PASSWORD="secret"
export SNOWFLAKE_ACCOUNT="xy12345"
export SNOWFLAKE_DATABASE="ANALYTICS"
export SNOWFLAKE_WAREHOUSE="COMPUTE_WH"

# Databricks
export DATABRICKS_HOST="adb-123.azuredatabricks.net"
export DATABRICKS_TOKEN="dapi12345"
export DATABRICKS_HTTP_PATH="/sql/1.0/warehouses/abc123"

# Assessment-specific
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
| Databricks | `system.access.*` | Lineage, audit logs |
| Databricks | Delta history | Schema evolution, freshness |
