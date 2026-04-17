# Layer: Monte Carlo (`rcm_mc/mc/`)

## TL;DR

Two-source Monte Carlo over the EBITDA bridge. Every simulation
combines (1) prediction uncertainty from the ridge predictor's
conformal CIs with (2) execution uncertainty from per-lever-family
beta distributions. Returns percentile bands on EBITDA, MOIC, IRR,
probability of covenant breach, variance-contribution decomposition,
and a convergence check. Partners can't underwrite a point estimate
in IC; this is what makes the platform credible.

## What this layer owns

- `RCMMonteCarloSimulator` — the simulator itself.
- `MetricAssumption` — per-lever uncertainty specification.
- Two-source sampling primitives (prediction + execution) with
  optional Cholesky-correlated prediction draws.
- Distribution summaries (p5/p10/p25/p50/p75/p90/p95/mean/std).
- Tornado bars, histogram bins, variance contribution.
- Convergence check (rolling P50 stability).
- Scenario comparison (pairwise win probabilities).
- SQLite persistence (`mc_simulation_runs` table).

## Files

### `ebitda_mc.py` (~620 lines)

**Purpose.** The simulator.

**Key enums / dataclasses.**
- `MetricAssumption` — spec for one lever:
  - `metric_key, current_value, target_value`
  - `uncertainty_source` — `conformal` / `manual` / `bootstrap` / `none`
  - `prediction_ci_low, prediction_ci_high` — treated as 5th/95th
    percentiles of the prediction marginal (normal with σ =
    (ci_high-ci_low)/2/1.645)
  - `execution_probability` — mean of the execution fraction draw
  - `execution_distribution` — `beta` / `normal` / `triangular` /
    `uniform` / `none`
  - `execution_params` — dist-specific parameters
  - `bootstrap_samples` — only for `uncertainty_source="bootstrap"`
- `DistributionSummary` — p5/p10/p25/p50/p75/p90/p95/mean/std.
  `from_array(arr)` class factory drops NaN/Inf.
- `TornadoBar` — metric, p10_impact, p90_impact, range.
- `HistogramBin` — bin_edge_low, bin_edge_high, count.
- `MonteCarloResult` — full output (15 fields).

**Simulator class.** `RCMMonteCarloSimulator(bridge, *,
n_simulations=10_000, seed=42)`.
- `configure(current_metrics, metric_assumptions, *,
  correlation_matrix, metric_order, entry_multiple, exit_multiple,
  hold_years, organic_growth_pct, moic_targets,
  covenant_leverage_threshold)` — lock the simulation before running.
  Correlation matrix must be (len(order), len(order)) with
  `metric_order` providing the column order.
- `run(*, scenario_label="") -> MonteCarloResult`.

**Sampling primitives.**
- `_sample_prediction(assumption, rng, uniform=None)` — draws from
  the prediction uncertainty distribution. When `uniform` is
  provided (from a correlated batch), uses it as the uniform
  quantile and applies the inverse-normal CDF via stdlib math.
- `_sample_execution(assumption, rng)` — draws from the execution
  distribution, clipped to [0, 1].
- `_make_uniforms(rng, n)` — Cholesky decomposition on the
  correlation matrix → correlated uniforms for the prediction
  marginals.

**The run loop.** For each sim:
1. For each lever: sample `predicted_target` (prediction noise) and
   `execution_fraction` (execution noise).
2. `final_value = current_value + (sampled_target − current_value) ×
   execution_fraction`.
3. Call `bridge.compute_bridge(current, final_values)`.
4. Record ebitda_impact, wc_release, MOIC, IRR, covenant breach.

**Output assembly.**
- Distribution summaries from raw arrays.
- `probability_of_target_moic` — `{"1.5x": P, "2x": P, ...}` —
  monotonically decreasing in target by construction.
- `variance_contribution` — normalized correlation-squared between
  each metric's sample column and the ebitda_impact output. Sums to
  1.0.
- `tornado_data` — per-metric `(p10_impact, p90_impact)` conditional
  on that metric being in its own P10 or P90 band.
- `histogram_data` — 30 bins, total count = `n_simulations`.
- `convergence_check` — uses `check_convergence()`.

**Convenience builders.**
- `default_execution_assumption(metric, *, current, target)` — uses
  `_LEVER_FAMILY_ALPHA_BETA` lookup. Denial management beta(7,3) →
  70% expected achievement; AR/collections beta(8,2) → 80%; CDI
  beta(6,4) → 60%; payer renegotiation beta(5,5) → 50%.
- `from_conformal_prediction(metric, *, current, target, ci_low,
  ci_high)` — prediction uncertainty from conformal CI + default
  execution from family.

**Numpy-free `_erf` and `_erfinv`.** Inline Abramowitz & Stegun +
Winitzki approximations so the CDF transforms work without scipy.

### `convergence.py` (~100 lines)

**Purpose.** Running-P50 convergence check.

**Public.** `check_convergence(results, *, window=1000,
tolerance=0.01) -> ConvergenceReport`.

**Mechanic.** Cumulative median at each step. Tail window = last
`window` steps. If `|max-min|/|p50_final| <= tolerance`, we've
converged. Otherwise recommend 2× the current N.

### `scenario_comparison.py` (~200 lines)

**Purpose.** Compare multiple MC scenarios (base / upside / downside
/ management plan) side-by-side.

**Public.** `compare_scenarios(simulator, scenarios, *,
risk_aversion=0.5) -> ScenarioComparison`.

**Output.**
- `per_scenario: dict[name, MonteCarloResult]`
- `pairwise_overlap: dict[str, float]` — `P(A beats B)` keyed as
  `"A__vs__B"`.
- `recommended_scenario: str` — highest `mean − risk_aversion ×
  downside_σ` score.
- `rationale: str`.

Re-runs each scenario with the deterministic seed so partners can
reproduce the comparison next quarter.

### `mc_store.py` (~180 lines)

**Purpose.** SQLite persistence for MC runs.

**Table.**
```sql
CREATE TABLE mc_simulation_runs (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_id TEXT NOT NULL,
    analysis_run_id TEXT,
    scenario_label TEXT NOT NULL DEFAULT '',
    n_simulations INTEGER NOT NULL DEFAULT 0,
    result_json BLOB NOT NULL,     -- zlib-compressed
    created_at TEXT NOT NULL
);
```

**Public surface.**
- `save_mc_run(store, deal_id, result, *, analysis_run_id=None)`.
- `load_latest_mc_run(store, deal_id, *, scenario_label=None)`.
- `list_mc_runs(store, deal_id=None)` — metadata only.

Append-only; partners can retrieve historical runs by scenario label.

### `__init__.py`

Re-exports `ConvergenceReport`, `check_convergence`,
`MetricAssumption`, `RCMMonteCarloSimulator`, `MonteCarloResult`,
`DistributionSummary`, `HistogramBin`, `TornadoBar`,
`default_execution_assumption`, `from_conformal_prediction`,
`ScenarioComparison`, `compare_scenarios`.

## How it fits the system

```
                ┌──────────────────────────────┐
                │ ml.ridge_predictor            │
                │ predicted_metrics with        │
                │ ci_low / ci_high              │
                └──────────────┬───────────────┘
                               │ conformal CIs
                               ▼
                ┌──────────────────────────────┐
                │ mc.ebitda_mc                  │
                │  from_conformal_prediction()  │
                │  + default_execution_         │
                │    assumption()               │
                │                                │
                │  RCMMonteCarloSimulator       │
                │   .configure(...)              │
                │   .run() → MonteCarloResult   │
                └──────────────┬───────────────┘
                               │
             ┌─────────────────┼──────────────────┐
             │                 │                  │
             ▼                 ▼                  ▼
  ┌──────────────────┐  ┌─────────────┐  ┌───────────────────┐
  │ packet.simulation │  │ pe_math.    │  │ mc_store.save     │
  │ (SimulationSummary│  │ hold_period_│  │ (mc_simulation_   │
  │  — flattened)     │  │ grid_with_mc│  │  runs table)      │
  │                   │  │ — P10/50/90 │  │                    │
  │                   │  │  MOIC cells │  │                    │
  └──────────────────┘  └─────────────┘  └───────────────────┘

  ┌──────────────────┐  ┌─────────────────┐
  │ scenario_comp.   │  │ convergence     │
  │ compare_scenarios│  │ check_          │
  │ — pairwise win P │  │ convergence     │
  └──────────────────┘  └─────────────────┘
```

## The two uncertainty sources, visualized

```
One simulation draw:

  1. Prediction uncertainty
     ┌──────────────────────────────┐
     │ Ridge predictor said         │
     │ denial_rate = 7.5% [6.0, 9.0]│
     │ Sample: 6.3% (from N(7.5, σ)) │
     └──────────────┬───────────────┘
                    │
                    ▼
  2. Execution uncertainty
     ┌──────────────────────────────┐
     │ Beta(7, 3) for denial mgmt   │
     │ Sample: 0.72 (72% achievement)│
     └──────────────┬───────────────┘
                    │
                    ▼
     Final value = current + (sampled_target − current) × exec_frac
                 = 12.0 + (6.3 − 12.0) × 0.72 = 7.9%
                    │
                    ▼
  3. Bridge compute
     ┌──────────────────────────────┐
     │ RCMEBITDABridge.compute_bridge│
     │  returns total_ebitda_impact │
     │  + MOIC + IRR                │
     └──────────────────────────────┘
                    │
                    ▼
  4. Repeat N_simulations times → distribution → percentiles
```

## API

- `POST /api/analysis/<deal_id>/simulate` — run MC with custom
  assumptions. Body: `{"assumptions": {metric: {...}}, "financials":
  {...}, "n_simulations": 2000, "seed": 42}`. Saves to
  `mc_simulation_runs`.
- `GET /api/analysis/<deal_id>/simulate/latest?scenario=X` — most
  recent stored run.
- `POST /api/analysis/<deal_id>/simulate/compare` — compare named
  scenarios. Body: `{"scenarios": {name: {metric: assumption}}}`.
- `POST /api/analysis/<deal_id>/simulate/v2` — run the v2 simulator
  (see below). Saves to `mc_simulation_runs` with a `v2:` prefix on
  `scenario_label` so v1 and v2 runs coexist in the same table.

## v2 simulator — `V2MonteCarloSimulator`

The v1 simulator above samples *two* noise sources — prediction CI
and execution probability — and runs each draw through the
research-band bridge. The **v2 simulator** in `mc/v2_monte_carlo.py`
runs the same prediction + execution draws through
`pe.value_bridge_v2.compute_value_bridge` and then layers four more
honest dimensions partners actually underwrite on:

| Dimension | Distribution | Mean | Note |
|---|---|---|---|
| `collection_realization` | beta, mean-locked | `base.collection_realization` (0.65) | concentration α+β ≈ 10 |
| `denial_overturn_rate` | beta, mean-locked | `base.denial_overturn_rate` (0.55) | concentration α+β ≈ 10 |
| `per_payer_revenue_leverage` | normal(μ, σ=0.05) per payer class | module default or `BridgeAssumptions.payer_revenue_leverage` override | clipped to [0.2, 1.2] |
| `exit_multiple` | triangular | mode = `base.exit_multiple` | default band [0.85×mode, 1.25×mode] |

The base assumption's `collection_realization` and
`denial_overturn_rate` stay the distribution *mean* (the beta is
rebalanced per-sim to honour the partner-supplied center), so a
partner-tuned base flows through unchanged when the simulator is run
in zero-variance mode.

### What `V2MonteCarloResult` carries

Unlike the v1 result (one `ebitda_impact` series), the v2 result
keeps **four distinct distributions** side-by-side:

- `recurring_ebitda_distribution` — capitalizable EBITDA lift
- `one_time_cash_distribution` — WC release, explicitly *not*
  capitalized into EV
- `ev_from_recurring_distribution` — `recurring_ebitda × exit_mult`
- `total_cash_distribution` — exit proceeds + one-time WC to equity
- `moic_distribution`, `irr_distribution`
- `variance_contribution` — per-dimension share of variance in
  recurring EBITDA, always summing to 1.0. Includes one
  `leverage:<payer>` entry per modelled payer class.
- `tornado_data` — sorted by |P90 − P10| descending
- `dependency_adjusted: bool` — always `True`. The v2 bridge walks
  the cross-lever dependency DAG (Prompt 15) on every sim, so v2
  output always reflects that adjustment. Flag is exposed so
  renderers sitting next to v1 output can label unambiguously.

### Zero-variance identity

`V2MonteCarloSimulator(...).configure(..., zero_variance=True).run()`
collapses every sampled dimension to its mean and reproduces the
deterministic `compute_value_bridge` output to the penny. Locked by
test — the v2 simulator is a strict generalization of the v2 bridge.

### Packet integration

`build_analysis_packet` runs the v2 simulator alongside the v1 MC
(step 8b in the orchestrator) whenever the v1 bridge produced levers.
The result dict lands on `DealAnalysisPacket.v2_simulation`
(optional; absent on packets that predate this section). The v1
`SimulationSummary` stays on `.simulation` — both coexist on the
packet so the workbench can render them side-by-side.

### v1 vs v2: when to use which

- **v1 (`RCMMonteCarloSimulator`)** — ties to the research-band
  calibration. Use when you want the partner-visible output to sit
  on top of the coefficient bridge that Phase-1 validated against
  the $400M NPR reference hospital.
- **v2 (`V2MonteCarloSimulator`)** — the unit-economics bridge with
  dependency-aware lever math and honest uncertainty on the deal-
  specific knobs. Use when you have a real payer mix and want EV
  from recurring to actually depend on commercial-vs-Medicaid tilt,
  or when you want exit-multiple compression reflected in the tail.

Both simulators run each build — no global switch — and the packet
carries both outputs. Renderers pick.

## Current state

### Strong points
- **Zero-variance identity.** When all uncertainty sources have zero
  spread, MC P50 matches the deterministic bridge exactly. Test
  locks this — the simulator is a strict generalization of the
  bridge, not a separate implementation.
- **Variance decomposition sums to 1.0.** Normalized correlation-
  squared gives an honest first-order Sobol-style attribution.
- **Monotone target MOIC probabilities** — P(MOIC ≥ 1.5x) ≥
  P(MOIC ≥ 2.0x) by construction. Test locks this.
- **Reproducibility.** Fixed seed + deterministic iteration order →
  same output every run.
- **No scipy.** Inline erf / erfinv. Project dep stays at numpy +
  pandas.
- 30 MC tests cover zero-variance identity, convergence, correlation,
  variance decomposition, packet integration, hold-period grid, MC
  store.

### Weak points
- **Python-loop inner.** 10K sims × 7 levers × bridge call is
  CPU-bound. Vectorizing the bridge call path is possible but risks
  breaking the 30 tests' calibration invariants. For now 2K sims is
  the default; 10K takes ~8-12s. The v2 simulator is similarly
  Python-loop-bound; vectorization is deferred to Prompt 19.
- **Independent execution draws.** Lever execution noise is
  independent across levers — no correlated execution structure
  (e.g., "if CDI fails, denials also won't improve"). Prompt 3
  summary flagged this.
- **Covenant model is simple.** Assumes 60% LTV debt + leverage turns
  at exit. No interim debt paydown schedule, no cash-trap triggers.
  (v1 only; the v2 simulator doesn't model covenants yet.)
- **v2 covenant model absent.** The v2 simulator doesn't produce
  `probability_of_covenant_breach` — add that when the debt
  structure is modelled on the deal packet.
