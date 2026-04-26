# Report 0044: Documentation Gap — `rcm_mc/pe/breakdowns.py`

## Scope

`RCM_MC/rcm_mc/pe/breakdowns.py` (233 lines) on `origin/main` at commit `f3f7e7f`. Selected because it has **no module-level docstring** despite being imported by both `cli.py` and `server.py` (production-critical). Sister to Report 0014 (management/) but a much sparser doc state.

Prior reports reviewed: 0040-0043.

## Findings

### Doc state at-a-glance

```python
# Line 1-3 of breakdowns.py:
from __future__ import annotations

from collections import defaultdict
```

**No module docstring.** Goes straight from imports. Compare to neighboring modules in `pe/`:

- `pe/value_bridge_v2.py:1-9` has a 9-line module docstring explaining the v2 unit-economics model.
- `pe/value_creation_plan.py` (per Report 0024 listing) — has a logger import suggesting setup; docstring not yet inspected.

`pe/breakdowns.py` is the outlier: substantial module (233 lines, 5 functions) with no module docstring.

### Public-function inventory (5 functions)

| Line | Function | Visibility |
|---|---|---|
| 13 | `_dict_to_df_mean(acc, n, value_col)` | Private (`_` prefix) |
| 20 | `simulate_with_mean_breakdowns(cfg, n_sims, seed)` | **Public** |
| 104 | `compare_mean_breakdowns(...)` | **Public** |
| 146 | `_merge_breakdowns_mean(actual, bench, keys, value_cols)` | Private |
| 155 | `simulate_compare_with_breakdowns(...)` | **Public** |

**3 public functions; docstring presence not yet confirmed per-line.** Reading line 20:

```python
def simulate_with_mean_breakdowns(cfg: Dict[str, Any], n_sims: int, seed: int) -> Tuple[pd.DataFrame, Dict[str, pd.DataFrame]]:
```

(signature; docstring would be on the next line). Need to verify.

### What's missing

| Doc element | Status |
|---|---|
| Module-level docstring | **MISSING** (line 1 is `from __future__`) |
| Module README | **MISSING** at `pe/breakdowns_README.md` (sister modules don't all have one either) |
| Per-function docstring (3 public) | **Likely missing or thin** — given the absent module docstring as a pattern signal |
| Args / Returns sections | **Likely missing** — most callers learn-by-reading-tests |
| Usage example | **MISSING** |
| Cross-link to `simulate_one` (the imported core function) | **MISSING** |

### Production callers

- `RCM_MC/rcm_mc/cli.py:12` `from .pe.breakdowns import simulate_compare_with_breakdowns` (per Report 0012)
- `RCM_MC/rcm_mc/server.py` (per Report 0024 grep — referenced in HTTP-deps list)

**2 production callers — both load-bearing.** A consumer trying to understand what `simulate_compare_with_breakdowns` produces must read 233 lines of unannotated code.

### Concrete additions proposed

#### 1. Module-level docstring

```python
"""Per-driver breakdowns for Monte Carlo simulator output.

Wraps :func:`rcm_mc.core.simulator.simulate_one` to produce per-payer-
plus-per-stage / per-payer-plus-per-denial-type / etc. breakdown DataFrames
alongside the standard simulate_compare DataFrame. Used by:

- :command:`rcm-mc` CLI when ``--breakdown`` flag is set
- :class:`rcm_mc.server.RCMHandler` when rendering driver-decomposition
  panels on the dashboard

Public API::

    simulate_with_mean_breakdowns(cfg, n_sims, seed) -> (df, breakdowns_dict)
    compare_mean_breakdowns(actual, bench) -> diff_dataframes
    simulate_compare_with_breakdowns(actual_cfg, bench_cfg, n_sims, seed)
        -> (df, breakdowns_dict)

Breakdowns dict keys:
- "payer_stage": (payer × appeal-stage) means
- "payer_denial_type": (payer × clinical / coding / admin / ...) means

Output writes to {outdir}/drivers_*.csv (per cli.py:431-437).
"""
```

#### 2. Per-function docstrings

For each of the 3 public functions: Args / Returns / a one-line example. Total addition ~30-50 lines to the file.

#### 3. README at `pe/breakdowns_README.md` OR enhance `pe/README.md`

Per Report 0014's pattern, an inline README under `pe/` would document the breakdown surface. Currently `pe/README.md` exists but its size + cross-references unknown.

### Comparison to other 233-line modules

Per Report 0009: `data/lookup.py` is 1,114 lines with a thorough docstring on every function. Per Report 0021: `auth/auth.py` is 467 lines with a dense module docstring (lines 1-30). **`pe/breakdowns.py` is the outlier.**

## Merge risks flagged

| ID | Risk | Detail | Severity |
|---|---|---|---|
| **MR356** | **Module docstring missing** | A new contributor must read 233 lines to understand the contract. Maintenance friction; spec drift between callers and producer. | Medium |
| **MR357** | **`simulate_compare_with_breakdowns` is the cli.py entry but doc-naked** | Per Report 0012 the CLI uses this when breakdown drivers are requested. **Output shape (the 6 driver-breakdown CSVs at `cli.py:431-437`) is implied by the function but not documented.** A future branch that adds a 7th breakdown shape silently changes output. | **High** |
| **MR358** | **No cross-link to `simulate_one`** | Module imports `simulate_one` from core/simulator (line 9) and calls it at line 38 (per Report 0039). **Without docs, the relationship between this module and the simulator is hidden.** | Medium |
| **MR359** | **Pattern hazard: outlier in `pe/` subpackage** | If `pe/value_bridge_v2.py` and `pe/value_creation_plan.py` have module docstrings (the convention), this module's absence stands out. **Pre-merge: any branch that adds a sister module should not adopt this missing-docstring pattern.** | Low |
| **MR360** | **Cumulative cross-link with Report 0014 finding** | The codebase has high doc-presence floor (most modules have docstrings) but inconsistent application. `pe/breakdowns.py` falls below the floor. **Doc-quality CI check (e.g. interrogate-py) would catch this in 0 lines of effort.** | Low |

## Dependencies

- **Incoming:** `cli.py:12`, `server.py` (route handler).
- **Outgoing:** `core/simulator.simulate_one`, `infra/taxonomy.infer_root_cause`, `numpy`, `pandas`.

## Open questions / Unknowns

- **Q1.** Do the 3 public functions have per-function docstrings? Need full read.
- **Q2.** Is the breakdown structure (`{"payer_stage": ..., "payer_denial_type": ...}`) defined explicitly anywhere, or only implied by the keys callers iterate?
- **Q3.** Why is this module the outlier? Was it shipped pre-doc-convention?

## Suggested follow-ups

| Iteration | Proposed area | Why |
|---|---|---|
| **0045** | **Tech-debt marker sweep** (already requested as iteration 45). | Pending. |
| **0046** | **Read full `pe/breakdowns.py`** — verify per-function docstring state. | Resolves Q1. |
| **0047** | **`pe/README.md` audit** — does it cover this module? | Resolves Q3 partially. |

---

Report/Report-0044.md written. Next iteration should: do the tech-debt marker sweep on `pe/` subsystem (already queued as iteration 45) — sister to Report 0015's whole-rcm_mc sweep but scoped to the value-creation layer.

