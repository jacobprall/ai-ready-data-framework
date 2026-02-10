"""Base suite class that all platform suites extend."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from agent.discover import ColumnInfo, DatabaseInventory, TableInfo


@dataclass
class Test:
    """A single test definition within a suite."""
    name: str                    # Unique test name within the suite
    factor: str                  # clean, contextual, consumable, current, correlated, compliant
    requirement: str             # Requirement key matching thresholds-default.json
    sql: str                     # SQL query template with {schema}, {table}, {column} placeholders
    target_type: str             # "column", "table", or "database"
    description: str = ""
    platform: str = "common"     # Which platform this test is native to


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
