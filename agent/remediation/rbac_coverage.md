# Remediation: RBAC Coverage

**Requirement:** `rbac_coverage`
**Factor:** Compliant
**Thresholds:** L1: ≥25%, L2: ≥50%, L3: ≥80%

## What It Means

The percentage of tables that have explicit access grants beyond the default public role. Tables accessible to everyone by default lack access control.

## Why It Matters

- **L1 (Analytics):** Sensitive data accessible to all users creates compliance risk.
- **L2 (RAG):** A RAG system that retrieves data from uncontrolled tables may surface confidential information.
- **L3 (Training):** Training data without access controls may include datasets the organization hasn't approved for AI use.

## Fix Patterns

**Option 1: Grant access to specific roles**

```sql
-- Revoke public access
REVOKE ALL ON TABLE {schema}.{table} FROM PUBLIC;

-- Grant to specific roles
GRANT SELECT ON TABLE {schema}.{table} TO ROLE {role_name};
```

**Option 2: Create a read-only role for AI workloads**

```sql
CREATE ROLE ai_reader;
GRANT USAGE ON SCHEMA {schema} TO ROLE ai_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA {schema} TO ROLE ai_reader;

-- Assign the role to AI service accounts
GRANT ROLE ai_reader TO USER ai_service_account;
```

## What to Generate

Suggest creating a dedicated `ai_reader` role with SELECT-only access on approved tables. List the tables that currently have only public/default access and generate GRANT statements for the new role. Emphasize that this is a governance decision -- the user needs to decide which tables should be accessible to AI workloads.
