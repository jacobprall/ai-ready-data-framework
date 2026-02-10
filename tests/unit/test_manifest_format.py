"""Tests for manifest formatting and sanitization helpers."""

import pytest

from agent.manifest import (
    _format_key,
    _format_section,
    _sanitize_for_manifest,
)


class TestFormatKey:

    def test_snake_case(self):
        assert _format_key("target_level") == "Target Level"

    def test_single_word(self):
        assert _format_key("platform") == "Platform"

    def test_multiple_underscores(self):
        assert _format_key("max_staleness_hours") == "Max Staleness Hours"


class TestSanitizeForManifest:

    def test_strips_credentials(self):
        result = _sanitize_for_manifest("postgresql://user:pass@host/db")
        assert "user" not in result
        assert "pass" not in result
        assert "host" in result

    def test_handles_non_url(self):
        result = _sanitize_for_manifest("not-a-url")
        # urlparse parses this successfully (as a path), so it comes back as-is
        assert isinstance(result, str)

    def test_preserves_scheme(self):
        result = _sanitize_for_manifest("snowflake://user:pass@account/db")
        assert result.startswith("snowflake://")


class TestFormatSection:

    def test_has_start_marker(self):
        section = _format_section("connection", "COMPLETE", {"platform": "duckdb"})
        assert "<!-- START -- aird:connection" in section
        assert "status: COMPLETE" in section

    def test_has_end_marker(self):
        section = _format_section("connection", "COMPLETE", {"platform": "duckdb"})
        assert "<!-- END -- aird:connection -->" in section

    def test_has_heading(self):
        section = _format_section("connection", "COMPLETE", {"platform": "duckdb"})
        assert "## Connection" in section

    def test_scalar_value(self):
        section = _format_section("test", "COMPLETE", {"platform": "duckdb"})
        assert "**Platform:** duckdb" in section

    def test_dict_value(self):
        section = _format_section("test", "COMPLETE", {"scores": {"L1": "80%", "L2": "60%"}})
        assert "**Scores:**" in section
        assert "- L1: 80%" in section

    def test_list_value(self):
        section = _format_section("test", "COMPLETE", {"items": ["a", "b", "c"]})
        assert "**Items:**" in section
        assert "- a" in section
        assert "- b" in section

    def test_list_of_dicts(self):
        section = _format_section("test", "COMPLETE", {
            "gaps": [{"factor": "clean", "reason": "no data"}]
        })
        assert "factor: clean" in section

    def test_in_progress_status(self):
        section = _format_section("assessment", "IN_PROGRESS", {"status": "running"})
        assert "status: IN_PROGRESS" in section
