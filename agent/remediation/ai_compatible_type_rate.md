# Remediation: AI-Compatible Type Rate

**Requirement:** `ai_compatible_type_rate`
**Factor:** Consumable
**Thresholds:** L1: ≥80%, L2: ≥90%, L3: ≥95%

## What It Means

The percentage of columns using data types that AI workloads can consume directly (numeric, string, timestamp, boolean, JSON, vector) vs types that require special handling (blob, xml, binary, geometry, etc.).

## Why It Matters

- **L1 (Analytics):** Incompatible types require transformation before use, adding complexity.
- **L2 (RAG):** Embeddings require text or numeric input. Binary and XML types need extraction pipelines.
- **L3 (Training):** Training pipelines expect tabular formats. Incompatible types create format transformation overhead that wastes compute.

## Fix Patterns

**Option 1: Extract content from complex types**

```sql
-- Extract text from XML
ALTER TABLE {schema}.{table} ADD COLUMN {column}_text TEXT;
UPDATE {schema}.{table} SET {column}_text = XMLSERIALIZE({column} AS TEXT);

-- Extract fields from binary/blob
-- This requires application-level processing, not SQL
```

**Option 2: Create a view with compatible types**

```sql
CREATE VIEW {schema}.{table}_ai AS
SELECT
    -- Include all compatible columns
    {compatible_columns},
    -- Cast or extract incompatible ones
    CAST({xml_column} AS TEXT) AS {xml_column}_text
FROM {schema}.{table};
```

## What to Generate

List the columns with incompatible types. For each, suggest the appropriate extraction or casting approach. If the column is a blob or binary, note that application-level processing may be required and suggest creating a derived text/JSON column.
