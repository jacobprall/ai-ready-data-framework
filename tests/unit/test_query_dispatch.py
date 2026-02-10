"""Tests for query type dispatch in the executor.

Verifies that:
- SQL queries use the default DB-API 2.0 path
- Custom query handlers can be registered and dispatched
- Unknown query types produce clear errors
- The Test dataclass supports query_type correctly
"""

import pytest

from agent.execute import register_query_handler, execute_test, load_thresholds, _QUERY_HANDLERS
from agent.suites.base import Test


@pytest.fixture
def thresholds():
    return load_thresholds()


class TestTestDataclass:

    def test_default_query_type(self):
        t = Test(name="t", factor="clean", requirement="null_rate",
                 query="SELECT 1", target_type="column")
        assert t.query_type == "sql"

    def test_custom_query_type(self):
        t = Test(name="t", factor="clean", requirement="null_rate",
                 query='{"$match": {}}', target_type="collection",
                 query_type="mongo_agg")
        assert t.query_type == "mongo_agg"
        assert t.query == '{"$match": {}}'

    def test_sql_backward_compat_property(self):
        """The .sql property returns the same value as .query."""
        t = Test(name="t", factor="clean", requirement="null_rate",
                 query="SELECT 1", target_type="column")
        assert t.sql == "SELECT 1"
        assert t.sql == t.query

    def test_target_type_collection(self):
        """Non-SQL platforms can use 'collection' as target_type."""
        t = Test(name="t", factor="clean", requirement="null_rate",
                 query="{}", target_type="collection",
                 query_type="mongo_agg")
        assert t.target_type == "collection"


class TestRegisterQueryHandler:

    def test_register_handler(self):
        def dummy_handler(conn, query):
            return 0.42

        register_query_handler("test_dummy", dummy_handler)
        assert "test_dummy" in _QUERY_HANDLERS
        assert _QUERY_HANDLERS["test_dummy"] is dummy_handler

    def test_handler_called_on_dispatch(self, thresholds):
        """A registered handler is called when query_type matches."""
        call_log = []

        def tracking_handler(conn, query):
            call_log.append(query)
            return 0.75

        register_query_handler("test_tracking", tracking_handler)

        test = Test(
            name="custom_test", factor="clean", requirement="null_rate",
            query="custom query payload",
            target_type="column", query_type="test_tracking",
            platform="test_platform",
        )

        # conn is unused by custom handler, pass None
        result = execute_test(None, test, thresholds)
        assert len(call_log) == 1
        assert call_log[0] == "custom query payload"
        assert result.measured_value == 0.75

    def test_handler_returning_none(self, thresholds):
        """Handler returning None produces 'No data returned'."""
        register_query_handler("test_none", lambda conn, q: None)

        test = Test(
            name="null_test", factor="clean", requirement="null_rate",
            query="ignored", target_type="column",
            query_type="test_none", platform="test",
        )
        result = execute_test(None, test, thresholds)
        assert result.measured_value is None
        assert "No data returned" in result.detail

    def test_handler_raising_exception(self, thresholds):
        """Handler exceptions produce error results."""
        def failing_handler(conn, query):
            raise RuntimeError("connection refused")

        register_query_handler("test_fail", failing_handler)

        test = Test(
            name="fail_test", factor="clean", requirement="null_rate",
            query="ignored", target_type="column",
            query_type="test_fail", platform="test",
        )
        result = execute_test(None, test, thresholds)
        assert "Query failed" in result.detail
        assert "connection refused" in result.detail


class TestUnknownQueryType:

    def test_unknown_query_type_error(self, thresholds):
        """Unknown query_type produces a clear error message."""
        test = Test(
            name="unknown_test", factor="clean", requirement="null_rate",
            query="some payload", target_type="column",
            query_type="unknown_lang", platform="test",
        )
        result = execute_test(None, test, thresholds)
        assert "Query failed" in result.detail
        assert "No handler registered" in result.detail
        assert "unknown_lang" in result.detail


class TestSQLDefaultHandler:

    def test_sql_handler_used_by_default(self, duckdb_conn, thresholds):
        """Default SQL path works for query_type='sql'."""
        test = Test(
            name="sql_test", factor="clean", requirement="null_rate",
            query="SELECT 0.42 AS measured_value",
            target_type="column", platform="common",
        )
        result = execute_test(duckdb_conn, test, thresholds)
        assert result.measured_value == 0.42

    def test_sql_readonly_enforced(self, duckdb_conn, thresholds):
        """SQL readonly validation still works."""
        test = Test(
            name="bad_test", factor="clean", requirement="null_rate",
            query="INSERT INTO x VALUES (1)",
            target_type="column", platform="common",
        )
        result = execute_test(duckdb_conn, test, thresholds)
        assert result.target == "error"
        assert "read-only" in result.detail.lower()
