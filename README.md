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
pip install -e "./agent"

# Install the driver for your database
pip install snowflake-connector-python   # Snowflake
pip install duckdb                       # DuckDB (also used for local testing)

# Run the assessment
python -m agent.cli assess --connection "snowflake://user:pass@account/db/schema?warehouse=WH"
```

Built-in support for **Snowflake** (with a full platform-native suite) and **DuckDB** (ANSI SQL baseline). Community platforms (PostgreSQL, Databricks, MySQL, etc.) can be added via the platform registry -- see [CONTRIBUTING.md](CONTRIBUTING.md).

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

A Python CLI with purpose-built test suites. The output is a scored report showing which workload levels your data is ready for.

**The agent is strictly read-only.** It will never create, modify, or delete anything in your data source. For SQL platforms, this is enforced at the connection layer (read-only transactions) and application layer (SQL statement validation). Non-SQL platforms enforce read-only via their native connection options. Grant it a read-only role for defense in depth.

**Built-in suites:**

| Suite | What it uses |
|---|---|
| `common` | ANSI SQL + information_schema. Works on any SQL database (DuckDB, etc). |
| `snowflake` | ACCOUNT_USAGE, OBJECT_DEPENDENCIES, masking policies, Snowpipe, Dynamic Tables, TIME_TRAVEL |

**Community suites** for Databricks, PostgreSQL, MongoDB, and more can be added via `examples/community-suites/`. The agent supports both SQL and non-SQL data sources through its query-type dispatch system -- see [CONTRIBUTING.md](CONTRIBUTING.md).

The suite is auto-detected from your connection. Or specify it: `--suite snowflake`

### [Design & Architecture](packages/)

Design decisions, architecture diagrams, and the project roadmap.

## How It Works

1. **Connect** -- Point the agent at your database
2. **Discover** -- The agent enumerates schemas, tables, and columns
3. **Generate** -- Column metadata is mapped to applicable tests from the framework
4. **Execute** -- Queries run against your data source (SQL, aggregation pipelines, APIs), producing measurements
5. **Score** -- Results are assessed against L1/L2/L3 thresholds
6. **Report** -- A scored report shows exactly where you stand and what to fix
7. **Save** -- Results are stored locally in SQLite (`~/.aird/assessments.db`) for history and diffing

```bash
# View assessment history
python -m agent.cli history

# Compare the two most recent assessments
python -m agent.cli diff

# Run an assessment and auto-compare against the previous one
python -m agent.cli assess --connection "snowflake://..." --compare
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Contributors

@jacobprall - Jacob Prall, Snowflake

## License

Content and images: [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)

Code: [Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0)
