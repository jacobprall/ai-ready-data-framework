"""Report module: renders assessment reports in JSON and markdown formats."""

from __future__ import annotations

import json
from typing import Any


def output_report(report: dict[str, Any], output: str = "stdout") -> None:
    """Output the assessment report.

    Args:
        report: The full report dict.
        output: Where to send it:
            - "stdout" -- JSON to stdout
            - "json:<path>" -- JSON to a file
            - "markdown" -- Markdown summary to stdout
    """
    if output == "stdout":
        print(json.dumps(report, indent=2, default=str))
    elif output.startswith("json:"):
        path = output[5:]
        with open(path, "w") as f:
            json.dump(report, f, indent=2, default=str)
        print(f"Report written to {path}")
    elif output == "markdown":
        print(render_markdown(report))
    else:
        print(json.dumps(report, indent=2, default=str))


def render_markdown(report: dict[str, Any]) -> str:
    """Render a human-readable markdown summary of the assessment."""
    lines: list[str] = []

    lines.append("# AI-Ready Data Assessment Report")
    lines.append("")
    lines.append(f"**Assessment ID:** {report['assessment_id']}")
    lines.append(f"**Timestamp:** {report['timestamp']}")
    lines.append(f"**Connection:** {report['environment']['connection']}")
    lines.append(f"**Tables assessed:** {report['environment']['tables_assessed']}")
    lines.append(f"**Columns assessed:** {report['environment']['columns_assessed']}")
    lines.append("")

    # Available providers
    providers = report["environment"]["available_providers"]
    lines.append(f"**Available providers:** {', '.join(providers)}")
    unavailable = report["environment"]["unavailable_providers"]
    if unavailable:
        lines.append(f"**Unavailable providers:** {', '.join(unavailable)}")
    lines.append("")

    # Summary
    lines.append("## Overall Scores")
    lines.append("")
    lines.append("| Level | Pass | Fail | Skip | Score |")
    lines.append("|---|---|---|---|---|")
    for level in ["L1", "L2", "L3"]:
        s = report["summary"][level]
        score_pct = f"{s['score'] * 100:.1f}%"
        lines.append(f"| {level} | {s['pass']} | {s['fail']} | {s['skip']} | {score_pct} |")
    lines.append("")

    # Factor scores
    lines.append("## Factor Scores")
    lines.append("")
    lines.append("| Factor | L1 | L2 | L3 |")
    lines.append("|---|---|---|---|")
    for factor, scores in report["factors"].items():
        l1 = f"{scores['L1'] * 100:.0f}%"
        l2 = f"{scores['L2'] * 100:.0f}%"
        l3 = f"{scores['L3'] * 100:.0f}%"
        lines.append(f"| {factor.capitalize()} | {l1} | {l2} | {l3} |")
    lines.append("")

    # Not assessed
    if report["not_assessed"]:
        lines.append("## Not Assessed")
        lines.append("")
        for item in report["not_assessed"]:
            factor = item["factor"].capitalize()
            req = item.get("requirement", "")
            reason = item["reason"]
            if req:
                lines.append(f"- **{factor}** ({req}): {reason}")
            else:
                lines.append(f"- **{factor}**: {reason}")
        lines.append("")

    # Failures summary
    failures = [t for t in report["tests"] if any(v == "fail" for v in t["result"].values())]
    if failures:
        lines.append("## Failures")
        lines.append("")
        lines.append("| Target | Requirement | Measured | L1 | L2 | L3 |")
        lines.append("|---|---|---|---|---|---|")
        for t in failures[:50]:  # Cap at 50 to keep report readable
            measured = f"{t['measured_value']:.4f}" if t['measured_value'] is not None else "N/A"
            l1 = t["result"].get("L1", "skip")
            l2 = t["result"].get("L2", "skip")
            l3 = t["result"].get("L3", "skip")
            lines.append(f"| {t['target']} | {t['requirement']} | {measured} | {l1} | {l2} | {l3} |")
        if len(failures) > 50:
            lines.append(f"| ... | ... | ... | ... | ... | ... |")
            lines.append(f"*{len(failures) - 50} additional failures not shown.*")
        lines.append("")

    # Passing summary
    total_tests = len(report["tests"])
    lines.append("## Summary")
    lines.append("")
    lines.append(f"**Total tests:** {total_tests}")
    lines.append(f"**Total failures:** {len(failures)}")
    lines.append("")

    # Level readiness
    for level in ["L1", "L2", "L3"]:
        score = report["summary"][level]["score"]
        if score >= 0.95:
            status = "READY"
        elif score >= 0.80:
            status = "MOSTLY READY (minor issues)"
        elif score >= 0.50:
            status = "NOT READY (significant gaps)"
        else:
            status = "NOT READY (major gaps)"
        lines.append(f"- **{level}:** {status} ({score * 100:.1f}%)")
    lines.append("")

    return "\n".join(lines)
