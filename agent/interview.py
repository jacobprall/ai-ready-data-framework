"""Interview module: generates structured questions for the three-phase interactive flow.

The interactive assessment gathers user context at three phases:

    Phase 1 (Pre-Assessment): Before connecting -- understand the data estate,
    the user's goals, and organizational context.

    Phase 2 (Post-Discovery): After discovering tables/columns -- confirm scope,
    validate heuristic assumptions, and add business semantics.

    Phase 3 (Post-Results): After running tests -- triage failures, confirm
    accepted gaps, and prioritize remediation.

Each phase function returns a list of Question objects. These are consumed by
the agent (Cursor, ChatGPT, etc.) to drive the conversation. The agent asks
the questions, collects answers, and updates the UserContext accordingly.

The questions are agent-driven, not CLI-driven. The CLI accepts a context file;
the interactive conversation happens in the agent layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agent.context import UserContext
from agent.discover import DatabaseInventory, TableInfo


# ---------------------------------------------------------------------------
# Question data model
# ---------------------------------------------------------------------------

@dataclass
class QuestionOption:
    """A selectable option for a question."""
    value: str
    label: str
    description: str = ""


@dataclass
class Question:
    """A structured question for the user.

    The agent renders these as conversational prompts. The question type
    determines how the answer is collected and applied to the UserContext.
    """
    id: str                                     # Unique identifier (e.g., "target_level")
    phase: int                                  # 1, 2, or 3
    category: str                               # Grouping (e.g., "scope", "pii", "freshness")
    prompt: str                                 # The question text to show the user
    question_type: str                          # "single_choice", "multi_choice", "yes_no",
                                                # "free_text", "confirm_list", "table_list"
    options: list[QuestionOption] = field(default_factory=list)
    context_field: str = ""                     # Which UserContext field this updates
    priority: int = 1                           # 1 = must ask, 2 = should ask, 3 = nice to have
    condition: str = ""                         # When to ask (e.g., "tables > 20")
    data: dict[str, Any] = field(default_factory=dict)  # Extra data (e.g., detected PII columns)


# ---------------------------------------------------------------------------
# Phase 1: Pre-Assessment Interview
# ---------------------------------------------------------------------------

def pre_assessment_questions() -> list[Question]:
    """Generate questions to ask before connecting to the database.

    These establish the user's goals, data estate context, and organizational
    posture -- things that no SQL query can discover.
    """
    questions: list[Question] = []

    # 1. Target workload level
    questions.append(Question(
        id="target_level",
        phase=1,
        category="goals",
        prompt=(
            "What are you building toward with this data? This determines which "
            "readiness level I'll focus on and how I'll prioritize findings.\n\n"
            "- **L1 (Analytics):** Dashboards, BI, ad-hoc queries\n"
            "- **L2 (RAG):** Retrieval-augmented generation, semantic search, AI-powered apps\n"
            "- **L3 (Training):** Fine-tuning models, building training datasets\n"
        ),
        question_type="single_choice",
        options=[
            QuestionOption("L1", "Analytics / BI", "Dashboards, reporting, ad-hoc queries"),
            QuestionOption("L2", "RAG / AI Applications", "Semantic search, retrieval-augmented generation, AI agents"),
            QuestionOption("L3", "Model Training", "Fine-tuning, training datasets, ML pipelines"),
        ],
        context_field="target_level",
        priority=1,
    ))

    # 2. Data estate overview
    questions.append(Question(
        id="estate_overview",
        phase=1,
        category="scope",
        prompt=(
            "Tell me about your data estate. Are there schemas I should skip? "
            "Common examples: staging schemas, scratch/temp schemas, test schemas, "
            "or system schemas that aren't relevant to your AI workloads."
        ),
        question_type="free_text",
        context_field="excluded_schemas",
        priority=1,
    ))

    # 3. Infrastructure context
    questions.append(Question(
        id="infrastructure",
        phase=1,
        category="infrastructure",
        prompt=(
            "Which of these tools are part of your data stack? This helps me "
            "unlock additional assessments.\n\n"
            "- **dbt** -- I can look for dbt artifacts for lineage\n"
            "- **Data catalog** (Alation, Collibra, DataHub) -- descriptions may live outside the DB\n"
            "- **OpenTelemetry** -- I can assess pipeline freshness and reliability\n"
            "- **Iceberg** -- I can assess dataset versioning and snapshot history"
        ),
        question_type="multi_choice",
        options=[
            QuestionOption("dbt", "dbt", "dbt for transformations and lineage"),
            QuestionOption("catalog", "Data Catalog", "Alation, Collibra, DataHub, or similar"),
            QuestionOption("otel", "OpenTelemetry", "Pipeline observability with OTEL"),
            QuestionOption("iceberg", "Iceberg", "Apache Iceberg table format"),
            QuestionOption("none", "None of the above", ""),
        ],
        priority=2,
    ))

    # 4. Governance posture
    questions.append(Question(
        id="governance",
        phase=1,
        category="governance",
        prompt=(
            "Do you have a PII classification policy or know which columns contain "
            "sensitive data? I'll scan for PII patterns, but domain knowledge helps "
            "me avoid false positives and catch columns I might miss."
        ),
        question_type="yes_no",
        context_field="known_pii_columns",
        priority=2,
    ))

    # 5. Table scoping for AI workloads
    questions.append(Question(
        id="ai_table_scope",
        phase=1,
        category="scope",
        prompt=(
            "Do you want to assess your entire database, or focus on the specific "
            "tables that feed your AI systems?\n\n"
            "If you have specific tables (e.g., feature stores, embedding tables, "
            "training datasets, or the source tables that feed them), list them and "
            "I'll scope the assessment to just those. Format: `schema.table`\n\n"
            "If you're not sure, I'll assess everything and then help you identify "
            "which tables matter most after discovery."
        ),
        question_type="free_text",
        context_field="included_tables",
        priority=1,
    ))

    # 6. Known pain points
    questions.append(Question(
        id="pain_points",
        phase=1,
        category="goals",
        prompt=(
            "What prompted this assessment? Are there specific data quality issues "
            "you already know about? This helps me validate that the assessment "
            "catches known problems and prioritize the areas you care most about."
        ),
        question_type="free_text",
        context_field="known_issues",
        priority=2,
    ))

    return questions


# ---------------------------------------------------------------------------
# Phase 2: Post-Discovery Questions
# ---------------------------------------------------------------------------

def discovery_questions(inventory: DatabaseInventory, ctx: UserContext) -> list[Question]:
    """Generate questions based on what was discovered in the database.

    These are targeted questions that correct heuristic assumptions and add
    business context. Only asked when discovery reveals ambiguity.

    Args:
        inventory: The discovered database inventory.
        ctx: Current user context (may have pre-assessment answers).

    Returns:
        List of questions ordered by priority.
    """
    questions: list[Question] = []

    # 1. Scope confirmation -- show what was found
    schema_counts: dict[str, int] = {}
    for table in inventory.tables:
        schema_counts[table.schema] = schema_counts.get(table.schema, 0) + 1

    total_tables = len(inventory.tables)
    total_columns = sum(len(t.columns) for t in inventory.tables)
    schema_summary = ", ".join(f"{s} ({c} tables)" for s, c in sorted(schema_counts.items()))

    questions.append(Question(
        id="scope_confirmation",
        phase=2,
        category="scope",
        prompt=(
            f"I found **{total_tables} tables** and **{total_columns} columns** "
            f"across **{len(schema_counts)} schemas**: {schema_summary}.\n\n"
            f"Should I assess all of them, or exclude any schemas or specific tables?"
        ),
        question_type="confirm_list",
        context_field="excluded_schemas",
        priority=1,
        data={"schema_counts": schema_counts},
    ))

    # 2. AI-feeding table detection -- suggest tables that look like they feed AI systems
    ai_candidates = _detect_ai_feeding_tables(inventory)
    if ai_candidates and ctx.scope_mode != "include":
        ai_table_list = "\n".join(
            f"- `{t.fqn}` ({len(t.columns)} columns) -- {reason}"
            for t, reason in ai_candidates[:20]
        )
        questions.append(Question(
            id="ai_table_scope_discovery",
            phase=2,
            category="scope",
            prompt=(
                f"I detected **{len(ai_candidates)} tables** that look like they may feed "
                f"AI systems based on naming patterns and structure:\n\n{ai_table_list}\n\n"
                f"Would you like to:\n"
                f"- **Focus** the assessment on just these tables (faster, more relevant)\n"
                f"- **Add** other tables to this list\n"
                f"- **Assess everything** (current mode)\n\n"
                f"Focusing on AI-feeding tables gives you a much more actionable report."
            ),
            question_type="free_text",
            context_field="included_tables",
            priority=1,
            data={
                "ai_candidates": [t.fqn for t, _ in ai_candidates],
                "reasons": {t.fqn: reason for t, reason in ai_candidates},
            },
        ))

    # 3. Table criticality -- only ask if there are enough tables to matter
    if total_tables > 5:
        # Suggest tables by heuristic: larger tables (more columns) or fact/dim naming
        candidate_critical = _suggest_critical_tables(inventory)
        if candidate_critical:
            table_list = "\n".join(f"- `{t.fqn}` ({len(t.columns)} columns)" for t in candidate_critical[:15])
            questions.append(Question(
                id="table_criticality",
                phase=2,
                category="scope",
                prompt=(
                    f"Which tables are most critical for your AI workloads? "
                    f"I'll weight failures on critical tables more heavily in the report.\n\n"
                    f"Here are some candidates based on size and naming patterns:\n{table_list}\n\n"
                    f"Tell me which are critical, or add others."
                ),
                question_type="table_list",
                context_field="table_criticality",
                priority=2,
                data={"candidates": [t.fqn for t in candidate_critical]},
            ))

    # 3. Candidate key confirmation -- flag heuristic key detections
    heuristic_keys = _find_heuristic_keys(inventory)
    if heuristic_keys:
        key_list = "\n".join(f"- `{schema}.{table}.{col}`" for schema, table, col in heuristic_keys[:20])
        questions.append(Question(
            id="candidate_keys",
            phase=2,
            category="keys",
            prompt=(
                f"I detected these columns as likely unique identifiers based on "
                f"naming patterns (ending in `_id` or named `id`). I'll check them "
                f"for duplicates.\n\n{key_list}\n\n"
                f"Are any of these **not** actually unique keys? "
                f"Are there natural keys I'm missing (e.g., `email`, `order_number`)?"
            ),
            question_type="confirm_list",
            context_field="not_keys",
            priority=2,
            data={"detected_keys": [f"{s}.{t}.{c}" for s, t, c in heuristic_keys]},
        ))

    # 4. PII column confirmation -- show detected PII-like column names
    pii_candidates = _find_pii_column_names(inventory)
    if pii_candidates:
        pii_list = "\n".join(f"- `{schema}.{table}.{col}`" for schema, table, col in pii_candidates[:20])
        questions.append(Question(
            id="pii_confirmation",
            phase=2,
            category="pii",
            prompt=(
                f"I found columns that look like they might contain PII based on "
                f"their names:\n\n{pii_list}\n\n"
                f"Which of these actually contain sensitive data? Are there other "
                f"PII columns I should know about that don't follow obvious naming patterns?"
            ),
            question_type="confirm_list",
            context_field="known_pii_columns",
            priority=2,
            data={"detected_pii": [f"{s}.{t}.{c}" for s, t, c in pii_candidates]},
        ))

    # 5. Nullable columns -- identify columns likely to have intentional nulls
    nullable_candidates = _find_nullable_candidates(inventory)
    if nullable_candidates:
        null_list = "\n".join(f"- `{schema}.{table}.{col}`" for schema, table, col in nullable_candidates[:15])
        questions.append(Question(
            id="nullable_by_design",
            phase=2,
            category="nulls",
            prompt=(
                f"I'll check null rates across all columns. These columns look like "
                f"they might intentionally allow nulls based on their names and types:\n\n"
                f"{null_list}\n\n"
                f"Which of these have nulls **by design** (e.g., optional fields)? "
                f"I'll relax thresholds for those."
            ),
            question_type="confirm_list",
            context_field="nullable_by_design",
            priority=3,
            data={"candidates": [f"{s}.{t}.{c}" for s, t, c in nullable_candidates]},
        ))

    # 6. Freshness expectations
    timestamp_tables = [t for t in inventory.tables
                        if any(c.is_timestamp for c in t.columns)]
    if timestamp_tables and len(timestamp_tables) > 3:
        questions.append(Question(
            id="freshness_slas",
            phase=2,
            category="freshness",
            prompt=(
                f"I'll check data freshness for {len(timestamp_tables)} tables "
                f"that have timestamp columns. The default thresholds are:\n\n"
                f"- L1 (Analytics): 1 week\n"
                f"- L2 (RAG): 24 hours\n"
                f"- L3 (Training): 6 hours\n\n"
                f"Do any tables have different freshness requirements? For example, "
                f"a transactions table that should be refreshed hourly, or a "
                f"dimension table that's fine being weekly."
            ),
            question_type="free_text",
            context_field="freshness_slas",
            priority=3,
            data={"timestamp_tables": [t.fqn for t in timestamp_tables[:20]]},
        ))

    return sorted(questions, key=lambda q: q.priority)


# ---------------------------------------------------------------------------
# Phase 3: Post-Results Questions
# ---------------------------------------------------------------------------

def results_questions(
    report: dict[str, Any],
    ctx: UserContext,
) -> list[Question]:
    """Generate questions based on assessment results for failure triage.

    These help the user decide which failures matter, which are acceptable,
    and which to prioritize for remediation.

    Args:
        report: The full assessment report dict.
        ctx: Current user context.

    Returns:
        List of triage questions ordered by priority.
    """
    questions: list[Question] = []
    target = ctx.target_level or "L2"

    # 1. Factor-level triage -- for factors below 80%, ask if this is expected
    factors = report.get("factors", {})
    weak_factors = []
    for factor_name, scores in factors.items():
        score = scores.get(target, 0)
        if score < 0.80:
            weak_factors.append((factor_name, score))

    if weak_factors:
        factor_summary = "\n".join(
            f"- **{name.capitalize()}**: {score:.0%}" for name, score in weak_factors
        )
        questions.append(Question(
            id="factor_triage",
            phase=3,
            category="triage",
            prompt=(
                f"At your target level ({target}), these factors scored below 80%:\n\n"
                f"{factor_summary}\n\n"
                f"Are any of these expected or acceptable for your use case? "
                f"I'll explain what each means for your workload and suggest fixes "
                f"for the ones you want to improve."
            ),
            question_type="free_text",
            priority=1,
            data={"weak_factors": weak_factors},
        ))

    # 2. Top failures -- present the most impactful failures for triage
    tests = report.get("tests", [])
    failures = _extract_top_failures(tests, target, limit=10)

    if failures:
        failure_lines = []
        for f in failures:
            measured = f.get("measured_value")
            measured_str = f"{measured:.4f}" if measured is not None else "N/A"
            threshold = f.get("thresholds", {}).get(target)
            threshold_str = f"{threshold}" if threshold is not None else "N/A"
            failure_lines.append(
                f"- `{f['target']}` -- **{f['requirement']}**: "
                f"measured {measured_str} (threshold: {threshold_str})"
            )

        failure_summary = "\n".join(failure_lines)
        questions.append(Question(
            id="failure_triage",
            phase=3,
            category="triage",
            prompt=(
                f"Here are the top failures at {target}:\n\n{failure_summary}\n\n"
                f"For each:\n"
                f"- Is this expected or acceptable? (I'll mark it as accepted)\n"
                f"- Should I generate a fix? (I'll create specific SQL for your schema)\n"
                f"- Should this be excluded from future assessments?"
            ),
            question_type="free_text",
            context_field="accepted_failures",
            priority=1,
            data={"failures": failures},
        ))

    # 3. Not-assessed items -- ask if the user can provide missing data
    not_assessed = report.get("not_assessed", [])
    if not_assessed:
        gap_lines = []
        for item in not_assessed:
            req = item.get("requirement", "general")
            gap_lines.append(f"- **{req}**: {item['reason']}")

        gap_summary = "\n".join(gap_lines)
        questions.append(Question(
            id="not_assessed_gaps",
            phase=3,
            category="gaps",
            prompt=(
                f"These areas couldn't be assessed:\n\n{gap_summary}\n\n"
                f"Can you provide any of the missing data sources? For example, "
                f"an OTEL endpoint for pipeline monitoring, or Iceberg metadata "
                f"table locations."
            ),
            question_type="free_text",
            priority=2,
            data={"gaps": not_assessed},
        ))

    # 4. Remediation priority -- ask what to fix first
    if failures:
        questions.append(Question(
            id="remediation_priority",
            phase=3,
            category="remediation",
            prompt=(
                "Which areas do you want to tackle first? I can generate specific, "
                "executable SQL fixes grouped by:\n\n"
                "- **Quick wins** -- comments, naming fixes, simple constraints\n"
                "- **Data quality** -- null handling, deduplication, type cleanup\n"
                "- **Governance** -- PII masking, RBAC, access controls\n"
                "- **Infrastructure** -- pipeline freshness, lineage, versioning"
            ),
            question_type="multi_choice",
            options=[
                QuestionOption("quick_wins", "Quick wins", "Comments, naming, constraints"),
                QuestionOption("data_quality", "Data quality", "Nulls, duplicates, types"),
                QuestionOption("governance", "Governance", "PII, RBAC, masking"),
                QuestionOption("infrastructure", "Infrastructure", "Freshness, lineage, versioning"),
                QuestionOption("all", "All of the above", "Generate everything"),
            ],
            priority=2,
        ))

    return sorted(questions, key=lambda q: q.priority)


# ---------------------------------------------------------------------------
# Heuristic helpers for discovery questions
# ---------------------------------------------------------------------------

def _detect_ai_feeding_tables(inventory: DatabaseInventory) -> list[tuple[TableInfo, str]]:
    """Detect tables that likely feed AI systems based on naming, schema, and structure.

    Returns a list of (table, reason) tuples sorted by confidence. These heuristics
    aren't perfect -- the goal is to surface good candidates for the user to confirm.
    """
    # Naming patterns that suggest AI/ML usage
    AI_NAME_PATTERNS = [
        # Embeddings and vectors
        ("embedding", "name suggests embedding storage"),
        ("vector", "name suggests vector storage"),
        ("_embed", "name suggests embedding data"),
        # Feature stores
        ("feature", "name suggests feature store"),
        ("_feat_", "name suggests feature data"),
        # Training and ML
        ("training", "name suggests training dataset"),
        ("train_", "name suggests training data"),
        ("_train", "name suggests training data"),
        ("label", "name suggests labeled data"),
        ("annotation", "name suggests annotated data"),
        ("ground_truth", "name suggests ground truth data"),
        ("prediction", "name suggests prediction output"),
        ("inference", "name suggests inference data"),
        ("model_", "name suggests model metadata"),
        ("_model", "name suggests model data"),
        ("ml_", "name suggests ML pipeline data"),
        # RAG and search
        ("chunk", "name suggests chunked documents for RAG"),
        ("document", "name suggests document storage for RAG"),
        ("corpus", "name suggests text corpus"),
        ("index", "name suggests search index data"),
        ("knowledge", "name suggests knowledge base"),
        ("catalog", "name suggests data catalog"),
        # Semantic / enrichment
        ("enriched", "name suggests enriched/processed data"),
        ("semantic", "name suggests semantic data"),
        ("entity", "name suggests entity data"),
        ("ontology", "name suggests ontology data"),
    ]

    AI_SCHEMA_PATTERNS = [
        "ml", "ai", "feature", "embedding", "vector", "training",
        "rag", "search", "nlp", "analytics", "gold", "curated",
        "semantic", "enriched", "warehouse",
    ]

    # Column-level signals: tables with vector/array columns or many text columns
    VECTOR_COLUMN_HINTS = ["embedding", "vector", "dense", "sparse", "encoding"]

    candidates: list[tuple[int, TableInfo, str]] = []

    for table in inventory.tables:
        score = 0
        reasons: list[str] = []
        name_lower = table.name.lower()
        schema_lower = table.schema.lower()

        # Check table name patterns
        for pattern, reason in AI_NAME_PATTERNS:
            if pattern in name_lower:
                score += 30
                reasons.append(reason)
                break  # One name match is enough

        # Check schema name patterns
        for pattern in AI_SCHEMA_PATTERNS:
            if pattern in schema_lower:
                score += 20
                reasons.append(f"schema '{table.schema}' suggests AI/analytics use")
                break

        # Check for vector/embedding columns
        for col in table.columns:
            col_lower = col.name.lower()
            for hint in VECTOR_COLUMN_HINTS:
                if hint in col_lower:
                    score += 25
                    reasons.append(f"column '{col.name}' suggests vector/embedding data")
                    break

        # Check for tables with high text column ratio (likely document/RAG tables)
        text_cols = sum(1 for c in table.columns if c.is_string)
        if table.columns and text_cols / len(table.columns) > 0.6 and text_cols >= 3:
            score += 15
            reasons.append(f"{text_cols}/{len(table.columns)} columns are text (document-like)")

        # Check for tables with many columns (feature stores tend to be wide)
        if len(table.columns) > 30:
            score += 10
            reasons.append(f"wide table ({len(table.columns)} columns, feature-store-like)")

        if score > 0:
            # Combine reasons into a single string
            combined_reason = "; ".join(reasons[:2])  # Cap at 2 reasons for readability
            candidates.append((score, table, combined_reason))

    # Sort by confidence score descending
    candidates.sort(key=lambda x: x[0], reverse=True)
    return [(table, reason) for _, table, reason in candidates]


def _suggest_critical_tables(inventory: DatabaseInventory) -> list[TableInfo]:
    """Identify tables likely to be critical based on naming and size."""
    critical_prefixes = ("fact_", "dim_", "fct_", "agg_", "core_", "gold_")
    critical_names = {"users", "customers", "orders", "products", "transactions",
                      "events", "accounts", "sessions", "payments", "invoices"}

    scored: list[tuple[int, TableInfo]] = []
    for table in inventory.tables:
        score = len(table.columns)  # larger tables are more likely critical
        name_lower = table.name.lower()
        if any(name_lower.startswith(p) for p in critical_prefixes):
            score += 100
        if name_lower in critical_names:
            score += 50
        scored.append((score, table))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [t for _, t in scored]


def _find_heuristic_keys(inventory: DatabaseInventory) -> list[tuple[str, str, str]]:
    """Find columns detected as candidate keys by heuristic (not by constraint)."""
    keys: list[tuple[str, str, str]] = []
    for table in inventory.tables:
        for col in table.columns:
            # Only flag heuristic keys (name-based, not constraint-based)
            has_constraint = "PRIMARY KEY" in col.constraints or "UNIQUE" in col.constraints
            is_name_based = col.name.lower().endswith("_id") or col.name.lower() == "id"
            if is_name_based and not has_constraint:
                keys.append((table.schema, table.name, col.name))
    return keys


_PII_PATTERNS = [
    "email", "ssn", "social_security", "phone", "address", "birth",
    "passport", "salary", "credit_card", "first_name", "last_name",
    "full_name", "mobile", "driver_license", "tax_id", "national_id",
]


def _find_pii_column_names(inventory: DatabaseInventory) -> list[tuple[str, str, str]]:
    """Find columns whose names suggest PII content."""
    pii: list[tuple[str, str, str]] = []
    for table in inventory.tables:
        for col in table.columns:
            name_lower = col.name.lower()
            for pattern in _PII_PATTERNS:
                if pattern in name_lower:
                    pii.append((table.schema, table.name, col.name))
                    break
    return pii


_NULLABLE_HINTS = [
    "middle_name", "suffix", "prefix", "nickname", "maiden_name",
    "secondary", "alternate", "optional", "memo", "notes", "comment",
    "description", "bio", "about", "fax", "pager", "extension",
    "discontinued", "deleted", "archived", "ended", "closed",
    "cancelled", "expired", "terminated", "deactivated",
]


def _find_nullable_candidates(inventory: DatabaseInventory) -> list[tuple[str, str, str]]:
    """Find columns likely to have intentional nulls based on naming."""
    candidates: list[tuple[str, str, str]] = []
    for table in inventory.tables:
        for col in table.columns:
            if not col.is_nullable:
                continue
            name_lower = col.name.lower()
            for hint in _NULLABLE_HINTS:
                if hint in name_lower:
                    candidates.append((table.schema, table.name, col.name))
                    break
    return candidates


def _extract_top_failures(
    tests: list[dict[str, Any]],
    target_level: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Extract the top failures sorted by impact (lower levels first)."""
    failures = [
        t for t in tests
        if t.get("result", {}).get(target_level) == "fail"
    ]

    # Sort: L1 failures first, then L2, then L3 (lower levels are more critical)
    level_order = {"L1": 0, "L2": 1, "L3": 2}

    def sort_key(t: dict) -> tuple[int, str]:
        # Find the lowest level where this test fails
        min_level = 3
        for level in ["L1", "L2", "L3"]:
            if t.get("result", {}).get(level) == "fail":
                min_level = min(min_level, level_order.get(level, 3))
                break
        return (min_level, t.get("target", ""))

    failures.sort(key=sort_key)
    return failures[:limit]
