# management_scorecard/

**Systematic quality-of-management diligence.** Replaces "will this team hit their forecast?" from ad-hoc reference calls + LinkedIn skimming into a scored, role-weighted deliverable.

## Files

| File | Purpose |
|------|---------|
| `__init__.py` | Package docstring — replaces ad-hoc reference calls + LinkedIn skimming. |
| `profile.py` | `Executive` dataclass — minimal, hand-collected from data room + reference calls. Optional fields degrade to neutral priors. |
| `scorer.py` | **Per-executive deterministic scoring.** Four dimensions × 0-100 × named reason string. Overall = weighted average; red-flag override clips to ≤40. |
| `analyzer.py` | **Team-level orchestrator.** Scores each exec, aggregates into `ManagementReport`. Role-weighted overall: CEO 35% / CFO 25% / COO 20% / remainder split. |

## The four per-exec dimensions

Each scored 0-100 with a named reason string:
1. **Forecast reliability** — actual-to-forecast ratio on last 4 reported periods (from data room)
2. **Comp competitiveness** — per-role comp vs MGMA / Sullivan Cotter / industry benchmark
3. **Tenure** — time in current role; step-function penalty for turnover <18mo
4. **Prior-role reputation** — pattern-match against named-failure + strong-exit roster

## Red-flag override

When any single dimension triggers a red-flag pattern (forecast miss >30% two periods in a row, prior role in named failure library, comp >2× peer benchmark), overall score clips to ≤40 regardless of other dimensions.

## Team-level weighting

Role weights encode that CFO + CEO carry the deal. A CEO at 40 overall on an otherwise-strong team makes the deal ungovernable.

## Where it plugs in

- **Thesis Pipeline step 9** — runs when roster data supplied
- **Bear Case** — management score <60 becomes OPERATIONAL theme evidence
- **Pre-IC chair brief** — management weight into the 4-bullet pre-IC talking points

## Tests

`tests/test_management_scorecard*.py` — per-dimension scoring + red-flag override + role-weighting contract.
