"""Storage module: local SQLite database for assessment history and diffing.

Uses Python's built-in sqlite3 -- no additional dependencies. Stores assessment
runs with full JSON reports, enabling history tracking and cross-run comparison.

Default location: ~/.aird/assessments.db (configurable via AIRD_DB_PATH).
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_DEFAULT_DB_DIR = Path.home() / ".aird"
_DEFAULT_DB_PATH = _DEFAULT_DB_DIR / "assessments.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS assessments (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    connection TEXT NOT NULL,
    tables_assessed INTEGER,
    columns_assessed INTEGER,
    providers TEXT,
    l1_score REAL,
    l2_score REAL,
    l3_score REAL,
    l1_pass INTEGER,
    l1_fail INTEGER,
    l2_pass INTEGER,
    l2_fail INTEGER,
    l3_pass INTEGER,
    l3_fail INTEGER,
    report_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_assessments_timestamp ON assessments(timestamp);
CREATE INDEX IF NOT EXISTS idx_assessments_connection ON assessments(connection);
"""


def _get_db_path() -> Path:
    """Get the database path from env or default."""
    env_path = os.environ.get("AIRD_DB_PATH")
    if env_path:
        return Path(env_path)
    return _DEFAULT_DB_PATH


def _ensure_db(db_path: Path) -> sqlite3.Connection:
    """Create the database and schema if they don't exist."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.executescript(_SCHEMA)
    return conn


def save_assessment(report: dict[str, Any], db_path: Path | None = None) -> str:
    """Save an assessment report to the local database.

    Args:
        report: The full report dict conforming to agent/schema/report.json.
        db_path: Override database path (default: ~/.aird/assessments.db).

    Returns:
        The assessment ID.
    """
    path = db_path or _get_db_path()
    conn = _ensure_db(path)

    assessment_id = report["assessment_id"]
    summary = report["summary"]
    env = report["environment"]

    conn.execute(
        """INSERT OR REPLACE INTO assessments
           (id, timestamp, connection, tables_assessed, columns_assessed, providers,
            l1_score, l2_score, l3_score, l1_pass, l1_fail, l2_pass, l2_fail, l3_pass, l3_fail,
            report_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            assessment_id,
            report["timestamp"],
            env["connection"],
            env.get("tables_assessed", 0),
            env.get("columns_assessed", 0),
            ",".join(env.get("available_providers", [])),
            summary["L1"]["score"],
            summary["L2"]["score"],
            summary["L3"]["score"],
            summary["L1"]["pass"],
            summary["L1"]["fail"],
            summary["L2"]["pass"],
            summary["L2"]["fail"],
            summary["L3"]["pass"],
            summary["L3"]["fail"],
            json.dumps(report, default=str),
        ),
    )
    conn.commit()
    conn.close()
    return assessment_id


def get_latest(connection: str | None = None, db_path: Path | None = None) -> dict[str, Any] | None:
    """Get the most recent assessment, optionally filtered by connection string.

    Args:
        connection: Filter by sanitized connection string. If None, returns the latest overall.
        db_path: Override database path.

    Returns:
        The full report dict, or None if no assessments exist.
    """
    path = db_path or _get_db_path()
    if not path.exists():
        return None

    conn = _ensure_db(path)

    if connection:
        row = conn.execute(
            "SELECT report_json FROM assessments WHERE connection = ? ORDER BY timestamp DESC LIMIT 1",
            (connection,),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT report_json FROM assessments ORDER BY timestamp DESC LIMIT 1",
        ).fetchone()

    conn.close()

    if row:
        return json.loads(row[0])
    return None


def get_previous(current_id: str, connection: str | None = None, db_path: Path | None = None) -> dict[str, Any] | None:
    """Get the assessment run immediately before the given one.

    Args:
        current_id: The current assessment ID.
        connection: Filter by connection string.
        db_path: Override database path.

    Returns:
        The previous report dict, or None.
    """
    path = db_path or _get_db_path()
    if not path.exists():
        return None

    conn = _ensure_db(path)

    # Get the timestamp of the current assessment
    current = conn.execute(
        "SELECT timestamp FROM assessments WHERE id = ?", (current_id,)
    ).fetchone()

    if not current:
        conn.close()
        return None

    current_ts = current[0]

    if connection:
        row = conn.execute(
            """SELECT report_json FROM assessments
               WHERE connection = ? AND timestamp < ?
               ORDER BY timestamp DESC LIMIT 1""",
            (connection, current_ts),
        ).fetchone()
    else:
        row = conn.execute(
            """SELECT report_json FROM assessments
               WHERE timestamp < ?
               ORDER BY timestamp DESC LIMIT 1""",
            (current_ts,),
        ).fetchone()

    conn.close()
    return json.loads(row[0]) if row else None


def list_assessments(
    connection: str | None = None,
    limit: int = 20,
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    """List recent assessments as summary dicts.

    Args:
        connection: Filter by connection string.
        limit: Max number of results.
        db_path: Override database path.

    Returns:
        List of summary dicts with id, timestamp, connection, and scores.
    """
    path = db_path or _get_db_path()
    if not path.exists():
        return []

    conn = _ensure_db(path)

    query = """
        SELECT id, timestamp, connection, tables_assessed, columns_assessed,
               l1_score, l2_score, l3_score, l1_pass, l1_fail, l2_pass, l2_fail, l3_pass, l3_fail
        FROM assessments
    """
    params: tuple = ()

    if connection:
        query += " WHERE connection = ?"
        params = (connection,)

    query += " ORDER BY timestamp DESC LIMIT ?"
    params = params + (limit,)

    rows = conn.execute(query, params).fetchall()
    conn.close()

    return [
        {
            "id": r[0],
            "timestamp": r[1],
            "connection": r[2],
            "tables_assessed": r[3],
            "columns_assessed": r[4],
            "L1": {"score": r[5], "pass": r[8], "fail": r[9]},
            "L2": {"score": r[6], "pass": r[10], "fail": r[11]},
            "L3": {"score": r[7], "pass": r[12], "fail": r[13]},
        }
        for r in rows
    ]


def diff_reports(current: dict[str, Any], previous: dict[str, Any]) -> dict[str, Any]:
    """Diff two assessment reports and return a structured comparison.

    Args:
        current: The current report.
        previous: The previous report to compare against.

    Returns:
        A diff dict with score changes, improvements, regressions, and new/removed tests.
    """
    diff: dict[str, Any] = {
        "current_id": current["assessment_id"],
        "previous_id": previous["assessment_id"],
        "current_timestamp": current["timestamp"],
        "previous_timestamp": previous["timestamp"],
        "score_changes": {},
        "factor_changes": {},
        "improvements": [],
        "regressions": [],
        "new_tests": [],
        "removed_tests": [],
    }

    # Score changes
    for level in ["L1", "L2", "L3"]:
        curr_score = current["summary"][level]["score"]
        prev_score = previous["summary"][level]["score"]
        delta = round(curr_score - prev_score, 4)
        diff["score_changes"][level] = {
            "current": curr_score,
            "previous": prev_score,
            "delta": delta,
            "direction": "improved" if delta > 0 else "regressed" if delta < 0 else "unchanged",
        }

    # Factor-level changes
    for factor in current.get("factors", {}):
        if factor in previous.get("factors", {}):
            factor_diff: dict[str, Any] = {}
            for level in ["L1", "L2", "L3"]:
                curr = current["factors"][factor].get(level, 0)
                prev = previous["factors"][factor].get(level, 0)
                delta = round(curr - prev, 4)
                factor_diff[level] = {
                    "current": curr,
                    "previous": prev,
                    "delta": delta,
                }
            diff["factor_changes"][factor] = factor_diff

    # Test-level comparison
    curr_tests = {t["target"] + "|" + t["requirement"]: t for t in current.get("tests", [])}
    prev_tests = {t["target"] + "|" + t["requirement"]: t for t in previous.get("tests", [])}

    for key, curr_test in curr_tests.items():
        if key in prev_tests:
            prev_test = prev_tests[key]
            for level in ["L1", "L2", "L3"]:
                curr_result = curr_test["result"].get(level)
                prev_result = prev_test["result"].get(level)
                if prev_result == "fail" and curr_result == "pass":
                    diff["improvements"].append({
                        "target": curr_test["target"],
                        "requirement": curr_test["requirement"],
                        "level": level,
                    })
                elif prev_result == "pass" and curr_result == "fail":
                    diff["regressions"].append({
                        "target": curr_test["target"],
                        "requirement": curr_test["requirement"],
                        "level": level,
                    })
        else:
            diff["new_tests"].append({
                "target": curr_test["target"],
                "requirement": curr_test["requirement"],
            })

    for key in prev_tests:
        if key not in curr_tests:
            prev_test = prev_tests[key]
            diff["removed_tests"].append({
                "target": prev_test["target"],
                "requirement": prev_test["requirement"],
            })

    return diff


def render_diff_markdown(diff: dict[str, Any]) -> str:
    """Render a diff as a human-readable markdown summary."""
    lines: list[str] = []

    lines.append("# Assessment Comparison")
    lines.append("")
    lines.append(f"**Current:** {diff['current_id']} ({diff['current_timestamp']})")
    lines.append(f"**Previous:** {diff['previous_id']} ({diff['previous_timestamp']})")
    lines.append("")

    # Score changes
    lines.append("## Score Changes")
    lines.append("")
    lines.append("| Level | Previous | Current | Delta |")
    lines.append("|---|---|---|---|")
    for level in ["L1", "L2", "L3"]:
        sc = diff["score_changes"][level]
        delta_str = f"+{sc['delta']:.1%}" if sc["delta"] > 0 else f"{sc['delta']:.1%}"
        if sc["delta"] == 0:
            delta_str = "unchanged"
        lines.append(f"| {level} | {sc['previous']:.1%} | {sc['current']:.1%} | {delta_str} |")
    lines.append("")

    # Factor changes
    if diff["factor_changes"]:
        lines.append("## Factor Changes")
        lines.append("")
        lines.append("| Factor | L1 Delta | L2 Delta | L3 Delta |")
        lines.append("|---|---|---|---|")
        for factor, changes in diff["factor_changes"].items():
            deltas = []
            for level in ["L1", "L2", "L3"]:
                d = changes[level]["delta"]
                deltas.append(f"+{d:.1%}" if d > 0 else f"{d:.1%}" if d < 0 else "--")
            lines.append(f"| {factor.capitalize()} | {deltas[0]} | {deltas[1]} | {deltas[2]} |")
        lines.append("")

    # Improvements
    if diff["improvements"]:
        lines.append(f"## Improvements ({len(diff['improvements'])})")
        lines.append("")
        for item in diff["improvements"]:
            lines.append(f"- **{item['target']}** -- {item['requirement']} now passes {item['level']}")
        lines.append("")

    # Regressions
    if diff["regressions"]:
        lines.append(f"## Regressions ({len(diff['regressions'])})")
        lines.append("")
        for item in diff["regressions"]:
            lines.append(f"- **{item['target']}** -- {item['requirement']} now fails {item['level']}")
        lines.append("")

    # New / removed
    if diff["new_tests"]:
        lines.append(f"## New Tests ({len(diff['new_tests'])})")
        lines.append("")
        for item in diff["new_tests"]:
            lines.append(f"- {item['target']} -- {item['requirement']}")
        lines.append("")

    if diff["removed_tests"]:
        lines.append(f"## Removed Tests ({len(diff['removed_tests'])})")
        lines.append("")
        for item in diff["removed_tests"]:
            lines.append(f"- {item['target']} -- {item['requirement']}")
        lines.append("")

    if not diff["improvements"] and not diff["regressions"]:
        lines.append("No improvements or regressions detected.")
        lines.append("")

    return "\n".join(lines)
