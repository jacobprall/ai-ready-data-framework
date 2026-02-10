"""Tests for report building: build_report, _build_summary, _build_factor_scores, _build_not_assessed."""

import pytest

from agent.discover import DatabaseInventory
from agent.score import (
    _build_factor_scores,
    _build_not_assessed,
    _build_summary,
    _build_user_context_section,
    _sanitize_connection,
    build_report,
)
from agent.suites.base import TestResult


class TestSanitizeConnection:

    def test_strips_credentials(self):
        result = _sanitize_connection("postgresql://user:pass@host/db")
        assert "user" not in result
        assert "pass" not in result
        assert "host" in result

    def test_handles_non_url(self):
        result = _sanitize_connection("not-a-url")
        # urlparse handles most strings without error; just verify no crash
        assert isinstance(result, str)


class TestBuildSummary:

    def test_counts_pass_fail_skip(self, sample_results):
        summary = _build_summary(sample_results)
        assert "L1" in summary
        assert "L2" in summary
        assert "L3" in summary
        assert summary["L1"]["pass"] + summary["L1"]["fail"] + summary["L1"]["skip"] == len(sample_results)

    def test_score_calculation(self):
        results = [
            TestResult("t1", "clean", "null_rate", "t", "common", ["L1"], {"L1": "pass"}, 0.01, {}, "", ""),
            TestResult("t2", "clean", "null_rate", "t", "common", ["L1"], {"L1": "fail"}, 0.50, {}, "", ""),
        ]
        summary = _build_summary(results)
        assert summary["L1"]["score"] == 0.5  # 1 pass / 2 applicable

    def test_empty_results(self):
        summary = _build_summary([])
        assert summary["L1"]["score"] == 0.0
        assert summary["L1"]["pass"] == 0

    def test_all_skips(self):
        results = [
            TestResult("t1", "clean", "null_rate", "t", "common", [], {"L1": "skip"}, None, {}, "", ""),
        ]
        summary = _build_summary(results)
        assert summary["L1"]["score"] == 0.0


class TestBuildFactorScores:

    def test_all_factors_present(self, sample_results):
        factors = _build_factor_scores(sample_results)
        assert "clean" in factors
        assert "contextual" in factors
        assert "consumable" in factors
        assert "current" in factors
        assert "correlated" in factors
        assert "compliant" in factors

    def test_each_factor_has_three_levels(self, sample_results):
        factors = _build_factor_scores(sample_results)
        for factor_scores in factors.values():
            assert "L1" in factor_scores
            assert "L2" in factor_scores
            assert "L3" in factor_scores

    def test_factor_with_no_tests(self):
        results = [
            TestResult("t1", "clean", "null_rate", "t", "common", ["L1"], {"L1": "pass"}, 0.01, {}, "", ""),
        ]
        factors = _build_factor_scores(results)
        assert factors["consumable"]["L1"] == 0.0  # No consumable tests


class TestBuildNotAssessed:

    def test_missing_iceberg(self):
        inv = DatabaseInventory(
            available_providers=["ansi-sql"],
            unavailable_providers=["iceberg"],
        )
        items = _build_not_assessed(inv)
        reqs = [i.get("requirement") for i in items]
        assert "dataset_versioning" in reqs
        assert "manifest_profiling" in reqs

    def test_missing_otel(self):
        inv = DatabaseInventory(
            available_providers=["ansi-sql"],
            unavailable_providers=["otel"],
        )
        items = _build_not_assessed(inv)
        reqs = [i.get("requirement") for i in items]
        assert "pipeline_freshness" in reqs
        assert "lineage" in reqs
        assert "data_loss_detection" in reqs

    def test_all_available(self):
        inv = DatabaseInventory(
            available_providers=["ansi-sql", "iceberg", "otel"],
            unavailable_providers=[],
        )
        items = _build_not_assessed(inv)
        assert len(items) == 0

    def test_permissions_gaps(self):
        inv = DatabaseInventory(
            available_providers=["ansi-sql", "iceberg", "otel"],
            unavailable_providers=[],
            permissions_gaps=["Cannot access ACCOUNT_USAGE"],
        )
        items = _build_not_assessed(inv)
        assert len(items) == 1
        assert items[0]["factor"] == "compliant"


class TestBuildReport:

    def test_has_all_required_keys(self, sample_results, sample_inventory):
        report = build_report(sample_results, sample_inventory, "duckdb://test.db", "common")
        assert "assessment_id" in report
        assert "timestamp" in report
        assert "suite" in report
        assert "environment" in report
        assert "summary" in report
        assert "factors" in report
        assert "not_assessed" in report
        assert "tests" in report

    def test_no_user_context_section_without_context(self, sample_results, sample_inventory):
        report = build_report(sample_results, sample_inventory, "duckdb://test.db", "common")
        assert "user_context" not in report

    def test_has_user_context_section_with_context(self, sample_results, sample_inventory, sample_context):
        report = build_report(sample_results, sample_inventory, "duckdb://test.db", "common", user_context=sample_context)
        assert "user_context" in report
        assert report["user_context"]["target_level"] == "L2"

    def test_environment_section(self, sample_results, sample_inventory):
        report = build_report(sample_results, sample_inventory, "postgresql://user:pass@host/db", "common")
        env = report["environment"]
        assert "user" not in env["connection"]
        assert "pass" not in env["connection"]
        assert env["tables_assessed"] == len(sample_inventory.tables)

    def test_tests_array_length(self, sample_results, sample_inventory):
        report = build_report(sample_results, sample_inventory, "duckdb://test.db", "common")
        assert len(report["tests"]) == len(sample_results)


class TestBuildUserContextSection:

    def test_includes_target_level(self, sample_context, sample_results):
        section = _build_user_context_section(sample_context, sample_results)
        assert section["target_level"] == "L2"

    def test_includes_scope_decisions(self, sample_context, sample_results):
        section = _build_user_context_section(sample_context, sample_results)
        assert "scope_decisions" in section
        assert "staging" in section["scope_decisions"]["excluded_schemas"]

    def test_includes_critical_tables(self, sample_context, sample_results):
        section = _build_user_context_section(sample_context, sample_results)
        assert "analytics.orders" in section["critical_tables"]

    def test_includes_pii_decisions(self, sample_context, sample_results):
        section = _build_user_context_section(sample_context, sample_results)
        assert "pii_decisions" in section

    def test_empty_context_minimal_section(self, empty_context, sample_results):
        section = _build_user_context_section(empty_context, sample_results)
        assert "target_level" not in section
        assert "scope_decisions" not in section
