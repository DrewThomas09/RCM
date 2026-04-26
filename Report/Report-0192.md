# Report 0192: Data Flow Trace — `benchmark.yaml` → MC Simulator

## Scope

Traces `configs/benchmark.yaml` (Report 0191) flow into MC simulator. Sister to Reports 0011 (actual.yaml), 0102 (data refresh), 0162 (value_plan.yaml).

## Findings

### Hop-by-hop

#### Hop 1 — File on disk

`RCM_MC/configs/benchmark.yaml` (~150 LOC). Default-shipped per Report 0101 `[tool.setuptools.package-data]`.

#### Hop 2 — CLI flag

`rcm-mc run --benchmark configs/benchmark.yaml ...` per CLAUDE.md "Running" + Report 0163 cli.py.

#### Hop 3 — `yaml.safe_load`

Per Reports 0131/0132/0161: project standard. **Parseable** (Report 0132 verified).

#### Hop 4 — `infra/config.load_and_validate` (per cli.py:15 import)

Per Report 0163 cli.py imports: `from .infra.config import load_and_validate`. Likely the entry validator.

#### Hop 5 — Per-section consumers

Per Report 0191 schema sections:
- `analysis` (n_sims, seed, working_days) → MC simulator
- `economics.wacc_annual` → DCF / pe_math
- `operations.denial_capacity` → simulator capacity model
- `appeals.stages.{L1,L2,L3}.{cost,days}` → claim-distribution sampling
- `underpayments.enabled` → feature flag

**5+ separate consumer modules per benchmark.yaml.**

#### Hop 6 — `core/distributions.sample_dist`

Per Report 0095 + 0129: `sample_dist(rng, spec, size)` consumes `{dist: lognormal, mean, sd}` shape.

The `appeals.stages.L1.cost` value flows into `sample_dist` calls during MC iteration. Cross-link Report 0117 `mc_simulation_runs.result_json` for output.

#### Hop 7 — Output

Per Report 0117: `MonteCarloResult` embeds benchmark-driven distribution. Per Report 0148: hash_inputs MAY include benchmark fields (cross-link Report 0148 MR823).

### Cross-link Report 0148 hash_inputs

Per Report 0148: hash_inputs includes `observed_metrics`, `profile`, `analyst_overrides` — but NOT raw benchmark.yaml content. **A benchmark.yaml change that affects MC results does NOT bust the cache** unless reflected in `observed_metrics` or upstream call.

**MR958 below** — same risk class as Report 0148 MR823 / 0162 MR874.

### Distribution-spec safety

The `{dist: lognormal, mean: 15, sd: 5}` syntax is consumed via `core/distributions.sample_dist` (Report 0129). Per Report 0129 MR734: scipy missing → silent degradation for `normal_trunc`. **lognormal/gamma/etc. don't trigger that fallback** — benchmark.yaml's lognormal specs are safe.

### Provenance flag (cross-link Report 0174)

Per Report 0191: `_source_map._default: prior`. Means every value is a "prior" (synthetic from industry source, not real-cohort calibrated). **Cross-link Report 0093 ml/README provenance**: `synthetic-priors` until ≥30 real closed-deal labels.

**benchmark.yaml is canonical "synthetic-priors" data.**

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR958** | **`hash_inputs` does NOT include benchmark.yaml content** | Cross-link Report 0148 MR823 + Report 0162 MR874. Same risk class. **Same fix: include benchmark content-hash in hash_inputs payload.** | High |
| **MR959** | **FY24-stamped benchmark.yaml** — staleness invisible to runtime | Per Report 0191 MR957. | (carried) |

## Dependencies

- **Incoming:** `rcm-mc run --benchmark` CLI, demo.py, tests.
- **Outgoing:** simulator, pe/breakdowns, `core/distributions.sample_dist`.

## Open questions / Unknowns

- **Q1.** Does `infra/config.load_and_validate` validate benchmark.yaml schema?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0193** | (next iteration TBD). |

---

Report/Report-0192.md written.
