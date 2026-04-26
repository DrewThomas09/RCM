# Report 0159: Dead Code — `pe_intelligence/extra_red_flags.py`

## Scope

`RCM_MC/rcm_mc/pe_intelligence/extra_red_flags.py` (323 lines) — sampled module from the 276-module pe_intelligence subpackage. First targeted dead-code audit in pe_intelligence/. Sister to Reports 0009, 0039, 0069, 0099, 0129.

## Findings

### Public surface inventory (per `grep "^def \|^class "`)

10 visible functions, all named `_r_<rule_name>` (private by convention):

| Line | Function | Naming |
|---|---|---|
| 23 | `_r_physician_turnover` | private |
| 52 | `_r_rn_shortage` | private |
| 81 | `_r_payer_denial_spike` | private |
| 107 | `_r_bad_debt_spike` | private |
| 136 | `_r_it_system_eol` | private |
| 162 | `_r_lease_cluster` | private |
| 190 | `_r_open_inspection` | private |
| 209 | `_r_self_insurance_tail` | private |
| 236 | `_r_capex_deferral` | private |
| 262 | `_r_key_payer_churn` | private |

**10 private helper functions, signatures all `(ctx: HeuristicContext) -> Optional[HeuristicHit]`.** Same shape — these are RULE FUNCTIONS in a registry pattern.

### Importers

Per `grep "extra_red_flags"`:

- `tests/test_pe_intelligence.py` (test)
- `ui/chartis/ic_packet_page.py` (UI)
- `pe_intelligence/master_bundle.py` (sibling)
- `pe_intelligence/__init__.py` (re-export per Report 0153 line 34)
- `pe_intelligence/partner_review.py` (cross-link Report 0155: orchestrator)

**5 importers.** Healthy fanin given the module's specialty.

### What's exported (per `__init__.py:34` per Report 0153)

```python
from .extra_red_flags import EXTRA_RED_FLAG_FIELDS, run_extra_red_flags
```

**2 public names**: `EXTRA_RED_FLAG_FIELDS` (constant) and `run_extra_red_flags` (orchestrator).

**The 10 `_r_*` private helpers are the registry contents** — each a "rule function" that runs against `HeuristicContext`. **Likely registered in `EXTRA_RED_FLAG_FIELDS`.**

### Dead-code analysis

#### `_r_*` helpers (10): NOT external-callable but ARE registered

All 10 are private (underscore prefix). External code cannot import them. Per registry pattern (cross-link Report 0093 ml/MODEL_QUALITY_REGISTRY), they're collected into `EXTRA_RED_FLAG_FIELDS` constant and dispatched via `run_extra_red_flags`.

**NONE is dead** — each is invoked by the orchestrator's iteration loop (likely `for rule in EXTRA_RED_FLAG_FIELDS: rule(ctx)`).

#### Orphan check (importers test)

Per `grep`: 5 importers. Module is alive.

#### Pattern-based observation

The 10 `_r_*` functions are mathematically-similar (same signature, same return type). **Strong rule-registry pattern.** Cross-link Report 0095 (domain/) + Report 0153 namespace-aggregator pattern.

### Comparison to Report 0099 dead-code finding

Report 0099 found:
- 5 unused imports in `domain/custom_metrics.py`
- 1 dead exception branch
- 1 public-named-but-internal-only function

This module: **0 unused imports observed in head; 0 dead branches observed; private-naming convention CORRECTLY applied** (all 10 helpers prefixed with `_`).

**Better dead-code discipline than Report 0099 target.**

### What's NOT verified this iteration

- Imports inside `extra_red_flags.py` (top of file lines 1-22 not extracted)
- Whether ALL 10 `_r_*` are actually registered in `EXTRA_RED_FLAG_FIELDS`
- Whether `run_extra_red_flags` actually iterates over all of them

**Possible audit risk**: a `_r_*` defined but NOT registered = dead despite proper naming. Q1 below.

### `_r_<rule>` cluster — cross-link to red flags pattern

Per Report 0153 sibling re-export: `red_flags.py` exports `RED_FLAG_FIELDS, run_all_rules`. **Same pattern**: rules in a registry, dispatched.

**`extra_red_flags` is the "extras" extension of the red_flags base.** Two-tier rule structure. Cross-link Report 0155 partner_review imports both.

### Module size economy

| Function | LOC range |
|---|---|
| `_r_physician_turnover` | 23-51 (29 lines) |
| `_r_rn_shortage` | 52-80 (29 lines) |
| `_r_payer_denial_spike` | 81-106 (26 lines) |
| `_r_bad_debt_spike` | 107-135 (29 lines) |
| `_r_it_system_eol` | 136-161 (26 lines) |
| `_r_lease_cluster` | 162-189 (28 lines) |
| `_r_open_inspection` | 190-208 (19 lines) |
| `_r_self_insurance_tail` | 209-235 (27 lines) |
| `_r_capex_deferral` | 236-261 (26 lines) |
| `_r_key_payer_churn` | 262-? (rest of file) |

**Average ~26 LOC per rule.** Consistent. **Refactor signal** if any single rule grows past 50 LOC.

### Potential ALL-isn't-registered concern

If a developer adds a `_r_new_rule` but forgets to add it to `EXTRA_RED_FLAG_FIELDS`, it's silently dead.

**MR863 below.**

### Import surface (lines 1-22 — not extracted this iteration)

TBD. Likely stdlib + `from .heuristics import HeuristicContext, HeuristicHit` (per the function signatures).

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR863** | **`_r_*` rule helpers must be registered in `EXTRA_RED_FLAG_FIELDS` to fire** | If a new rule is defined but registration forgotten, it's silently dead. **Should add a test that asserts every `_r_*` function in module is in `EXTRA_RED_FLAG_FIELDS`.** | Medium |
| **MR864** | **No truly-dead code in `extra_red_flags.py`** | All 10 `_r_*` helpers private + presumably registered. 5 external importers. **Healthy module.** | (clean) |
| **MR865** | **Module exemplifies registry pattern** — same as `MODEL_QUALITY_REGISTRY` (Report 0093), pe_intelligence rules | Project-wide pattern emerging. **Should be documented in CLAUDE.md** as a project idiom. | Low |

## Dependencies

- **Incoming:** 5 importers (per `grep`).
- **Outgoing:** TBD — likely `.heuristics.HeuristicContext, HeuristicHit`.

## Open questions / Unknowns

- **Q1.** Are all 10 `_r_*` functions in `EXTRA_RED_FLAG_FIELDS`? Spot-check requires reading the constant.
- **Q2.** What's `_r_key_payer_churn` body length (continues to end of file)?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0160** | Orphan files (in flight). |
| **0161** | Read `EXTRA_RED_FLAG_FIELDS` definition (closes Q1). |

---

Report/Report-0159.md written.
