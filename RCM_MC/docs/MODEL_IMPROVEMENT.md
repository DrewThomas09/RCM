# Improving and “training” the RCM Monte Carlo model

This guide separates **governance** (making the model more trustworthy) from **optional ML** (speed or screening only).

## 1. Primary improvement loop: calibration + validation

### Calibration (closest to “training” today)

- **Input:** Diligence CSVs (`claims_summary.csv`, `denials.csv`, `ar_aging.csv`) via `--actual-data-dir`.
- **Mechanism:** [`rcm_mc/core/calibration.py`](../rcm_mc/core/calibration.py) reads empirical rates and blends them with YAML priors (e.g. beta-style updates, smoothed shares).
- **Outputs:** `calibrated_actual.yaml`, `calibration_actual_report.csv`.
- **How to improve:**
  - Log **prior vs posterior** explicitly in the calibration report (means, effective sample sizes).
  - Add **holdout months** or payer-level cross-validation before accepting calibrated YAML.
  - Tighten **DataPackage** column mapping and payer canonicalization tests.

### Validation (non-ML)

- **Reproducibility:** Every run writes [`provenance.json`](../rcm_mc/infra/provenance.py) with `n_sims`, `seed`, `align_profile`, config SHA256, and optional `git_revision`.
- **Marginal checks:** Compare simulated marginal IDR/FWR/DAR (from `simulations.csv`) to published benchmarks (see `BENCHMARK_SOURCES.md`).
- **Stress:** Use `--stress` / `--full-report` to stress suites in [`rcm_mc/analysis/stress.py`](../rcm_mc/analysis/stress.py).
- **Regression:** Run `pytest tests/` including golden / simulator tests after any change to [`rcm_mc/core/simulator.py`](../rcm_mc/core/simulator.py).

## 2. Making logic explicit (already shipped)

| Artifact | Role |
|----------|------|
| `docs/METRIC_PROVENANCE.md` | Human-readable metric dictionary. |
| `provenance.json` | Per-run lineage for each `summary.csv` row. |
| `simulation_trace.json` | Optional single-iteration drill-down (`--trace-iteration N`). |
| Report section “Metric methodology and lineage” | Renders from `provenance.json` in [`html_report.py`](../rcm_mc/reports/html_report.py). |

## 3. Optional ML / surrogate (advanced, not for signing)

Use **only** for portfolio screening or fast sensitivity—not as a replacement for the full simulator in diligence sign-off.

- **Interface stub:** [`rcm_mc/analysis/surrogate.py`](../rcm_mc/analysis/surrogate.py) documents intended hooks.
- **Suggested approach:** Generate a training table with many runs `(flattened_config_features → mean_ebitda_drag)`; fit gradient boosting or shallow nets; compare surrogate vs simulator on a **holdout** grid.
- **Guardrails:** Never overwrite `summary.csv` with surrogate output; label any surrogate chart clearly as “approximate.”

## 4. Suggested backlog (priority order)

1. Backtest calibrated configs on holdout claims months.
2. Extend `provenance.json` with `rcm_mc` package version string.
3. Add automated “KPI vs benchmark” check script (reads `summary.csv` + `BENCHMARK_SOURCES.md` ranges).
4. Implement surrogate training script under `scripts/` (optional, separate from `cli.py`).
