---
name: remediate
description: "Generate specific, executable fixes from remediation templates. Substitutes real schema/table/column names into SQL fix patterns."
parent_skill: assess-data
---

# Generate Remediation

Read remediation templates and generate specific, executable SQL fixes for the user's failures. Substitute actual schema names, table names, and column names into fix patterns. Group by effort level.

The agent is **strictly read-only** -- all fixes are presented for user review and execution. Never execute remediation SQL.

## Forbidden Actions

- NEVER execute remediation SQL against the user's database -- present it for review only
- NEVER generate fixes without reading the corresponding remediation template first
- NEVER skip the user confirmation step for ambiguous decisions (column descriptions, PII handling, default values)
- NEVER generate DROP or TRUNCATE statements
- NEVER present fixes without risk warnings for data-modifying operations

## When to Load

- After interpreting results and triaging failures (from `interpret/SKILL.md`)
- When the user asks "how do I fix this?"
- When the user wants fix SQL for specific requirements
- Can be used standalone for a single requirement

## Prerequisites

- A JSON assessment report with test failures
- Knowledge of which failures the user wants to fix (from `interview/SKILL.md` Phase 3)
- The remediation templates in `agent/remediation/`

## Workflow

### Step 1: Identify Failures to Fix

From the triage in Phase 3, collect the failures the user wants remediation for. Filter out accepted failures.

Group by effort level:

| Effort | Requirements | Typical Fix |
|--------|-------------|-------------|
| **Quick wins** | `column_comment_coverage`, `table_comment_coverage`, `naming_consistency` | COMMENT ON statements, ALTER COLUMN RENAME |
| **Data quality** | `null_rate`, `duplicate_rate`, `type_inconsistency_rate`, `zero_negative_rate` | DEFAULT values, deduplication queries, type casts |
| **Constraints** | `constraint_coverage`, `foreign_key_coverage`, `ai_compatible_type_rate` | ADD PRIMARY KEY, ADD FOREIGN KEY, ALTER COLUMN TYPE |
| **Governance** | `pii_detection_rate`, `pii_column_name_rate`, `rbac_coverage` | Masking policies, GRANT statements, column renames |
| **Freshness** | `max_staleness_hours`, `timestamp_column_coverage` | Pipeline fixes, ADD COLUMN for timestamps |

### Step 2: Read Remediation Templates

For each failing requirement, read the corresponding template:

| Requirement | Template Path |
|-------------|--------------|
| null_rate | `agent/remediation/null_rate.md` |
| duplicate_rate | `agent/remediation/duplicate_rate.md` |
| column_comment_coverage | `agent/remediation/column_comment_coverage.md` |
| table_comment_coverage | `agent/remediation/table_comment_coverage.md` |
| naming_consistency | `agent/remediation/naming_consistency.md` |
| foreign_key_coverage | `agent/remediation/foreign_key_coverage.md` |
| pii_detection_rate | `agent/remediation/pii_detection_rate.md` |
| pii_column_name_rate | `agent/remediation/pii_column_name_rate.md` |
| ai_compatible_type_rate | `agent/remediation/ai_compatible_type_rate.md` |
| timestamp_column_coverage | `agent/remediation/timestamp_column_coverage.md` |
| max_staleness_hours | `agent/remediation/max_staleness_hours.md` |
| constraint_coverage | `agent/remediation/constraint_coverage.md` |
| rbac_coverage | `agent/remediation/rbac_coverage.md` |

If no template exists for a requirement, use the framework content for that factor (`framework/factor-XX-*.md`) to reason about what the fix should be.

### Step 3: Generate User-Specific Fixes

For each template, substitute the user's actual values:
- Replace `{schema}` with the actual schema name
- Replace `{table}` with the actual table name
- Replace `{column}` with the actual column name
- Use the `measured_value` and `thresholds` from the test result to explain severity

**Ask for confirmation on ambiguous decisions:**

- **Column descriptions**: "Column `orders.status` has no description. Based on column name and data type (VARCHAR), it likely represents an order lifecycle state. What should the description say?"
- **PII handling**: "Column `users.contact_info` matched PII patterns. Should this be: (a) masked with a masking policy, (b) renamed to indicate sensitivity, (c) documented as intentionally containing PII, or (d) confirmed as not actually PII?"
- **Default values**: "Column `orders.shipping_address` has 23% nulls. Should the default be: (a) 'unknown', (b) empty string, (c) NULL is acceptable here?"
- **Primary keys**: "Table `events` has no primary key. Should I suggest: (a) a surrogate key (auto-increment), (b) a composite key from existing columns, or (c) you have a natural key I should use?"

**STOP**: Wait for user answers on ambiguous decisions before generating SQL.

### Step 4: Present Fixes by Group

Present all fixes organized by effort level, starting with quick wins:

**Quick Wins (can be applied immediately):**

```sql
-- Column descriptions (column_comment_coverage)
COMMENT ON COLUMN analytics.orders.customer_id IS 'Foreign key to customers table. Identifies the customer who placed the order.';
COMMENT ON COLUMN analytics.orders.status IS 'Order lifecycle state. Valid values: pending, confirmed, shipped, delivered, cancelled.';
-- ... generate for every undocumented column

-- Table descriptions (table_comment_coverage)
COMMENT ON TABLE analytics.orders IS 'Customer orders with line items, shipping, and payment details. Grain: one row per order.';
```

**Data Quality (requires impact analysis):**

```sql
-- Null rate fixes (null_rate)
-- Option 1: Set default for new rows
ALTER TABLE analytics.orders ALTER COLUMN customer_id SET DEFAULT 0;
-- Option 2: Backfill existing nulls
UPDATE analytics.orders SET customer_id = 0 WHERE customer_id IS NULL;
-- Option 3: Add NOT NULL constraint (after backfill)
ALTER TABLE analytics.orders ALTER COLUMN customer_id SET NOT NULL;
```

**Constraints (requires dependency audit):**

```sql
-- Primary key (constraint_coverage)
ALTER TABLE analytics.orders ADD PRIMARY KEY (order_id);
-- Foreign key (foreign_key_coverage)
ALTER TABLE analytics.orders ADD FOREIGN KEY (customer_id) REFERENCES analytics.customers(customer_id);
```

**Governance (requires policy decisions):**

```sql
-- RBAC (rbac_coverage)
GRANT SELECT ON analytics.orders TO ROLE ai_reader;
GRANT SELECT ON analytics.customers TO ROLE ai_reader;
-- PII masking (pii_detection_rate)
-- Platform-specific: use Snowflake masking policies, Databricks column masks, or application-level
```

### Step 5: Warn About Side Effects

For each fix category, note risks:

- **COMMENT ON**: Safe. No data changes. Can be applied immediately.
- **ALTER COLUMN SET DEFAULT**: Safe for new rows. Does not backfill existing data.
- **UPDATE ... SET ... WHERE NULL**: Changes data. Run a SELECT COUNT first to verify scope. Consider doing in batches for large tables.
- **ADD PRIMARY KEY / FOREIGN KEY**: May fail if data violates the constraint. Run validation queries first.
- **GRANT**: Requires appropriate privileges. Review with your DBA.
- **Renames (naming_consistency)**: Breaks downstream dependencies. Audit consumers before executing.

### Step 6: Generate Validation Queries

For each fix, provide a validation query the user can run after applying:

```sql
-- After fixing null_rate on orders.customer_id:
SELECT
  COUNT(*) AS total_rows,
  COUNT(customer_id) AS non_null,
  ROUND(1.0 - COUNT(customer_id)::FLOAT / COUNT(*), 4) AS null_rate
FROM analytics.orders;
-- Expected: null_rate = 0.0000
```

## Output

- SQL fix scripts organized by effort level
- Validation queries for each fix
- Risk warnings for data-modifying operations
- Ambiguous decisions documented (user's answers recorded)

## Next Skill

**Continue to** `compare/SKILL.md` after fixes are applied and a re-assessment is run.
