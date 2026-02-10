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

1. Snowflake
2. DuckDB
3. Other (community-supported -- see CONTRIBUTING.md)
```

If the user provides a connection string directly, skip to Step 3.

**STOP**: Wait for user response.

### Step 2: Construct Connection String

**Load** `references/platforms.md` for the chosen platform's connection format, required parameters, environment variable fallbacks, and driver install commands.

Collect the required parameters from the user, then construct the connection string using the format specified in the reference.

**STOP**: Present the constructed connection string (with credentials masked) for confirmation.

### Step 3: Verify Driver

**Load** `references/platforms.md` for the driver package and install command for the chosen platform.

If the driver is missing, provide the install command from the reference and install it before proceeding.

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
- Detected platform identifier (snowflake, duckdb, or any community-registered platform, or generic)
- Connection string (stored for re-use)

## Next Skill

**Continue to** `discover/SKILL.md`
