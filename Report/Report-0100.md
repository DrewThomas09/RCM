# Report 0100: Orphan Files — Sweep of 13 Newly-Discovered Subpackages + 2 More Found

## Scope

Orphan-file sweep across the 13 sibling subpackages discovered in Report 0097 MR529 (`pricing/`, `market_intel/`, `montecarlo_v3/`, `vbc/`, `sector_themes/`, `referral/`, `exit_readiness/`, `esg/`, `comparables/`, `buyandbuild/`, `vbc_contracts/`, `regulatory/`, `qoe/`). Sister to Reports 0010, 0040, 0070 (orphan sweeps). **Iteration 100 milestone.**

## Findings

### Subpackage-level import sanity check

| Subpackage | .py files | Prod importers | Test importers | Orphan? |
|---|---|---|---|---|
| `pricing/` | 9 | 2 | 9 | NO |
| `market_intel/` | 7 | 8 | 2 | NO |
| `montecarlo_v3/` | 9 | 1 | 1 | low fanin |
| `vbc/` | 7 | 8 | 3 | NO |
| `sector_themes/` | 7 | 2 | 2 | NO |
| `referral/` | 6 | 3 | 2 | NO |
| `exit_readiness/` | 7 | 2 | 2 | NO |
| `esg/` | 7 | 2 | 2 | NO |
| `comparables/` | 7 | 4 | 1 | NO |
| `buyandbuild/` | 7 | 1 | 2 | low fanin |
| `vbc_contracts/` | 6 | 1 | 1 | low fanin |
| `regulatory/` | 6 | 10 | 2 | NO |
| `qoe/` | 6 | 2 | 2 | NO |

**Zero subpackages are fully orphaned.** Lowest-fanin trio: `montecarlo_v3`, `buyandbuild`, `vbc_contracts` — each has 1 production importer.

### Discovery: per-file fanout is zero (namespace re-export pattern)

Per-file `grep` for direct submodule imports (e.g. `from rcm_mc.vbc_contracts.bayesian import ...`):

**`vbc_contracts/`** (5 submodules + __init__):

| Submodule | Direct importers |
|---|---|
| `bayesian.py` | 0 |
| `posterior.py` | 0 |
| `programs.py` | 0 |
| `stochastic.py` | 0 |
| `valuator.py` | 0 |

**`montecarlo_v3/`** (8 submodules + __init__):

| Submodule | Direct importers |
|---|---|
| `antithetic.py` | 0 |
| `control_variates.py` | 0 |
| `copula.py` | 0 |
| `healthcare.py` | 0 |
| `importance.py` | 0 |
| `nested.py` | 0 |
| `sobol.py` | 0 |
| `stratified.py` | 0 |

**Every submodule has 0 direct importers.** All access flows through `__init__.py` which re-exports the public names.

This is **a Python namespace-aggregator pattern**, not orphan-file dead-code. But it has consequences:
- Mass renames must update `__init__.py`, not files outside the subpackage.
- A submodule deleted without `__init__.py` cleanup leaves an `ImportError` only at first import.
- Static-analysis tools that look for "module is imported by name" find these files orphan-by-default.

### Importers of `vbc_contracts/` and `montecarlo_v3/`

**vbc_contracts/** importers:
- `tests/test_vbc_contracts.py`
- `rcm_mc/diligence_synthesis/runner.py` ← **HIGH-PRIORITY DISCOVERY**

**montecarlo_v3/** importers:
- `tests/test_montecarlo_v3.py`
- `rcm_mc/diligence_synthesis/runner.py` ← **HIGH-PRIORITY DISCOVERY**

Same orchestrator imports both. **`diligence_synthesis/` is a NEW unmapped subpackage** never reported in 99 prior iterations.

### HIGH-PRIORITY DISCOVERY: 2 more unmapped subpackages

In addition to the 13 from Report 0097:

| Subpackage | .py files | Lines | Status |
|---|---|---|---|
| `rcm_mc/diligence_synthesis/` | 3 (+ README + __init__) | 404 | **never reported** |
| `rcm_mc/ic_binder/` | (TBD) | (TBD) | **never reported** |

`diligence_synthesis/`:
- `__init__.py` (37 lines)
- `dossier.py` (93 lines)
- `runner.py` (274 lines)
- `README.md`

`ic_binder/`:
- `__init__.py` (per `grep`)
- Other files TBD this iteration.

**Total unmapped subpackages now: 15** (was 13 per Report 0097). Plus `diligence_synthesis` is the **gateway** that links `vbc_contracts` + `montecarlo_v3` — strong central importer.

### Filesystem orphans (cruft)

`find RCM_MC/rcm_mc/ -name "*.orig" -o -name ".DS_Store" -o -name "*.bak"`:

**Zero results.** No backup, no .orig from merge conflicts, no macOS metadata files. `__pycache__/` is the only build artifact, ignored per `.gitignore` (Report 0001).

**Filesystem cruft is clean.** Stronger discipline than typical.

### Re-export pattern: cross-link to Reports 0093, 0094

- Report 0093 (`ml/`): 41 modules; only 4 publicly re-exported. Heavy direct-path imports.
- Report 0094 (`domain/`): 3 modules; 14 re-exports. Cleaner aggregation.
- This report (`vbc_contracts/`, `montecarlo_v3/`): 0 direct submodule imports outside the subpackage. **Pure namespace-aggregator.**

**Three distinct organizing styles in the codebase.** No single convention enforced.

### Per-Report 0091 list updates

Pre-this-iteration unmapped count (post Report 0091): ~15-20 subpackages.
Post Report 0097 + this report: **17+ subpackages still unmapped, 2 newly discovered.**

Cross-link Report 0099 dead-code finding: `domain/custom_metrics.py` had 5 unused imports + 1 dead branch. That's a sample of `domain/`. Likely similar gear in 17 unmapped subpackages × ~5 unused imports each = ~85+ dead-import sites.

### Tests for the namespace pattern

- `test_vbc_contracts.py` → exists.
- `test_montecarlo_v3.py` → exists.
- `test_diligence_synthesis.py` → exists (per grep result).
- `test_ic_binder.py` → exists.

**Per-subpackage test files exist** for the 4 sampled. Cross-link to CLAUDE.md "each feature has a `test_<feature>.py`" — convention upheld here.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR544** | **2 NEW unmapped subpackages discovered (`diligence_synthesis/` + `ic_binder/`)** beyond the 13 from Report 0097 — total 15. **HIGH-PRIORITY**. | **Critical** |
| **MR545** | **`__init__.py` re-export pattern in `vbc_contracts/` + `montecarlo_v3/` masks per-submodule import dependencies** | A submodule deleted without `__init__.py` line removed produces ImportError at runtime, not commit time. Pre-commit hook (Report 0056) won't catch. | Medium |
| **MR546** | **3 distinct subpackage-organization styles coexist** (`ml/` direct-path; `domain/` re-export-most; `vbc_contracts/` re-export-all) | No single convention enforced. New subpackages may pick whichever pattern; cross-team confusion. | Low |
| **MR547** | **`diligence_synthesis/runner.py` is the single shared importer of `vbc_contracts` + `montecarlo_v3`** | Single point of breakage. If runner.py is refactored or deleted, both subpackages have only 1 prod importer remaining (zero, in fact, since both other importers are tests). | **High** |
| **MR548** | **`__pycache__/` directories present in 13+ subpackages** (per Report 0092 mention; confirmed in this sweep) | Build artifacts; .gitignore handles them. Local-only. No risk. | (clean) |

## Dependencies

- **Incoming:** Reports 0010, 0040, 0070 set the orphan-sweep baseline. Reports 0091 + 0097 established the unmapped-subpackage list.
- **Outgoing:** future iterations must prioritize the 15 unmapped subpackages — at 1 per iteration, that's 15+ iterations of mapping work.

## Open questions / Unknowns

- **Q1.** What's in `rcm_mc/ic_binder/`? Size, file count, public surface?
- **Q2.** What does `diligence_synthesis/runner.py` (274 lines) do — orchestrate the full diligence run?
- **Q3.** Are there MORE unmapped subpackages in `rcm_mc/` that this report missed?
- **Q4.** Is the `__init__.py` re-export pattern the new convention, or legacy in some subpackages?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0101** | `ls RCM_MC/rcm_mc/` — full directory inventory to close Q3 (find ALL unmapped subpackages once and for all). |
| **0102** | Map `rcm_mc/diligence_synthesis/` (closes Q2). |
| **0103** | Map `rcm_mc/ic_binder/` (closes Q1). |
| **0104** | Map `rcm_mc/pe_intelligence/` (perpetually deferred — Reports 0093 → 0098). |

---

Report/Report-0100.md written.
Next iteration should: full `ls RCM_MC/rcm_mc/` directory enumeration to find ALL remaining unmapped subpackages — close the never-ending discovery loop.
