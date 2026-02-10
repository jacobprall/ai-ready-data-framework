# Remediation: Naming Consistency

**Requirement:** `naming_consistency`
**Factor:** Contextual
**Thresholds:** L1: ≥50%, L2: ≥75%, L3: ≥90%

## What It Means

The percentage of columns following the dominant naming convention in a table (snake_case, camelCase, UPPER_CASE, etc.). Mixed conventions indicate organic growth without standards.

## Why It Matters

- **L1 (Analytics):** Inconsistent names slow down query writing and increase errors.
- **L2 (RAG):** AI systems use column names as semantic signals. Mixed conventions degrade the model's ability to infer meaning.
- **L3 (Training):** Feature pipelines that reference columns by name break when conventions are inconsistent across sources.

## Fix Patterns

**Rename columns to follow the dominant convention:**

```sql
ALTER TABLE {schema}.{table} RENAME COLUMN "{old_name}" TO {new_name};
```

**Caution:** Column renames break downstream queries, views, and applications. Always:
1. Identify all downstream dependencies first
2. Create a migration plan
3. Consider adding an alias view during transition

## What to Generate

Identify the dominant convention in each table. List every column that deviates. Generate rename statements but **prominently warn** that renames have downstream impact. Suggest the user audit dependencies before executing.
