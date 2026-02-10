# AI-Ready Data Assessment Agent

**A self-deploying agent that turns the AI-Ready Data Framework into executable, red/green test suites against your data infrastructure.**

Give it a connection. It profiles your environment, generates a custom test suite, and scores your data estate against the five factors of AI-ready data. Built on open standards (ANSI SQL, Iceberg, OpenTelemetry, Git) for maximum portability.

---

## Architecture

The agent is a Cortex Code CLI coding agent. It reads the framework, discovers the target environment, generates SQL tests, executes them, and produces a scored report. The "code" is SQL queries, test templates, and orchestration prompts.

```
┌──────────────────────────────────────────────────────────────┐
│                     Cortex Code CLI Agent                    │
│                                                              │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌──────────┐ │
│  │ Discovery │→ │ Generator │→ │ Executor  │→ │  Scorer  │ │
│  └───────────┘  └───────────┘  └───────────┘  └──────────┘ │
│       │               │              │              │        │
│       ↓               ↓              ↓              ↓        │
│  ┌──────────────────────────────────────────────────────────┐│
│  │                  Test Schema (shared)                    ││
│  │  factor | requirement | target | result | level | value  ││
│  └──────────────────────────────────────────────────────────┘│
│       │                                              │       │
│       ↓                                              ↓       │
│                                              ┌───────────┐ │
│                                              │  Report   │ │
│                                              │  Output   │ │
│                                              └───────────┘ │
└──────────────────────┬───────────────────────────────────────┘
                       │
            Queries tagged by requirement:
            ┌──────────┼──────────┐
            ↓          ↓          ↓
       ┌─────────┐ ┌────────┐ ┌──────┐
       │  ansi   │ │  info  │ │ otel │      ← always runs what's available
       │  sql    │ │_schema │ │      │
       └─────────┘ └────────┘ └──────┘
            │          │
            ↓          ↓
       ┌─────────┐ ┌────────┐
       │snowflake│ │iceberg │               ← enrichment (optional)
       └─────────┘ └────────┘
```

### Query Providers

Every query is tagged with what it requires. The agent discovers what's available, then runs every query whose requirements are met.

| Requirement Tag | Always Available | What It Covers |
|---|---|---|
| `ansi-sql` | Yes | Data profiling, validation, business rules |
| `information-schema` | Yes | Structure, types, constraints, comments, grants |
| `iceberg-rest` | If present | Snapshots, schema evolution, statistics, versioning |
| `otel` | If present | Pipeline lineage, freshness, reliability |
| `snowflake` | If Snowflake | ACCOUNT_USAGE views, Snowpipe, Dynamic Tables |
| `databricks` | If Databricks | Unity Catalog, Delta change data feed |

The agent runs whatever queries are compatible with the detected environment.

---

## Test Schema

Every test produces the same output:

```json
{
  "factor": "clean",
  "requirement": "null_handling",
  "target": "analytics.core.orders.customer_id",
  "levels": ["L1", "L2", "L3"],
  "result": {
    "L1": "pass",
    "L2": "fail",
    "L3": "fail"
  },
  "measured_value": 0.04,
  "thresholds": {
    "L1": 0.10,
    "L2": 0.02,
    "L3": 0.01
  },
  "detail": "4% null rate on customer_id. Passes L1 (≤10%), fails L2 (≤2%) and L3 (≤1%)",
  "query": "SELECT COUNT(*) FILTER (WHERE customer_id IS NULL)::FLOAT / COUNT(*) FROM analytics.core.orders",
  "requires": "ansi-sql"
}
```

Each test is assessed against all three workload levels. The report shows: "Your data passes L1 requirements but fails L2 on PII redaction and deduplication."

---

## Report Schema

The report aggregates test results into a scored summary:

```json
{
  "assessment_id": "a1b2c3",
  "timestamp": "2026-02-09T18:30:00Z",
  "environment": {
    "connection": "snowflake://account/analytics",
    "available_providers": ["ansi-sql", "information-schema", "snowflake"],
    "unavailable_providers": ["iceberg-rest", "otel"],
    "permissions_gaps": ["ACCOUNT_USAGE.ACCESS_HISTORY requires IMPORTED PRIVILEGES on SNOWFLAKE database"]
  },
  "summary": {
    "L1": { "pass": 142, "fail": 8, "score": 0.95 },
    "L2": { "pass": 98, "fail": 52, "score": 0.65 },
    "L3": { "pass": 71, "fail": 79, "score": 0.47 }
  },
  "factors": {
    "clean":      { "L1": 0.97, "L2": 0.72, "L3": 0.51 },
    "contextual": { "L1": 0.88, "L2": 0.60, "L3": 0.45 },
    "consumable": { "L1": 0.99, "L2": 0.80, "L3": 0.55 },
    "current":    { "L1": 0.95, "L2": 0.58, "L3": 0.40 },
    "correlated": { "L1": 0.90, "L2": 0.50, "L3": 0.35 },
    "compliant":  { "L1": 0.93, "L2": 0.65, "L3": 0.48 }
  },
  "not_assessed": [
    { "factor": "correlated", "reason": "No Iceberg catalog or OTEL data available. Lineage and versioning could not be assessed." },
    { "factor": "compliant", "requirement": "access_auditing", "reason": "ACCESS_HISTORY requires IMPORTED PRIVILEGES grant." }
  ],
  "tests": [ ... ]
}
```

Key properties:
- **Three scores per factor.** You see exactly which workload level you're ready for.
- **Gaps are explicit.** What couldn't be assessed and why. Permissions limitations, missing providers, and infrastructure gaps are findings, not silent omissions.
- **Diffable.** Save reports as JSON and compare across runs to track improvement over time.

---

## Generator Mapping

The generator is the core logic that maps column metadata to applicable tests. This is the codified knowledge of *which tests matter for which data*.

| Column Metadata | Tests Generated |
|---|---|
| Any column | Null rate, distinct count, type validation |
| String column | PII pattern scan (SSN, email, phone), cardinality check, encoding consistency |
| String, low cardinality (< 50 distinct) | Enum validation, naming consistency, missing category detection |
| Numeric column | Distribution analysis (min, max, mean, stddev, percentiles), outlier detection, zero/negative check |
| Timestamp column | Freshness (`MAX(col)` staleness), format consistency, future-date check, timezone consistency |
| Column named `*_id` or primary key | Uniqueness check, duplicate detection |
| Column with foreign key constraint | Referential integrity (orphaned values) |
| Column with `COMMENT` / description | Comment exists (contextual), comment is non-empty |
| Column without `COMMENT` | Missing documentation (contextual finding) |
| Table-level | Row count, duplicate record detection, schema drift (if Iceberg), last write time (if available) |

The generator also checks table-to-table relationships: naming convention consistency across schemas, cross-table referential integrity, and coverage gaps (tables with no timestamp columns, no comments, no constraints).

---

## Gameplan

### Target Directory Structure

```
ai-ready-data-framework/
├── README.md                      # Project overview, quick start, links
├── CLAUDE.md                      # AI agent instructions for this repo
├── CONTRIBUTING.md
├── CONTRIBUTORS.md
├── LICENSE
├── Makefile                       # dev, test, build, docker
├── Dockerfile                     # Agent container
├── .gitignore
│
├── framework/                     # The AI-Ready Data Framework (content, CC BY-SA 4.0)
│   ├── README.md                  # The framework document
│   ├── factor-00-clean.md
│   ├── factor-01-contextual.md
│   ├── factor-02-consumable.md
│   ├── factor-03-current.md
│   ├── factor-04-correlated.md
│   └── factor-05-compliant.md
│
├── agent/                         # The assessment agent (Apache 2.0)
│   ├── README.md                  # Architecture, usage, configuration
│   ├── schema/                    # Test result + report JSON schemas
│   │   ├── test-result.json
│   │   ├── report.json
│   │   └── thresholds-default.json
│   ├── queries/                   # All queries, tagged by requirement
│   │   ├── ansi-sql/              # Universal SQL profiling queries
│   │   ├── information-schema/    # Catalog metadata queries
│   │   ├── snowflake/             # Snowflake-specific enrichment queries
│   │   ├── iceberg/               # Iceberg REST catalog queries
│   │   └── otel/                  # OpenTelemetry queries
│   ├── generator/                 # Column metadata → test mapping logic
│   └── scorer/                    # Aggregation and scoring logic
│
├── tests/                         # Agent tests and fixtures
│   └── fixtures/
│
├── docs/
│   ├── getting-started.md
│   ├── architecture.md
│   ├── design-decisions.md
│   ├── scoring.md
│   ├── adding-queries.md          # How to add new queries (replaces adapters.md)
│   └── deployment.md
│
├── examples/                      # Sample assessment outputs
│   └── snowflake-sample/
│
└── workshops/
```

Flat where possible. `agent/` has files and one level of directories, not four. Structure emerges when complexity demands it.

---

### Build Phases

#### Phase 0: Foundation

Restructure the repo and lock the contracts.

| Deliverable | Description |
|---|---|
| Repo restructure | Move `v1/content/` to `framework/`. Clean up root. |
| `CLAUDE.md` | Agent instructions: structure, conventions, content vs code |
| `Makefile` | `make dev`, `make test`, `make build`, `make docker` |
| Test result JSON Schema | `agent/schema/test-result.json` -- with per-level results |
| Report JSON Schema | `agent/schema/report.json` -- aggregated output format |
| Default thresholds | `agent/schema/thresholds-default.json` -- L1/L2/L3 thresholds per requirement |
| Runtime decision | Document: Cortex Code CLI agent orchestrating SQL queries. Not a compiled application. |

**Exit criteria:** The test result schema, report schema, and default thresholds are defined. A developer can clone the repo and `make dev`. The runtime model (Cortex Code CLI + SQL queries) is documented.

---

#### Phase 1: Factor 0 (Clean) end-to-end

Prove the full pipeline with one factor on the universal queries.

| Deliverable | Description |
|---|---|
| `agent/queries/ansi-sql/` | Profiling queries: null rates, duplicates, type consistency, distributions, PII patterns |
| `agent/queries/information-schema/` | Column types, constraints, comments, grants |
| Discovery | Connect, enumerate schemas/tables/columns, build inventory |
| Generator mapping | Column metadata → applicable Factor 0 tests (see mapping table above) |
| Executor | Run generated queries, collect results in test schema format |
| Scorer | Score Factor 0: per-column, per-table, per-database, at all three levels |
| Report output | JSON report to stdout. Human-readable markdown summary. |
| `tests/fixtures/` | Sample database with known issues for deterministic testing |

**Exit criteria:** Point the agent at any SQL database. It discovers tables, generates Factor 0 tests, runs them, and produces a scored report showing L1/L2/L3 pass/fail. All on `ansi-sql` + `information-schema`.

---

#### Phase 2: Snowflake queries + all factors

Extend breadth (all factors) and depth (Snowflake enrichment) in parallel.

| Deliverable | Description |
|---|---|
| **All factors -- core queries** | |
| Factor 1: Contextual | Comments populated? FKs declared? Naming consistency? Low-cardinality columns constrained? |
| Factor 2: Consumable | Types compatible with AI formats? Sizes and partitioning assessed? |
| Factor 3: Current | Timestamp columns present? Staleness measured? Write cadence? |
| Factor 4: Correlated | Iceberg snapshots? Schema evolution? (Gap reported if no Iceberg) |
| Factor 5: Compliant | PII scan on names + values. RBAC grants. Masking policies. |
| **Snowflake enrichment queries** | |
| `agent/queries/snowflake/` | `TABLE_STORAGE_METRICS` for row counts, `COPY_HISTORY` for ingestion errors, `ACCESS_HISTORY` for auditing, `POLICY_REFERENCES` for masking, Snowpipe/Dynamic Table/Task detection |
| Generator mapping extended | New column/table metadata patterns → Factors 1-5 tests |

**Exit criteria:** The agent produces a scored assessment across all five factors on any SQL database. On Snowflake, the assessment is richer. The report clearly shows what was assessed, what couldn't be, and why.

---

#### Phase 3: Iceberg + OTEL queries

Add the two remaining query providers.

| Deliverable | Description |
|---|---|
| `agent/queries/iceberg/` | REST catalog queries: snapshots, schema evolution, manifest stats, table properties |
| `agent/queries/otel/` | Span traces (lineage), durations (freshness), error counts (reliability), throughput (data loss), access logs |
| Factor 3 enriched | Pipeline freshness from OTEL span timestamps, Iceberg snapshot timestamps |
| Factor 4 enriched | Lineage from spans, dataset versioning from Iceberg snapshots |
| Factor 5 enriched | Access logs from OTEL |

**Exit criteria:** The agent uses Iceberg and OTEL when available. Factors 3 and 4 coverage jumps significantly. Gaps are explicitly reported when these providers are absent.

---

#### Phase 4: Report diffing + continuous mode

Add comparison, history tracking, and ongoing monitoring.

| Deliverable | Description |
|---|---|
| Report diffing | `--compare previous-report.json` flag that diffs two reports and shows improvements, regressions, and new findings |
| Permissions adaptation | Detect permissions, run maximum possible assessment, report gaps as findings |
| Continuous mode | Run on schedule, diff against previous run, alert on score regressions |
| `docs/getting-started.md` | End-to-end: install, connect, first assessment, interpret results |
| `docs/adding-queries.md` | How to add tagged queries for new platforms or requirements |

**Exit criteria:** `docker run`, point at a database, get a scored assessment. Compare to last week's report and see the delta.

---

## Design Decisions

### Why Cortex Code CLI, not a compiled application

The agent's logic is: read the framework, discover the environment, generate SQL, run SQL, score results. This is exactly what a coding agent does. The intellectual property is in the query library, the generator mapping, and the scoring logic -- all of which are declarative (SQL, JSON schemas, mapping tables). A compiled application would add build complexity without adding capability.

### Why one concept (tagged queries), not two (surfaces + adapters)

Every query is tagged with its requirement (`ansi-sql`, `snowflake`, `iceberg-rest`, `otel`). The agent runs whatever queries match the detected environment. Adding a new platform means adding tagged queries to `agent/queries/<platform>/`, not implementing an interface. Lower barrier to contribution, simpler mental model.

### Why three-level scoring, not binary pass/fail

The framework defines three workload levels (L1: BI, L2: RAG, L3: Training) with different tolerances. A 4% null rate is fine for dashboards but unacceptable for training data. One measurement, three verdicts. The user sees exactly which workload level they're ready for without running the assessment three times.

### Why open standards first

The agent requires only ANSI SQL + `information_schema`. Everything else enriches. Any SQL database is assessable on day one. Platform queries are contributions, not prerequisites.

### Why Docker-first

API-only access. No install dependencies beyond Docker. Credentials via environment variables. Isolated from host. Clean teardown.

### Why flat directory structure

Start flat. Nest when complexity demands it. A directory with one file is overhead, not organization.

---

## Configuration

| Variable | Default | Description |
|---|---|---|
| `AIRD_CONNECTION_STRING` | -- | Database connection string (required) |
| `AIRD_CATALOG_URL` | -- | Iceberg REST catalog endpoint (optional) |
| `AIRD_OTEL_ENDPOINT` | -- | OTEL backend query endpoint (optional) |
| `AIRD_TARGET_LEVEL` | `all` | Assess against: `L1`, `L2`, `L3`, or `all` |
| `AIRD_THRESHOLDS` | `defaults.json` | Path to custom threshold configuration |
| `AIRD_LOG_LEVEL` | `info` | Log level (`debug`, `info`, `warn`, `error`) |
| `AIRD_OUTPUT` | `markdown` | Output: `stdout` (JSON), `markdown`, `json:<path>` |
| `AIRD_COMPARE` | -- | Path to previous report JSON for diffing |

---

## Quick Start

```bash
# Clone the repo
git clone https://github.com/[org]/ai-ready-data-framework.git
cd ai-ready-data-framework
make dev && source .venv/bin/activate

# Install the driver for your database
pip install psycopg2-binary              # PostgreSQL
pip install snowflake-connector-python   # Snowflake
pip install duckdb                       # DuckDB

# Run the assessment
python -m agent.cli assess --connection "postgresql://user:pass@localhost/mydb"

# Or via Docker (build with your driver)
docker build --build-arg DRIVER=postgres -t aird/agent .
docker run -e AIRD_CONNECTION_STRING="postgresql://user:pass@host/db" aird/agent
```

---

## Development

```bash
make dev            # Start dev environment
make test           # Run agent tests against fixtures
make lint           # Lint
make docker         # Build Docker image
make assess-local   # Run assessment against local test fixture
```

---

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md).

**Adding queries for a new platform:**

1. Create `agent/queries/<platform>/`
2. Write SQL queries tagged with `requires: <platform>`
3. Add fixture data to `tests/fixtures/`
4. Submit a PR

**Adding framework content:**

Framework content lives in `framework/` and is licensed CC BY-SA 4.0. Code is Apache 2.0.
