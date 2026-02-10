---
name: assess-data
description: "Assess a database against the AI-Ready Data Framework. Use when: evaluating AI readiness, running data quality assessments, checking if data is AI-ready. Triggers: assess my data, is my data AI-ready, data readiness, run assessment, evaluate my database."
---

# AI-Ready Data Assessment

End-to-end workflow for assessing a database against the AI-Ready Data Framework. Produces a scored report across five factors (Clean, Contextual, Consumable, Current, Correlated, Compliant) at three workload levels (L1: Analytics, L2: RAG, L3: Training).

## Forbidden Actions

- NEVER execute SQL that creates, modifies, or deletes data in the user's database
- NEVER execute remediation SQL -- present it for the user to review and run
- NEVER skip a STOP point -- always wait for explicit user confirmation
- NEVER store or log database credentials in plain text
- NEVER proceed to the next skill without confirming the current skill's output

## Setup

**Load** `references/platforms.md` when helping users construct connection strings.

Ensure the assessment tool is installed:

```bash
cd /path/to/ai-ready-data-framework
pip install -e "./agent"
```

## Intent Detection

| User Situation | Route |
|----------------|-------|
| First-time assessment, no connection yet | Start at Step 1 |
| Has connection string, wants full assessment | Skip to `connect/SKILL.md` |
| Already connected, wants to re-run | Skip to `assess/SKILL.md` |
| Has a report, wants to understand results | Skip to `interpret/SKILL.md` |
| Has results, wants to fix issues | Skip to `remediate/SKILL.md` |
| Wants to compare against a previous run | Skip to `compare/SKILL.md` |
| Wants to understand their data estate first | Skip to `interview/SKILL.md` |

## Workflow

### Step 1: Gather Context

**Load** `interview/SKILL.md` (Phase 1 only)

Ask the user about their goals, data estate, and infrastructure context before connecting. This produces a `UserContext` that improves assessment quality.

**STOP**: Wait for user responses before proceeding.

### Step 2: Connect to Database

**Load** `connect/SKILL.md`

Establish a read-only connection to the user's database. Supports PostgreSQL, Snowflake, Databricks, and DuckDB.

**STOP**: Confirm connection is established.

### Step 3: Discover and Confirm Scope

**Load** `discover/SKILL.md`

Enumerate schemas, tables, and columns. Then **Load** `interview/SKILL.md` (Phase 2) to walk through discoveries with the user -- confirm scope, validate heuristic assumptions, add business context.

**STOP**: Present discovery summary and confirm scope.

### Step 4: Execute Assessment

**Load** `assess/SKILL.md`

Generate and execute tests from the appropriate platform suite. Apply context-aware threshold overrides. Score results at L1/L2/L3.

**STOP**: Report execution completion.

### Step 5: Interpret Results

**Load** `interpret/SKILL.md`

Walk through results interactively. Then **Load** `interview/SKILL.md` (Phase 3) for failure triage -- the user confirms which failures matter, which are acceptable, and which to fix.

**STOP**: Present findings and get triage decisions.

### Step 6: Generate Fixes

**Load** `remediate/SKILL.md`

For each failure the user wants to fix, generate specific, executable SQL using the remediation templates. Group by effort level.

**STOP**: Present fix suggestions for review.

### Step 7: Save and Compare (Optional)

**Load** `compare/SKILL.md`

Save results to history. If previous assessments exist, show progress. On re-assessments, use `--compare` to track improvements.

## Stopping Points

- Step 1: After gathering user context
- Step 2: After connection established
- Step 3: After discovery and scope confirmation
- Step 4: After test execution
- Step 5: After results interpretation and triage
- Step 6: After fix suggestions generated
- Step 7: After comparison (if applicable)

## Output

- JSON assessment report (`report.json`)
- User context file (`context.yaml` or `~/.aird/contexts/`)
- Assessment history (`~/.aird/assessments.db`)
- Remediation SQL scripts (presented for review)

## Next Steps

After completion, suggest:

```
Your assessment is complete. You might also want to:

1. Fix the identified issues and re-assess → re-run with --compare
2. Set up a scheduled assessment pipeline
3. Share the report with your team
4. Dive deeper into a specific factor → read framework/factor-XX-*.md
```
