"""Test suites for the AI-Ready Data Assessment Agent.

Each suite is a complete, self-contained set of tests that covers all five factors
using a specific platform's native capabilities. The common suite provides the
ANSI SQL baseline. Platform suites extend and override common tests with deeper,
platform-native assessments.

Usage:
    from agent.suites import get_suite

    suite = get_suite("snowflake")  # Returns SnowflakeSuite
    suite = get_suite("auto", conn) # Auto-detects from connection
"""

from __future__ import annotations

import importlib
from typing import Any

from agent.platforms import detect_platform, get_platform, list_platforms
from agent.suites.base import Suite
from agent.suites.common import CommonSuite


# Registry of platform suites -- can be extended at runtime
_REGISTRY: dict[str, type[Suite]] = {
    "common": CommonSuite,
}


def register_suite(platform: str, suite_cls: type[Suite]) -> None:
    """Register a platform suite."""
    _REGISTRY[platform] = suite_cls


def get_suite(platform: str, conn: Any | None = None) -> Suite:
    """Get a suite by platform name or auto-detect from connection.

    Args:
        platform: Platform name ("snowflake", "duckdb", "auto", "common") or any community-registered name.
        conn: DB-API 2.0 connection for auto-detection.

    Returns:
        An instantiated Suite.
    """
    if platform == "auto" and conn is not None:
        # Use the centralized detection from agent.platforms
        platform = detect_platform(conn)

    # Check local registry first (explicitly registered suites)
    if platform in _REGISTRY:
        return _REGISTRY[platform]()

    # Try lazy-loading from platform registry
    plat = get_platform(platform)
    if plat and plat.suite_class:
        suite_cls = _import_suite_class(plat.suite_class)
        _REGISTRY[platform] = suite_cls
        return suite_cls()

    # Fall back to common if no suite exists for this platform
    return CommonSuite()


def list_suites() -> list[str]:
    """List all registered suite names."""
    # Merge explicit registry with platform registry
    names = set(_REGISTRY.keys())
    for name in list_platforms():
        plat = get_platform(name)
        if plat and plat.suite_class:
            names.add(name)
    return sorted(names)


def _import_suite_class(dotted_path: str) -> type[Suite]:
    """Import a suite class from a dotted path like 'agent.suites.snowflake:SnowflakeSuite'."""
    module_path, class_name = dotted_path.rsplit(":", 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)
