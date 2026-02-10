"""Tests for UserContext methods, merge_context, and serialization."""

import pytest

from agent.context import (
    UserContext,
    _connection_hash,
    _context_to_dict,
    _dict_to_context,
    context_path_for_connection,
    load_context,
    merge_context,
    save_context,
)


class TestUserContextLookups:

    def test_is_table_excluded_by_schema(self, sample_context):
        assert sample_context.is_table_excluded("staging", "tmp_orders") is True

    def test_is_table_excluded_by_fqn(self):
        ctx = UserContext(excluded_tables=["analytics.debug"])
        assert ctx.is_table_excluded("analytics", "debug") is True

    def test_is_table_excluded_case_insensitive(self):
        ctx = UserContext(excluded_schemas=["STAGING"])
        assert ctx.is_table_excluded("staging", "foo") is True

    def test_is_table_not_excluded(self, sample_context):
        assert sample_context.is_table_excluded("analytics", "orders") is False

    def test_is_nullable_by_design(self, sample_context):
        assert sample_context.is_nullable_by_design("analytics", "customers", "middle_name") is True

    def test_is_not_nullable_by_design(self, sample_context):
        assert sample_context.is_nullable_by_design("analytics", "orders", "customer_id") is False

    def test_is_confirmed_pii(self, sample_context):
        assert sample_context.is_confirmed_pii("analytics", "customers", "email") is True

    def test_is_not_confirmed_pii(self, sample_context):
        assert sample_context.is_confirmed_pii("analytics", "orders", "status") is False

    def test_is_false_positive_pii(self, sample_context):
        assert sample_context.is_false_positive_pii("analytics", "orders", "status") is True

    def test_is_confirmed_key(self, sample_context):
        assert sample_context.is_confirmed_key("analytics", "events", "event_id") is True

    def test_is_not_key(self, sample_context):
        assert sample_context.is_not_key("analytics", "products", "product_id") is True

    def test_get_table_criticality_critical(self, sample_context):
        assert sample_context.get_table_criticality("analytics", "orders") == "critical"

    def test_get_table_criticality_default(self, sample_context):
        assert sample_context.get_table_criticality("analytics", "events") == "standard"

    def test_get_freshness_sla(self, sample_context):
        assert sample_context.get_freshness_sla("analytics", "orders") == 2

    def test_get_freshness_sla_none(self, sample_context):
        assert sample_context.get_freshness_sla("analytics", "events") is None

    def test_is_failure_accepted(self, sample_context):
        assert sample_context.is_failure_accepted("null_rate", "analytics.customers.middle_name") is True

    def test_is_failure_not_accepted(self, sample_context):
        assert sample_context.is_failure_accepted("null_rate", "analytics.orders.customer_id") is False


class TestMergeContext:

    def test_scalar_interactive_wins(self):
        saved = UserContext(target_level="L1")
        interactive = UserContext(target_level="L2")
        merged = merge_context(saved, interactive)
        assert merged.target_level == "L2"

    def test_scalar_saved_used_when_interactive_empty(self):
        saved = UserContext(target_level="L1")
        interactive = UserContext()
        merged = merge_context(saved, interactive)
        assert merged.target_level == "L1"

    def test_lists_unioned(self):
        saved = UserContext(excluded_schemas=["staging"])
        interactive = UserContext(excluded_schemas=["_scratch"])
        merged = merge_context(saved, interactive)
        assert "staging" in merged.excluded_schemas
        assert "_scratch" in merged.excluded_schemas

    def test_lists_deduplicated(self):
        saved = UserContext(excluded_schemas=["staging"])
        interactive = UserContext(excluded_schemas=["staging", "_scratch"])
        merged = merge_context(saved, interactive)
        assert merged.excluded_schemas.count("staging") == 1

    def test_dicts_merged_interactive_wins(self):
        saved = UserContext(freshness_slas={"analytics.orders": 24})
        interactive = UserContext(freshness_slas={"analytics.orders": 2})
        merged = merge_context(saved, interactive)
        assert merged.freshness_slas["analytics.orders"] == 2

    def test_dicts_merged_both_kept(self):
        saved = UserContext(table_criticality={"analytics.orders": "critical"})
        interactive = UserContext(table_criticality={"analytics.events": "low"})
        merged = merge_context(saved, interactive)
        assert "analytics.orders" in merged.table_criticality
        assert "analytics.events" in merged.table_criticality

    def test_bool_or_logic(self):
        saved = UserContext(has_dbt=True)
        interactive = UserContext(has_dbt=False)
        merged = merge_context(saved, interactive)
        assert merged.has_dbt is True


class TestSerialization:

    def test_round_trip(self, sample_context):
        d = _context_to_dict(sample_context)
        restored = _dict_to_context(d)
        assert restored.target_level == sample_context.target_level
        assert restored.excluded_schemas == sample_context.excluded_schemas
        assert restored.known_pii_columns == sample_context.known_pii_columns
        assert restored.freshness_slas == sample_context.freshness_slas
        assert restored.table_criticality == sample_context.table_criticality
        assert restored.has_dbt == sample_context.has_dbt
        assert restored.accepted_failures == sample_context.accepted_failures

    def test_empty_context_round_trip(self, empty_context):
        d = _context_to_dict(empty_context)
        restored = _dict_to_context(d)
        assert restored.target_level is None
        assert restored.excluded_schemas == []
        assert restored.freshness_slas == {}

    def test_dict_to_context_handles_missing_keys(self):
        d = {"target_level": "L1"}
        ctx = _dict_to_context(d)
        assert ctx.target_level == "L1"
        assert ctx.excluded_schemas == []
        assert ctx.has_dbt is False

    def test_dict_to_context_handles_empty_dict(self):
        ctx = _dict_to_context({})
        assert ctx.target_level is None


class TestConnectionHash:

    def test_same_host_same_hash(self):
        h1 = _connection_hash("postgresql://user:pass@host/db")
        h2 = _connection_hash("postgresql://other:secret@host/db")
        assert h1 == h2

    def test_different_host_different_hash(self):
        h1 = _connection_hash("postgresql://user:pass@host1/db")
        h2 = _connection_hash("postgresql://user:pass@host2/db")
        assert h1 != h2

    def test_hash_length(self):
        h = _connection_hash("postgresql://user:pass@host/db")
        assert len(h) == 12


class TestContextFileIO:

    def test_save_and_load(self, tmp_path, sample_context):
        path = tmp_path / "ctx.yaml"
        save_context(sample_context, path)
        loaded = load_context(path)
        assert loaded.target_level == sample_context.target_level
        assert loaded.excluded_schemas == sample_context.excluded_schemas
        assert loaded.freshness_slas == sample_context.freshness_slas

    def test_load_nonexistent_returns_default(self, tmp_path):
        path = tmp_path / "nonexistent.yaml"
        ctx = load_context(path)
        assert ctx.target_level is None
        assert ctx.excluded_schemas == []

    def test_save_creates_parent_dirs(self, tmp_path):
        path = tmp_path / "deep" / "nested" / "ctx.yaml"
        save_context(UserContext(target_level="L3"), path)
        assert path.exists()
        loaded = load_context(path)
        assert loaded.target_level == "L3"
