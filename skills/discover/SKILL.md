---
name: discover
description: "Enumerate schemas, tables, columns, and constraints. Detect platform capabilities and available data providers."
parent_skill: assess-data
---

# Discover Database Inventory

Enumerate the database's schemas, tables, columns, and constraints using `information_schema`. Detect platform-specific capabilities (Iceberg, OTEL, platform-native metadata). Apply user context exclusions.

## Forbidden Actions

- NEVER execute SQL beyond SELECT, DESCRIBE, SHOW, EXPLAIN, or WITH
- NEVER skip scope confirmation -- always present the discovery summary before proceeding
- NEVER assess tables the user has excluded in their context
- NEVER assume a platform without probing -- let auto-detection or user confirmation decide

## When to Load

- After establishing a database connection
- When the user wants to see what's in their database before assessing
- When scoping an assessment to specific schemas or tables
- Can be used standalone to inventory a database

## Prerequisites

- A live database connection (from `connect/SKILL.md`)
- Optional: a `UserContext` with exclusion filters (from `interview/SKILL.md`)

## Workflow

### Step 1: Run Discovery

```bash
python -m agent.cli assess \
  --connection "<connection_string>" \
  --log-level debug \
  --no-save \
  --output stdout 2>&1 | grep -E "(Discovered|Using suite|providers)"
```

Or with schema filters:

```bash
python -m agent.cli assess \
  --connection "<connection_string>" \
  --schema analytics production \
  --log-level debug \
  --no-save \
  --output stdout 2>&1 | grep -E "(Discovered|Using suite|providers)"
```

Or with user context (applies exclusions):

```bash
python -m agent.cli assess \
  --connection "<connection_string>" \
  --context context.yaml \
  --log-level debug \
  --no-save \
  --output stdout 2>&1 | grep -E "(Discovered|Excluded|Using suite)"
```

### Step 2: Present Discovery Summary

Present findings to the user in this format:

```
Discovery Results:
- Platform: [detected platform]
- Schemas: [count] ([list with table counts per schema])
- Tables: [total count]
- Columns: [total count]
- Available providers: [list]
- Unavailable providers: [list]
- Permission gaps: [list, if any]
```

**Key things to highlight:**
- **System schemas** that were auto-excluded (`information_schema`, `pg_catalog`)
- **Schemas with many tables** -- ask if all are in scope
- **Tables with no columns** -- these may indicate permission issues
- **Unavailable providers** -- explain what can't be assessed and why

### Step 3: What Discovery Detects

**Structural metadata per table:**
- Table catalog, schema, name, type (TABLE, VIEW)
- All columns with: name, data_type, is_nullable, column_default, ordinal_position
- Character max length, numeric precision/scale
- Constraints: PRIMARY KEY, FOREIGN KEY, UNIQUE

**Computed column properties:**
- `is_numeric` -- matches int, bigint, float, decimal, number, etc.
- `is_string` -- matches varchar, char, text, string, etc.
- `is_timestamp` -- matches timestamp, datetime, date, timestamptz, etc.
- `is_candidate_key` -- PK/UNIQUE constraint OR name ends in `_id` / equals `id` (heuristic)
- `has_comment` -- whether the column has a description (platform-dependent)

**Platform detection probes:**
- Snowflake: `SELECT CURRENT_ACCOUNT()`
- Databricks: `SELECT current_metastore()`
- PostgreSQL: `SELECT version()` containing "postgresql"
- DuckDB: `SELECT version()` containing "duckdb"

**Provider detection:**
- Iceberg: tries `SELECT * FROM "schema"."table".snapshots LIMIT 1`
- OTEL: checks `AIRD_OTEL_ENDPOINT` env var or queries `otel_traces`
- Both can be overridden by user context flags (`has_iceberg`, `has_otel`)

### Step 4: Apply Context Exclusions

If a `UserContext` is loaded, discovery automatically:
- Skips tables in `excluded_schemas`
- Skips tables in `excluded_tables`
- Respects `has_iceberg` / `has_otel` flags (skips brittle probes when user declares availability)

After filtering, report what was excluded:

```
Exclusions applied:
- Excluded schema "staging" (23 tables)
- Excluded schema "_scratch" (7 tables)
- Excluded table "analytics.tmp_debug" (1 table)
- Total: 31 tables excluded, [remaining] tables in scope
```

**STOP**: Present discovery summary. Confirm scope with the user.

## Output

- `DatabaseInventory` object containing:
  - `tables`: list of `TableInfo` with `ColumnInfo` for each
  - `detected_platform`: platform identifier
  - `available_providers`: what data sources are accessible
  - `unavailable_providers`: what couldn't be found
  - `permissions_gaps`: any permission issues
- Suite selection (auto-detected from platform)

## Next Skill

**Continue to** `interview/SKILL.md` (Phase 2) for scope confirmation, then `assess/SKILL.md`
