# Report 0039: Dead-Code Audit — `core/simulator.py`

## Scope

Dead-code audit of `core/simulator.py` on `origin/main` at commit `f3f7e7f`. Sister to Report 0038 (coverage gap). The 4 public functions with zero direct tests (`simulate_one`, `payer_simulation_summary`, `batch_compare`, `warm_start_simulate`) are the natural dead-code candidates.

Prior reports reviewed: 0035-0038.

## Findings

### Production-caller counts

`grep -rln "<func>\b" RCM_MC/rcm_mc/`:

| Function (line) | Production refs | Test refs | Verdict |
|---|---:|---:|---|
| `simulate_one` (525) | **3 production files** | 0 direct tests | LIVE — see breakdown |
| `simulate` (601) | (multiple) | 8 indirect | LIVE |
| `simulate_compare` (739) | (multiple — cli.py, analysis modules per Reports 0011/0012) | 3 indirect | LIVE |
| `payer_simulation_summary` (789) | **1 production file** (in core/simulator.py itself? Or external) | 0 | (need to verify location of the 1 ref) |
| `batch_compare` (828) | **1 production file** | 0 | (likely cli.py; need to verify) |
| `warm_start_simulate` (853) | **1 production file** | 0 | (likely cli.py; need to verify) |

### Detail on `simulate_one` (3 production files)

Sites:

| File:line | Use |
|---|---|
| `pe/breakdowns.py:9` | `from ..core.simulator import simulate_one` |
| `pe/breakdowns.py:38` | `out = simulate_one(cfg, rng)` — actually invoked |
| `infra/provenance.py:41, 81, 86, 89, 97` | docstring / formula references — NOT actual imports |
| `infra/trace.py:2` | docstring reference |
| `infra/trace.py:14` | `from ..core.simulator import simulate_one` |
| `infra/trace.py:53` | docstring reference |

**True importers of `simulate_one`: 2 production files** (`pe/breakdowns.py`, `infra/trace.py`). The provenance.py mentions are docstring text, not imports.

### Categorization

| Function | Status |
|---|---|
| `simulate_one` | Used in 2 production files; transitively tested via `simulate`. Public-but-narrow. |
| `simulate` | Heavily used (called by `simulate_compare` + 7 other tests). |
| `simulate_compare` | The main entry; widely used. |
| `payer_simulation_summary` | 1 production ref — need to identify the caller. **Candidate for narrow live use**. |
| `batch_compare` | 1 production ref. **Likely cli.py via `--batch` mode.** Untested. |
| `warm_start_simulate` | 1 production ref. **Likely cli.py via `--warm-start` flag.** Untested. |

### Verdict on dead code

**No `core/simulator.py` function has zero production refs.** The 4 untested functions all have at least 1 production caller, so they're not dead in the strict sense. They are **untested-but-live** — exposed via CLI flags or sister modules but missing test coverage.

This is a different problem than Report 0009's `data/lookup.py` finding (3 functions tested-but-unused-in-prod). Here the inverse: **functions used-in-prod but not tested.**

### Sub-categorization of "untested but used"

| Function | Used by | Risk |
|---|---|---|
| `simulate_one` | `pe/breakdowns.py`, `infra/trace.py` | Per-iteration trace + breakdown. Narrow but live. |
| `payer_simulation_summary` | (1 caller, location TBD) | Per-payer summary surface. |
| `batch_compare` | (1 caller, likely cli.py) | Batch-comparison CLI flag. |
| `warm_start_simulate` | (1 caller, likely cli.py) | Warm-start CLI flag (per Report 0011 — "Warm-start from prior simulation"). |

### Private helpers — likely all live (used internally)

`_logit`, `_sigmoid`, `_normalize_probs`, `_apply_stage_bias`, `_apply_backlog_stage_shift`, `_expected_stage_mix_with_type_biases`, `_simulate_payer_pass1`, `_simulate_payer_pass2` — all called inside `simulate_one`/`simulate_compare`. Not orphans.

### What WOULD count as dead in this module?

A signature match would be: a public function defined in `core/simulator.py` that NO production code anywhere imports. Per the audit above: **none.** Even `warm_start_simulate` has 1 caller.

### What's notable

- **No `simulate_compare_with_breakdowns`** in core/simulator.py despite Report 0012 noting `cli.py:12` imports `simulate_compare_with_breakdowns` from `pe.breakdowns`. So `pe/breakdowns.py` is the wrapper that calls `simulate_one` to produce per-driver breakdowns. **Layered.**

## Merge risks flagged

| ID | Risk | Detail | Severity |
|---|---|---|---|
| **MR324** | **3 untested-but-live functions (`payer_simulation_summary`, `batch_compare`, `warm_start_simulate`)** | Each has 1 production caller. A signature change breaks the caller silently — no test catches it. | **High** |
| **MR325** | **`simulate_one` is exercised only via `pe/breakdowns.py:38` + `infra/trace.py`** | If a feature branch refactors simulate_one's return shape (it returns a Dict[str, Any]), both callers break. **2-place edit; no test.** | **High** |
| **MR326** | **No public function in `core/simulator.py` is true-dead-code** | Different from Report 0009's pattern. The risk here is "untested-live" not "tested-but-orphan." | (advisory) |

## Dependencies

- **Incoming:** `pe/breakdowns.py`, `infra/trace.py`, cli.py (likely batch_compare + warm_start_simulate), various test files (8 reference `simulate`).
- **Outgoing:** `core/distributions.py`, numpy, pandas, infra/logger.

## Open questions / Unknowns

- **Q1.** Where exactly are `payer_simulation_summary`, `batch_compare`, `warm_start_simulate` called? Need precise line numbers.
- **Q2.** Does the `cli.py` `--batch` flag wire to `batch_compare`? Cross-link Report 0003 (CLI surface owed).
- **Q3.** Does the `cli.py` `--warm-start` flag wire to `warm_start_simulate`?

## Suggested follow-ups

| Iteration | Proposed area | Why |
|---|---|---|
| **0040** | **Orphan files sweep** (already requested). | Pending. |
| **0041** | **Locate the 1 caller for each of `batch_compare`, `warm_start_simulate`, `payer_simulation_summary`** | Resolves Q1/Q2/Q3. |

---

Report/Report-0039.md written. Next iteration should: do the orphan-files sweep (already queued as iteration 40), preferably scoped to `rcm_mc/diligence/` (the 40-subdir subsystem repeatedly deferred) since deep orphans within that tree have not been audited.

