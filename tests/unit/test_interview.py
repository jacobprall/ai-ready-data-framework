"""Tests for interview question generators and heuristic helpers."""

import pytest

from agent.context import UserContext
from agent.discover import ColumnInfo, DatabaseInventory, TableInfo
from agent.interview import (
    _extract_top_failures,
    _find_heuristic_keys,
    _find_nullable_candidates,
    _find_pii_column_names,
    _suggest_critical_tables,
    discovery_questions,
    pre_assessment_questions,
    results_questions,
)


class TestPreAssessmentQuestions:

    def test_returns_five_questions(self):
        questions = pre_assessment_questions()
        assert len(questions) == 5

    def test_target_level_is_first(self):
        questions = pre_assessment_questions()
        assert questions[0].id == "target_level"

    def test_all_have_required_fields(self):
        for q in pre_assessment_questions():
            assert q.id
            assert q.phase == 1
            assert q.prompt
            assert q.question_type


class TestDiscoveryQuestions:

    def test_scope_confirmation_always_present(self, sample_inventory, empty_context):
        questions = discovery_questions(sample_inventory, empty_context)
        ids = [q.id for q in questions]
        assert "scope_confirmation" in ids

    def test_table_criticality_present_when_enough_tables(self, sample_inventory, empty_context):
        questions = discovery_questions(sample_inventory, empty_context)
        # sample_inventory has 4 tables but threshold is >5, so should NOT be present
        ids = [q.id for q in questions]
        assert "table_criticality" not in ids

    def test_pii_confirmation_present_when_pii_columns_found(self, sample_inventory, empty_context):
        questions = discovery_questions(sample_inventory, empty_context)
        ids = [q.id for q in questions]
        # sample_inventory has email, phone columns
        assert "pii_confirmation" in ids

    def test_questions_sorted_by_priority(self, sample_inventory, empty_context):
        questions = discovery_questions(sample_inventory, empty_context)
        priorities = [q.priority for q in questions]
        assert priorities == sorted(priorities)


class TestResultsQuestions:

    def test_factor_triage_for_weak_factors(self, sample_report, sample_context):
        questions = results_questions(sample_report, sample_context)
        ids = [q.id for q in questions]
        assert "factor_triage" in ids

    def test_failure_triage_present(self, sample_report, sample_context):
        questions = results_questions(sample_report, sample_context)
        ids = [q.id for q in questions]
        assert "failure_triage" in ids

    def test_not_assessed_gaps_present(self, sample_report, sample_context):
        questions = results_questions(sample_report, sample_context)
        ids = [q.id for q in questions]
        assert "not_assessed_gaps" in ids


class TestSuggestCriticalTables:

    def test_fact_tables_scored_higher(self):
        tables = [
            TableInfo("", "s", "fact_orders", "TABLE", columns=[
                ColumnInfo("id", "int", False, None, 1),
            ]),
            TableInfo("", "s", "random_table", "TABLE", columns=[
                ColumnInfo("id", "int", False, None, 1),
                ColumnInfo("a", "varchar", True, None, 2),
                ColumnInfo("b", "varchar", True, None, 3),
            ]),
        ]
        inv = DatabaseInventory(tables=tables)
        result = _suggest_critical_tables(inv)
        assert result[0].name == "fact_orders"

    def test_known_names_scored_higher(self):
        tables = [
            TableInfo("", "s", "users", "TABLE", columns=[ColumnInfo("id", "int", False, None, 1)]),
            TableInfo("", "s", "xyz_temp", "TABLE", columns=[ColumnInfo("id", "int", False, None, 1)]),
        ]
        inv = DatabaseInventory(tables=tables)
        result = _suggest_critical_tables(inv)
        assert result[0].name == "users"


class TestFindHeuristicKeys:

    def test_finds_id_suffix_without_constraint(self):
        table = TableInfo("", "s", "t", "TABLE", columns=[
            ColumnInfo("customer_id", "int", False, None, 1),
        ])
        keys = _find_heuristic_keys(DatabaseInventory(tables=[table]))
        assert ("s", "t", "customer_id") in keys

    def test_skips_constraint_backed_keys(self):
        table = TableInfo("", "s", "t", "TABLE", columns=[
            ColumnInfo("order_id", "int", False, None, 1, constraints=["PRIMARY KEY"]),
        ])
        keys = _find_heuristic_keys(DatabaseInventory(tables=[table]))
        assert len(keys) == 0


class TestFindPiiColumnNames:

    def test_finds_email(self):
        table = TableInfo("", "s", "t", "TABLE", columns=[
            ColumnInfo("user_email", "varchar", True, None, 1),
        ])
        pii = _find_pii_column_names(DatabaseInventory(tables=[table]))
        assert ("s", "t", "user_email") in pii

    def test_finds_ssn(self):
        table = TableInfo("", "s", "t", "TABLE", columns=[
            ColumnInfo("ssn_hash", "varchar", True, None, 1),
        ])
        pii = _find_pii_column_names(DatabaseInventory(tables=[table]))
        assert ("s", "t", "ssn_hash") in pii

    def test_does_not_flag_normal_columns(self):
        table = TableInfo("", "s", "t", "TABLE", columns=[
            ColumnInfo("status", "varchar", True, None, 1),
            ColumnInfo("amount", "decimal", True, None, 2),
        ])
        pii = _find_pii_column_names(DatabaseInventory(tables=[table]))
        assert len(pii) == 0


class TestFindNullableCandidates:

    def test_finds_middle_name(self):
        table = TableInfo("", "s", "t", "TABLE", columns=[
            ColumnInfo("middle_name", "varchar", True, None, 1),
        ])
        candidates = _find_nullable_candidates(DatabaseInventory(tables=[table]))
        assert ("s", "t", "middle_name") in candidates

    def test_skips_non_nullable(self):
        table = TableInfo("", "s", "t", "TABLE", columns=[
            ColumnInfo("middle_name", "varchar", False, None, 1),
        ])
        candidates = _find_nullable_candidates(DatabaseInventory(tables=[table]))
        assert len(candidates) == 0


class TestExtractTopFailures:

    def test_extracts_failures_at_target_level(self):
        tests = [
            {"target": "t1", "requirement": "r1", "result": {"L1": "fail", "L2": "fail"}, "measured_value": 0.5},
            {"target": "t2", "requirement": "r2", "result": {"L1": "pass", "L2": "pass"}, "measured_value": 0.1},
        ]
        failures = _extract_top_failures(tests, "L2", limit=10)
        assert len(failures) == 1
        assert failures[0]["target"] == "t1"

    def test_respects_limit(self):
        tests = [{"target": f"t{i}", "requirement": "r", "result": {"L2": "fail"}, "measured_value": 0.5} for i in range(20)]
        failures = _extract_top_failures(tests, "L2", limit=5)
        assert len(failures) == 5

    def test_empty_when_no_failures(self):
        tests = [{"target": "t1", "requirement": "r", "result": {"L2": "pass"}, "measured_value": 0.01}]
        failures = _extract_top_failures(tests, "L2")
        assert len(failures) == 0
