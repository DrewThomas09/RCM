# Report 0129: Dead Code — `core/distributions.py`

## Scope

`RCM_MC/rcm_mc/core/distributions.py` (258 lines) — referenced by Reports 0013 (public API), 0035 (incoming graph for `infra/config`), 0125 (single internal import from `portfolio/store.py`). First dead-code spot-check on this module.

## Findings

### Public surface inventory

`grep -n "^def \|^class "` returns 10 top-level definitions:

| Line | Symbol | Kind | External callers | Status |
|---|---|---|---|---|
| 8 | `class DistributionError(ValueError)` | exception class | 2 | live |
| 12 | `def _as_float` | private helper | (internal) | live |
| 19 | `def beta_alpha_beta_from_mean_sd` | converter | 1 | live |
| 51 | `def lognormal_mu_sigma_from_mean_sd` | converter | 0 (BUT used internally) | **public-named but internal-only** |
| 63 | `def gamma_shape_scale_from_mean_sd` | converter | 0 (BUT used internally) | **public-named but internal-only** |
| 75 | `def triangular_mean_var` | converter | 0 (BUT used internally) | **public-named but internal-only** |
| 86 | `def dist_moments` | dispatcher | 2 | live |
| 147 | `def sample_dist` | workhorse | 4 | live |
| 211 | `def sample_dirichlet` | special-case | 1 | live |
| 235 | `def sample_sum_iid_as_gamma` | special-case | 1 | live |

### Cross-codebase usage check

```
DistributionError                     → 2 files (1 prod + 1 test likely)
beta_alpha_beta_from_mean_sd          → 1 file
lognormal_mu_sigma_from_mean_sd       → 0 files
gamma_shape_scale_from_mean_sd        → 0 files
triangular_mean_var                   → 0 files
dist_moments                          → 2 files
sample_dist                           → 4 files (the workhorse — Report 0125 confirmed portfolio.store imports it)
sample_dirichlet                      → 1 file
sample_sum_iid_as_gamma               → 1 file
```

### NO truly-dead code

The 3 zero-external-caller functions are **all called internally**:

| Function | Internal call site | Pattern |
|---|---|---|
| `lognormal_mu_sigma_from_mean_sd` | line 190 (in `sample_dist`) | dispatch from `d == "lognormal"` |
| `gamma_shape_scale_from_mean_sd` | line 196 (in `sample_dist`) | dispatch from `d == "gamma"` |
| `triangular_mean_var` | line 108 (in `dist_moments`) | dispatch from `d == "triangular"` |

**Reachable transitively via `sample_dist` and `dist_moments`.** Not dead.

### Same pattern as Report 0099 MR540

Cross-link Report 0099 (`domain/custom_metrics.py validate_metric_key`): public-named but internal-only function. Per CLAUDE.md "Private helpers prefix with underscore." 

**This module has 3 such functions.** Either:
- Promote: leave them public — they're useful library functions for any caller doing distribution math.
- Demote: prefix with underscore (private) since no current external caller exists.

**Library-style argument**: these are mathematical converters with no internal-state side effects. Public is reasonable. **No clear recommendation to demote.**

### Imports — all used

`grep -n "^import\|^from"`:

```python
1: from __future__ import annotations
3: from typing import Any, Dict, Optional, Tuple
5: import numpy as np
```

`Any, Dict, Optional, Tuple` — all used in type signatures. `np` — used many places. **No unused imports.**

### Lazy import — scipy.stats.truncnorm

Line 117-124 (in `dist_moments`):

```python
if d == "normal_trunc" and sd > 0:
    a_lo = float(spec.get("min", -np.inf))
    a_hi = float(spec.get("max", np.inf))
    if np.isfinite(a_lo) or np.isfinite(a_hi):
        try:
            from scipy.stats import truncnorm as _tn
            ...
            return float(tn_mean), float(tn_var)
        except ImportError:
            pass
return mean, sd * sd  # untruncated fallback
```

**scipy IS optional** (per pyproject `[all]` extras, Report 0113). When scipy missing:
- `dist_moments` returns `(mean, sd*sd)` for `normal_trunc` — **untruncated variance**.
- This is mathematically wrong for truncated distributions (variance is smaller after truncation).

**MR734 below.** Silent degradation: results SILENTLY differ depending on whether scipy is installed. No log warning, no error. A test suite that runs without scipy could pass with subtly-wrong moments.

### No module docstring

Line 1 is `from __future__ import annotations` — **no docstring at top**. The first docstring is at line 19+ (`beta_alpha_beta_from_mean_sd`).

Cross-link Report 0104 doc-gap pattern: `infra/webhooks.py` had module docstring but missing per-function. Here: missing module docstring but per-function docstrings exist (per spot-check at line 19+).

### Per-function docstrings (sampled)

| Line | Function | Docstring? |
|---|---|---|
| 8 | `DistributionError` | NONE (single-line class) |
| 12 | `_as_float` | NONE (trivial helper) |
| 19 | `beta_alpha_beta_from_mean_sd` | YES |
| 86 | `dist_moments` | (TBD — not extracted) |
| 147 | `sample_dist` | YES (per line 148-) |
| 211 | `sample_dirichlet` | (TBD) |
| 235 | `sample_sum_iid_as_gamma` | (TBD) |

### Comparison to Report 0099 dead-code findings

Report 0099 in `domain/custom_metrics.py` (185 lines) found:
- 5 unused imports (field, asdict, Dict, Optional, logger)
- 1 dead exception branch
- 1 public-named-internal function

This module (258 lines) finds:
- 0 unused imports
- 0 dead branches
- 3 public-named-internal functions (different stylistic choice — same pattern)
- 1 silent-degradation path (scipy fallback)

**Substantially cleaner than custom_metrics.py.** Confirms `core/` discipline is high.

### `DistributionError(ValueError)` — minimal class

Line 8-9: `class DistributionError(ValueError): pass` — empty subclass. Used to discriminate distribution-input-validation errors from other ValueError sources. **OK pattern**, even if minimal.

### `_as_float` private helper

Line 12-16:
```python
def _as_float(x: Any, name: str) -> float:
    try:
        return float(x)
    except Exception as e:
        raise DistributionError(f"Expected numeric for '{name}', got: {x!r}") from e
```

**`except Exception`** — no `noqa: BLE001`. Cross-link Report 0020 broad-except pattern. This catches `Exception`, not `BaseException`, so SystemExit/KeyboardInterrupt propagate (correct). But `from e` chains the original exception — good debugging.

### Unused-import check (formal)

| Import | Used | Confirmed |
|---|---|---|
| `__future__.annotations` | YES — type hints | implicit |
| `Any, Dict, Optional, Tuple` | YES — annotations | grep |
| `numpy as np` | YES — many sites | grep |

**Zero dead imports.** Cleaner than Report 0099's 5-dead-imports finding for `domain/custom_metrics.py`.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR734** | **Silent degradation when scipy missing** for `normal_trunc` distribution | `dist_moments` returns untruncated variance instead of truncated. Mathematically wrong; tests without scipy silently use the fallback. Should log a warning OR raise informative error. | **Medium** |
| **MR735** | **3 public-named-but-internal-only converter functions** (`lognormal_mu_sigma_from_mean_sd`, `gamma_shape_scale_from_mean_sd`, `triangular_mean_var`) | Same pattern as Report 0099 MR540 (`validate_metric_key`). Library-style: public is OK. But CLAUDE.md "private helpers prefix with underscore" leaves the convention ambiguous. | Low |
| **MR736** | **No module docstring** | Per CLAUDE.md "Docstrings explain *why*, not *what*" — module-level intent unclear. New developer reading top of file sees only imports. | Low |
| **MR737** | **`DistributionError(ValueError): pass`** — minimal subclass adds no semantic info | Catchers can't distinguish from ValueError without `isinstance` check on this specific class. Acceptable but fragile. | Low |

## Dependencies

- **Incoming:** ≥4 production files (per `sample_dist` count) including `portfolio/store.py` (Report 0125), tests, and likely `simulator.py` / `mc/ebitda_mc.py` (cross-link Report 0112).
- **Outgoing:** stdlib (`__future__`, `typing`); numpy; lazy scipy.

## Open questions / Unknowns

- **Q1.** Where does `dist_moments` need scipy.stats.truncnorm — does any production code path actually use `normal_trunc` distributions, OR is the scipy fallback path effectively never exercised?
- **Q2.** Are tests currently checking `normal_trunc` math correctness? If yes, are they running with scipy installed (CI install per Report 0116 uses `[dev]` only — does NOT include scipy)?
- **Q3.** Should the 3 public-named-internal converters be promoted to a `__all__` declaration to make the public API explicit?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0130** | Schema-walk `generated_exports` (Report 0127 MR724 high — pre-merge requirement). |
| **0131** | Read `cli.py` head (1,252 lines, 14+ iterations owed). |
| **0132** | Verify CI install includes scipy or not (closes Q2). |

---

Report/Report-0129.md written.
Next iteration should: schema-walk `generated_exports` table — pre-merge requirement (Report 0127 MR724 high, carried 3+ iterations now).
