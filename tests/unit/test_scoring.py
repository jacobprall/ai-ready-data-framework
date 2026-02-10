"""Tests for scoring logic: _score, _is_max_threshold, _apply_context_overrides, _get_context_annotations."""

import pytest

from agent.execute import (
    _apply_context_overrides,
    _get_context_annotations,
    _get_thresholds,
    _is_max_threshold,
    _parse_target_parts,
    _score,
)
from agent.suites.base import Test


# ---------------------------------------------------------------------------
# _is_max_threshold
# ---------------------------------------------------------------------------

class TestIsMaxThreshold:
    """Tests for _is_max_threshold, which reads direction from threshold data first,
    then falls back to the legacy hardcoded set."""

    # --- Direction from threshold data (new behavior) ---

    def test_reads_direction_max_from_data(self):
        assert _is_max_threshold("null_rate", {"direction": "max", "L1": 0.10}) is True

    def test_reads_direction_min_from_data(self):
        assert _is_max_threshold("null_rate", {"direction": "min", "L1": 0.10}) is False

    def test_direction_overrides_legacy(self):
        """Even for a metric the legacy set says is min, direction='max' wins."""
        assert _is_max_threshold("column_comment_coverage", {"direction": "max", "L1": 0.5}) is True

    # --- Legacy fallback (no direction in data) ---

    def test_null_rate_is_max(self):
        assert _is_max_threshold("null_rate") is True

    def test_duplicate_rate_is_max(self):
        assert _is_max_threshold("duplicate_rate") is True

    def test_pii_detection_rate_is_max(self):
        assert _is_max_threshold("pii_detection_rate") is True

    def test_column_comment_coverage_is_min(self):
        assert _is_max_threshold("column_comment_coverage") is False

    def test_table_comment_coverage_is_min(self):
        assert _is_max_threshold("table_comment_coverage") is False

    def test_constraint_coverage_is_min(self):
        assert _is_max_threshold("constraint_coverage") is False

    def test_rbac_coverage_is_min(self):
        assert _is_max_threshold("rbac_coverage") is False

    def test_naming_consistency_is_min(self):
        assert _is_max_threshold("naming_consistency") is False

    def test_unknown_requirement_defaults_to_max(self):
        assert _is_max_threshold("some_unknown_metric") is True


# ---------------------------------------------------------------------------
# _score
# ---------------------------------------------------------------------------

class TestScore:

    def test_max_threshold_pass(self):
        """Lower is better: 0.03 <= 0.05 -> pass."""
        result = _score(0.03, {"L1": 0.10, "L2": 0.05, "L3": 0.01}, "null_rate")
        assert result["L1"] == "pass"
        assert result["L2"] == "pass"
        assert result["L3"] == "fail"

    def test_max_threshold_exact_boundary(self):
        """Exactly at threshold -> pass."""
        result = _score(0.05, {"L1": 0.10, "L2": 0.05, "L3": 0.01}, "null_rate")
        assert result["L2"] == "pass"

    def test_max_threshold_fail(self):
        """Higher is worse: 0.25 > 0.10 -> fail."""
        result = _score(0.25, {"L1": 0.10, "L2": 0.05, "L3": 0.01}, "null_rate")
        assert result["L1"] == "fail"
        assert result["L2"] == "fail"
        assert result["L3"] == "fail"

    def test_min_threshold_pass(self):
        """Higher is better: 0.95 >= 0.90 -> pass."""
        result = _score(0.95, {"L1": 0.50, "L2": 0.90, "L3": 0.95}, "column_comment_coverage")
        assert result["L1"] == "pass"
        assert result["L2"] == "pass"
        assert result["L3"] == "pass"

    def test_min_threshold_fail(self):
        """Lower is worse: 0.40 < 0.50 -> fail."""
        result = _score(0.40, {"L1": 0.50, "L2": 0.90, "L3": 0.95}, "column_comment_coverage")
        assert result["L1"] == "fail"

    def test_min_threshold_exact_boundary(self):
        """Exactly at threshold -> pass."""
        result = _score(0.50, {"L1": 0.50, "L2": 0.90, "L3": 0.95}, "column_comment_coverage")
        assert result["L1"] == "pass"

    def test_none_threshold_skips(self):
        """None threshold at a level means skip."""
        result = _score(0.5, {"L1": None, "L2": 0.05, "L3": None}, "null_rate")
        assert result["L1"] == "skip"
        assert result["L2"] == "fail"
        assert result["L3"] == "skip"

    def test_none_measured_value_fails(self):
        """None measured value fails all applicable levels."""
        result = _score(None, {"L1": 0.10, "L2": 0.05, "L3": 0.01}, "null_rate")
        assert result["L1"] == "fail"
        assert result["L2"] == "fail"
        assert result["L3"] == "fail"

    def test_all_none_thresholds(self):
        result = _score(0.5, {"L1": None, "L2": None, "L3": None}, "null_rate")
        assert all(v == "skip" for v in result.values())

    def test_zero_measured_value(self):
        """0.0 is a valid measured value, not None."""
        result = _score(0.0, {"L1": 0.10, "L2": 0.05, "L3": 0.01}, "null_rate")
        assert result["L1"] == "pass"
        assert result["L2"] == "pass"
        assert result["L3"] == "pass"


# ---------------------------------------------------------------------------
# _get_thresholds
# ---------------------------------------------------------------------------

class TestGetThresholds:

    def test_existing_requirement(self, sample_thresholds):
        result = _get_thresholds(sample_thresholds, "clean", "null_rate")
        assert result["L1"] == 0.10
        assert result["L2"] == 0.05
        assert result["L3"] == 0.01

    def test_preserves_direction(self, sample_thresholds):
        result = _get_thresholds(sample_thresholds, "clean", "null_rate")
        assert result.get("direction") == "max"

    def test_preserves_min_direction(self, sample_thresholds):
        result = _get_thresholds(sample_thresholds, "contextual", "column_comment_coverage")
        assert result.get("direction") == "min"

    def test_missing_factor(self, sample_thresholds):
        result = _get_thresholds(sample_thresholds, "nonexistent", "null_rate")
        assert result == {"L1": None, "L2": None, "L3": None}

    def test_missing_requirement(self, sample_thresholds):
        result = _get_thresholds(sample_thresholds, "clean", "nonexistent")
        assert result == {"L1": None, "L2": None, "L3": None}


# ---------------------------------------------------------------------------
# _parse_target_parts
# ---------------------------------------------------------------------------

class TestParseTargetParts:

    def test_three_parts(self):
        assert _parse_target_parts("schema.table.column") == ("schema", "table", "column")

    def test_two_parts(self):
        assert _parse_target_parts("schema.table") == ("schema", "table", "")

    def test_one_part(self):
        assert _parse_target_parts("database") == ("", "", "")

    def test_four_parts(self):
        assert _parse_target_parts("a.b.c.d") == ("a", "b", "c")


# ---------------------------------------------------------------------------
# _apply_context_overrides
# ---------------------------------------------------------------------------

class TestApplyContextOverrides:

    def _make_test(self, requirement: str) -> Test:
        return Test(
            name="test", factor="clean", requirement=requirement,
            query="SELECT 1", target_type="column", platform="common",
        )

    def test_nullable_by_design_relaxes_null_rate(self, sample_context):
        test = self._make_test("null_rate")
        original = {"L1": 0.10, "L2": 0.05, "L3": 0.01}
        result = _apply_context_overrides(original, test, "analytics.customers.middle_name", sample_context)
        assert result["L1"] == 1.0
        assert result["L2"] == 1.0
        assert result["L3"] == 0.50

    def test_non_nullable_column_unchanged(self, sample_context):
        test = self._make_test("null_rate")
        original = {"L1": 0.10, "L2": 0.05, "L3": 0.01}
        result = _apply_context_overrides(original, test, "analytics.orders.customer_id", sample_context)
        assert result == original

    def test_false_positive_pii_skips(self, sample_context):
        test = self._make_test("pii_column_name_rate")
        original = {"L1": None, "L2": 0.0, "L3": 0.0}
        result = _apply_context_overrides(original, test, "analytics.orders.status", sample_context)
        assert result == {"L1": None, "L2": None, "L3": None}

    def test_freshness_sla_override(self, sample_context):
        test = self._make_test("max_staleness_hours")
        original = {"L1": 168, "L2": 24, "L3": 6}
        result = _apply_context_overrides(original, test, "analytics.orders.updated_at", sample_context)
        assert result == {"L1": 2.0, "L2": 2.0, "L3": 2.0}

    def test_no_sla_leaves_unchanged(self, sample_context):
        test = self._make_test("max_staleness_hours")
        original = {"L1": 168, "L2": 24, "L3": 6}
        result = _apply_context_overrides(original, test, "analytics.events.created_at", sample_context)
        assert result == original

    def test_does_not_mutate_original(self, sample_context):
        test = self._make_test("null_rate")
        original = {"L1": 0.10, "L2": 0.05, "L3": 0.01}
        original_copy = dict(original)
        _apply_context_overrides(original, test, "analytics.customers.middle_name", sample_context)
        assert original == original_copy


# ---------------------------------------------------------------------------
# _get_context_annotations
# ---------------------------------------------------------------------------

class TestGetContextAnnotations:

    def _make_test(self, requirement: str) -> Test:
        return Test(
            name="test", factor="clean", requirement=requirement,
            query="SELECT 1", target_type="column", platform="common",
        )

    def test_nullable_by_design(self, sample_context):
        test = self._make_test("null_rate")
        annotations = _get_context_annotations(test, "analytics.customers.middle_name", sample_context)
        assert "nullable by design" in annotations

    def test_confirmed_pii(self, sample_context):
        test = self._make_test("pii_detection_rate")
        annotations = _get_context_annotations(test, "analytics.customers.email", sample_context)
        assert "confirmed PII" in annotations

    def test_confirmed_not_pii(self, sample_context):
        test = self._make_test("pii_column_name_rate")
        annotations = _get_context_annotations(test, "analytics.orders.status", sample_context)
        assert "confirmed not PII" in annotations

    def test_custom_sla(self, sample_context):
        test = self._make_test("max_staleness_hours")
        annotations = _get_context_annotations(test, "analytics.orders.updated_at", sample_context)
        assert "custom SLA: 2h" in annotations

    def test_critical_table(self, sample_context):
        test = self._make_test("null_rate")
        annotations = _get_context_annotations(test, "analytics.orders.customer_id", sample_context)
        assert "critical table" in annotations

    def test_previously_accepted(self, sample_context):
        test = self._make_test("null_rate")
        annotations = _get_context_annotations(test, "analytics.customers.middle_name", sample_context)
        assert "previously accepted" in annotations

    def test_no_annotations_without_context_match(self, sample_context):
        test = self._make_test("null_rate")
        annotations = _get_context_annotations(test, "analytics.events.event_id", sample_context)
        assert annotations == []
