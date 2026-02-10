"""Executor module: runs suite tests and collects results.

SAFETY: The executor enforces read-only access. Every SQL statement is validated
before execution -- only SELECT, DESCRIBE, SHOW, and EXPLAIN are permitted. Any
statement containing DDL, DML, or DCL is rejected and logged as an error.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from agent.suites.base import Test, TestResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# SQL Safety
# ---------------------------------------------------------------------------

_ALLOWED_PREFIXES = re.compile(
    r"^\s*(SELECT|DESCRIBE|DESC|SHOW|EXPLAIN|WITH)\b",
    re.IGNORECASE,
)

_BLOCKED_KEYWORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|MERGE|CREATE|ALTER|DROP|TRUNCATE|REPLACE|"
    r"GRANT|REVOKE|CALL|EXEC|EXECUTE|COPY|PUT|GET|REMOVE|UNDROP|"
    r"BEGIN|COMMIT|ROLLBACK)\b",
    re.IGNORECASE,
)


class ReadOnlyViolation(Exception):
    """Raised when a SQL statement violates the read-only constraint."""
    pass


def validate_readonly(sql: str) -> None:
    """Validate that a SQL statement is read-only."""
    stripped = sql.strip()
    if not _ALLOWED_PREFIXES.match(stripped):
        raise ReadOnlyViolation(
            f"Statement rejected: does not start with SELECT, DESCRIBE, SHOW, EXPLAIN, or WITH. "
            f"The assessment agent is read-only. Got: {stripped[:80]}..."
        )
    no_strings = re.sub(r"'[^']*'", "''", stripped)
    no_strings = re.sub(r'"[^"]*"', '""', no_strings)
    if _BLOCKED_KEYWORDS.search(no_strings):
        match = _BLOCKED_KEYWORDS.search(no_strings)
        raise ReadOnlyViolation(
            f"Statement rejected: contains blocked keyword '{match.group()}'. "
            f"The assessment agent is read-only."
        )


# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

def load_thresholds(thresholds_path: str | None = None) -> dict:
    """Load threshold configuration."""
    if thresholds_path:
        path = Path(thresholds_path)
    else:
        path = Path(__file__).parent / "schema" / "thresholds-default.json"
    with open(path) as f:
        data = json.load(f)
    return {k: v for k, v in data.items() if not k.startswith("$")}


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

def execute_test(
    conn: Any,
    test: Test,
    thresholds: dict,
    user_context: Any | None = None,
) -> TestResult:
    """Execute a single test and return a scored result.

    If a UserContext is provided, it influences scoring:
    - nullable_by_design columns get relaxed null_rate thresholds
    - false_positive_pii columns skip PII tests
    - per-table freshness SLAs override default staleness thresholds
    - accepted failures are annotated in the result detail
    """
    sql = test.sql.strip()

    # Validate read-only
    try:
        validate_readonly(sql)
    except ReadOnlyViolation as e:
        logger.error(f"Read-only violation for {test.name}: {e}")
        return _error_result(test, str(e), thresholds)

    # Build target string
    if test.target_type == "database":
        target = "database"
    elif test.target_type == "table":
        target = f"{test.sql}"  # table target is embedded in the test
        target = f"{test.name}"
    else:
        target = test.name

    # Execute
    cursor = conn.cursor()
    measured_value: float | None = None
    error_detail: str | None = None

    try:
        cursor.execute(sql)
        row = cursor.fetchone()
        if row is not None:
            col_names = [desc[0].lower() for desc in cursor.description] if cursor.description else []
            if "measured_value" in col_names:
                idx = col_names.index("measured_value")
                measured_value = float(row[idx]) if row[idx] is not None else None
            else:
                measured_value = float(row[0]) if row[0] is not None else None
    except Exception as e:
        error_detail = str(e)
        logger.warning(f"Query failed for {test.name}: {e}")
    finally:
        cursor.close()

    # Apply context-aware threshold overrides
    req_thresholds = _get_thresholds(thresholds, test.factor, test.requirement)
    if user_context is not None:
        req_thresholds = _apply_context_overrides(
            req_thresholds, test, target, user_context
        )

    levels = [level for level in ["L1", "L2", "L3"] if req_thresholds.get(level) is not None]
    result = _score(measured_value, req_thresholds, test.requirement)

    # Detail
    context_notes: list[str] = []
    if error_detail:
        detail = f"Query failed: {error_detail}"
    elif measured_value is not None:
        parts = []
        for level in ["L1", "L2", "L3"]:
            threshold = req_thresholds.get(level)
            if threshold is not None:
                status = result.get(level, "skip")
                is_max = _is_max_threshold(test.requirement)
                op = "<=" if is_max else ">="
                parts.append(f"{level}: {status} ({op}{threshold})")
        detail = f"Measured {measured_value:.4f}. {'; '.join(parts)}"
    else:
        detail = "No data returned"

    # Annotate with context info
    if user_context is not None:
        annotations = _get_context_annotations(test, target, user_context)
        if annotations:
            detail += f" [{'; '.join(annotations)}]"

    return TestResult(
        name=test.name,
        factor=test.factor,
        requirement=test.requirement,
        target=target,
        platform=test.platform,
        levels=levels,
        result=result,
        measured_value=measured_value,
        thresholds=req_thresholds,
        detail=detail,
        query=sql,
    )


def execute_all(
    conn: Any,
    tests: list[Test],
    thresholds: dict,
    user_context: Any | None = None,
) -> list[TestResult]:
    """Execute all tests and return results."""
    results: list[TestResult] = []
    for test in tests:
        result = execute_test(conn, test, thresholds, user_context=user_context)
        results.append(result)
    return results


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _error_result(test: Test, error: str, thresholds: dict) -> TestResult:
    """Create an error TestResult."""
    req_thresholds = _get_thresholds(thresholds, test.factor, test.requirement)
    levels = [level for level in ["L1", "L2", "L3"] if req_thresholds.get(level) is not None]
    return TestResult(
        name=test.name,
        factor=test.factor,
        requirement=test.requirement,
        target="error",
        platform=test.platform,
        levels=levels,
        result={level: "fail" for level in ["L1", "L2", "L3"]},
        measured_value=None,
        thresholds=req_thresholds,
        detail=error,
        query="",
    )


def _get_thresholds(thresholds: dict, factor: str, requirement: str) -> dict[str, float | None]:
    factor_thresholds = thresholds.get(factor, {})
    req_thresholds = factor_thresholds.get(requirement, {})
    if isinstance(req_thresholds, dict):
        return {"L1": req_thresholds.get("L1"), "L2": req_thresholds.get("L2"), "L3": req_thresholds.get("L3")}
    return {"L1": None, "L2": None, "L3": None}


def _is_max_threshold(requirement: str) -> bool:
    """Returns True if threshold is a maximum (lower is better)."""
    min_thresholds = {
        "column_comment_coverage", "table_comment_coverage", "foreign_key_coverage",
        "naming_consistency", "ai_compatible_type_rate", "timestamp_column_coverage",
        "constraint_coverage", "rbac_coverage", "classification_coverage",
        "column_statistics_coverage", "pii_masking_coverage",
    }
    return requirement not in min_thresholds


def _score(measured_value: float | None, thresholds: dict[str, float | None], requirement: str) -> dict[str, str]:
    result: dict[str, str] = {}
    is_max = _is_max_threshold(requirement)
    for level in ["L1", "L2", "L3"]:
        threshold = thresholds.get(level)
        if threshold is None:
            result[level] = "skip"
        elif measured_value is None:
            result[level] = "fail"
        else:
            if is_max:
                result[level] = "pass" if measured_value <= threshold else "fail"
            else:
                result[level] = "pass" if measured_value >= threshold else "fail"
    return result


# ---------------------------------------------------------------------------
# Context-aware overrides
# ---------------------------------------------------------------------------

def _parse_target_parts(target: str) -> tuple[str, str, str]:
    """Parse a target string into (schema, table, column) parts.

    Target formats vary: "schema.table.column", "schema.table", "test_name", etc.
    Returns empty strings for unparseable parts.
    """
    parts = target.split(".")
    if len(parts) >= 3:
        return parts[0], parts[1], parts[2]
    elif len(parts) == 2:
        return parts[0], parts[1], ""
    return "", "", ""


def _apply_context_overrides(
    req_thresholds: dict[str, float | None],
    test: Test,
    target: str,
    user_context: Any,
) -> dict[str, float | None]:
    """Apply user context overrides to thresholds for a specific test.

    Returns a copy of the thresholds with any overrides applied.
    """
    schema, table, column = _parse_target_parts(target)
    overridden = dict(req_thresholds)

    # Nullable-by-design: relax null_rate thresholds significantly
    if test.requirement == "null_rate" and column:
        if user_context.is_nullable_by_design(schema, table, column):
            # Allow up to 100% nulls for intentionally nullable columns
            overridden = {"L1": 1.0, "L2": 1.0, "L3": 0.50}

    # False-positive PII: skip PII tests for confirmed non-PII columns
    if test.requirement in ("pii_detection_rate", "pii_column_name_rate") and column:
        if user_context.is_false_positive_pii(schema, table, column):
            # Skip all levels -- this column is confirmed not-PII
            overridden = {"L1": None, "L2": None, "L3": None}

    # Per-table freshness SLAs: override staleness thresholds
    if test.requirement == "max_staleness_hours" and table:
        sla = user_context.get_freshness_sla(schema, table)
        if sla is not None:
            # Use the user's SLA as the threshold at all levels
            overridden = {"L1": float(sla), "L2": float(sla), "L3": float(sla)}

    return overridden


def _get_context_annotations(test: Test, target: str, user_context: Any) -> list[str]:
    """Get human-readable annotations from user context for a test result."""
    schema, table, column = _parse_target_parts(target)
    annotations: list[str] = []

    if test.requirement == "null_rate" and column:
        if user_context.is_nullable_by_design(schema, table, column):
            annotations.append("nullable by design")

    if test.requirement in ("pii_detection_rate", "pii_column_name_rate") and column:
        if user_context.is_false_positive_pii(schema, table, column):
            annotations.append("confirmed not PII")
        elif user_context.is_confirmed_pii(schema, table, column):
            annotations.append("confirmed PII")

    if test.requirement == "max_staleness_hours" and table:
        sla = user_context.get_freshness_sla(schema, table)
        if sla is not None:
            annotations.append(f"custom SLA: {sla}h")

    if table and user_context.get_table_criticality(schema, table) == "critical":
        annotations.append("critical table")

    if user_context.is_failure_accepted(test.requirement, target):
        annotations.append("previously accepted")

    return annotations
