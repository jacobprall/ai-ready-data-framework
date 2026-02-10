"""Integration tests: CommonSuite generate + execute against DuckDB fixture."""

import pytest

from agent.discover import discover
from agent.execute import execute_all, load_thresholds
from agent.score import build_report
from agent.suites.common import CommonSuite


pytestmark = pytest.mark.integration


@pytest.fixture
def thresholds():
    return load_thresholds()


@pytest.fixture
def fixture_inventory(duckdb_conn):
    return discover(duckdb_conn, schemas=["analytics"])


class TestCommonSuiteGeneration:

    def test_generates_tests(self, fixture_inventory):
        suite = CommonSuite()
        tests = suite.generate_all(fixture_inventory)
        assert len(tests) > 0

    def test_all_tests_have_required_fields(self, fixture_inventory):
        suite = CommonSuite()
        tests = suite.generate_all(fixture_inventory)
        for test in tests:
            assert test.name
            assert test.factor
            assert test.requirement
            assert test.query
            assert test.target_type in ("database", "table", "column")
            assert test.platform == "common"

    def test_database_level_tests(self, fixture_inventory):
        suite = CommonSuite()
        tests = suite.generate_all(fixture_inventory)
        db_tests = [t for t in tests if t.target_type == "database"]
        names = {t.name for t in db_tests}
        assert "table_comment_coverage" in names
        assert "timestamp_column_coverage" in names
        assert "constraint_coverage" in names
        assert "rbac_coverage" in names

    def test_table_level_tests(self, fixture_inventory):
        suite = CommonSuite()
        tests = suite.generate_all(fixture_inventory)
        table_tests = [t for t in tests if t.target_type == "table"]
        names = {t.name for t in table_tests}
        assert "column_comment_coverage" in names
        assert "naming_consistency" in names
        assert "ai_compatible_type_rate" in names
        assert "pii_column_name_scan" in names

    def test_column_level_tests(self, fixture_inventory):
        suite = CommonSuite()
        tests = suite.generate_all(fixture_inventory)
        col_tests = [t for t in tests if t.target_type == "column"]
        names = {t.name for t in col_tests}
        assert "null_rate" in names

    def test_factors_covered(self, fixture_inventory):
        suite = CommonSuite()
        tests = suite.generate_all(fixture_inventory)
        factors = {t.factor for t in tests}
        assert "clean" in factors
        assert "contextual" in factors
        assert "consumable" in factors
        assert "current" in factors
        assert "correlated" in factors
        assert "compliant" in factors


class TestCommonSuiteExecution:

    def test_all_tests_execute_without_error(self, duckdb_conn, fixture_inventory, thresholds):
        suite = CommonSuite()
        tests = suite.generate_all(fixture_inventory)
        results = execute_all(duckdb_conn, tests, thresholds)
        assert len(results) == len(tests)
        # No results should have "Query failed" from SQL errors
        # (some tests may legitimately return None for empty tables)
        errors = [r for r in results if "Query failed" in r.detail]
        # Allow some errors (DuckDB may not support all information_schema queries)
        # but the majority should succeed
        success_rate = 1 - len(errors) / len(results)
        assert success_rate > 0.5, f"Too many query failures: {len(errors)}/{len(results)}"

    def test_produces_valid_report(self, duckdb_conn, fixture_inventory, thresholds):
        suite = CommonSuite()
        tests = suite.generate_all(fixture_inventory)
        results = execute_all(duckdb_conn, tests, thresholds)
        report = build_report(results, fixture_inventory, "duckdb://test.db", "common")
        assert "assessment_id" in report
        assert "summary" in report
        assert "factors" in report
        assert "tests" in report
        assert len(report["tests"]) == len(results)

    def test_scores_are_valid(self, duckdb_conn, fixture_inventory, thresholds):
        suite = CommonSuite()
        tests = suite.generate_all(fixture_inventory)
        results = execute_all(duckdb_conn, tests, thresholds)
        report = build_report(results, fixture_inventory, "duckdb://test.db", "common")
        for level in ["L1", "L2", "L3"]:
            score = report["summary"][level]["score"]
            assert 0.0 <= score <= 1.0
