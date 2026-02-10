"""Tests for diff_reports and render_diff_markdown."""

import pytest

from agent.storage import diff_reports, render_diff_markdown


@pytest.fixture
def report_a():
    return {
        "assessment_id": "aaa",
        "timestamp": "2025-01-01T00:00:00",
        "summary": {
            "L1": {"pass": 10, "fail": 2, "skip": 0, "score": 0.8333},
            "L2": {"pass": 8, "fail": 4, "skip": 0, "score": 0.6667},
            "L3": {"pass": 6, "fail": 6, "skip": 0, "score": 0.5},
        },
        "factors": {
            "clean": {"L1": 0.80, "L2": 0.60, "L3": 0.40},
            "contextual": {"L1": 0.90, "L2": 0.70, "L3": 0.50},
        },
        "tests": [
            {"target": "t1", "requirement": "null_rate", "result": {"L1": "pass", "L2": "fail"}},
            {"target": "t2", "requirement": "comment_coverage", "result": {"L1": "fail", "L2": "fail"}},
            {"target": "t3", "requirement": "constraint_coverage", "result": {"L1": "pass", "L2": "pass"}},
        ],
    }


@pytest.fixture
def report_b():
    return {
        "assessment_id": "bbb",
        "timestamp": "2025-02-01T00:00:00",
        "summary": {
            "L1": {"pass": 11, "fail": 1, "skip": 0, "score": 0.9167},
            "L2": {"pass": 9, "fail": 3, "skip": 0, "score": 0.75},
            "L3": {"pass": 7, "fail": 5, "skip": 0, "score": 0.5833},
        },
        "factors": {
            "clean": {"L1": 0.90, "L2": 0.70, "L3": 0.50},
            "contextual": {"L1": 0.95, "L2": 0.80, "L3": 0.60},
        },
        "tests": [
            {"target": "t1", "requirement": "null_rate", "result": {"L1": "pass", "L2": "pass"}},  # improvement
            {"target": "t2", "requirement": "comment_coverage", "result": {"L1": "pass", "L2": "fail"}},  # L1 improvement
            {"target": "t3", "requirement": "constraint_coverage", "result": {"L1": "fail", "L2": "pass"}},  # L1 regression
            {"target": "t4", "requirement": "new_test", "result": {"L1": "pass", "L2": "pass"}},  # new
        ],
    }


class TestDiffReports:

    def test_score_changes(self, report_a, report_b):
        diff = diff_reports(report_b, report_a)
        assert diff["score_changes"]["L1"]["direction"] == "improved"
        assert diff["score_changes"]["L1"]["delta"] > 0

    def test_improvements_detected(self, report_a, report_b):
        diff = diff_reports(report_b, report_a)
        targets = [(i["target"], i["level"]) for i in diff["improvements"]]
        assert ("t1", "L2") in targets  # t1 fail->pass at L2
        assert ("t2", "L1") in targets  # t2 fail->pass at L1

    def test_regressions_detected(self, report_a, report_b):
        diff = diff_reports(report_b, report_a)
        targets = [(r["target"], r["level"]) for r in diff["regressions"]]
        assert ("t3", "L1") in targets  # t3 pass->fail at L1

    def test_new_tests_detected(self, report_a, report_b):
        diff = diff_reports(report_b, report_a)
        new_targets = [n["target"] for n in diff["new_tests"]]
        assert "t4" in new_targets

    def test_removed_tests_detected(self, report_a, report_b):
        # Remove t3 from report_b to simulate removal
        report_b["tests"] = [t for t in report_b["tests"] if t["target"] != "t3"]
        diff = diff_reports(report_b, report_a)
        removed_targets = [r["target"] for r in diff["removed_tests"]]
        assert "t3" in removed_targets

    def test_factor_changes(self, report_a, report_b):
        diff = diff_reports(report_b, report_a)
        assert "clean" in diff["factor_changes"]
        assert diff["factor_changes"]["clean"]["L1"]["delta"] > 0


class TestRenderDiffMarkdown:

    def test_contains_header(self, report_a, report_b):
        diff = diff_reports(report_b, report_a)
        md = render_diff_markdown(diff)
        assert "Assessment Comparison" in md

    def test_contains_score_table(self, report_a, report_b):
        diff = diff_reports(report_b, report_a)
        md = render_diff_markdown(diff)
        assert "Score Changes" in md
        assert "L1" in md

    def test_contains_improvements(self, report_a, report_b):
        diff = diff_reports(report_b, report_a)
        md = render_diff_markdown(diff)
        assert "Improvements" in md

    def test_contains_regressions(self, report_a, report_b):
        diff = diff_reports(report_b, report_a)
        md = render_diff_markdown(diff)
        assert "Regressions" in md

    def test_no_changes_message(self):
        same = {
            "current_id": "a", "previous_id": "b",
            "current_timestamp": "t1", "previous_timestamp": "t2",
            "score_changes": {"L1": {"current": 0.5, "previous": 0.5, "delta": 0, "direction": "unchanged"},
                              "L2": {"current": 0.5, "previous": 0.5, "delta": 0, "direction": "unchanged"},
                              "L3": {"current": 0.5, "previous": 0.5, "delta": 0, "direction": "unchanged"}},
            "factor_changes": {},
            "improvements": [], "regressions": [], "new_tests": [], "removed_tests": [],
        }
        md = render_diff_markdown(same)
        assert "No improvements or regressions" in md
