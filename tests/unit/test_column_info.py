"""Tests for ColumnInfo type detection properties."""

import pytest

from agent.discover import ColumnInfo


class TestIsNumeric:

    @pytest.mark.parametrize("dtype", [
        "int", "integer", "bigint", "smallint", "tinyint",
        "float", "double", "decimal", "numeric", "real", "number", "money",
    ])
    def test_numeric_types(self, dtype):
        col = ColumnInfo(name="x", data_type=dtype, is_nullable=False, column_default=None, ordinal_position=1)
        assert col.is_numeric is True

    def test_numeric_with_precision(self):
        col = ColumnInfo(name="x", data_type="decimal(10,2)", is_nullable=False, column_default=None, ordinal_position=1)
        assert col.is_numeric is True

    @pytest.mark.parametrize("dtype", ["varchar", "text", "timestamp", "boolean", "json"])
    def test_non_numeric_types(self, dtype):
        col = ColumnInfo(name="x", data_type=dtype, is_nullable=False, column_default=None, ordinal_position=1)
        assert col.is_numeric is False


class TestIsString:

    @pytest.mark.parametrize("dtype", [
        "varchar", "char", "text", "string", "nvarchar", "nchar",
        "character varying", "character", "clob",
    ])
    def test_string_types(self, dtype):
        col = ColumnInfo(name="x", data_type=dtype, is_nullable=False, column_default=None, ordinal_position=1)
        assert col.is_string is True

    def test_varchar_with_length(self):
        col = ColumnInfo(name="x", data_type="varchar(255)", is_nullable=False, column_default=None, ordinal_position=1)
        assert col.is_string is True

    @pytest.mark.parametrize("dtype", ["int", "float", "timestamp", "boolean"])
    def test_non_string_types(self, dtype):
        col = ColumnInfo(name="x", data_type=dtype, is_nullable=False, column_default=None, ordinal_position=1)
        assert col.is_string is False


class TestIsTimestamp:

    @pytest.mark.parametrize("dtype", [
        "timestamp", "datetime", "date", "timestamptz",
        "timestamp_tz", "timestamp_ltz", "timestamp_ntz",
        "timestamp with time zone", "timestamp without time zone",
    ])
    def test_timestamp_types(self, dtype):
        col = ColumnInfo(name="x", data_type=dtype, is_nullable=False, column_default=None, ordinal_position=1)
        assert col.is_timestamp is True

    @pytest.mark.parametrize("dtype", ["varchar", "int", "boolean"])
    def test_non_timestamp_types(self, dtype):
        col = ColumnInfo(name="x", data_type=dtype, is_nullable=False, column_default=None, ordinal_position=1)
        assert col.is_timestamp is False


class TestIsCandidateKey:

    def test_primary_key_constraint(self):
        col = ColumnInfo(name="x", data_type="int", is_nullable=False, column_default=None, ordinal_position=1, constraints=["PRIMARY KEY"])
        assert col.is_candidate_key is True

    def test_unique_constraint(self):
        col = ColumnInfo(name="x", data_type="int", is_nullable=False, column_default=None, ordinal_position=1, constraints=["UNIQUE"])
        assert col.is_candidate_key is True

    def test_id_suffix(self):
        col = ColumnInfo(name="customer_id", data_type="int", is_nullable=False, column_default=None, ordinal_position=1)
        assert col.is_candidate_key is True

    def test_bare_id(self):
        col = ColumnInfo(name="id", data_type="int", is_nullable=False, column_default=None, ordinal_position=1)
        assert col.is_candidate_key is True

    def test_non_key(self):
        col = ColumnInfo(name="status", data_type="varchar", is_nullable=True, column_default=None, ordinal_position=1)
        assert col.is_candidate_key is False

    def test_name_is_case_insensitive(self):
        col = ColumnInfo(name="Customer_ID", data_type="int", is_nullable=False, column_default=None, ordinal_position=1)
        assert col.is_candidate_key is True
