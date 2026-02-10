"""Integration tests: manifest file operations."""

import pytest

from agent.context import UserContext
from agent.discover import DatabaseInventory
from agent.manifest import (
    append_section,
    get_latest_section,
    has_in_progress,
    init_manifest,
    read_manifest,
    record_assessment,
    record_context,
    record_discovery,
    update_section_status,
)


pytestmark = pytest.mark.integration


@pytest.fixture
def manifest_path(tmp_path):
    return tmp_path / ".aird" / "manifest.md"


class TestInitManifest:

    def test_creates_file(self, manifest_path):
        init_manifest(manifest_path, "duckdb://test.db", "duckdb")
        assert manifest_path.exists()

    def test_has_header(self, manifest_path):
        init_manifest(manifest_path, "duckdb://test.db", "duckdb")
        content = manifest_path.read_text()
        assert "AI-Ready Data Assessment Manifest" in content

    def test_has_connection_section(self, manifest_path):
        init_manifest(manifest_path, "duckdb://test.db", "duckdb")
        content = manifest_path.read_text()
        assert "aird:connection" in content
        assert "duckdb" in content

    def test_sanitizes_credentials(self, manifest_path):
        init_manifest(manifest_path, "postgresql://user:pass@host/db", "postgresql")
        content = manifest_path.read_text()
        assert "user" not in content.split("Connection")[1] or "***" in content
        assert "pass" not in content.split("Connection")[1] or "***" in content


class TestAppendSection:

    def test_appends_to_existing(self, manifest_path):
        init_manifest(manifest_path, "duckdb://test.db", "duckdb")
        append_section(manifest_path, "context", "COMPLETE", {"target_level": "L2"})
        content = manifest_path.read_text()
        assert "aird:context" in content
        assert "Target Level" in content

    def test_auto_inits_if_missing(self, manifest_path):
        append_section(manifest_path, "test", "COMPLETE", {"key": "value"})
        assert manifest_path.exists()
        content = manifest_path.read_text()
        assert "aird:test" in content


class TestGetLatestSection:

    def test_finds_section(self, manifest_path):
        init_manifest(manifest_path, "duckdb://test.db", "duckdb")
        result = get_latest_section(manifest_path, "connection")
        assert result is not None
        assert result["status"] == "COMPLETE"

    def test_returns_none_for_missing_section(self, manifest_path):
        init_manifest(manifest_path, "duckdb://test.db", "duckdb")
        result = get_latest_section(manifest_path, "nonexistent")
        assert result is None

    def test_returns_none_for_missing_file(self, tmp_path):
        result = get_latest_section(tmp_path / "nope.md", "connection")
        assert result is None


class TestUpdateSectionStatus:

    def test_updates_status(self, manifest_path):
        init_manifest(manifest_path, "duckdb://test.db", "duckdb")
        append_section(manifest_path, "assessment", "IN_PROGRESS", {"status": "running"})
        update_section_status(manifest_path, "assessment", "IN_PROGRESS", "COMPLETE")
        content = manifest_path.read_text()
        assert "status: COMPLETE" in content
        assert "status: IN_PROGRESS" not in content

    def test_noop_for_missing_file(self, tmp_path):
        update_section_status(tmp_path / "nope.md", "assessment", "IN_PROGRESS", "COMPLETE")
        # Should not raise


class TestHasInProgress:

    def test_detects_in_progress(self, manifest_path):
        init_manifest(manifest_path, "duckdb://test.db", "duckdb")
        append_section(manifest_path, "assessment", "IN_PROGRESS", {"status": "running"})
        result = has_in_progress(manifest_path)
        assert result == "assessment"

    def test_none_when_all_complete(self, manifest_path):
        init_manifest(manifest_path, "duckdb://test.db", "duckdb")
        result = has_in_progress(manifest_path)
        assert result is None


class TestRecordHelpers:

    def test_record_context(self, manifest_path):
        init_manifest(manifest_path, "duckdb://test.db", "duckdb")
        ctx = UserContext(target_level="L2", excluded_schemas=["staging"])
        record_context(manifest_path, ctx)
        content = manifest_path.read_text()
        assert "aird:context" in content
        assert "L2" in content

    def test_record_discovery(self, manifest_path, sample_inventory):
        init_manifest(manifest_path, "duckdb://test.db", "duckdb")
        record_discovery(manifest_path, sample_inventory)
        content = manifest_path.read_text()
        assert "aird:discovery" in content

    def test_record_assessment(self, manifest_path, sample_report):
        init_manifest(manifest_path, "duckdb://test.db", "duckdb")
        record_assessment(manifest_path, sample_report)
        content = manifest_path.read_text()
        assert "aird:assessment" in content
        assert sample_report["assessment_id"] in content
