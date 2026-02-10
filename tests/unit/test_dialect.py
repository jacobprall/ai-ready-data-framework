"""Tests for the SQL dialect layer on CommonSuite.

Verifies that dialect properties (quote, cast_float, regex_match, epoch_diff)
are used in generated SQL and can be overridden by subclasses.
"""

import pytest

from agent.discover import ColumnInfo, DatabaseInventory, TableInfo
from agent.suites.common import CommonSuite


class TestDialectDefaults:

    def test_default_quote(self):
        suite = CommonSuite()
        assert suite.quote == '"'

    def test_default_cast_float(self):
        suite = CommonSuite()
        assert suite.cast_float == "FLOAT"

    def test_default_regex_match(self):
        suite = CommonSuite()
        result = suite.regex_match('"col"', '[0-9]+')
        assert "SIMILAR TO" in result
        assert '"col"' in result

    def test_default_epoch_diff(self):
        suite = CommonSuite()
        result = suite.epoch_diff("CURRENT_TIMESTAMP", 'MAX("ts")')
        assert "EXTRACT(EPOCH FROM" in result


class TestQuoteHelper:

    def test_single_identifier(self):
        suite = CommonSuite()
        assert suite._q("schema") == '"schema"'

    def test_two_identifiers(self):
        suite = CommonSuite()
        assert suite._q("schema", "table") == '"schema"."table"'

    def test_three_identifiers(self):
        suite = CommonSuite()
        assert suite._q("s", "t", "c") == '"s"."t"."c"'


class _MockMySQLSuite(CommonSuite):
    """Mock MySQL suite to test dialect overriding."""

    @property
    def platform(self) -> str:
        return "mysql"

    @property
    def quote(self) -> str:
        return '`'

    @property
    def cast_float(self) -> str:
        return 'DOUBLE'

    def regex_match(self, column: str, pattern: str) -> str:
        return f"{column} REGEXP '{pattern}'"

    def epoch_diff(self, ts1: str, ts2: str) -> str:
        return f"TIMESTAMPDIFF(SECOND, {ts2}, {ts1})"


class TestDialectOverride:

    def test_mysql_quote(self):
        suite = _MockMySQLSuite()
        assert suite.quote == '`'
        assert suite._q("schema", "table") == '`schema`.`table`'

    def test_mysql_cast_float(self):
        suite = _MockMySQLSuite()
        assert suite.cast_float == 'DOUBLE'

    def test_mysql_regex_match(self):
        suite = _MockMySQLSuite()
        result = suite.regex_match('`col`', '[0-9]+')
        assert "REGEXP" in result
        assert "SIMILAR TO" not in result

    def test_mysql_epoch_diff(self):
        suite = _MockMySQLSuite()
        result = suite.epoch_diff("CURRENT_TIMESTAMP", 'MAX(`ts`)')
        assert "TIMESTAMPDIFF" in result
        assert "EXTRACT" not in result


class TestDialectInGeneratedSQL:
    """Verify that generated SQL actually uses the dialect properties."""

    @pytest.fixture
    def table(self):
        return TableInfo(
            catalog="main",
            schema="analytics",
            name="orders",
            table_type="BASE TABLE",
            columns=[
                ColumnInfo(name="order_id", data_type="integer", is_nullable=False, column_default=None, ordinal_position=1, constraints=["PRIMARY KEY"]),
                ColumnInfo(name="email", data_type="varchar", is_nullable=True, column_default=None, ordinal_position=2),
                ColumnInfo(name="total", data_type="float", is_nullable=False, column_default=None, ordinal_position=3),
                ColumnInfo(name="created_at", data_type="timestamp", is_nullable=False, column_default=None, ordinal_position=4),
            ],
        )

    @pytest.fixture
    def inventory(self, table):
        return DatabaseInventory(
            tables=[table],
            available_providers=["ansi-sql"],
            unavailable_providers=[],
        )

    def test_null_rate_uses_quote(self, table):
        suite = CommonSuite()
        tests = suite.column_tests(table, table.columns[0])
        null_test = [t for t in tests if t.name == "null_rate"][0]
        # Should use double-quote identifiers
        assert '"order_id"' in null_test.sql
        assert '"analytics"."orders"' in null_test.sql

    def test_null_rate_uses_cast_float(self, table):
        suite = CommonSuite()
        tests = suite.column_tests(table, table.columns[0])
        null_test = [t for t in tests if t.name == "null_rate"][0]
        assert "AS FLOAT" in null_test.sql

    def test_pii_scan_uses_regex_match(self, table):
        suite = CommonSuite()
        # email column is string
        tests = suite.column_tests(table, table.columns[1])
        pii_test = [t for t in tests if t.name == "pii_pattern_scan"][0]
        assert "SIMILAR TO" in pii_test.sql

    def test_freshness_uses_epoch_diff(self, table):
        suite = CommonSuite()
        # created_at is timestamp
        tests = suite.column_tests(table, table.columns[3])
        freshness_test = [t for t in tests if t.name == "table_freshness"][0]
        assert "EXTRACT(EPOCH FROM" in freshness_test.sql

    def test_mysql_suite_uses_backtick_quotes(self, table):
        suite = _MockMySQLSuite()
        tests = suite.column_tests(table, table.columns[0])
        null_test = [t for t in tests if t.name == "null_rate"][0]
        assert '`order_id`' in null_test.sql
        assert '`analytics`.`orders`' in null_test.sql

    def test_mysql_suite_uses_double_cast(self, table):
        suite = _MockMySQLSuite()
        tests = suite.column_tests(table, table.columns[0])
        null_test = [t for t in tests if t.name == "null_rate"][0]
        assert "AS DOUBLE" in null_test.sql

    def test_mysql_suite_uses_regexp(self, table):
        suite = _MockMySQLSuite()
        tests = suite.column_tests(table, table.columns[1])
        pii_test = [t for t in tests if t.name == "pii_pattern_scan"][0]
        assert "REGEXP" in pii_test.sql
        assert "SIMILAR TO" not in pii_test.sql

    def test_mysql_suite_uses_timestampdiff(self, table):
        suite = _MockMySQLSuite()
        tests = suite.column_tests(table, table.columns[3])
        freshness_test = [t for t in tests if t.name == "table_freshness"][0]
        assert "TIMESTAMPDIFF" in freshness_test.sql

    def test_database_tests_use_cast_float(self, inventory):
        suite = CommonSuite()
        tests = suite.database_tests(inventory)
        for test in tests:
            assert "AS FLOAT" in test.sql

    def test_mysql_database_tests_use_double(self, inventory):
        suite = _MockMySQLSuite()
        tests = suite.database_tests(inventory)
        for test in tests:
            assert "AS DOUBLE" in test.sql
