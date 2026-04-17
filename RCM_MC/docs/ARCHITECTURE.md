# Architecture

Technical reference for the RCM Monte Carlo engine: what it models, where inputs come from, how they move through the simulator, and what the outputs mean. For metric-by-metric definitions, see [METRIC_PROVENANCE.md](METRIC_PROVENANCE.md). For the source of truth on any formula, read [rcm_mc/simulator.py](../rcm_mc/simulator.py).

---

## 1. Purpose

The system estimates how much recurring EBITDA (and, optionally, enterprise value) is tied up in RCM friction — denials, underpayments, rework, slow cash — by comparing two fully-specified hospital scenarios (**Actual** vs **Benchmark**) on the same financial profile (same scale and payer mix when profile alignment is on).

Uncertainty is handled with Monte Carlo simulation: each iteration draws plausible values for dozens of correlated inputs, computes dollar outcomes, and the ensemble produces distributions (mean, P10, P90) rather than a single point estimate.

### What it is
- A structured, repeatable way to translate YAML-encoded assumptions (and optional CSV calibration) into distributions of RCM drag and attribution to drivers.
- A comparison engine: almost every headline is **Actual − Benchmark** on a comparable hospital, so the signal is operating / RCM performance rather than revenue size.

### What it is not
- Not a full hospital income-statement model (no labor, supplies, or volume forecasting).
- Not a guarantee of recoverable dollars; it is a probabilistic view under stated assumptions.
- EV translation (`EBITDA drag × multiple`) is a valuation shorthand, not a discounted cash flow.

---

## 2. Three data layers

### Layer A — Scenario configs (YAML)

Typically `configs/actual.yaml` and `configs/benchmark.yaml`.

**Structure:**
- **Hospital:** name, annual revenue (NPSR proxy), optional EBITDA margin, debt, RCM spend.
- **Economics:** `wacc_annual` for working-capital carry; optional EV multiple.
- **Operations:** denial capacity (FTE, throughput), backlog rules, outsourcing cost hooks.
- **Payers** (Medicare / Medicaid / Commercial / SelfPay / …):
  - `revenue_share`, `avg_claim_dollars`
  - **Denials:** IDR / FWR distributions, appeal-stage mix, denial-type taxonomy (clinical / coding / admin) with odds multipliers and stage biases
  - **Underpayments:** rate, severity, recovery, follow-up cost, timing
  - **Timing:** clean DAR distributions
  - Optional **claim-size buckets** for size-dependent denial behavior

Loaded by `rcm_mc.config.load_and_validate`, which parses, validates, resolves distributions, and returns the in-memory `cfg` dict.

### Layer B — Industry benchmarks (documentation)

The **Benchmark** YAML is written to be consistent with published industry ranges (AHA, HFMA MAP concepts, Kodiak / HealthLeaders A/R stats). See [BENCHMARK_SOURCES.md](BENCHMARK_SOURCES.md) for the source map. Nothing automatic reads that file — it is for humans. The machine input is the Benchmark YAML.

### Layer C — Optional diligence data (CSV packages)

Triggered by `--actual-data-dir` (and rarely `--benchmark-data-dir`).

| Logical role | Filenames searched |
|--------------|--------------------|
| Claims / revenue by payer | `claims_summary*.csv`, `claims.csv`, `revenue_summary*.csv` |
| Denials | `denials*.csv` |
| A/R aging | `ar_aging*.csv`, `aging.csv`, `ar_summary*.csv` |

`rcm_mc.calibration.calibrate_config`:
- Detects encoding and delimiter.
- Maps flexible column names (payer / amount / writeoff aliases).
- Resolves payer name aliases (BCBS, UHC, Medi-Cal, …).
- Builds a `DataQualityReport` (row counts, nulls, date ranges, payers found, which parameters were updated vs left at prior).
- Updates Actual payer-level parameters when the data supports it, subject to validation and quality gates.

**Calibration outputs:** `calibration_actual_report.csv`, `calibrated_actual.yaml`, `data_quality_report.json`, optional `anomalies.json`. Demo package: `data_demo/` (synthetic, non-PHI).

---

## 3. End-to-end pipeline

1. **Load** Actual and Benchmark YAML → validated configs.
2. **Optional:** merge JSON scenario adjustments (`--scenario`) into Actual via `scenario_builder.apply_scenario_dict`.
3. **Optional:** calibrate Actual (and/or Benchmark) from CSV directories.
4. **Optional:** align Benchmark to Actual (`profile.align_benchmark_to_actual`, default **on**): copy hospital scale and payer-level `revenue_share` / `avg_claim_dollars` so the comparison is not confounded by volume or mix.
5. **Simulate:** many iterations of `simulate_one` for Actual and Benchmark (separate RNG streams).
6. **Compare:** build `actual_*`, `bench_*`, and `drag_* = actual − bench`; define `ebitda_drag = drag_rcm_ebitda_impact`.
7. **Optional:** breakdowns by payer × denial type, payer × stage, underpayments.
8. **Scrub** (`data_scrub.scrub_simulation_data`): cap extreme drivers, winsorize tails, optionally cap drag vs revenue; rename `sim` → `iteration` for board-facing outputs.
9. **Summarize:** `summary.csv` with mean, median, P10, P90.
10. **Prove:** `provenance.json` with run metadata and metric formulas.
11. **Report:** HTML / Markdown / optional PPTX, charts, optional attribution, stress tests, initiatives, value plan.

---

## 4. Simulation engine (per iteration)

Entry point: `rcm_mc.simulator.simulate_one(cfg, rng)`.

### 4.1 Revenue and claims
Annual revenue × payer `revenue_share` → payer revenue. `avg_claim_dollars` anchors claim volume for Poisson-style counts.

### 4.2 Denials
- **IDR** and **FWR** sampled from configured distributions (beta, etc.).
- **Denial-type mix** Dirichlet-sampled with configurable concentration.
- **Stage mix** (L1 / L2 / L3 by default; configurable) biased by denial type; backlog logic shifts mass toward higher stages under capacity stress.
- Optional **claim-size buckets** change denial probability per bucket.
- Pass 2 resolves dollars through appeal stages, realized write-offs, and rework costs.

### 4.3 Capacity and backlog
`rcm_mc.capacity` computes whether denial workload exceeds capacity, derives backlog multipliers, and feeds queue-wait metrics. Outsourced cost appears in capacity results when configured and flows into totals.

### 4.4 Underpayments
When enabled, underpayment cases and dollar leakage follow configured UPR, severity, recovery, and follow-up cost distributions.

### 4.5 Working-capital cost
Economic cost approximates financing carry on trapped receivables using WACC and simulated A/R dollars. Kept distinct from core RCM EBITDA impact so reports can separate RCM friction from working-capital drag.

### 4.6 Hospital totals and EBITDA definition
- **Leakage** = denial write-offs + underpayment leakage
- **Rework** = denial rework + underpayment follow-up cost
- **`rcm_ebitda_impact`** = leakage + rework + outsourced_cost
- **`economic_cost`** = WACC × trapped receivables (separate bucket)
- **`rcm_ebitda_impact_incl_wc`** = `rcm_ebitda_impact` + `economic_cost` for "all-in" views

`simulate` builds a DataFrame with one row per iteration and a `sim` index column. `simulate_compare` runs Actual and Benchmark and aligns rows by `sim`.

---

## 5. Compare semantics

`simulate_compare` produces:
- Side-by-side `actual_*` and `bench_*` columns.
- `drag_*` = Actual − Benchmark.
- **`ebitda_drag`** = **`drag_rcm_ebitda_impact`** (the gap in RCM friction + outsourced dollars between scenarios).
- **`economic_drag`** = `drag_economic_cost`.

The primary "EBITDA drag" headline is not a GAAP reconciliation; it is the modeled gap in RCM-related friction dollars between two scenarios paired by iteration index.

Summary statistics are computed on **scrubbed** `simulations.csv`. Raw engine traces (`--trace-iteration`) are pre-scrub.

---

## 6. Outputs

| Artifact | Role |
|----------|------|
| `simulations.csv` | One row per iteration (scrubbed). `iteration` column plus `actual_*`, `bench_*`, `drag_*`, drivers |
| `summary.csv` | Distribution summary (mean, P10, P90) per metric |
| `provenance.json` | Run manifest, formulas, scrub metadata |
| `assumptions_actual.csv` / `assumptions_benchmark.csv` | Monte Carlo sampling summary |
| Driver CSVs | Mean breakdowns by payer × type / stage / underpayment |
| `sensitivity.csv` | Correlation of drivers to `ebitda_drag` |
| `strategic_priority_matrix.csv` | Derived from sensitivity |
| `waterfall.png`, `ebitda_drag_distribution.png`, `deal_summary.png` | Charts |
| `report.html` | Executive HTML report |
| `full_report.html` | Extended narrative + methodology (`--full-report`) |
| `simulation_trace.json` | Single-iteration audit (`--trace-iteration N`) |
| `runs.sqlite` | Run history (`--list-runs`) |

Optional: `report.md`, `summary.json`, attribution CSVs, stress tests, initiative rankings, value-creation CSVs, `report.pptx`.

---

## 7. CLI capabilities

The CLI (`rcm-mc` or `python -m rcm_mc.cli`) exposes:

- **`--explain-config`** — flattened view of all resolved config keys.
- **`--scenario`** — JSON structured adjustments applied before validation.
- **`--pptx`** — PowerPoint export.
- **`--list-runs`** — inspect `runs.sqlite`.
- **`--template`** — start from `configs/templates/*.yaml`.
- **`--validate-only`**, **`--diff`**, **`--screen`**, **`--trace-iteration`**, **`--full-report`**, **`--attribution`**, **`--initiatives`**, **`--stress`**, **`--value-plan`**, **`--compare-to`**, **`--json-output`**, **`--markdown`**, **`--theme`**.

Engine internals include: capacity integration in the main path, dollar-weighted portfolio queue metrics, FWR base vs realized driver columns, convergence / early-stop logic, NaN/inf sanitization, `rcm_ebitda_impact_incl_wc`, scenario builder for JSON-driven runs, and provenance paths that follow resolved template / actual paths.

---

## 8. Related subpackages

- **`rcm_mc.portfolio_cli`** — alternate entry point for multi-site portfolio workflows.

---

## 9. Limitations

1. **Calibration quality** depends on CSV completeness and column mapping. Always read `data_quality_report.json` and `calibration_actual_report.csv`.
2. **Scrubbing** changes tail behavior. Disclose that board-facing summaries use scrubbed data.
3. **Profile alignment** changes interpretation: default compares same-scale/mix; turning it off compares raw configs (different hospital economics).
4. **Sensitivity** is correlation-based unless you invest in fuller global variance methods.
5. **Regulatory / PHI:** treat real diligence extracts under your compliance policy; use `data_demo/` for learning.

---

*For exact metric formulas on a given run, prefer `provenance.json` + [METRIC_PROVENANCE.md](METRIC_PROVENANCE.md), and verify against [rcm_mc/simulator.py](../rcm_mc/simulator.py) for engine truth.*
