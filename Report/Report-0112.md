# Report 0112: Circular Import Risk — `rcm_mc/mc/` Subpackage

## Scope

Traces import chains in `RCM_MC/rcm_mc/mc/` (7 files, 2,207 lines). Sister to Reports 0022 (analysis/), 0052 (infra/), 0082 (compliance/). `mc/` only previously mentioned in CLAUDE.md (Phase 4 `mc/ebitda_mc.py`); 6 of 7 files **never reported**.

## Findings

### `mc/` inventory (7 files, 2,207 lines)

| File | Lines | Status |
|---|---|---|
| `__init__.py` | 38 | re-export |
| `convergence.py` | 114 | **never reported** |
| `ebitda_mc.py` | 760 | mentioned in CLAUDE.md |
| `mc_store.py` | 202 | discovered Report 0110 |
| `portfolio_monte_carlo.py` | 191 | **never reported** |
| `scenario_comparison.py` | 169 | mentioned via Report 0093 |
| `v2_monte_carlo.py` | 733 | **never reported** |

**4 of 7 modules never reported.** Add to Report 0091 unmapped backlog.

### Internal DAG (within mc/)

| Module | Imports siblings |
|---|---|
| `convergence.py` | NONE — leaf |
| `scenario_comparison.py` | NONE — leaf |
| `mc_store.py` | `.ebitda_mc.MonteCarloResult` |
| `ebitda_mc.py` | `.convergence` |
| `portfolio_monte_carlo.py` | `.ebitda_mc` + `.convergence` |
| `v2_monte_carlo.py` | `.ebitda_mc` + `.convergence` |
| `__init__.py` | re-exports from all 4 above |

### Topology

```
       convergence.py    scenario_comparison.py
         ▲     ▲                    ▲
         │     │                    │
         │     └──────┬─────────────┘
         │            │
       ebitda_mc.py   │
         ▲    ▲       │
         │    │       │
         │    │       │
   mc_store   ├───────┴──── portfolio_monte_carlo.py
              │
              └──────────── v2_monte_carlo.py
```

**Forward-only DAG.** No cycles within `mc/`.

### Cross-package import edges

| From | To | Symbol |
|---|---|---|
| `mc/ebitda_mc.py:36` | `pe/rcm_ebitda_bridge.py` | `RCMEBITDABridge` |
| `mc/v2_monte_carlo.py:41` | `finance/reimbursement_engine.py` | `PayerClass`, `ReimbursementProfile` |
| `mc/v2_monte_carlo.py:42` | `pe/value_bridge_v2.py` | (multi-symbol) |

**3 cross-package edges, all `mc/` → others.** Need to verify the reverse direction.

### Cycle check: does `pe/` or `finance/` import `mc/`?

`grep "^from.*\.mc\b\|^from rcm_mc\.mc\b" RCM_MC/rcm_mc/pe/ RCM_MC/rcm_mc/finance/`:

**Empty result. No back-edges from pe/ or finance/ to mc/.** Cycle-free.

### Cross-link to Report 0094 MR516 (ReimbursementProfile name collision)

`v2_monte_carlo.py:41`:
```python
from ..finance.reimbursement_engine import PayerClass, ReimbursementProfile
```

Imports the **`finance.reimbursement_engine.ReimbursementProfile`** — the per-hospital revenue exposure dataclass — NOT the `domain.__init__.ReimbursementProfile` deprecated alias for `MetricReimbursementSensitivity`.

**Cross-link Report 0094 MR516**: this is a correct import that respects the disambiguation. But because the name is identical, a developer reading just `from ... import ReimbursementProfile` cannot tell which one is meant without checking the source path. The collision **persists as a footgun**.

### HIGH-PRIORITY: privacy-boundary violation

`mc/portfolio_monte_carlo.py:24`:
```python
from .ebitda_mc import DistributionSummary, _histogram, HistogramBin
```

`mc/v2_monte_carlo.py:55`:
```python
from .ebitda_mc import (
    ...,
    _histogram,
    ...
)
```

**`_histogram` is leading-underscore (private per CLAUDE.md "Private helpers prefix with underscore") but imported by 2 sibling modules.**

Within a Python subpackage, this is a tolerated idiom (sibling modules see each other's privates), but **CLAUDE.md sets the convention as private = single-module**. Cross-link Report 0099 MR540 (inverse — public-named-but-internal-only). **Cross-link Report 0095 (domain/ private helpers)** — those are NOT cross-imported.

This is a **convention violation tolerated by Python**. Not a cycle, not a bug; a structural smell.

**Recommended refactor**: rename `_histogram` to `histogram` (public — it has 3 sibling consumers + is genuinely useful) or move the helper to `mc/_helpers.py`-style internal-helper module.

### `_histogram` body location

`mc/ebitda_mc.py:696 def _histogram(values: np.ndarray, *, n_bins: int = 30) -> List[HistogramBin]`

Used at:
- `mc/ebitda_mc.py:672` — internal use
- `mc/portfolio_monte_carlo.py:173` — sibling use
- `mc/v2_monte_carlo.py:641` — sibling use

3 use-sites; 1 is intra-module, 2 are cross-module. Strong case for promotion to public `histogram`.

### Comparison to other subpackages

| Subpackage | Cycles | Cross-pkg imports | Privacy violations |
|---|---|---|---|
| `domain/` (Report 0095) | 0 | 0 (stdlib only) | 0 |
| `auth/` (Reports 0021-0075) | 0 | minimal | 0 (Report 0075) |
| `analysis/` (Report 0022) | 0 (clean) | several | (TBD) |
| `infra/` (Report 0052) | 0 (clean) | minimal | (TBD) |
| `compliance/` (Report 0082) | 0 (clean) | (TBD) | (TBD) |
| **`mc/` (this report)** | **0** | **3 edges to pe/ + finance/** | **1 (`_histogram`)** |

`mc/` is **structurally clean** but has the privacy-convention smell.

### Schema-vs-import discipline

`mc/mc_store.py` (per Report 0110) is one of the 8+ modules that violates CLAUDE.md "store is the only module that talks to SQLite directly." Consistent with Report 0111 MR626 project-wide finding.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR627** | **`_histogram` (private name) imported across mc/ siblings** | Two 700+-line modules cross the privacy boundary. Either promote to `histogram` (public) or move to `mc/_helpers.py`. | Medium |
| **MR628** | **`mc/v2_monte_carlo.py:41` imports `ReimbursementProfile`** — the name-colliding symbol per Report 0094 MR516 | Code is correct but reader must check source path to disambiguate. Project-wide footgun. | Medium |
| **MR629** | **4 of 7 `mc/` modules never reported** in 111 prior iterations: convergence, portfolio_monte_carlo, v2_monte_carlo, mc_store partly | Add to Report 0091 backlog. **HIGH-PRIORITY**. | High |
| **MR630** | **`v2_monte_carlo.py` (733 lines) and `ebitda_mc.py` (760 lines) are very large** | Per CLAUDE.md no module-size convention, but these rival server.py-section size. Refactor candidate if structural cleanup is later prioritized. | Low |
| **MR631** | **`mc/__init__.py` re-export pattern uses `noqa: F401` 4×** | Standard for re-exports, but cross-link Report 0105 noqa density. F401 here is correct. | (clean) |

## Dependencies

- **Incoming:** Reports 0008/0017/0077 (`analysis_runs`), Report 0027 (ServerConfig), Report 0093 (`ml/scenario_comparison.py` cross-link), `analysis/packet_builder` (likely consumer of MonteCarloResult).
- **Outgoing:** numpy, stdlib, `pe/rcm_ebitda_bridge`, `pe/value_bridge_v2`, `finance/reimbursement_engine`, `mc/convergence`, `mc/ebitda_mc`.

## Open questions / Unknowns

- **Q1.** What's in `pe/value_bridge_v2.py` (cross-imported from v2_monte_carlo)? Per Reports 0044, 0045: pe/ partially mapped; this file specifically TBD.
- **Q2.** Is `_histogram` a 30-line trivial helper or a substantial function? Read `ebitda_mc.py:696-720` next iteration.
- **Q3.** Do any tests directly test `mc_store.py`, `portfolio_monte_carlo.py`, `v2_monte_carlo.py`?
- **Q4.** Does `MonteCarloResult` (per `mc_store.py:14 from .ebitda_mc import MonteCarloResult`) flow into `DealAnalysisPacket` (Report 0057)?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0113** | Schema-walk `mc_simulation_runs` table (Report 0110 MR616 backlog); likely owned by `mc/mc_store.py`. |
| **0114** | Read `mc/ebitda_mc.py` head + `_histogram` body (closes Q2). |
| **0115** | Read `pe/value_bridge_v2.py` (closes Q1). |
| **0116** | Map `rcm_mc_diligence/` separate package (carried 11+ iterations). |

---

Report/Report-0112.md written.
Next iteration should: schema-walk `mc_simulation_runs` table — likely owned by `mc/mc_store.py` per the import chain (Report 0110 MR616 backlog).
