"""CLI entry point for the AI-Ready Data Assessment Agent.

Usage:
    python -m agent.cli assess --connection "postgresql://user:pass@localhost/mydb"
    python -m agent.cli assess --connection "snowflake://user:pass@account/db" --schema analytics
    python -m agent.cli assess --connection "databricks://token:xxx@host/catalog?http_path=..."
    python -m agent.cli assess --connection "duckdb://path/to/data.db" --output markdown
    python -m agent.cli history
    python -m agent.cli diff

Install the driver for your database:
    pip install psycopg2-binary              # PostgreSQL
    pip install snowflake-connector-python   # Snowflake
    pip install databricks-sql-connector     # Databricks
    pip install duckdb                       # DuckDB
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time

from pathlib import Path

from agent.context import (
    UserContext,
    context_path_for_connection,
    load_context,
    save_context,
)
from agent.discover import connect, discover
from agent.execute import execute_all, load_thresholds
from agent.interview import (
    discovery_questions,
    pre_assessment_questions,
    results_questions,
)
from agent.manifest import (
    get_manifest_path,
    init_manifest,
    record_assessment,
    record_comparison,
    record_context,
    record_discovery,
)
from agent.report import output_report
from agent.score import build_report
from agent.storage import (
    diff_reports,
    get_previous,
    list_assessments,
    render_diff_markdown,
    save_assessment,
)
from agent.suites import get_suite, list_suites


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="aird",
        description="AI-Ready Data Assessment Agent: assess your data estate against the AI-Ready Data Framework.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # assess command
    assess_parser = subparsers.add_parser("assess", help="Run an AI-readiness assessment")
    assess_parser.add_argument(
        "--connection", "-c",
        type=str,
        default=os.environ.get("AIRD_CONNECTION_STRING"),
        help="Database connection string (or set AIRD_CONNECTION_STRING env var)",
    )
    assess_parser.add_argument(
        "--schema", "-s",
        type=str,
        nargs="*",
        default=None,
        help="Schemas to assess (default: all non-system schemas)",
    )
    assess_parser.add_argument(
        "--suite",
        type=str,
        default="auto",
        help=f"Test suite to use: auto (detect), {', '.join(list_suites())} (default: auto)",
    )
    assess_parser.add_argument(
        "--output", "-o",
        type=str,
        default=os.environ.get("AIRD_OUTPUT", "markdown"),
        help="Output format: stdout (JSON), markdown, json:<path> (default: markdown)",
    )
    assess_parser.add_argument(
        "--thresholds",
        type=str,
        default=os.environ.get("AIRD_THRESHOLDS"),
        help="Path to custom thresholds JSON file",
    )
    assess_parser.add_argument(
        "--no-save",
        action="store_true",
        help="Don't save results to local history",
    )
    assess_parser.add_argument(
        "--compare",
        action="store_true",
        help="After running, compare against the previous assessment",
    )
    assess_parser.add_argument(
        "--context",
        type=str,
        default=os.environ.get("AIRD_CONTEXT"),
        help="Path to a user context YAML file (or set AIRD_CONTEXT env var)",
    )
    assess_parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        default=False,
        help="Enable interactive mode: generate interview questions and save context",
    )
    assess_parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Preview: connect, discover, and generate tests, but don't execute them",
    )
    assess_parser.add_argument(
        "--log-level",
        type=str,
        default=os.environ.get("AIRD_LOG_LEVEL", "info"),
        choices=["debug", "info", "warn", "error"],
        help="Log level (default: info)",
    )

    # history command
    history_parser = subparsers.add_parser("history", help="Show assessment history")
    history_parser.add_argument("--connection", "-c", type=str, default=None)
    history_parser.add_argument("--limit", "-n", type=int, default=20)

    # diff command
    diff_parser = subparsers.add_parser("diff", help="Compare the two most recent assessments")
    diff_parser.add_argument("--connection", "-c", type=str, default=None)

    # suites command
    subparsers.add_parser("suites", help="List available test suites")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "assess":
        run_assessment(args)
    elif args.command == "history":
        run_history(args)
    elif args.command == "diff":
        run_diff(args)
    elif args.command == "suites":
        run_list_suites()


def run_assessment(args: argparse.Namespace) -> None:
    """Run the full assessment pipeline."""

    log_level = getattr(logging, args.log_level.upper(), logging.INFO)
    logging.basicConfig(level=log_level, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%H:%M:%S")
    logger = logging.getLogger("aird")

    if not args.connection:
        logger.error("No connection string provided. Use --connection or set AIRD_CONNECTION_STRING.")
        sys.exit(1)

    # Load user context
    ctx = _load_user_context(args)
    if ctx.target_level:
        logger.info(f"Target workload level: {ctx.target_level}")
    if ctx.excluded_schemas:
        logger.info(f"Excluded schemas: {', '.join(ctx.excluded_schemas)}")
    if ctx.excluded_tables:
        logger.info(f"Excluded tables: {', '.join(ctx.excluded_tables)}")

    # In interactive mode, output Phase 1 questions before connecting
    if args.interactive:
        phase1 = pre_assessment_questions()
        _output_questions(phase1, "Phase 1: Pre-Assessment Interview")

    # Load thresholds
    thresholds = load_thresholds(args.thresholds)

    # Connect
    logger.info("Connecting to database...")
    start = time.time()
    try:
        conn = connect(args.connection)
    except Exception as e:
        logger.error(f"Failed to connect: {e}")
        sys.exit(1)
    logger.info(f"Connected in {time.time() - start:.1f}s")

    # Select suite
    suite = get_suite(args.suite, conn)
    logger.info(f"Using suite: {suite.platform} -- {suite.description}")

    # Initialize manifest
    manifest_path = get_manifest_path()
    init_manifest(manifest_path, args.connection, suite.platform)
    logger.debug(f"Manifest: {manifest_path}")

    # Record context in manifest
    record_context(manifest_path, ctx)

    # Discover (with context-aware filtering)
    logger.info("Discovering schemas, tables, and columns...")
    start = time.time()
    inventory = discover(conn, schemas=args.schema, user_context=ctx)
    total_columns = sum(len(t.columns) for t in inventory.tables)
    logger.info(f"Discovered {len(inventory.tables)} tables, {total_columns} columns in {time.time() - start:.1f}s")

    # Record discovery in manifest
    record_discovery(manifest_path, inventory)

    if not inventory.tables:
        logger.warning("No tables found. Check your connection and schema filters.")
        sys.exit(0)

    # In interactive mode, output Phase 2 questions after discovery
    if args.interactive:
        phase2 = discovery_questions(inventory, ctx)
        if phase2:
            _output_questions(phase2, "Phase 2: Discovery Walkthrough")

    # Generate tests from suite
    logger.info("Generating test suite...")
    start = time.time()
    tests = suite.generate_all(inventory)
    logger.info(f"Generated {len(tests)} tests in {time.time() - start:.1f}s")

    # Dry-run: preview tests without executing
    if args.dry_run:
        _output_dry_run(tests, inventory, suite, ctx)
        conn.close()
        return

    # Execute (with context-aware scoring)
    logger.info(f"Executing {len(tests)} tests...")
    start = time.time()
    results = execute_all(conn, tests, thresholds, user_context=ctx)
    logger.info(f"Executed in {time.time() - start:.1f}s")

    # Score & Report (with context)
    report = build_report(results, inventory, args.connection, suite.platform, user_context=ctx)

    # In interactive mode, output Phase 3 questions after results
    if args.interactive:
        phase3 = results_questions(report, ctx)
        if phase3:
            _output_questions(phase3, "Phase 3: Results Conversation")

    # Record assessment in manifest
    record_assessment(manifest_path, report)

    # Save
    if not args.no_save:
        assessment_id = save_assessment(report)
        logger.info(f"Assessment saved: {assessment_id}")

    # Save context for future runs
    _save_user_context(args, ctx)

    # Output
    output_report(report, args.output)

    # Summary
    summary = report["summary"]
    target = ctx.target_level or "L2"
    for level in ["L1", "L2", "L3"]:
        s = summary[level]
        marker = " <-- target" if level == target else ""
        logger.info(f"{level}: {s['pass']} pass, {s['fail']} fail, {s['skip']} skip ({s['score'] * 100:.1f}%){marker}")

    # Compare
    if args.compare and not args.no_save:
        previous = get_previous(report["assessment_id"], connection=report["environment"]["connection"])
        if previous:
            diff = diff_reports(report, previous)
            record_comparison(manifest_path, diff)
            print("\n" + render_diff_markdown(diff))
        else:
            logger.info("No previous assessment found for comparison.")

    logger.info(f"Manifest written to {manifest_path}")

    conn.close()


def _load_user_context(args: argparse.Namespace) -> UserContext:
    """Load user context from explicit path or per-connection storage."""
    ctx = UserContext()

    # Try explicit context file first
    if args.context:
        explicit_path = Path(args.context)
        ctx = load_context(explicit_path)
        logging.getLogger("aird").info(f"Loaded context from {explicit_path}")
        return ctx

    # Try per-connection saved context
    if args.connection:
        conn_path = context_path_for_connection(args.connection)
        if conn_path.exists():
            ctx = load_context(conn_path)
            logging.getLogger("aird").info(f"Loaded saved context for this connection")

    return ctx


def _save_user_context(args: argparse.Namespace, ctx: UserContext) -> None:
    """Save user context for future runs."""
    if args.context:
        # Save to explicit path
        save_context(ctx, Path(args.context))
    elif args.connection:
        # Save per-connection
        conn_path = context_path_for_connection(args.connection)
        save_context(ctx, conn_path)


def _output_dry_run(tests: list, inventory: object, suite: object, ctx: UserContext) -> None:
    """Preview what an assessment would do without executing any tests."""
    import json
    from collections import Counter

    total_columns = sum(len(t.columns) for t in inventory.tables)

    # Summary
    print("\n# Dry Run Preview")
    print(f"\n**Suite:** {suite.platform} -- {suite.description}")
    print(f"**Tables in scope:** {len(inventory.tables)}")
    print(f"**Columns in scope:** {total_columns}")
    print(f"**Tests to execute:** {len(tests)}")

    # Context applied
    if ctx.target_level:
        print(f"**Target level:** {ctx.target_level}")
    if ctx.excluded_schemas:
        print(f"**Excluded schemas:** {', '.join(ctx.excluded_schemas)}")
    if ctx.excluded_tables:
        print(f"**Excluded tables:** {', '.join(ctx.excluded_tables)}")
    if ctx.nullable_by_design:
        print(f"**Nullable by design:** {len(ctx.nullable_by_design)} columns")
    if ctx.false_positive_pii:
        print(f"**False-positive PII:** {len(ctx.false_positive_pii)} columns")
    if ctx.freshness_slas:
        print(f"**Custom freshness SLAs:** {len(ctx.freshness_slas)} tables")

    # Test breakdown by factor
    factor_counts = Counter(t.factor for t in tests)
    print("\n## Tests by Factor\n")
    print("| Factor | Count |")
    print("|--------|-------|")
    for factor in ["clean", "contextual", "consumable", "current", "correlated", "compliant"]:
        count = factor_counts.get(factor, 0)
        print(f"| {factor.capitalize()} | {count} |")

    # Test breakdown by level
    level_counts = Counter(t.target_type for t in tests)
    print("\n## Tests by Level\n")
    print("| Level | Count |")
    print("|-------|-------|")
    for level in ["database", "table", "column"]:
        count = level_counts.get(level, 0)
        print(f"| {level.capitalize()} | {count} |")

    # Test breakdown by requirement
    req_counts = Counter(t.requirement for t in tests)
    print("\n## Tests by Requirement\n")
    print("| Requirement | Count |")
    print("|-------------|-------|")
    for req, count in sorted(req_counts.items(), key=lambda x: -x[1]):
        print(f"| {req} | {count} |")

    # Sample SQL (first 5 tests)
    print("\n## Sample Test SQL (first 5)\n")
    for i, test in enumerate(tests[:5]):
        print(f"### {i+1}. {test.name} ({test.factor} / {test.requirement})")
        print(f"```sql\n{test.sql.strip()}\n```\n")

    # JSON output for agent consumption
    print("\n## Full Test List (JSON)\n")
    test_list = [{
        "name": t.name,
        "factor": t.factor,
        "requirement": t.requirement,
        "target_type": t.target_type,
        "platform": t.platform,
        "description": t.description,
    } for t in tests]
    print(f"```json\n{json.dumps(test_list, indent=2)}\n```")

    print(f"\n**Dry run complete.** Remove --dry-run to execute {len(tests)} tests.\n")


def _output_questions(questions: list, phase_title: str) -> None:
    """Output interview questions as structured JSON for agent consumption."""
    import json
    print(f"\n--- {phase_title} ---")
    for q in questions:
        print(json.dumps({
            "id": q.id,
            "phase": q.phase,
            "category": q.category,
            "prompt": q.prompt,
            "type": q.question_type,
            "options": [{"value": o.value, "label": o.label, "description": o.description}
                        for o in q.options] if q.options else [],
            "priority": q.priority,
            "context_field": q.context_field,
            "data": q.data,
        }, indent=2))
    print(f"--- End {phase_title} ---\n")


def run_history(args: argparse.Namespace) -> None:
    assessments = list_assessments(connection=args.connection, limit=args.limit)
    if not assessments:
        print("No assessments found.")
        return
    print(f"{'ID':<10} {'Timestamp':<22} {'Tables':<8} {'L1':<8} {'L2':<8} {'L3':<8} Connection")
    print("-" * 90)
    for a in assessments:
        l1 = f"{a['L1']['score'] * 100:.0f}%"
        l2 = f"{a['L2']['score'] * 100:.0f}%"
        l3 = f"{a['L3']['score'] * 100:.0f}%"
        print(f"{a['id']:<10} {a['timestamp'][:19]:<22} {a['tables_assessed']:<8} {l1:<8} {l2:<8} {l3:<8} {a['connection']}")


def run_diff(args: argparse.Namespace) -> None:
    from agent.storage import get_latest
    current = get_latest(connection=args.connection)
    if not current:
        print("No assessments found.")
        return
    previous = get_previous(current["assessment_id"], connection=args.connection)
    if not previous:
        print("Need at least two assessments to compare.")
        return
    diff = diff_reports(current, previous)
    print(render_diff_markdown(diff))


def run_list_suites() -> None:
    for name in list_suites():
        suite = get_suite(name)
        print(f"  {name:<15} {suite.description}")


if __name__ == "__main__":
    main()
