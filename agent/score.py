"""Scorer module: aggregates test results into per-factor, per-level scores."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from agent.discover import DatabaseInventory
from agent.execute import TestResult


def build_report(
    results: list[TestResult],
    inventory: DatabaseInventory,
    connection_string: str,
    suite_platform: str = "common",
    user_context: Any | None = None,
) -> dict[str, Any]:
    """Build a full assessment report from test results.

    Args:
        results: All test results from execution.
        inventory: The discovered database inventory.
        connection_string: The original connection string (will be sanitized).
        suite_platform: The suite that was used for the assessment.
        user_context: Optional UserContext with business context.

    Returns:
        A report dict conforming to agent/schema/report.json.
    """
    report: dict[str, Any] = {
        "assessment_id": str(uuid.uuid4())[:8],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "suite": suite_platform,
        "environment": _build_environment(inventory, connection_string),
        "summary": _build_summary(results),
        "factors": _build_factor_scores(results),
        "not_assessed": _build_not_assessed(inventory),
        "tests": [_result_to_dict(r) for r in results],
    }

    # Add user context section if provided
    if user_context is not None:
        report["user_context"] = _build_user_context_section(user_context, results)

    return report


def _sanitize_connection(connection_string: str) -> str:
    """Remove credentials from a connection string."""
    from urllib.parse import urlparse, urlunparse

    try:
        parsed = urlparse(connection_string)
        sanitized = parsed._replace(
            netloc=f"***@{parsed.hostname}" if parsed.hostname else parsed.netloc
        )
        return urlunparse(sanitized)
    except Exception:
        return "***"


def _build_environment(inventory: DatabaseInventory, connection_string: str) -> dict:
    """Build the environment section of the report."""
    total_columns = sum(len(t.columns) for t in inventory.tables)
    return {
        "connection": _sanitize_connection(connection_string),
        "available_providers": inventory.available_providers,
        "unavailable_providers": inventory.unavailable_providers,
        "permissions_gaps": inventory.permissions_gaps,
        "tables_assessed": len(inventory.tables),
        "columns_assessed": total_columns,
    }


def _build_summary(results: list[TestResult]) -> dict:
    """Build the aggregate summary with pass/fail/skip counts per level."""
    summary: dict[str, dict[str, Any]] = {}

    for level in ["L1", "L2", "L3"]:
        pass_count = sum(1 for r in results if r.result.get(level) == "pass")
        fail_count = sum(1 for r in results if r.result.get(level) == "fail")
        skip_count = sum(1 for r in results if r.result.get(level) == "skip")
        total_applicable = pass_count + fail_count

        summary[level] = {
            "pass": pass_count,
            "fail": fail_count,
            "skip": skip_count,
            "score": round(pass_count / total_applicable, 4) if total_applicable > 0 else 0.0,
        }

    return summary


def _build_factor_scores(results: list[TestResult]) -> dict:
    """Build per-factor scores at each level."""
    factors: dict[str, dict[str, float]] = {}
    factor_names = ["clean", "contextual", "consumable", "current", "correlated", "compliant"]

    for factor in factor_names:
        factor_results = [r for r in results if r.factor == factor]
        scores: dict[str, float] = {}

        for level in ["L1", "L2", "L3"]:
            applicable = [r for r in factor_results if r.result.get(level) in ("pass", "fail")]
            if applicable:
                passed = sum(1 for r in applicable if r.result.get(level) == "pass")
                scores[level] = round(passed / len(applicable), 4)
            else:
                scores[level] = 0.0

        factors[factor] = scores

    return factors


def _build_not_assessed(inventory: DatabaseInventory) -> list[dict]:
    """Build the list of things that couldn't be assessed."""
    not_assessed: list[dict] = []

    if "iceberg" not in inventory.available_providers:
        not_assessed.append({
            "factor": "correlated",
            "requirement": "dataset_versioning",
            "reason": "No Iceberg metadata tables available. Snapshot history, schema evolution, and dataset versioning could not be assessed.",
        })
        not_assessed.append({
            "factor": "clean",
            "requirement": "manifest_profiling",
            "reason": "No Iceberg metadata tables available. Manifest-level statistics (profiling without scanning) could not be assessed.",
        })

    if "otel" not in inventory.available_providers:
        not_assessed.append({
            "factor": "current",
            "requirement": "pipeline_freshness",
            "reason": "No OpenTelemetry data available. Pipeline latency, reliability, and freshness from pipeline spans could not be assessed.",
        })
        not_assessed.append({
            "factor": "correlated",
            "requirement": "lineage",
            "reason": "No OpenTelemetry data available. Pipeline lineage and span-level tracing could not be assessed.",
        })
        not_assessed.append({
            "factor": "clean",
            "requirement": "data_loss_detection",
            "reason": "No OpenTelemetry data available. Rows-in vs rows-out throughput analysis could not be assessed.",
        })

    for gap in inventory.permissions_gaps:
        not_assessed.append({
            "factor": "compliant",
            "reason": gap,
        })

    return not_assessed


def _result_to_dict(result: TestResult) -> dict:
    """Convert a TestResult to a dict conforming to the test-result schema."""
    return {
        "name": result.name,
        "factor": result.factor,
        "requirement": result.requirement,
        "target": result.target,
        "platform": result.platform,
        "levels": result.levels,
        "result": result.result,
        "measured_value": result.measured_value,
        "thresholds": result.thresholds,
        "detail": result.detail,
        "query": result.query,
    }


def _build_user_context_section(user_context: Any, results: list[TestResult]) -> dict:
    """Build the user_context section of the report.

    Documents what business context was applied and how it influenced the
    assessment. This provides an audit trail of user decisions.
    """
    section: dict[str, Any] = {}

    # Target level
    if user_context.target_level:
        section["target_level"] = user_context.target_level

    # Scope decisions
    scope: dict[str, Any] = {}
    if user_context.excluded_schemas:
        scope["excluded_schemas"] = user_context.excluded_schemas
    if user_context.excluded_tables:
        scope["excluded_tables"] = user_context.excluded_tables
    if scope:
        section["scope_decisions"] = scope

    # Table criticality
    critical_tables = {k: v for k, v in user_context.table_criticality.items() if v == "critical"}
    if critical_tables:
        section["critical_tables"] = list(critical_tables.keys())

    # PII decisions
    pii: dict[str, Any] = {}
    if user_context.known_pii_columns:
        pii["confirmed_pii"] = user_context.known_pii_columns
    if user_context.false_positive_pii:
        pii["confirmed_not_pii"] = user_context.false_positive_pii
    if pii:
        section["pii_decisions"] = pii

    # Null handling
    if user_context.nullable_by_design:
        section["nullable_by_design"] = user_context.nullable_by_design

    # Freshness SLAs
    if user_context.freshness_slas:
        section["freshness_slas"] = user_context.freshness_slas

    # Key decisions
    keys: dict[str, Any] = {}
    if user_context.confirmed_keys:
        keys["confirmed_keys"] = user_context.confirmed_keys
    if user_context.not_keys:
        keys["confirmed_not_keys"] = user_context.not_keys
    if keys:
        section["key_decisions"] = keys

    # Accepted failures
    if user_context.accepted_failures:
        section["accepted_failures"] = user_context.accepted_failures

    # Count how many results were influenced by context
    context_influenced = sum(
        1 for r in results
        if any(tag in r.detail for tag in [
            "nullable by design", "confirmed not PII", "confirmed PII",
            "custom SLA", "critical table", "previously accepted",
        ])
    )
    if context_influenced > 0:
        section["tests_influenced"] = context_influenced

    # Infrastructure context
    infra: dict[str, bool] = {}
    if user_context.has_dbt:
        infra["dbt"] = True
    if user_context.has_catalog:
        infra["data_catalog"] = True
    if user_context.has_otel:
        infra["opentelemetry"] = True
    if user_context.has_iceberg:
        infra["iceberg"] = True
    if infra:
        section["infrastructure"] = infra

    return section
