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


class TestInclusionScoping:
    """Tests for the inclusion-first scoping model."""

    def test_default_scope_mode_includes_all(self):
        ctx = UserContext()
        assert ctx.is_table_included("any", "table") is True
        assert ctx.is_table_excluded("any", "table") is False

    def test_include_mode_filters_to_listed_tables(self):
        ctx = UserContext(
            scope_mode="include",
            included_tables=["analytics.orders", "analytics.customers"],
        )
        assert ctx.is_table_included("analytics", "orders") is True
        assert ctx.is_table_included("analytics", "customers") is True
        assert ctx.is_table_included("analytics", "events") is False

    def test_include_mode_excluded_means_not_in_list(self):
        ctx = UserContext(
            scope_mode="include",
            included_tables=["analytics.orders"],
        )
        # events is not in the inclusion list, so it's excluded
        assert ctx.is_table_excluded("analytics", "events") is True
        # orders IS in the list, so it's not excluded
        assert ctx.is_table_excluded("analytics", "orders") is False

    def test_include_mode_exclusions_still_apply(self):
        """Even in include mode, explicit exclusions take precedence."""
        ctx = UserContext(
            scope_mode="include",
            included_tables=["analytics.orders", "analytics.debug"],
            excluded_tables=["analytics.debug"],
        )
        assert ctx.is_table_excluded("analytics", "orders") is False
        assert ctx.is_table_excluded("analytics", "debug") is True  # excluded wins

    def test_include_mode_schema_exclusion_still_applies(self):
        ctx = UserContext(
            scope_mode="include",
            included_tables=["staging.temp_orders"],
            excluded_schemas=["staging"],
        )
        assert ctx.is_table_excluded("staging", "temp_orders") is True  # schema excluded

    def test_include_mode_case_insensitive(self):
        ctx = UserContext(
            scope_mode="include",
            included_tables=["Analytics.Orders"],
        )
        assert ctx.is_table_included("analytics", "orders") is True

    def test_include_mode_empty_list_includes_all(self):
        """If scope_mode is 'include' but list is empty, include everything."""
        ctx = UserContext(scope_mode="include", included_tables=[])
        assert ctx.is_table_included("analytics", "anything") is True

    def test_all_mode_ignores_included_tables(self):
        """In 'all' mode, included_tables is ignored."""
        ctx = UserContext(
            scope_mode="all",
            included_tables=["analytics.orders"],
        )
        assert ctx.is_table_included("analytics", "events") is True

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

    def test_infrastructure_set_union(self):
        saved = UserContext(infrastructure={"dbt", "catalog"})
        interactive = UserContext(infrastructure={"otel"})
        merged = merge_context(saved, interactive)
        assert merged.infrastructure == {"dbt", "catalog", "otel"}

    def test_merge_included_tables_unioned(self):
        saved = UserContext(scope_mode="include", included_tables=["analytics.orders"])
        interactive = UserContext(scope_mode="include", included_tables=["ml.features"])
        merged = merge_context(saved, interactive)
        assert "analytics.orders" in merged.included_tables
        assert "ml.features" in merged.included_tables
        assert merged.scope_mode == "include"

    def test_merge_scope_mode_interactive_wins_when_tables_provided(self):
        saved = UserContext(scope_mode="all")
        interactive = UserContext(scope_mode="include", included_tables=["analytics.orders"])
        merged = merge_context(saved, interactive)
        assert merged.scope_mode == "include"

    def test_merge_scope_mode_saved_when_no_interactive_tables(self):
        saved = UserContext(scope_mode="include", included_tables=["analytics.orders"])
        interactive = UserContext()
        merged = merge_context(saved, interactive)
        assert merged.scope_mode == "include"

    def test_infrastructure_backward_compat_properties(self):
        """Legacy has_dbt/has_otel properties still work."""
        ctx = UserContext(infrastructure={"dbt", "otel"})
        assert ctx.has_dbt is True
        assert ctx.has_otel is True
        assert ctx.has_catalog is False
        assert ctx.has_iceberg is False

    def test_infrastructure_setter_adds_to_set(self):
        """Legacy setters mutate the infrastructure set."""
        ctx = UserContext()
        ctx.has_dbt = True
        ctx.has_iceberg = True
        assert "dbt" in ctx.infrastructure
        assert "iceberg" in ctx.infrastructure

    def test_infrastructure_setter_removes_from_set(self):
        ctx = UserContext(infrastructure={"dbt"})
        ctx.has_dbt = False
        assert "dbt" not in ctx.infrastructure


class TestSerialization:

    def test_round_trip(self, sample_context):
        d = _context_to_dict(sample_context)
        restored = _dict_to_context(d)
        assert restored.target_level == sample_context.target_level
        assert restored.scope_mode == sample_context.scope_mode
        assert restored.included_tables == sample_context.included_tables
        assert restored.excluded_schemas == sample_context.excluded_schemas
        assert restored.known_pii_columns == sample_context.known_pii_columns
        assert restored.freshness_slas == sample_context.freshness_slas
        assert restored.table_criticality == sample_context.table_criticality
        assert restored.infrastructure == sample_context.infrastructure
        assert restored.accepted_failures == sample_context.accepted_failures

    def test_round_trip_inclusion_mode(self):
        ctx = UserContext(
            scope_mode="include",
            included_tables=["analytics.orders", "ml.features"],
        )
        d = _context_to_dict(ctx)
        restored = _dict_to_context(d)
        assert restored.scope_mode == "include"
        assert restored.included_tables == ["analytics.orders", "ml.features"]

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
        assert ctx.infrastructure == set()

    def test_dict_to_context_handles_empty_dict(self):
        ctx = _dict_to_context({})
        assert ctx.target_level is None

    def test_dict_to_context_legacy_booleans(self):
        """Old YAML with has_dbt/has_otel booleans migrates to infrastructure set."""
        d = {"has_dbt": True, "has_otel": True, "has_catalog": False, "has_iceberg": False}
        ctx = _dict_to_context(d)
        assert ctx.infrastructure == {"dbt", "otel"}
        assert ctx.has_dbt is True
        assert ctx.has_otel is True
        assert ctx.has_catalog is False

    def test_dict_to_context_new_infrastructure_list(self):
        """New YAML with infrastructure list."""
        d = {"infrastructure": ["dbt", "otel", "airflow"]}
        ctx = _dict_to_context(d)
        assert ctx.infrastructure == {"dbt", "otel", "airflow"}

    def test_infrastructure_serializes_as_sorted_list(self):
        ctx = UserContext(infrastructure={"otel", "dbt", "catalog"})
        d = _context_to_dict(ctx)
        assert d["infrastructure"] == ["catalog", "dbt", "otel"]


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
