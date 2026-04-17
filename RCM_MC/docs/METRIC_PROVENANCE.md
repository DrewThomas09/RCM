# Metric dictionary and model provenance

This document is the human-readable source of truth for **how each headline number is defined**, **where it is computed**, and **which YAML inputs move it**. Machine-readable lineage for each run is written to `outputs/provenance.json` (or your `--outdir`).

---

## End-to-end chain

1. **Configs** (`configs/actual.yaml`, `configs/benchmark.yaml`) define priors and operating rules (payer mix, IDR/FWR distributions, appeals, capacity, underpayments, WACC).
2. **Optional calibration** (`--actual-data-dir`) rewrites Actual from CSVs; see `calibration.py`.
3. **Profile alignment** (default on): `profile.align_benchmark_to_actual` copies Actual’s revenue, payer `revenue_share`, and `avg_claim_dollars` into Benchmark so the gap is RCM performance, not volume.
4. **Per iteration**: `simulator.simulate_one` draws all random inputs, builds payer-level dollars, then totals.
5. **Compare**: `breakdowns.simulate_compare_with_breakdowns` sets `actual_*`, `bench_*`, `drag_* = actual - bench`, and `ebitda_drag = drag_rcm_ebitda_impact`.
6. **Scrub**: `data_scrub.scrub_simulation_data` caps drivers, winsorizes `ebitda_drag`, optional revenue cap (see caveats).
7. **Summarize**: `reporting.summary_table` computes mean, median, P10, P90, etc. over **scrubbed** `simulations.csv` columns.
8. **Report**: `html_report.generate_html_report` reads `summary.csv` and charts.

---

## Core columns in `simulations.csv`

| Column pattern | Meaning |
|----------------|---------|
| `actual_*` / `bench_*` | Single-scenario outcome for that iteration. |
| `drag_*` | `actual_* - bench_*` for the same component. |
| `ebitda_drag` | `drag_rcm_ebitda_impact` (total RCM friction gap, dollars). |
| `economic_drag` | `drag_economic_cost` (working-capital carry). |
| `actual_idr_{Payer}` etc. | Sampled driver for Actual that iteration (used in sensitivity). |

### `rcm_ebitda_impact` (within one scenario)

Computed in `simulator.simulate_one` totals:

- `leakage_total = denial_writeoff + underpay_leakage`
- `rework_total = denial_rework_cost + underpay_cost`
- **`rcm_ebitda_impact = leakage_total + rework_total`**

So EBITDA drag is **not** EBITDA reconciliation to GAAP; it is **modeled recoverable/leakage + rework** in dollar space.

### `economic_cost` / `economic_drag`

Per payer, `economic_cost ≈ ar_total_dollars * WACC` (see `simulator._simulate_payer_pass2`).  
`economic_drag` is the **difference** in that cost between Actual and Benchmark.

### `dar_total` / `drag_dar_total`

Hospital-level days-in-A/R proxy from simulated A/R dollars and net collectible velocity (`simulator.simulate_one`).

---

## `summary.csv` metrics (primary table)

Each row is a **distribution summary** over the `simulations.csv` column with the same name (after scrub).

| Metric | Definition (per iteration column) | Primary code | Main YAML levers |
|--------|-------------------------------------|--------------|------------------|
| **ebitda_drag** | `drag_rcm_ebitda_impact` | `breakdowns.py` → `reporting.summarize_distribution` | `payers.*.denials.{idr,fwr,...}`, `underpayments.*`, `appeals.*`, `operations.denial_capacity.*` |
| **economic_drag** | `drag_economic_cost` | same | `economics.wacc_annual`, `payers.*.dar_clean_days`, denial/underpay paths (A/R dollars) |
| **drag_denial_writeoff** | `drag_denial_writeoff` | same | `payers.*.denials.fwr`, IDR, stage mix, backlog/queue params |
| **drag_underpay_leakage** | `drag_underpay_leakage` | same | `payers.*.underpayments.{upr,severity,recovery}` |
| **drag_denial_rework_cost** | `drag_denial_rework_cost` | same | `appeals.stages.*`, denial volume, stage mix |
| **drag_underpay_cost** | `drag_underpay_cost` | same | underpayment case counts + followup cost specs |
| **drag_dar_total** | `drag_dar_total` | same | `dar_clean_days`, denial/underpay timing add-ons |
| **actual_rcm_ebitda_impact** | Actual scenario total friction | `simulator.simulate` | All Actual payer + ops blocks |
| **bench_rcm_ebitda_impact** | Benchmark scenario total friction | same | All Benchmark payer + ops blocks |

### Mean vs P10 vs P90

- **Mean**: arithmetic average over iterations (after scrub).
- **P10 / P90**: empirical quantiles of the **same** column. For drag, **higher P90** = heavier tail of underperformance vs benchmark in that run ensemble.

---

## Caveats (always disclose)

1. **Scrubbing** (`data_scrub.py`): driver caps, P99.5 winsor on `ebitda_drag`, optional max drag vs revenue — **summary stats reflect scrubbed data**, not raw draws.
2. **Alignment**: if `--no-align-profile` is off (default), Benchmark payer mix matches Actual; reported gap is not “different hospitals,” it’s “different RCM parameters on the same profile.”
3. **EV translation**: `mean(ebitda_drag) * ev_multiple` is a **valuation shorthand**, not a DCF.

---

## Related files

- `provenance.json` — per-run manifest + metric lineage (generated).
- `docs/MODEL_IMPROVEMENT.md` — calibration, validation, optional ML/surrogate roadmap.
- `simulation_trace.json` — optional single-iteration drill-down (`--trace-iteration N`).
