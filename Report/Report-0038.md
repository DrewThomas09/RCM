# Report 0038: Test-Coverage Spot-Check — `core/simulator.py`

## Scope

Structural coverage audit of `RCM_MC/rcm_mc/core/simulator.py` on `origin/main` at commit `f3f7e7f`. The module is the Monte Carlo simulator core — entry points `simulate_one`, `simulate`, `simulate_compare` per Reports 0011/0012/0027/0029. Long-deferred audit target.

Prior reports reviewed: 0034-0037.

## Findings

### Module shape

- `core/simulator.py` — earlier reads found `simulate_one` at line 525, `simulate` at line 601, `simulate_compare` at line 739, `payer_simulation_summary` at line 789, `batch_compare` at line 828, `warm_start_simulate` at line 853 plus several helpers (`_logit`, `_sigmoid`, `_normalize_probs`, `_apply_stage_bias`, `_apply_backlog_stage_shift`, `_expected_stage_mix_with_type_biases`, `_simulate_payer_pass1`, `_simulate_payer_pass2`). **At least ~860 lines.**
- 6 public functions + 8 private helpers. Imports: `from .distributions import sample_dirichlet, sample_dist, sample_sum_iid_as_gamma` (Report 0013).

### Test coverage

Direct test file: `tests/test_simulator.py` — **only 25 lines!**

```python
import os
import unittest
import numpy as np
from rcm_mc.infra.config import load_and_validate
from rcm_mc.core.simulator import simulate_compare

class TestSimulator(unittest.TestCase):
    def test_simulation_runs_and_has_columns(self):
        base_dir = os.path.dirname(os.path.dirname(__file__))
        actual = os.path.join(base_dir, "configs", "actual.yaml")
        bench = os.path.join(base_dir, "configs", "benchmark.yaml")
        a = load_and_validate(actual)
        b = load_and_validate(bench)
        df = simulate_compare(a, b, n_sims=300, seed=123)
        self.assertIn("ebitda_drag", df.columns)
        self.assertIn("economic_drag", df.columns)
        self.assertIn("drag_denial_writeoff", df.columns)
        self.assertTrue(np.isfinite(df["ebitda_drag"]).all())
        self.assertGreater(df["ebitda_drag"].mean(), 0.0)
```

**ONE test method, one entry point exercised.** This is shockingly thin coverage for the load-bearing simulator.

### Per-public-function coverage table

| Function (line) | Test files referencing | Verdict |
|---|---:|---|
| `simulate_one` (525) | **0** | **UNTESTED directly.** Only exercised transitively via `simulate`. |
| `simulate` (601) | 8 | Adequate (used by other tests indirectly). |
| `simulate_compare` (739) | 3 | The single direct test (`test_simulator.py`) plus 2 sister tests. |
| `payer_simulation_summary` (789) | **0** | **UNTESTED.** |
| `batch_compare` (828) | **0** | **UNTESTED.** |
| `warm_start_simulate` (853) | **0** | **UNTESTED.** |

**4 of 6 public functions have ZERO direct test references.** The single test file (`test_simulator.py`) exercises one path through `simulate_compare` with one set of fixtures.

### Untested branches (likely)

- `_simulate_payer_pass1` (line 102, per Report 0012) — 0 direct tests; exercised transitively.
- `_simulate_payer_pass2` (line 284) — 0 direct tests; the capacity / backlog branch.
- `_apply_backlog_stage_shift`, `_expected_stage_mix_with_type_biases` — 0 direct tests; mathematical helpers used inside simulator passes.

### Coverage by complexity

| Complexity zone | Lines (approx) | Tests |
|---|---|---|
| Distribution sampling (helper functions ~ lines 15-100) | ~85 | 0 direct |
| Per-payer pass-1 (line 102-283) | 181 | 0 direct |
| Per-payer pass-2 (line 284-524) | 240 | 0 direct |
| `simulate_one` orchestrator (525-600) | 75 | 0 direct |
| `simulate` MC loop (601-738) | 137 | 8 indirect |
| `simulate_compare` (739-788) | 49 | 3 indirect |
| Other entry points (789-end) | ~70+ | 0 |

**Roughly 750+ lines of simulator code with 0 direct tests; only ~50 lines (the simulate_compare path) are exercised by the single existing test.**

### Output-shape verification only

The single test (`test_simulator.py:13-25`) verifies:

1. The output DataFrame has 3 expected columns: `ebitda_drag`, `economic_drag`, `drag_denial_writeoff`.
2. `ebitda_drag` is finite for all rows.
3. `ebitda_drag.mean() > 0.0` (an end-to-end smoke).

It does NOT verify:

- Per-payer pass-1 / pass-2 correctness.
- Distribution sampling semantics.
- Determinism (same seed → same df).
- Capacity / backlog effect under specified conditions.
- `n_sims` scaling behavior.
- Behavior with degenerate configs (zero payers, zero revenue, etc.).
- Output shape under `include_payer_drivers=True`.
- Convergence detection (early-stop, per Report 0012).
- Progress callback firing.

### CI status

Per Report 0026, the CI go-live test subset includes `test_full_pipeline_10_hospitals.py` — a heavier e2e test. **`test_simulator.py` is NOT in the CI gate.** The simulator's only direct test only runs in the weekly regression sweep (per Report 0026 regression-sweep.yml).

### Sibling tests that exercise simulator

| File | Function used |
|---|---|
| `tests/test_simulator.py` | `simulate_compare` directly (1 test) |
| `tests/test_claim_distribution.py` | likely `simulate_one` / `simulate` (count not measured) |
| `tests/test_queue.py` | likely capacity-related (`_simulate_payer_pass2`) |
| (5 more) | various — `simulate` referenced in 8 test files total |

Even the 8-file count is small relative to the simulator's complexity. **The simulator is the most under-tested critical-path module surveyed so far.**

## Merge risks flagged

| ID | Risk | Detail | Severity |
|---|---|---|---|
| **MR316** | **HIGH-PRIORITY: 4 of 6 public simulator functions have ZERO direct tests** | `simulate_one`, `payer_simulation_summary`, `batch_compare`, `warm_start_simulate`. **A regression in any of these passes silently in CI**. | **Critical** |
| **MR317** | **`test_simulator.py` is 25 lines for an ~860-line module** | Coverage ratio is dramatic. Smoke-only — no boundary tests, no determinism test, no failure-mode test. | **Critical** |
| **MR318** | **No determinism regression test** | `simulate(cfg, n_sims=300, seed=42)` must produce byte-identical output run-over-run. **No test pins this.** A branch that breaks RNG forking is silently undetected. (Cross-link Report 0012 MR90.) | **High** |
| **MR319** | **No degenerate-config tests** | What does `simulate` do when `cfg["payers"]` is empty? When `revenue = 0`? When `n_sims = 0`? Untested. | **High** |
| **MR320** | **Capacity / backlog branch (`_simulate_payer_pass2`) is 240+ lines, 0 direct tests** | This is the operations-modeling layer (denial capacity, backlog effects). Bugs here directly distort EBITDA drag. | **Critical** |
| **MR321** | **No `payer_simulation_summary` test** | The per-payer summary surface is untested. Pre-merge: any branch that changes its output shape passes CI. | **High** |
| **MR322** | **`warm_start_simulate` (line 853) is dead-untested** | Implies a feature added but not tested. Possible orphan-with-tests-pending. | Medium |
| **MR323** | **The single test depends on `configs/actual.yaml` + `configs/benchmark.yaml` shape** | If those YAMLs change in a future branch (Report 0011's schema drift), the test breaks. | Medium |

## Dependencies

- **Incoming:** test files (8); cli.py (per Report 0012); analysis/packet_builder.py (Report 0020); pe/ modules (likely).
- **Outgoing:** core/distributions.py (sample_dirichlet, sample_dist, sample_sum_iid_as_gamma per Report 0013), numpy, pandas, infra/logger (Pattern A).

## Open questions / Unknowns

- **Q1.** Why is `simulate_one` not directly tested? It's the per-iteration core — should have a test that fixes RNG seed and checks output dict shape.
- **Q2.** Does `tests/test_full_pipeline_10_hospitals.py` (the CI-gated test) exercise simulator paths that aren't covered by `test_simulator.py`?
- **Q3.** What's `warm_start_simulate` supposed to do? If untested, was it shipped in a feature branch and never integrated?

## Suggested follow-ups

| Iteration | Proposed area | Why |
|---|---|---|
| **0039** | **Dead-code audit** (already requested as Iteration 39). | Pending. |
| **0040** | **Orphan files** (already requested as Iteration 40). | Pending. |
| **0041** | **Read `tests/test_full_pipeline_10_hospitals.py`** — the heavier simulator coverage target. | Resolves Q2. |
| **0042** | **Read `core/simulator.py:simulate_one`** end-to-end — the per-iteration core. | Closes Q1. |
| **0043** | **Read `core/simulator.py:_simulate_payer_pass2`** — the 240-line untested capacity branch. | MR320 mitigation. |

---

Report/Report-0038.md written. Next iteration should: dead-code audit on `core/simulator.py` itself — given that 4 of 6 public functions have 0 direct tests, several may be defined-but-never-called externally (sister to Report 0009's data/lookup.py finding).

