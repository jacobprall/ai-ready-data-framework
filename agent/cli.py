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

from agent.discover import connect, discover
from agent.execute import execute_all, load_thresholds
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

    # Discover
    logger.info("Discovering schemas, tables, and columns...")
    start = time.time()
    inventory = discover(conn, schemas=args.schema)
    total_columns = sum(len(t.columns) for t in inventory.tables)
    logger.info(f"Discovered {len(inventory.tables)} tables, {total_columns} columns in {time.time() - start:.1f}s")

    if not inventory.tables:
        logger.warning("No tables found. Check your connection and schema filters.")
        sys.exit(0)

    # Generate tests from suite
    logger.info("Generating test suite...")
    start = time.time()
    tests = suite.generate_all(inventory)
    logger.info(f"Generated {len(tests)} tests in {time.time() - start:.1f}s")

    # Execute
    logger.info(f"Executing {len(tests)} tests...")
    start = time.time()
    results = execute_all(conn, tests, thresholds)
    logger.info(f"Executed in {time.time() - start:.1f}s")

    # Score & Report
    report = build_report(results, inventory, args.connection, suite.platform)

    # Save
    if not args.no_save:
        assessment_id = save_assessment(report)
        logger.info(f"Assessment saved: {assessment_id}")

    # Output
    output_report(report, args.output)

    # Summary
    summary = report["summary"]
    for level in ["L1", "L2", "L3"]:
        s = summary[level]
        logger.info(f"{level}: {s['pass']} pass, {s['fail']} fail, {s['skip']} skip ({s['score'] * 100:.1f}%)")

    # Compare
    if args.compare and not args.no_save:
        previous = get_previous(report["assessment_id"], connection=report["environment"]["connection"])
        if previous:
            diff = diff_reports(report, previous)
            print("\n" + render_diff_markdown(diff))
        else:
            logger.info("No previous assessment found for comparison.")

    conn.close()


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
