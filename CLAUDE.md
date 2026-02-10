# AI-Ready Data Framework -- Agent Instructions

## Two Modes

This repo supports two modes of interaction:

1. **Assessment mode:** The user wants to assess their database. **Read `AGENTS.md` and follow the playbook.** It will walk you through connecting, running the assessment, interpreting results, and suggesting fixes. Individual skills in `skills/` can be loaded for specific pipeline stages.

2. **Contribution mode:** The user wants to contribute to the framework or agent code. Continue reading this file.

---

## What This Repo Is

This repo contains two things:

1. **The AI-Ready Data Framework** (`framework/`) -- an open standard defining what "AI-ready data" means across five factors. Content is licensed CC BY-SA 4.0.

2. **The Assessment Agent** (`agent/`) -- a Python CLI with per-platform test suites that assess data against the framework. Code is licensed Apache 2.0.

## Repo Structure

```
framework/              Framework content (markdown). The standard itself.
agent/schema/           Test result, report, and threshold JSON schemas. The contracts.
agent/suites/           Per-platform test suites. Each suite covers all 5 factors.
  base.py               Base Suite class all suites extend.
  common.py             ANSI SQL baseline. Works on any SQL database (DuckDB, etc).
  snowflake.py          Snowflake-native suite (ACCOUNT_USAGE, TIME_TRAVEL, etc).
agent/queries/          Legacy SQL query files (being migrated to suites).
agent/cli.py            CLI entry point.
agent/context.py        User context model: business context that enriches the assessment.
agent/platforms.py      Platform registry: centralizes driver, detection, and dialect knowledge.
agent/discover.py       Environment discovery: connect, enumerate tables/columns.
agent/manifest.py       Session manifest: tracks full assessment as readable markdown.
agent/execute.py        Test runner with read-only enforcement.
agent/interview.py      Interview question generators for three-phase interactive flow.
agent/score.py          Scorer: aggregate results into per-factor, per-level scores.
agent/report.py         Report generator: JSON + markdown output.
agent/storage.py        Local SQLite storage for assessment history and diffing.
agent/remediation/      Per-requirement fix templates the agent reads to generate suggestions.
skills/                 Composable agent skills. Each maps to a pipeline stage.
  SKILL.md              Top-level router: intent detection and workflow orchestration.
  connect/SKILL.md      Database connection setup for any supported platform.
  discover/SKILL.md     Schema/table/column enumeration and platform detection.
  interview/SKILL.md    Three-phase interactive context gathering.
  assess/SKILL.md       Test execution and scoring.
  interpret/SKILL.md    Results interpretation and factor walkthroughs.
  remediate/SKILL.md    Fix generation from remediation templates.
  compare/SKILL.md      Cross-run diffing and progress tracking.
  references/           Shared reference material loaded by multiple skills.
examples/               Community platform examples (Databricks, PostgreSQL, etc).
AGENTS.md               Assessment playbook -- instructions for any agent running an assessment.
CONTRIBUTING.md         Guide for adding new platforms and community contributions.
tests/fixtures/         Sample databases for deterministic testing.
packages/               Agent design doc and gameplan.
v1/                     Archived v1 content (kept for reference).
```

## Key Conventions

- **The agent is strictly read-only.** Enforced at connection level (read-only transactions where supported) and application level (SQL validation rejects non-SELECT statements). Never write a query that mutates data.
- **Platform registry.** All platform knowledge (driver, detection, SQL dialect, type mappings) is centralized in `agent/platforms.py`. Adding a platform means registering a `Platform` dataclass -- no more editing 7-11 files.
- **Suite-based architecture with dialect layer.** Each platform gets a full test suite that uses native capabilities. Suites extend CommonSuite, inheriting ANSI SQL tests and adding platform-specific ones. CommonSuite provides overridable dialect properties (`quote`, `cast_float`, `regex_match`, `epoch_diff`) so new platforms only override syntax, not entire test methods.
- **Three-level scoring.** Every test is assessed against L1 (BI), L2 (RAG), L3 (Training). One measurement, three verdicts. Thresholds in `thresholds-default.json` are self-describing -- each includes a `direction` field ("max" or "min") so scoring logic doesn't rely on hardcoded lists.
- **Content vs code.** Framework content in `framework/` is prose. Agent logic in `agent/` is implementation. Don't mix them.
- **Interactive assessment.** The assessment supports a three-phase interactive flow (pre-assessment interview, post-discovery walkthrough, post-results triage). User context is stored in `UserContext` (`agent/context.py`) and persisted per connection at `~/.aird/contexts/`. The agent drives the conversation; the CLI accepts a `--context` YAML file.
- **Composable skills.** The `skills/` directory contains agent skills that map 1:1 to pipeline stages. Each skill is a self-contained markdown document with YAML frontmatter, prerequisites, workflow steps, STOP points, and forward/back references. The top-level `skills/SKILL.md` is a router that detects user intent and jumps to the right skill. Skills compose via `**Load**` directives. Shared knowledge lives in `skills/references/`.

## When Writing Framework Content

- Write in Martin Fowler's style: declarative, concrete, no hyperbole.
- Requirements state what must be true about the data, not how to achieve it.
- The framework is vendor-agnostic. Never name a specific product as a requirement.

## When Writing Test Suites

- Extend `CommonSuite` (which extends `Suite`).
- Override `database_tests()`, `table_tests()`, and `column_tests()`.
- Call `super()` first to inherit common tests, then extend with platform-native tests.
- Each test is a `Test` dataclass with inline SQL -- no external query files needed.
- Use the platform's full capabilities. Don't limit yourself to ANSI SQL.
- Set `platform=self.platform` on every test so the report shows which suite generated it.

## When Writing Python Code

- Python 3.10+. Use type hints.
- Core dependencies are minimal (pyyaml, rich). Database drivers are optional extras.
- All test results must conform to `agent/suites/base.TestResult`.
- All reports must conform to `agent/schema/report.json`.
- Thresholds come from `agent/schema/thresholds-default.json` unless overridden.

## Built-in vs Community Platforms

The agent ships with two built-in platforms: **Snowflake** (with a native suite) and **DuckDB** (using CommonSuite). All other platforms are community contributions.

See `CONTRIBUTING.md` for the complete guide to adding a new platform. The short version:

1. **Register the platform** via `register_platform()` with a `Platform` dataclass
2. **Optionally create a suite** extending `CommonSuite` with platform-native tests
3. **Submit a PR** adding your files to `examples/community-suites/`

Working examples for PostgreSQL and Databricks live in `examples/community-suites/`.
