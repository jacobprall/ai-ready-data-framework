"""Base suite class that all platform suites extend.

The Test dataclass uses `query` (not `sql`) to hold the test logic, and
`query_type` to declare the language. This allows non-SQL platforms (MongoDB,
Elasticsearch, APIs) to participate in the same framework:

    query_type="sql"         -- default; DB-API 2.0 cursor.execute(query)
    query_type="mongo_agg"   -- MongoDB aggregation pipeline (JSON)
    query_type="python"      -- a Python callable name (for API-based sources)

SQL suites set query_type="sql" implicitly (it's the default).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from agent.discover import ColumnInfo, DatabaseInventory, TableInfo


@dataclass
class Test:
    """A single test definition within a suite.

    The `query` field holds the test logic in the language declared by
    `query_type`. For SQL platforms this is a SELECT statement. For MongoDB
    it would be a JSON aggregation pipeline. For API-based sources it could
    be a Python callable reference.
    """
    name: str                    # Unique test name within the suite
    factor: str                  # clean, contextual, consumable, current, correlated, compliant
    requirement: str             # Requirement key matching thresholds-default.json
    query: str                   # Query in the language specified by query_type
    target_type: str             # "column", "table", "collection", or "database"
    query_type: str = "sql"      # "sql", "mongo_agg", "python", etc.
    description: str = ""
    platform: str = "common"     # Which platform this test is native to

    # Backward compatibility: support construction with sql= kwarg
    @property
    def sql(self) -> str:
        """Backward-compatible alias for query (SQL tests only)."""
        return self.query

    def __post_init__(self) -> None:
        # Validate query_type
        if not self.query_type:
            self.query_type = "sql"


@dataclass
class TestResult:
    """Result of a single test execution."""
    name: str
    factor: str
    requirement: str
    target: str
    platform: str
    levels: list[str]
    result: dict[str, str]
    measured_value: float | None
    thresholds: dict[str, float | None]
    detail: str
    query: str


class Suite(ABC):
    """Base class for platform test suites.

    Each suite provides a complete set of tests for all five factors using
    the platform's native capabilities. Suites can override common tests
    with platform-specific versions that provide deeper coverage.
    """

    @property
    @abstractmethod
    def platform(self) -> str:
        """Platform identifier (e.g., 'snowflake', 'databricks', 'common')."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of this suite."""
        ...

    @abstractmethod
    def database_tests(self, inventory: DatabaseInventory) -> list[Test]:
        """Tests that run once per assessment (database-level)."""
        ...

    @abstractmethod
    def table_tests(self, table: TableInfo) -> list[Test]:
        """Tests that run once per table."""
        ...

    @abstractmethod
    def column_tests(self, table: TableInfo, column: ColumnInfo) -> list[Test]:
        """Tests that run per column based on column metadata."""
        ...

    def generate_all(self, inventory: DatabaseInventory) -> list[Test]:
        """Generate all tests for the entire inventory."""
        tests: list[Test] = []

        # Database-level
        tests.extend(self.database_tests(inventory))

        # Table and column level
        for table in inventory.tables:
            tests.extend(self.table_tests(table))
            for column in table.columns:
                tests.extend(self.column_tests(table, column))

        return tests
