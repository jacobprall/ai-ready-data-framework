---
name: connect
description: "Establish a read-only database connection for assessment. Handles connection string parsing, driver installation, and platform detection."
parent_skill: assess-data
---

# Connect to Database

Establish a read-only DB-API 2.0 connection to the user's database. This skill handles connection string construction, driver verification, and platform auto-detection.

## Forbidden Actions

- NEVER store credentials in plain text outside of environment variables or the connection string
- NEVER log the full connection string with credentials visible
- NEVER attempt to write data to the database -- connections are read-only
- NEVER install drivers without confirming with the user first

## When to Load

- User wants to assess a database but hasn't connected yet
- User provides a connection string or database credentials
- User asks which platforms are supported

## Prerequisites

- Python 3.10+ installed
- `agent` package installed (`pip install -e "./agent"`)

## Workflow

### Step 1: Determine Platform

**Ask user:**

```
Which database platform are you using?

1. PostgreSQL
2. Snowflake
3. Databricks (Unity Catalog)
4. DuckDB
```

If the user provides a connection string directly, skip to Step 3.

**STOP**: Wait for user response.

### Step 2: Construct Connection String

**Load** `references/platforms.md` for platform-specific connection formats.

Based on the platform, collect the required parameters:

**PostgreSQL:**
```
I need: host, port (default 5432), database name, username, password.
Connection format: postgresql://user:pass@host:5432/dbname
```

**Snowflake:**
```
I need: account identifier, username, password, database, schema (optional),
warehouse, role (optional).
Connection format: snowflake://user:pass@account/database/schema?warehouse=WH&role=ROLE

You can also set environment variables: SNOWFLAKE_USER, SNOWFLAKE_PASSWORD, etc.
```

**Databricks:**
```
I need: workspace host, access token, catalog name, HTTP path to SQL warehouse.
Connection format: databricks://token:ACCESS_TOKEN@host/catalog?http_path=...

You can also set: DATABRICKS_HOST, DATABRICKS_TOKEN, DATABRICKS_HTTP_PATH
```

**DuckDB:**
```
I need: path to the .db file (or :memory: for in-memory).
Connection format: duckdb://path/to/file.db
```

**STOP**: Present the constructed connection string (with credentials masked) for confirmation.

### Step 3: Verify Driver

Check if the required driver is installed. If not, provide the install command:

| Platform | Driver Package | Install Command |
|----------|---------------|-----------------|
| PostgreSQL | psycopg2-binary | `pip install psycopg2-binary` |
| Snowflake | snowflake-connector-python | `pip install snowflake-connector-python` |
| Databricks | databricks-sql-connector | `pip install databricks-sql-connector` |
| DuckDB | duckdb | `pip install duckdb` |

If the driver is missing, install it before proceeding.

### Step 4: Connect

```bash
# Test the connection by running discovery with schema filter
python -m agent.cli assess \
  --connection "<connection_string>" \
  --log-level debug \
  --no-save \
  --output stdout 2>&1 | head -20
```

Or connect programmatically:

```python
from agent.discover import connect
conn = connect("<connection_string>")
```

If connection fails, diagnose:
- **Authentication error**: Check credentials, role, IP allowlist
- **Network error**: Check host, port, firewall, VPN
- **Driver error**: Check driver version, Python version compatibility
- **Permission error**: The agent needs at minimum SELECT on `information_schema`

**STOP**: Confirm connection is established. Report the detected platform.

## Output

- A live DB-API 2.0 connection object
- Detected platform identifier (snowflake, databricks, postgresql, duckdb, generic)
- Connection string (stored for re-use)

## Next Skill

**Continue to** `discover/SKILL.md`
