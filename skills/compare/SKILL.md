---
name: compare
description: "Compare assessments across runs. Track improvements, regressions, and progress toward AI readiness."
parent_skill: assess-data
---

# Compare Assessments

Compare assessment results across runs to track progress. Show score changes, improvements, regressions, and new/removed tests. This is the feedback loop that validates remediation efforts.

## Forbidden Actions

- NEVER delete or modify assessment history in the SQLite database
- NEVER compare assessments from different databases without warning the user
- NEVER hide regressions -- always surface pass-to-fail transitions prominently
- NEVER attribute score changes to remediation without verifying the corresponding tests

## When to Load

- After applying fixes and re-running an assessment
- When the user wants to see their assessment history
- When reviewing progress over time
- Can be used standalone: `python -m agent.cli diff` or `python -m agent.cli history`

## Prerequisites

- At least two assessment runs saved to `~/.aird/assessments.db`
- For meaningful comparison: same connection string and similar scope

## Workflow

### Step 1: View Assessment History

```bash
python -m agent.cli history
```

Output:

```
ID         Timestamp              Tables   L1       L2       L3       Connection
------------------------------------------------------------------------------------------
a1b2c3d4   2025-02-10T14:30:00   47       86%      72%      54%      ***@myhost/analytics
e5f6g7h8   2025-02-03T09:15:00   45       78%      65%      48%      ***@myhost/analytics
```

Filter by connection:

```bash
python -m agent.cli history --connection "postgresql://user:pass@host/db" --limit 10
```

### Step 2: Run Comparison

**Option A: Auto-compare on re-assessment**

```bash
python -m agent.cli assess \
  --connection "<connection_string>" \
  --output json:report.json \
  --context context.yaml \
  --compare
```

The `--compare` flag automatically finds the previous assessment for this connection and appends a diff to the output.

**Option B: Compare the two most recent runs**

```bash
python -m agent.cli diff
```

Or filtered by connection:

```bash
python -m agent.cli diff --connection "postgresql://user:pass@host/db"
```

### Step 3: Present the Comparison

The diff output contains five sections:

**Score Changes:**

```
| Level | Previous | Current | Delta |
|-------|----------|---------|-------|
| L1    | 78.0%    | 86.1%   | +8.1% |
| L2    | 65.0%    | 71.5%   | +6.5% |
| L3    | 48.0%    | 53.9%   | +5.9% |
```

**Factor Changes:**

```
| Factor      | L1 Delta | L2 Delta | L3 Delta |
|-------------|----------|----------|----------|
| Clean       | +12.0%   | +8.5%    | +5.2%    |
| Contextual  | +15.0%   | +10.0%   | +8.0%    |
| Consumable  | --       | --       | --       |
| Current     | +2.0%    | +3.0%    | +1.5%    |
| Correlated  | --       | --       | --       |
| Compliant   | +5.0%    | +4.0%    | +3.0%    |
```

**Improvements** (fail -> pass):

```
- analytics.orders -- column_comment_coverage now passes L1
- analytics.users.email -- pii_detection_rate now passes L2
- analytics.products -- naming_consistency now passes L1, L2
```

**Regressions** (pass -> fail):

```
- analytics.events.created_at -- max_staleness_hours now fails L2
```

**New/Removed Tests:**

```
New: analytics.audit_log -- 8 new tests (table added since last run)
Removed: staging.tmp_debug -- 5 tests removed (table excluded by context)
```

### Step 4: Interpret the Comparison

Frame the comparison around the user's target level:

```
Progress toward {target} readiness:

You moved from {prev_score}% to {curr_score}% at {target}.
{N} tests improved, {M} regressed.

{verdict}
```

**Verdicts:**
- Big improvement: "Strong progress. The {factor} improvements from adding column descriptions and fixing null rates are paying off."
- Regression: "Watch out -- {table} freshness regressed. A pipeline may have stalled since your last assessment."
- Plateau: "Scores are stable. The remaining gaps are in {factors}, which require {type of work}."
- Crossed threshold: "You crossed the 80% threshold at L2 -- your data is now 'mostly ready' for RAG workloads."

### Step 5: Track Context-Aware Progress

If both runs used a `UserContext`, note what changed:
- New exclusions added or removed
- New accepted failures
- Changed freshness SLAs
- Tables reclassified (standard -> critical)

This helps distinguish genuine improvements from scoring changes caused by context updates.

**STOP**: Present comparison. Ask if the user wants to continue remediating remaining failures.

## Output

- A structured diff with score changes, improvements, regressions, and new/removed tests
- Markdown-rendered comparison report
- Progress narrative framed around the user's target level

## Next Skill

- If improvements are needed: **Continue to** `remediate/SKILL.md`
- If re-assessment is needed: **Continue to** `assess/SKILL.md`
- If the user is satisfied: Workflow complete.
