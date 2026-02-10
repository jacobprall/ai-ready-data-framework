"""User context module: captures business context that enriches the assessment.

The assessment agent can measure structural facts about a database (null rates,
comment coverage, constraint presence) without any user input. But many
assessment decisions require domain knowledge:

    - Which columns intentionally allow nulls (nullable by design)
    - Which columns actually contain PII vs. false-positive name matches
    - Per-table freshness SLAs (some tables refresh hourly, others monthly)
    - Which tables are critical for AI workloads vs. staging/scratch
    - What the user is building toward (analytics, RAG, training)

UserContext captures this knowledge and flows through the assessment pipeline.
It is persisted per connection so users don't repeat themselves on re-runs.

Storage location: ~/.aird/contexts/ (one YAML file per connection hash).
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class UserContext:
    """Business context provided by the user to enrich the assessment.

    Every field has a sensible default so the assessment works without
    any user input (graceful degradation). Interactive mode populates
    these fields through conversation.
    """

    # What the user is building toward: "L1" (Analytics), "L2" (RAG), "L3" (Training)
    target_level: str | None = None

    # Scope mode: "all" (assess everything, then exclude) or "include" (only assess listed tables)
    scope_mode: str = "all"

    # Inclusion-first scoping: when populated, ONLY these tables are assessed.
    # Format: "schema.table" (e.g., "analytics.orders", "ml.feature_store")
    # When scope_mode is "include" and this list is non-empty, exclusions are
    # still applied on top (belt-and-suspenders).
    included_tables: list[str] = field(default_factory=list)

    # Schemas and tables to exclude from assessment
    excluded_schemas: list[str] = field(default_factory=list)
    excluded_tables: list[str] = field(default_factory=list)

    # PII context
    known_pii_columns: list[str] = field(default_factory=list)      # confirmed PII (schema.table.column)
    false_positive_pii: list[str] = field(default_factory=list)     # columns named like PII but aren't

    # Null handling
    nullable_by_design: list[str] = field(default_factory=list)     # columns where nulls are expected

    # Table importance
    table_criticality: dict[str, str] = field(default_factory=dict)  # fqn -> "critical" | "standard" | "low"

    # Per-table freshness SLAs (hours)
    freshness_slas: dict[str, int] = field(default_factory=dict)    # fqn -> max acceptable staleness hours

    # Candidate key overrides
    confirmed_keys: list[str] = field(default_factory=list)         # columns confirmed as unique keys
    not_keys: list[str] = field(default_factory=list)               # columns that look like keys but aren't

    # Infrastructure context -- set of tool names (e.g., "dbt", "catalog", "otel", "iceberg")
    infrastructure: set[str] = field(default_factory=set)

    # Free-text context
    known_issues: list[str] = field(default_factory=list)           # pain points the user already knows about
    notes: str = ""                                                 # any other context

    # Accepted failures from previous triage (requirement|target)
    accepted_failures: list[str] = field(default_factory=list)

    # Backward-compatible properties for infrastructure booleans
    @property
    def has_dbt(self) -> bool:
        return "dbt" in self.infrastructure

    @has_dbt.setter
    def has_dbt(self, value: bool) -> None:
        if value:
            self.infrastructure.add("dbt")
        else:
            self.infrastructure.discard("dbt")

    @property
    def has_catalog(self) -> bool:
        return "catalog" in self.infrastructure

    @has_catalog.setter
    def has_catalog(self, value: bool) -> None:
        if value:
            self.infrastructure.add("catalog")
        else:
            self.infrastructure.discard("catalog")

    @property
    def has_otel(self) -> bool:
        return "otel" in self.infrastructure

    @has_otel.setter
    def has_otel(self, value: bool) -> None:
        if value:
            self.infrastructure.add("otel")
        else:
            self.infrastructure.discard("otel")

    @property
    def has_iceberg(self) -> bool:
        return "iceberg" in self.infrastructure

    @has_iceberg.setter
    def has_iceberg(self, value: bool) -> None:
        if value:
            self.infrastructure.add("iceberg")
        else:
            self.infrastructure.discard("iceberg")

    def is_table_included(self, schema: str, table_name: str) -> bool:
        """Check if a table is in the inclusion list.

        When scope_mode is "include" and included_tables is non-empty, only
        tables on the inclusion list pass. When scope_mode is "all" (default),
        every table passes (inclusion is not checked).
        """
        if self.scope_mode != "include" or not self.included_tables:
            return True
        fqn = f"{schema}.{table_name}"
        return fqn.lower() in [t.lower() for t in self.included_tables]

    def is_table_excluded(self, schema: str, table_name: str) -> bool:
        """Check if a table should be excluded from assessment.

        A table is excluded if:
        1. It fails the inclusion check (scope_mode="include" and not in list), OR
        2. Its schema is in excluded_schemas, OR
        3. Its fqn is in excluded_tables

        Exclusions are always applied, even in inclusion mode.
        """
        # Inclusion check first
        if not self.is_table_included(schema, table_name):
            return True
        # Then exclusion checks
        fqn = f"{schema}.{table_name}"
        if schema.lower() in [s.lower() for s in self.excluded_schemas]:
            return True
        if fqn.lower() in [t.lower() for t in self.excluded_tables]:
            return True
        return False

    def is_nullable_by_design(self, schema: str, table: str, column: str) -> bool:
        """Check if a column is expected to have nulls."""
        fqn = f"{schema}.{table}.{column}"
        return fqn.lower() in [n.lower() for n in self.nullable_by_design]

    def is_confirmed_pii(self, schema: str, table: str, column: str) -> bool:
        """Check if a column is confirmed PII."""
        fqn = f"{schema}.{table}.{column}"
        return fqn.lower() in [p.lower() for p in self.known_pii_columns]

    def is_false_positive_pii(self, schema: str, table: str, column: str) -> bool:
        """Check if a column was flagged as PII but confirmed safe."""
        fqn = f"{schema}.{table}.{column}"
        return fqn.lower() in [p.lower() for p in self.false_positive_pii]

    def is_confirmed_key(self, schema: str, table: str, column: str) -> bool:
        """Check if a column is confirmed as a unique key."""
        fqn = f"{schema}.{table}.{column}"
        return fqn.lower() in [k.lower() for k in self.confirmed_keys]

    def is_not_key(self, schema: str, table: str, column: str) -> bool:
        """Check if a column was flagged as a key but confirmed not unique."""
        fqn = f"{schema}.{table}.{column}"
        return fqn.lower() in [k.lower() for k in self.not_keys]

    def get_table_criticality(self, schema: str, table: str) -> str:
        """Get the criticality level for a table. Defaults to 'standard'."""
        fqn = f"{schema}.{table}"
        return self.table_criticality.get(fqn, self.table_criticality.get(fqn.lower(), "standard"))

    def get_freshness_sla(self, schema: str, table: str) -> int | None:
        """Get the freshness SLA for a table in hours, or None for default."""
        fqn = f"{schema}.{table}"
        return self.freshness_slas.get(fqn, self.freshness_slas.get(fqn.lower()))

    def is_failure_accepted(self, requirement: str, target: str) -> bool:
        """Check if a specific failure was previously accepted by the user."""
        key = f"{requirement}|{target}"
        return key.lower() in [f.lower() for f in self.accepted_failures]


# ---------------------------------------------------------------------------
# Persistence (YAML)
# ---------------------------------------------------------------------------

_DEFAULT_CONTEXT_DIR = Path.home() / ".aird" / "contexts"


def _connection_hash(connection_string: str) -> str:
    """Generate a stable hash for a connection string (credentials stripped)."""
    # Strip credentials for hashing so the same DB gets the same context
    from urllib.parse import urlparse, urlunparse
    try:
        parsed = urlparse(connection_string)
        stripped = parsed._replace(netloc=parsed.hostname or "local")
        normalized = urlunparse(stripped).lower()
    except Exception:
        normalized = connection_string.lower()
    return hashlib.sha256(normalized.encode()).hexdigest()[:12]


def context_path_for_connection(connection_string: str, context_dir: Path | None = None) -> Path:
    """Get the context file path for a given connection string."""
    base_dir = context_dir or _DEFAULT_CONTEXT_DIR
    conn_hash = _connection_hash(connection_string)
    return base_dir / f"context-{conn_hash}.yaml"


def save_context(ctx: UserContext, path: Path) -> None:
    """Save a UserContext to a YAML file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _context_to_dict(ctx)
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


def load_context(path: Path) -> UserContext:
    """Load a UserContext from a YAML file. Returns default context if file doesn't exist."""
    if not path.exists():
        return UserContext()
    with open(path) as f:
        data = yaml.safe_load(f)
    if not data:
        return UserContext()
    return _dict_to_context(data)


def merge_context(saved: UserContext, interactive: UserContext) -> UserContext:
    """Merge interactive answers into a saved context.

    Interactive values take precedence. Lists are unioned (deduplicated).
    Dicts are merged with interactive values winning on conflict.
    """
    merged = UserContext()

    # Scalars: interactive wins if set
    merged.target_level = interactive.target_level or saved.target_level
    # If either context is in inclusion mode, the merged context should be too
    merged.scope_mode = interactive.scope_mode if interactive.included_tables else saved.scope_mode
    merged.infrastructure = saved.infrastructure | interactive.infrastructure
    merged.notes = interactive.notes or saved.notes

    # Lists: union and deduplicate (case-insensitive)
    list_fields = [
        "included_tables",
        "excluded_schemas", "excluded_tables", "known_pii_columns",
        "false_positive_pii", "nullable_by_design", "confirmed_keys",
        "not_keys", "known_issues", "accepted_failures",
    ]
    for field_name in list_fields:
        saved_list = getattr(saved, field_name)
        interactive_list = getattr(interactive, field_name)
        seen: set[str] = set()
        merged_list: list[str] = []
        for item in interactive_list + saved_list:
            key = item.lower()
            if key not in seen:
                seen.add(key)
                merged_list.append(item)
        setattr(merged, field_name, merged_list)

    # Dicts: merge with interactive winning
    dict_fields = ["table_criticality", "freshness_slas"]
    for field_name in dict_fields:
        saved_dict = getattr(saved, field_name)
        interactive_dict = getattr(interactive, field_name)
        merged_dict = {**saved_dict, **interactive_dict}
        setattr(merged, field_name, merged_dict)

    return merged


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------

def _context_to_dict(ctx: UserContext) -> dict[str, Any]:
    """Convert a UserContext to a plain dict for YAML serialization."""
    return {
        "target_level": ctx.target_level,
        "scope_mode": ctx.scope_mode,
        "included_tables": ctx.included_tables,
        "excluded_schemas": ctx.excluded_schemas,
        "excluded_tables": ctx.excluded_tables,
        "known_pii_columns": ctx.known_pii_columns,
        "false_positive_pii": ctx.false_positive_pii,
        "nullable_by_design": ctx.nullable_by_design,
        "table_criticality": ctx.table_criticality,
        "freshness_slas": ctx.freshness_slas,
        "confirmed_keys": ctx.confirmed_keys,
        "not_keys": ctx.not_keys,
        "infrastructure": sorted(ctx.infrastructure),
        "known_issues": ctx.known_issues,
        "notes": ctx.notes,
        "accepted_failures": ctx.accepted_failures,
    }


def _dict_to_context(data: dict[str, Any]) -> UserContext:
    """Convert a plain dict (from YAML) to a UserContext.

    Supports both the new infrastructure set format and the legacy boolean format
    (has_dbt, has_catalog, has_otel, has_iceberg) for backward compatibility.
    """
    # Build infrastructure set from new or legacy format
    infra: set[str] = set()
    if "infrastructure" in data:
        raw = data["infrastructure"]
        if isinstance(raw, (list, set)):
            infra = set(raw)
        elif isinstance(raw, dict):
            # Handle {tool: True/False} format
            infra = {k for k, v in raw.items() if v}
    else:
        # Legacy boolean format -- migrate to set
        if data.get("has_dbt", False):
            infra.add("dbt")
        if data.get("has_catalog", False):
            infra.add("catalog")
        if data.get("has_otel", False):
            infra.add("otel")
        if data.get("has_iceberg", False):
            infra.add("iceberg")

    return UserContext(
        target_level=data.get("target_level"),
        scope_mode=data.get("scope_mode", "all"),
        included_tables=data.get("included_tables", []),
        excluded_schemas=data.get("excluded_schemas", []),
        excluded_tables=data.get("excluded_tables", []),
        known_pii_columns=data.get("known_pii_columns", []),
        false_positive_pii=data.get("false_positive_pii", []),
        nullable_by_design=data.get("nullable_by_design", []),
        table_criticality=data.get("table_criticality", {}),
        freshness_slas=data.get("freshness_slas", {}),
        confirmed_keys=data.get("confirmed_keys", []),
        not_keys=data.get("not_keys", []),
        infrastructure=infra,
        known_issues=data.get("known_issues", []),
        notes=data.get("notes", ""),
        accepted_failures=data.get("accepted_failures", []),
    )
