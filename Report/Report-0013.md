# Report 0013: Public API Surface — `rcm_mc/core/distributions.py`

## Scope

This report covers the **complete public API surface of `RCM_MC/rcm_mc/core/distributions.py`** on `origin/main` at commit `f3f7e7f`. The module was selected because Report 0012 named it as the **single sampling chokepoint** for every Monte Carlo distribution draw in the simulator pipeline, and Reports 0011 + 0012 left open the question (Q2) of which distribution shapes are accepted.

For each public symbol the report lists: signature, docstring presence, internal vs external usage, and notable behavioral edge cases. The companion validator `_validate_dist_spec` (in `infra/config.py:119`) is referenced but not fully covered — that is reserved for a follow-up.

Prior reports reviewed before writing: 0009-0012.

## Findings

### Module shape

- `RCM_MC/rcm_mc/core/distributions.py` — **258 lines**.
- Outgoing imports: `numpy` (line 5); stdlib `typing`. Optional `scipy.stats.truncnorm` lazily imported at line 118 (`dist_moments` only — wrapped in `try/except ImportError`). **No internal `rcm_mc.*` imports** — the module is a pure-stdlib + numpy primitive.
- Public symbol count: **9** (1 exception class, 4 conversion helpers, 1 moment computer, 3 samplers).
- Private symbol count: **1** (`_as_float` at line 12).

### Distribution shapes accepted

Cross-checked against both `dist_moments` (line 86) and `sample_dist` (line 147). Symmetric — every shape supported by one is supported by the other.

| `dist:` value | Required keys | Optional keys | Returned by `sample_dist` |
|---|---|---|---|
| `fixed` | — | `value` (default 0.0) | `np.full(n, value)` |
| `beta` | `mean`, `sd` | `min` (default 0.0), `max` (default 1.0) | `np.clip(rng.beta(a, b, n), min, max)` |
| `triangular` | `low`, `mode`, `high` | — | `rng.triangular(low, mode, high, n)` |
| `normal` / `gaussian` | `mean`, `sd` | — | `rng.normal(mean, sd, n)` |
| `normal_trunc` | `mean`, `sd` | `min` (default `-inf`), `max` (default `+inf`) | `np.clip(rng.normal(mean, sd, n), min, max)` (rejection-style truncation NOT used) |
| `lognormal` | `mean`, `sd` | — | `rng.lognormal(mu, sigma, n)` (mean/sd are real-space, converted via `lognormal_mu_sigma_from_mean_sd`) |
| `gamma` | `mean`, `sd` | — | `rng.gamma(shape, scale, n)` (converted via `gamma_shape_scale_from_mean_sd`) |
| `empirical` | `values` (non-empty list) | — | `rng.choice(values, n, replace=True)` |

**8 distinct shapes accepted.** Resolves Report 0011 Q2 / Report 0012 MR86 inventory.

### Public symbols — full signatures

#### `class DistributionError(ValueError)` — line 8

- **No docstring.**
- Specialized exception. Used to wrap parse / range / spec errors.
- External use: 1 production file, 1 test file.

#### `def beta_alpha_beta_from_mean_sd(mean: float, sd: float) -> Tuple[float, float]` — line 19

- **Has docstring** — explains method-of-moments derivation (`mean = a/(a+b)`, `var = a*b/((a+b)^2*(a+b+1))`) and feasibility constraint `sd^2 < mean*(1-mean)`.
- **Behavioral edge case:** when `var >= max_var`, **silently clamps `var = 0.95 * max_var`** at line 38-40 ("Clamp to a feasible variance (keeps the run alive; validation warns upstream)"). Caller sees a value but the spec was effectively rewritten.
- **Numerical guard:** clamps `a, b >= 1e-6` at lines 46-47.
- External use: 1 production file (`core/_calib_stats.py:8`).

#### `def lognormal_mu_sigma_from_mean_sd(mean: float, sd: float) -> Tuple[float, float]` — line 51

- **No docstring.** Method-of-moments converter from real-space mean/sd to lognormal `mu, sigma`.
- Validates `mean > 0` and `sd > 0` (raises `DistributionError`).
- **External use: 0 production, 0 test.** Internally called by `sample_dist` only.

#### `def gamma_shape_scale_from_mean_sd(mean: float, sd: float) -> Tuple[float, float]` — line 63

- **No docstring.** Method-of-moments for gamma.
- Same validation as lognormal.
- **External use: 0 production, 0 test.** Internally called by `sample_dist` only.

#### `def triangular_mean_var(low: float, mode: float, high: float) -> Tuple[float, float]` — line 75

- **No docstring.** Closed-form mean + variance for triangular distribution.
- Validates `low <= mode <= high` (raises).
- **External use: 0 production, 0 test.** Internally called by `dist_moments` only.

#### `def dist_moments(spec: Dict[str, Any]) -> Tuple[float, float]` — line 86

- **Has docstring** — "Return (mean, variance) for a supported distribution spec."
- Dispatches on `spec["dist"]` (default `fixed`); 8 shapes recognized.
- **HIGH-PRIORITY behavioral subtlety:** for `normal_trunc`, lazily imports `scipy.stats.truncnorm` (line 118-122) for true truncated moments. **If scipy is missing, falls back silently to (mean, sd^2)** at line 125 — i.e. the un-truncated moments. Per Report 0003, scipy is in `[all]` extras only. Default-installed users get the wrong moments.
- External use: 1 production file (`pe/value_plan.py:10`), 1 test file.

#### `def sample_dist(rng: np.random.Generator, spec: Optional[Dict[str, Any]], size: Optional[int] = None) -> np.ndarray` — line 147

- **Has docstring** — "Sample from a distribution spec. Convention: if size is None, returns an array of length 1 (not a scalar), so callers can safely index [0]."
- Dispatches on `spec["dist"]`; 8 shapes recognized.
- **Behavioral asymmetry with `dist_moments`:** for `normal_trunc`, this function uses **`np.clip` (clamping) — NOT rejection sampling**. Combined with `dist_moments`'s scipy-aware true-moment computation, **the sampled mean does not equal the moment-computed mean** for tight truncation bounds. Silent statistical bias.
- External use: 3 production files (`core/simulator.py:10`, `portfolio/store.py:15`, `reports/reporting.py:521`), 1 test file.

#### `def sample_dirichlet(rng: np.random.Generator, base_shares: Dict[str, float], concentration: float) -> Dict[str, float]` — line 211

- **Has docstring** — explains Dirichlet posterior around `base_shares` with concentration parameter.
- Validates non-negative shares, sum > 0, concentration > 0.
- Auto-renormalizes if `base_shares` doesn't sum to 1 (line 226 `p = p / s`) — silent normalization.
- External use: 1 production file (`core/simulator.py:10`).

#### `def sample_sum_iid_as_gamma(rng: np.random.Generator, per_unit_spec: Dict[str, Any], n: float, min_total: float = 0.0) -> float` — line 235

- **Has docstring** — "Approximate sum of n IID random variables with the specified per-unit distribution as a Gamma distribution matched on mean/variance. This avoids per-claim simulation while still preserving variability that scales with volume."
- Dispatches to `dist_moments` to get `(mu, var)` of the per-unit spec, then samples from a Gamma matched on `n*mu / n*var` (lines 248-257).
- **Behavioral edge case:** when `var_sum <= 1e-12`, returns `max(mean_sum, min_total)` deterministically — no random draw at all.
- External use: 1 production file (`core/simulator.py:10`).

### Per-symbol external-usage roll-up

| Symbol | Prod files | Test files | Verdict |
|---|---:|---:|---|
| `DistributionError` | 1 | 1 | live, public |
| `beta_alpha_beta_from_mean_sd` | 1 (`core/_calib_stats.py`) | 0 | live but untested directly |
| **`lognormal_mu_sigma_from_mean_sd`** | **0** | **0** | **DE-FACTO PRIVATE — public-named but no external use** |
| **`gamma_shape_scale_from_mean_sd`** | **0** | **0** | **DE-FACTO PRIVATE** |
| **`triangular_mean_var`** | **0** | **0** | **DE-FACTO PRIVATE** |
| `dist_moments` | 1 (`pe/value_plan.py`) | 1 | live |
| `sample_dist` | **3** (`simulator.py`, `store.py`, `reports/reporting.py`) | 1 | **the chokepoint** |
| `sample_dirichlet` | 1 (`core/simulator.py`) | 0 | live but untested directly |
| `sample_sum_iid_as_gamma` | 1 (`core/simulator.py`) | 0 | live but untested directly |

**3 of 9 public symbols are de-facto private** (no external consumer). They should arguably be prefixed with `_`.

**4 of 9 public symbols lack docstrings** — `DistributionError`, `lognormal_mu_sigma_from_mean_sd`, `gamma_shape_scale_from_mean_sd`, `triangular_mean_var`.

**5 of 9 public symbols have 0 direct test coverage** — `beta_alpha_beta_from_mean_sd`, `lognormal_mu_sigma_from_mean_sd`, `gamma_shape_scale_from_mean_sd`, `triangular_mean_var`, `sample_dirichlet`, `sample_sum_iid_as_gamma`. (These are exercised transitively via `simulator` runs.)

### Naming-collision risk

A **sibling `distributions.py`** exists at `RCM_MC/rcm_mc/negotiation/distributions.py` (verified by file-existence check). Its docstring describes "Rate distributions per service-line × payer × geography" — a domain-specific module unrelated to the core math one.

The relative import in `rcm_mc/negotiation/__init__.py:50` (`from .distributions import (...)`) resolves to the sibling, not to `core/distributions.py`. **This is correct Python resolution but a confusion vector** — a developer reading `from .distributions import sample_dist` might miss that there are two modules named the same.

## Merge risks flagged

| ID | Risk | Detail | Severity |
|---|---|---|---|
| **MR92** | **`sample_dist` ↔ `dist_moments` symmetry must be preserved** | Two functions, same dispatch on `spec["dist"]`. Adding a new distribution requires editing BOTH. Already an issue: `normal_trunc` is sampled by clipping in `sample_dist` but its moments are scipy-truncated in `dist_moments` — silently inconsistent. Pre-merge: any branch adding a `dist:` value must edit both functions and the validator at `infra/config.py:119`. **Three-place edit**. | **Critical** |
| **MR93** | **`normal_trunc` moments depend on scipy availability** | `dist_moments` lazily imports `scipy.stats.truncnorm` (line 118). Per Report 0003, scipy is in `[all]` extras only — default `pip install -e .` users get the un-truncated moments back at line 125. **Silent precision regression** depending on install variant. Output of `value_plan.py` (line 10) differs by install. | **High** |
| **MR94** | **3 public-named functions are de-facto private** | `lognormal_mu_sigma_from_mean_sd`, `gamma_shape_scale_from_mean_sd`, `triangular_mean_var`. A branch could rename or change their signatures — no external test catches it. Should be `_`-prefixed in a cleanup pass. | Medium |
| **MR95** | **`beta_alpha_beta_from_mean_sd` silently rewrites the spec when sd is too high** | Line 40: `var = 0.95 * max_var`. The Beta spec the user wrote is silently replaced. Pre-merge: any branch that adds Beta priors with high SD will run with subtly different distributions. | Medium |
| **MR96** | **`sample_dirichlet` silently renormalizes `base_shares`** | Line 226: `p = p / s`. If a config payer-mix file doesn't sum to 1.0 (Report 0011's `revenue_share` validation may catch this — but if not), this function masks the error. | Low |
| **MR97** | **Sibling `distributions.py` in `negotiation/` is a confusion vector** | Two modules named `distributions.py`. A future iteration that documents the negotiation subsystem must disambiguate. | Low |
| **MR98** | **Empirical distribution accepts arbitrary value lists with no shape validation** | Line 137-142 / 200-205: just calls `np.array(values, dtype=float)`. A branch that introduces non-numeric `values` will hit `np.array` raising — but the error message is generic ("could not convert string to float") rather than wrapped in `DistributionError`. | Low |
| **MR99** | **No docstring on `DistributionError`** | Public exception class with zero documentation. Callers don't know what conditions raise it (range violations? type errors? feasibility failures?). | Low |
| **MR100** | **`sample_dist` returns array, never scalar — non-obvious convention** | Line 152: "if size is None, returns an array of length 1 (not a scalar), so callers can safely index [0]." Branch that "fixes" this by returning a scalar when `size is None` would break every caller's `[0]` indexing. | **High** |

## Dependencies

- **Incoming:** 6 unique production importers (`pe/value_plan.py`, `core/_calib_stats.py`, `core/simulator.py`, `portfolio/store.py`, `negotiation/__init__.py` — but that one is the sibling, ignore — `reports/reporting.py`); 2 test files (`test_distributions.py` and one other not enumerated).
- **Outgoing:** numpy (`np.random.Generator`, `np.array`, `np.clip`, `np.full`, `np.log`, `np.sqrt`, `np.mean`, `np.var`, `np.choice`, `np.isfinite`, `np.inf`); optional `scipy.stats.truncnorm` (lazy, in `dist_moments` only); stdlib `typing`. No internal `rcm_mc.*` imports.

## Open questions / Unknowns

- **Q1 (this report).** What does `infra/config.py:119 _validate_dist_spec` check? Per-distribution required-key presence, or any deeper feasibility checks (e.g. `mean*(1-mean) > sd^2` for beta)? Without the validator catching infeasibility, `beta_alpha_beta_from_mean_sd`'s silent clamp (MR95) is the failure mode.
- **Q2.** Do tests exercise the `normal_trunc`-without-scipy fallback path? Quick check: `pytest -k "truncnorm"` would surface.
- **Q3.** Does `sample_dirichlet`'s `concentration` parameter have a documented "natural" range? Code says `>0`; in practice values < 1 produce sparser draws than the prior, > 1 produces tighter. No guidance in docstring.
- **Q4.** Are any test cases checking the output of `sample_dist` against the moments computed by `dist_moments` for the same spec? That would surface the `normal_trunc` clipping ↔ scipy-truncated asymmetry.
- **Q5.** Does any non-default `pip install` path actually install scipy alongside the default deps? The diligence subsystem (`rcm_mc_diligence`) doesn't pull scipy; the `[all]` extra does.
- **Q6.** Does any branch on origin add a 9th distribution shape (e.g. `mixture`, `kde`, `pareto`)? Pre-merge sweep needed.

## Suggested follow-ups

| Iteration | Proposed area | Why |
|---|---|---|
| **0014** | **Read `infra/config.py:_validate_dist_spec` (line 119) end-to-end** — enumerate the validation rules per dist shape. | Closes Q1 / MR98. Tells us which spec errors are caught vs slip through to `sample_dist` / `dist_moments`. |
| **0015** | **Diff `sample_dist` (clip) vs `dist_moments` (scipy-true)** for `normal_trunc` numerically — bench the bias. | Quantifies MR92 / MR93. |
| **0016** | **`tests/test_distributions.py`** — read end-to-end. Surface coverage gaps. | Resolves Q2/Q4. |
| **0017** | **`infra/config.py:validate_config` line-by-line** — owed since Report 0011's suggested follow-up. | Closes the schema-dispatch picture. |
| **0018** | **Cross-branch sweep** — does any ahead-of-main branch add a new distribution shape to `core/distributions.py`? | Resolves Q6. |
| **0019** | **`negotiation/distributions.py`** — short report on the sibling module to disambiguate (MR97). | Single-iteration cleanup. |

---

Report/Report-0013.md written. Next iteration should: read `infra/config.py:_validate_dist_spec` (line 119) end-to-end and enumerate the validation rules per distribution shape — closes Q1 here, MR98, and the implicit-schema gap from Report 0011 MR76.

