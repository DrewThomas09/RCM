# Core

Monte Carlo simulation engine: probability distributions, RNG management, the main simulator, and calibration pipeline. This is the mathematical kernel of the platform — all numeric simulation flows through here.

---

## `simulator.py` — Core Monte Carlo Simulator

**What it does:** Runs N simulation draws for a deal, modeling claim buckets, payer-mix-weighted denial rates, capacity constraints, and A/R timing to produce a distribution of EBITDA drag outcomes.

**How it works:** For each simulation draw: (1) samples payer-specific denial rates and final write-off rates from their Beta distributions using `rng.py` child streams; (2) samples DAR-clean-days from lognormal distributions per payer; (3) applies the capacity model (unlimited / outsourced / staffed-up); (4) aggregates across payer buckets to total EBITDA drag. Returns a `SimulationResult` with drag percentiles (P5/P10/P25/P50/P75/P90/P95), mean, std, and per-payer breakdown. The vectorized code path runs 100,000 draws in under a second using NumPy broadcasting.

**Data in:** YAML configuration dict with payer distributions (loaded by `infra/config.py`); optional calibrated priors from `calibration.py`.

**Data out:** `SimulationResult` dataclass with drag percentiles and per-payer attribution.

---

## `kernel.py` — Stable Simulator API

**What it does:** Stable public entry point wrapping the simulator. Returns a `SimulationResult` with drag percentiles and economic metrics. Provides the interface that `cli.py` and test code call so internal simulator changes don't break callers.

**How it works:** Calls `simulator.simulate_compare()` with the actual and benchmark configs, validates inputs, normalizes config shapes, and wraps the raw output into a `SimulationResult`. Also computes derived economic metrics (`revenue_at_risk_mm`, `ar_release_mm`) from the drag distribution and the hospital's NPR input.

**Data in:** Two YAML config dicts (actual + benchmark scenario) plus hospital revenue parameters.

**Data out:** `SimulationResult` with drag percentiles, economic metrics, and a per-payer attribution table.

---

## `distributions.py` — Statistical Distribution Primitives

**What it does:** Implements all probability distribution sampling the platform uses: Beta, Dirichlet, lognormal, and gamma. No SciPy dependency — parameters are converted from mean/variance using method-of-moments.

**How it works:** Each distribution is a pure function taking a `numpy.Generator` (from `rng.py`) and distribution parameters. Beta is used for denial and write-off rates (bounded 0–1). Dirichlet is used for payer-mix sampling. Lognormal is used for DAR-clean-days. `beta_params_from_mean_sd()` converts the analyst's intuitive (mean, std) inputs to Beta (α, β) with a validity fallback for edge-case inputs.

**Data in:** Distribution parameters (mean, sd, or α/β) from the YAML config; a `numpy.Generator` from `rng.py`.

**Data out:** NumPy arrays of sampled values for each simulation draw.

---

## `rng.py` — Centralized RNG Management

**What it does:** Provides reproducible, independent random streams per simulation component using `numpy.random.SeedSequence`. Ensures the same seed always produces the same results regardless of call order.

**How it works:** A root `SeedSequence` is spawned from the analyst-provided seed. Named child streams are derived using `SeedSequence.spawn()` with a stable string-to-integer mapping for each component name (e.g., "denial_rates", "dar_clean_days", "execution_uncertainty"). Each child stream is a fully independent `numpy.random.Generator` (PCG64). This guarantees that adding a new stream does not perturb existing streams' output.

**Data in:** Integer seed from the CLI flag `--seed` or `packet_builder.py` default (42).

**Data out:** Named `numpy.random.Generator` child streams consumed by `distributions.py`, `ebitda_mc.py`, and `v2_monte_carlo.py`.

---

## `calibration.py` — Bayesian Calibration Pipeline

**What it does:** Ingests actual claim-level data from a seller's system, applies Bayesian posterior updates to the prior distributions, and produces a calibrated simulation config that blends observed data with benchmark priors.

**How it works:** For each payer: (1) reads observed denial counts and totals from the claim data CSV; (2) applies Beta conjugate posterior updates (`_calib_stats.py`) — `α_posterior = α_prior + observed_denials`, `β_posterior = β_prior + (total_claims - observed_denials)`; (3) optionally reweights the prior using the hospital's similarity score to its peer cohort. Writes the updated YAML config via `write_yaml()`. The `calibrate_config()` function is the primary entry point called by `rcm-mc ingest`.

**Data in:** Observed claim data CSV (from `data/ingest.py`); prior YAML config; optional benchmark priors from `hospital_benchmarks` table.

**Data out:** Calibrated YAML config written to disk; a `CalibrationReport` with per-payer posterior summaries.

---

## `_calib_schema.py` — Calibration Schema Helpers

**What it does:** Column and value normalization helpers used by the calibration pipeline. Maps the many ways seller files label the same field ("Denial Rate", "denial_rate", "IDR", "initial_denial") to a single canonical key.

**How it works:** A dict-based alias table (~120 entries) mapping raw column names to canonical field names. A separate payer-name canonicalization function handles variants ("Medicare FFS", "Medicare Fee for Service", "CMS Medicare") → "medicare_ffs". Called by `calibration.py` and `data/document_reader.py` before any numeric parsing.

**Data in:** Raw column headers and payer name strings from seller files.

**Data out:** Canonical field names and payer keys.

---

## `_calib_stats.py` — Calibration Statistical Helpers

**What it does:** Statistical helper functions for the calibration pipeline: Beta posterior updates, payer share smoothing, and top-N grouping for long-tail payer bucketing.

**How it works:** `beta_posterior(α_prior, β_prior, successes, trials)` → `(α_post, β_post)`. `smooth_shares(shares, floor=0.01)` applies Laplace smoothing so zero-count payers don't collapse to point masses. `top_n_group(payer_dict, n=6)` merges the long tail into an "Other" bucket to keep the config tractable.

**Data in:** Raw Beta prior parameters and observed count data from `calibration.py`.

**Data out:** Updated Beta parameters fed back into `calibration.py`.

---

## Key Concepts

- **Reproducible RNG**: Named child streams via `SeedSequence` ensure the same seed always produces the same results regardless of call order.
- **Bayesian calibration**: Prior benchmarks are updated with observed hospital data using conjugate Beta posteriors — the analyst gets a posterior that respects both the public benchmark and the seller's specific data.
- **stdlib + numpy only**: No scipy or sklearn dependency; all distributions are implemented from closed-form solutions, keeping the dependency surface small and auditable.
