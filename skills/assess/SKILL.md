---
name: assess
description: "Execute tests and score results against the AI-Ready Data Framework. Generates, runs, and scores all tests for the appropriate platform suite."
parent_skill: assess-data
---

# Execute Assessment

Generate tests from the appropriate platform suite, execute them against the database, and score results at three workload levels. This is the core measurement engine.

## Forbidden Actions

- NEVER execute SQL that modifies data -- the executor rejects INSERT, UPDATE, DELETE, CREATE, ALTER, DROP
- NEVER bypass the read-only validator in `execute.py`
- NEVER override threshold scores without user context justification
- NEVER suppress or hide test failures from the report

## When to Load

- After discovery and scope confirmation
- When re-running an assessment with updated context
- When the user wants to run tests without the full interactive flow
- Can be used standalone: `python -m agent.cli assess --connection "..." --output json:report.json`

## Prerequisites

- A live database connection (from `connect/SKILL.md`)
- A `DatabaseInventory` (from `discover/SKILL.md`)
- Optional: a `UserContext` (from `interview/SKILL.md`)

## Workflow

### Step 1: Select Test Suite

The suite is auto-detected from the platform, or can be forced:

| Detected Platform | Suite | Tests Included |
|-------------------|-------|----------------|
| PostgreSQL | `common` | ANSI SQL baseline (15+ test types) |
| DuckDB | `common` | ANSI SQL baseline |
| Snowflake | `snowflake` | Common + 13 Snowflake-native tests (ACCOUNT_USAGE, TIME_TRAVEL, etc.) |
| Databricks | `databricks` | Common + 11 Databricks-native tests (Unity Catalog, Delta Lake) |
| Generic | `common` | ANSI SQL baseline |

To list available suites: `python -m agent.cli suites`

### Step 2: Generate Tests

The suite generates tests at three levels from the inventory:

**Database-level tests** (run once):
- `table_comment_coverage` -- % tables with descriptions
- `timestamp_column_coverage` -- % tables with timestamp columns
- `constraint_coverage` -- % tables with PK or unique constraints
- `rbac_coverage` -- % tables with explicit grants

**Table-level tests** (per table):
- `column_comment_coverage` -- % columns with descriptions
- `naming_consistency` -- % columns following dominant naming convention
- `ai_compatible_type_rate` -- % columns using AI-friendly types
- `pii_column_name_scan` -- PII-like column name detection
- `foreign_key_coverage` -- % of `_id` columns with FK constraints (conditional)

**Column-level tests** (per column, conditional on type):
- `null_rate` -- all columns
- `pii_pattern_scan` -- string columns only
- `type_consistency` -- string columns only
- `zero_negative_check` -- numeric columns only
- `duplicate_detection` -- candidate key columns only
- `table_freshness` -- timestamp columns only

Platform suites add additional tests using native capabilities.

### Step 3: Run the Assessment

**Full assessment with context:**

```bash
python -m agent.cli assess \
  --connection "<connection_string>" \
  --output json:report.json \
  --context context.yaml \
  --suite auto
```

**Minimal assessment (no context, no save):**

```bash
python -m agent.cli assess \
  --connection "<connection_string>" \
  --output json:report.json \
  --suite auto \
  --no-save
```

**Scoped to specific schemas:**

```bash
python -m agent.cli assess \
  --connection "<connection_string>" \
  --schema analytics production \
  --output json:report.json
```

**With custom thresholds:**

```bash
python -m agent.cli assess \
  --connection "<connection_string>" \
  --thresholds custom-thresholds.json \
  --output json:report.json
```

### Step 4: How Scoring Works

Each test produces a `measured_value` (a float). This is compared against three-level thresholds:

**Max thresholds** (lower is better): `null_rate`, `duplicate_rate`, `pii_detection_rate`, `max_staleness_hours`, etc.
- Pass if `measured_value <= threshold`
- Example: null_rate measured 0.03, L2 threshold 0.05 -> pass

**Min thresholds** (higher is better): `column_comment_coverage`, `constraint_coverage`, `rbac_coverage`, etc.
- Pass if `measured_value >= threshold`
- Example: comment_coverage measured 0.40, L2 threshold 0.90 -> fail

**Default thresholds** from `agent/schema/thresholds-default.json`:

| Requirement | L1 (Analytics) | L2 (RAG) | L3 (Training) |
|-------------|----------------|----------|----------------|
| null_rate | 0.10 (10%) | 0.05 (5%) | 0.01 (1%) |
| duplicate_rate | 0.05 | 0.02 | 0.005 |
| column_comment_coverage | 0.50 | 0.90 | 0.95 |
| table_comment_coverage | 0.50 | 0.90 | 0.95 |
| max_staleness_hours | 168 (1 week) | 24 | 6 |
| constraint_coverage | 0.50 | 0.80 | 0.95 |

### Step 5: Context-Aware Overrides

When a `UserContext` is loaded, the executor applies these overrides:

- **Nullable by design**: Columns in `nullable_by_design` get relaxed null_rate thresholds (up to 100% at L1/L2, 50% at L3)
- **False-positive PII**: Columns in `false_positive_pii` skip PII tests entirely
- **Freshness SLAs**: Tables in `freshness_slas` use the user's SLA instead of default thresholds
- **Annotations**: Results are tagged with context markers (`[nullable by design]`, `[critical table]`, `[custom SLA: 1h]`, `[previously accepted]`)

### Step 6: Review Execution Summary

After execution, the CLI logs:

```
L1: 142 pass, 23 fail, 5 skip (86.1%)
L2: 118 pass, 47 fail, 5 skip (71.5%) <-- target
L3: 89 pass, 76 fail, 5 skip (53.9%)
```

**STOP**: Report execution results. Proceed to interpretation.

## Output

- JSON report at the specified path (or stdout)
- Assessment saved to `~/.aird/assessments.db` (unless `--no-save`)
- Context saved to `~/.aird/contexts/` (if context was loaded)

The report contains:
- `summary`: per-level pass/fail/skip/score
- `factors`: per-factor per-level scores
- `not_assessed`: what couldn't be tested and why
- `tests`: full array of every test result with measured values, thresholds, and SQL
- `user_context`: audit trail of context decisions (if context was provided)

## Next Skill

**Continue to** `interpret/SKILL.md`
