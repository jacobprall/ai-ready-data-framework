# The AI-Ready Data Framework

<div align="center">
<a href="https://www.apache.org/licenses/LICENSE-2.0">
        <img src="https://img.shields.io/badge/Code-Apache%202.0-blue.svg" alt="Code License: Apache 2.0"></a>
<a href="https://creativecommons.org/licenses/by-sa/4.0/">
        <img src="https://img.shields.io/badge/Content-CC%20BY--SA%204.0-lightgrey.svg" alt="Content License: CC BY-SA 4.0"></a>
</div>

<p></p>

**Five factors that determine whether your data can reliably power AI systems.**

An open standard defining what "AI-ready data" actually means, plus an assessment agent that turns the framework into executable, red/green test suites against your data infrastructure.

## Quick Start

```bash
# Clone and install
git clone https://github.com/[org]/ai-ready-data-framework.git
cd ai-ready-data-framework
make dev
source .venv/bin/activate

# Install the driver for your database
pip install psycopg2-binary              # PostgreSQL
pip install snowflake-connector-python   # Snowflake
pip install databricks-sql-connector     # Databricks
pip install duckdb                       # DuckDB

# Run the assessment
python -m agent.cli assess --connection "postgresql://user:pass@localhost/mydb"
```

The agent works with any SQL database that supports `information_schema`. No vendor lock-in.

## What's In This Repo

### [The Framework](framework/)

The AI-Ready Data Framework defines five factors of AI-ready data with requirements at three workload levels (L1: Analytics, L2: RAG, L3: Training).

| Factor | Name | Definition |
|---|---|---|
| **0** | [**Clean**](framework/factor-00-clean.md) | Accurate, complete, valid, and free of errors |
| **1** | [**Contextual**](framework/factor-01-contextual.md) | Meaning is explicit and co-located |
| **2** | [**Consumable**](framework/factor-02-consumable.md) | Right format, right latency, right scale |
| **3** | [**Current**](framework/factor-03-current.md) | Reflects the present state |
| **4** | [**Correlated**](framework/factor-04-correlated.md) | Traceable from source to decision |
| **5** | [**Compliant**](framework/factor-05-compliant.md) | Governed with AI-specific safeguards |

### [The Assessment Agent](agent/)

A Python CLI with purpose-built test suites for each platform. Each suite uses the platform's native capabilities to their fullest -- not just ANSI SQL, but ACCOUNT_USAGE views, Unity Catalog system tables, Delta Lake history, and more. The output is a scored report showing which workload levels your data is ready for.

**The agent is strictly read-only.** It will never create, modify, or delete anything in your database. This is enforced at the connection layer (read-only transactions where the driver supports it) and the application layer (every SQL statement is validated before execution -- only SELECT, DESCRIBE, SHOW, and EXPLAIN are permitted). Grant it a read-only role for defense in depth.

**Available suites:**

| Suite | What it uses |
|---|---|
| `common` | ANSI SQL + information_schema. Works on any SQL database. |
| `snowflake` | ACCOUNT_USAGE, OBJECT_DEPENDENCIES, masking policies, Snowpipe, Dynamic Tables, TIME_TRAVEL |
| `databricks` | Unity Catalog system tables, Delta Lake DESCRIBE HISTORY, column tags, table lineage |

The suite is auto-detected from your connection. Or specify it: `--suite snowflake`

### [Design & Architecture](packages/)

Design decisions, architecture diagrams, and the project gameplan.

## How It Works

1. **Connect** -- Point the agent at your database
2. **Discover** -- The agent enumerates schemas, tables, and columns
3. **Generate** -- Column metadata is mapped to applicable tests from the framework
4. **Execute** -- SQL queries run against your data, producing measurements
5. **Score** -- Results are assessed against L1/L2/L3 thresholds
6. **Report** -- A scored report shows exactly where you stand and what to fix
7. **Save** -- Results are stored locally in SQLite (`~/.aird/assessments.db`) for history and diffing

```bash
# View assessment history
python -m agent.cli history

# Compare the two most recent assessments
python -m agent.cli diff

# Run an assessment and auto-compare against the previous one
python -m agent.cli assess --connection "postgresql://..." --compare
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Contributors

@jacobprall - Jacob Prall, Snowflake

## License

Content and images: [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)

Code: [Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0)
