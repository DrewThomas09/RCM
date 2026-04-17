# Core

Monte Carlo simulation engine: probability distributions, RNG management, the main simulator, and calibration pipeline. This is the mathematical kernel of the platform -- all numeric simulation flows through here.

| File | Purpose |
|------|---------|
| `simulator.py` | Core Monte Carlo simulator: samples distributions, models claim buckets, denial rates, capacity, and computes EBITDA drag |
| `kernel.py` | Stable API entry point wrapping the simulator; returns a `SimulationResult` with drag percentiles and economic metrics |
| `distributions.py` | Distribution primitives: Beta, Dirichlet, lognormal, and gamma sampling with method-of-moments parameter conversion |
| `rng.py` | Centralized RNG management using `SeedSequence` for reproducible, independent streams per simulation component |
| `calibration.py` | Calibration pipeline: ingests actual claim data, applies Bayesian posterior updates, and produces calibrated simulation configs |
| `_calib_schema.py` | Column/value normalization helpers (alias mapping, payer name canonicalization) used by the calibration pipeline |
| `_calib_stats.py` | Statistical helpers for calibration: Beta posterior updates, share smoothing, top-N grouping |

## Key Concepts

- **Reproducible RNG**: Named child streams via `SeedSequence` ensure the same seed always produces the same results regardless of call order.
- **Bayesian calibration**: Prior benchmarks are updated with observed hospital data using conjugate Beta posteriors.
- **stdlib + numpy only**: No scipy or sklearn dependency; all distributions are implemented from closed-form solutions.
