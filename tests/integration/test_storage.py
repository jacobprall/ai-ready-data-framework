"""Integration tests: SQLite storage round-trip operations."""

import pytest

from agent.storage import (
    _ensure_db,
    diff_reports,
    get_latest,
    get_previous,
    list_assessments,
    save_assessment,
)


pytestmark = pytest.mark.integration


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "test_assessments.db"


def _make_report(assessment_id: str, timestamp: str, l1_score: float = 0.8) -> dict:
    return {
        "assessment_id": assessment_id,
        "timestamp": timestamp,
        "suite": "common",
        "environment": {
            "connection": "duckdb://test.db",
            "available_providers": ["ansi-sql"],
            "unavailable_providers": ["iceberg"],
            "permissions_gaps": [],
            "tables_assessed": 5,
            "columns_assessed": 20,
        },
        "summary": {
            "L1": {"pass": 8, "fail": 2, "skip": 0, "score": l1_score},
            "L2": {"pass": 6, "fail": 4, "skip": 0, "score": 0.6},
            "L3": {"pass": 4, "fail": 6, "skip": 0, "score": 0.4},
        },
        "factors": {"clean": {"L1": 0.8, "L2": 0.6, "L3": 0.4}},
        "not_assessed": [],
        "tests": [],
    }


class TestSaveAndRetrieve:

    def test_save_returns_id(self, db_path):
        report = _make_report("abc123", "2025-01-01T00:00:00")
        result = save_assessment(report, db_path)
        assert result == "abc123"

    def test_get_latest(self, db_path):
        save_assessment(_make_report("first", "2025-01-01T00:00:00"), db_path)
        save_assessment(_make_report("second", "2025-02-01T00:00:00"), db_path)
        latest = get_latest(db_path=db_path)
        assert latest["assessment_id"] == "second"

    def test_get_latest_by_connection(self, db_path):
        save_assessment(_make_report("a", "2025-01-01T00:00:00"), db_path)
        latest = get_latest(connection="duckdb://test.db", db_path=db_path)
        assert latest is not None

    def test_get_latest_none_when_empty(self, db_path):
        _ensure_db(db_path)
        assert get_latest(db_path=db_path) is None

    def test_get_previous(self, db_path):
        save_assessment(_make_report("first", "2025-01-01T00:00:00"), db_path)
        save_assessment(_make_report("second", "2025-02-01T00:00:00"), db_path)
        prev = get_previous("second", db_path=db_path)
        assert prev["assessment_id"] == "first"

    def test_get_previous_none_when_only_one(self, db_path):
        save_assessment(_make_report("only", "2025-01-01T00:00:00"), db_path)
        prev = get_previous("only", db_path=db_path)
        assert prev is None


class TestListAssessments:

    def test_lists_all(self, db_path):
        save_assessment(_make_report("a", "2025-01-01T00:00:00"), db_path)
        save_assessment(_make_report("b", "2025-02-01T00:00:00"), db_path)
        assessments = list_assessments(db_path=db_path)
        assert len(assessments) == 2

    def test_respects_limit(self, db_path):
        for i in range(10):
            save_assessment(_make_report(f"r{i}", f"2025-01-{i+1:02d}T00:00:00"), db_path)
        assessments = list_assessments(limit=3, db_path=db_path)
        assert len(assessments) == 3

    def test_empty_db(self, db_path):
        _ensure_db(db_path)
        assessments = list_assessments(db_path=db_path)
        assert len(assessments) == 0

    def test_summary_has_scores(self, db_path):
        save_assessment(_make_report("a", "2025-01-01T00:00:00", l1_score=0.85), db_path)
        assessments = list_assessments(db_path=db_path)
        assert assessments[0]["L1"]["score"] == 0.85


class TestEnsureDb:

    def test_creates_directory(self, tmp_path):
        db_path = tmp_path / "deep" / "nested" / "test.db"
        conn = _ensure_db(db_path)
        assert db_path.exists()
        conn.close()

    def test_idempotent(self, db_path):
        conn1 = _ensure_db(db_path)
        conn1.close()
        conn2 = _ensure_db(db_path)
        conn2.close()
        assert db_path.exists()
