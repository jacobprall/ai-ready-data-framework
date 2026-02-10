"""Integration tests: context YAML file operations."""

import pytest

from agent.context import (
    UserContext,
    context_path_for_connection,
    load_context,
    merge_context,
    save_context,
)


pytestmark = pytest.mark.integration


class TestContextPersistence:

    def test_save_and_load_round_trip(self, tmp_path, sample_context):
        path = tmp_path / "ctx.yaml"
        save_context(sample_context, path)
        loaded = load_context(path)

        assert loaded.target_level == "L2"
        assert "staging" in loaded.excluded_schemas
        assert "analytics.customers.email" in loaded.known_pii_columns
        assert loaded.freshness_slas["analytics.orders"] == 2
        assert loaded.table_criticality["analytics.orders"] == "critical"
        assert loaded.has_dbt is False

    def test_load_nonexistent_returns_default(self, tmp_path):
        ctx = load_context(tmp_path / "does_not_exist.yaml")
        assert ctx.target_level is None
        assert ctx.excluded_schemas == []

    def test_creates_parent_directories(self, tmp_path):
        path = tmp_path / "deep" / "nested" / "dir" / "ctx.yaml"
        save_context(UserContext(target_level="L3"), path)
        assert path.exists()

    def test_overwrite_existing(self, tmp_path):
        path = tmp_path / "ctx.yaml"
        save_context(UserContext(target_level="L1"), path)
        save_context(UserContext(target_level="L3"), path)
        loaded = load_context(path)
        assert loaded.target_level == "L3"

    def test_merge_and_save(self, tmp_path):
        path = tmp_path / "ctx.yaml"
        saved = UserContext(target_level="L1", excluded_schemas=["staging"])
        interactive = UserContext(target_level="L2", excluded_schemas=["_scratch"])
        merged = merge_context(saved, interactive)
        save_context(merged, path)
        loaded = load_context(path)
        assert loaded.target_level == "L2"
        assert "staging" in loaded.excluded_schemas
        assert "_scratch" in loaded.excluded_schemas


class TestConnectionPathMapping:

    def test_consistent_paths(self):
        p1 = context_path_for_connection("duckdb://test.db")
        p2 = context_path_for_connection("duckdb://test.db")
        assert p1 == p2

    def test_different_connections_different_paths(self):
        p1 = context_path_for_connection("duckdb://db1.db")
        p2 = context_path_for_connection("duckdb://db2.db")
        assert p1 != p2

    def test_credentials_stripped_for_hash(self):
        p1 = context_path_for_connection("postgresql://user1:pass1@host/db")
        p2 = context_path_for_connection("postgresql://user2:pass2@host/db")
        assert p1 == p2

    def test_custom_context_dir(self, tmp_path):
        path = context_path_for_connection("duckdb://test.db", context_dir=tmp_path)
        assert str(tmp_path) in str(path)
        assert path.name.startswith("context-")
        assert path.suffix == ".yaml"
