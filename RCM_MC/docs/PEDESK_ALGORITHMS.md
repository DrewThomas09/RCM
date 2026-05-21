# PE Desk — Algorithms, Models & Statistical Methods

> Every model and scoring method in PE Desk, with the actual technique, inputs, outputs, and the honesty/defensibility safeguards. File paths are authoritative — open them to see the exact formulas. See [PEDESK_OVERVIEW.md](PEDESK_OVERVIEW.md) for the system map and [PEDESK_DATA.md](PEDESK_DATA.md) for the data these consume.

**Cross-cutting principles** (true throughout):
- **Honest empty / INCOMPLETE states** instead of fabricated numbers (the bridge returns `INCOMPLETE`; the predictor returns `None` when a branch can't fire; benchmark fallbacks are graded `D`).
- **n-thresholds** gate confidence (ridge needs ≥15 comparables, weighted-median ≥5, sector aggregates ≥3).
- **Numerical stability** is deliberate: pseudo-inverse over inverse on collinear designs, non-negative variance clamps, leverage ∈ [0,1], Cook's-D caps, probability/logit clipping, inf/NaN coercion with logging.
- **Provenance** — the simulator, bridges, and PE-math can record each computed metric with its formula string and upstream references for audit traceback.

---

## A. The simulation core

### 1. RCM revenue-cycle Monte Carlo simulator
**`rcm_mc/core/simulator.py`** (`simulate()`, `simulate_one()`, two-pass payer kernel)
- **Problem:** project the annual EBITDA leakage/cost of a hospital's revenue cycle (denials, underpayments, rework, working-capital drag) under uncertainty, per payer.
- **Method:** two-pass-per-payer Monte Carlo.
  - *Pass 1* samples per-payer KPI primitives: clean days-in-AR, initial denial rate (IDR), final write-off rate (FWR), denial-type mix via **Dirichlet** (default concentration 120), optional **lognormal claim-size bucketing**. Denial counts are **Poisson** (`λ = claims × IDR`); underpayments Poisson on `claims × UPR`.
  - *Capacity/queue layer:* converts denial "touches" into a backlog multiplier + queue-wait days.
  - *Pass 2* applies backlog in **logit space**: `fwr = sigmoid(logit(fwr_base) + ln(odds_mult) + penalties + size_beta·ln(size))`, clipped to `max_fwr` (0.98). Stage mix (L1/L2/L3) shifts with backlog; cases drawn **multinomial**; rework cost & extra A/R days via a **Gamma matched on the mean/variance of N iid per-unit draws** (`sample_sum_iid_as_gamma`). A/R, working capital, and a WACC economic cost computed per payer and summed.
  - *Convergence/early-stop:* from 10k sims, every 5k iterations compares last-5k vs prior-5k mean and P90; stops when both relative deltas `< 0.5%`.
- **Inputs:** a calibrated config (hospital, payers, appeals, economics.wacc, operations.denial_capacity), `n_sims`, `seed`.
- **Outputs:** DataFrame, one row per sim: `rcm_ebitda_impact` (leakage + rework + outsourced), `…_incl_wc`, `dar_total`, per-payer drivers.
- **Safeguards:** probability/logit clipping; FWR cap; uniform fallback + warning on degenerate probability vectors; post-run inf/NaN→0 with logging; provenance records only top-line p50/stddev (driver columns excluded as noisy).

### 2. Distribution sampling library
**`rcm_mc/core/distributions.py`** + **`rcm_mc/rcm/claim_distribution.py`**
- Method-of-moments converters: Beta `a,b` from `(mean, sd)` (with a **variance clamp** to `0.95×max_var` to keep runs alive), lognormal `μ,σ` from `(mean, sd)`, Gamma `shape,scale`, triangular moments. `sample_dirichlet(shares, concentration)`. `sample_sum_iid_as_gamma` approximates a sum of N iid per-unit RVs as one Gamma matched on `(N·μ, N·var)` — volume-scaled variance without per-claim simulation.
- **Claim-size bucketing:** lognormal claims split into quantile buckets; **bisection** (`solve_alpha_for_target_mean`) finds the logit intercept α so `Σ w·sigmoid(α + β·x)` equals the target IDR; larger claims get higher denial odds (β≈0.60).

## B. RCM → EBITDA bridges (turning KPI deltas into dollars)

### 3. RCM→EBITDA 7-Lever Bridge — v1, the "calibration floor"
**`rcm_mc/pe/rcm_ebitda_bridge.py`** (`RCMEBITDABridge.compute_bridge`)
- **Problem:** convert deltas in seven HFMA-style RCM KPIs into recurring EBITDA + working-capital impact, sized so a $400M-NPR reference hospital lands inside published research bands.
- **Method:** seven **linear, profile-conditioned** levers:
  1. **Denial rate** — `(Δpp/100)·NPR·0.35` avoidable + rework saved.
  2. **Days in A/R** — one-time WC release `Δdays·NPR/365`; recurring = `WC·cost_of_capital (0.08)` + bad-debt avoided.
  3. **Net collection rate** — `(Δpp/100)·NPR·0.60`.
  4. **Clean claim rate** — `(Δpp/100)·claims·cost_per_rework`.
  5. **Cost to collect** — `(Δpp/100)·NPR`.
  6. **First-pass resolution** — rework saved + FTE savings.
  7. **Case mix index** — `Δcmi/0.01 × Medicare_revenue × 0.75%/pt` (**Medicare-only**, scaled by payer mix).
  Every lever is linear in `(target − current)`, so the whole bridge is a dot product (`lever_coefficients`); `compute_bridge_vectorized` batch-evaluates `deltas @ coefs` across N sims (locked to equal the scalar path). A **tornado** ranks levers at {1,5,10,20}% relative improvements. `suggest_targets` proposes conservative/base/aggressive tiers from registry P25/P50/P75, **only ever recommending improvement**, with an achievability score `1/(1+distance)`.
- **Safeguards:** `INCOMPLETE` status when `net_revenue ≤ 0` or no lever fires; EV impact reported at multiple exit multiples (10/12/15×) on EBITDA only. **This v1 bridge is the calibration floor, locked by ~29 regression tests to research bands.**

### 4. RCM Value Bridge — v2 (payer/method-mix unit economics)
**`rcm_mc/pe/value_bridge_v2.py`** + `rcm_mc/finance/reimbursement_engine.py`
- **Problem:** v1 applies uniform coefficients to every hospital; v2 produces **different value for different archetypes** (commercial-heavy vs Medicare-heavy, DRG- vs capitation-exposed).
- **Method:** starts from **collectible** net revenue (not raw NPSR, to avoid double-counting leakage). Per payer class: `recovered = payer_nr × delta × method_sensitivity × payer_leverage × avoidable_share`. Payer leverage (Commercial 1.00 → Self-pay 0.40); method sensitivity from a per-reimbursement-method table (e.g. DRG sets coding/CDI = 1.00); default avoidable share 0.39. Separates recurring revenue, recurring cost, one-time WC release, and ongoing financing benefit; exit multiple applied only to recurring EBITDA.
- **Safeguards:** FFS fallback profile; per-lever + overall confidence; `INCOMPLETE` when net revenue can't be sourced. The packet runs **both** v1 (`packet.ebitda_bridge`) and v2 (`packet.value_bridge_result`) side-by-side.

### 5. Two-Source Monte Carlo over the bridge
**`rcm_mc/mc/ebitda_mc.py`** (`RCMMonteCarloSimulator`) + `mc/convergence.py`
- **Problem:** honestly combine the two uncertainties a partner underwrites — "we might be wrong about the target" and "we might not hit it."
- **Method:** per draw, `final = current + (sampled_target − current) × execution_fraction`.
  - *Prediction uncertainty:* normal fit treating the ridge conformal `[ci_low, ci_high]` as 5th/95th percentiles (`σ = half_width/1.645`), or bootstrap.
  - *Execution uncertainty:* **Beta** on [0,1] by lever family (denial_management Beta(7,3), CDI (6,4), payer_renegotiation (5,5), ar_collections (8,2)).
  - *Correlated draws:* Cholesky on a correlation matrix → correlated normals → inverse-normal marginal transform (self-contained erf/erfinv, no scipy).
- **Outputs:** distribution summaries (p5…p95), P(negative), P(covenant breach), P(MOIC ≥ {1.5,2,2.5,3}×), variance contribution per driver, P10/P90 tornado. A convergence check reports `converged=False` + a doubled `recommended_n` if the running P50 still moves > tolerance.
- **Safeguards:** fractions clamped [0,1]; a bridge failure inside a draw is contained (zeros, not a crash); inf/NaN filtered.

## C. Prediction & statistics

### 6. Prediction stack: Ridge + LOO-α + split conformal
**`rcm_mc/ml/ridge_predictor.py`** + **`rcm_mc/ml/conformal.py`**
- **Problem:** predict a hospital's missing RCM metrics from comparable hospitals, with honest 90% intervals.
- **Method — three-branch ladder gated by cohort size:**
  - **n ≥ 15 → Ridge + split conformal.** Closed-form numpy Ridge (z-scored features, normal-equation solve with **pinv fallback** on singularity). α chosen by **RidgeCV LOO** over `logspace(-3,3,25)`, minimizing LOO MSE via the **hat-matrix (PRESS) shortcut** `ê_LOO = ê/(1−h_ii)` (Allen 1974 / ESL §7.10 — O(N·p²), ~30× faster than naive LOO). LOO R² reported honestly (can go negative).
  - **n ≥ 5 → similarity-weighted median + bootstrap CI.**
  - **n < 5 → benchmark P25/P50/P75 fallback,** graded `D`.
  - **Split conformal:** margin = the `⌈(1−α)(n+1)⌉/n`-quantile of absolute calibration residuals (clamped to 1.0 on small n → deliberately over-covers). Distribution-free finite-sample coverage. Train/cal split 30%, with a **provider-disjoint mode** preferred for claim-derived data (a deprecation warning fires if provider_ids are passed without a disjoint manifest, since coverage claims would otherwise be invalid).
- **Five post-fit diagnostics**, each with a literature anchor: VIF>10, Cook's D>4/N, Breusch-Pagan heteroskedasticity (Wilson-Hilferty χ² survival), high leverage (>2p/N), RESET-style nonlinearity. A **"verify-not-assume" guardrail**: if R²<0 and Cook's D fires, it refits without the high-Cook's-D row to test whether the outlier caused it.
- **Outputs:** per metric — value, ci_low/high, coverage target, n_used, LOO R², feature importances (|standardized coef|), reliability grade, failure reason.
- **Safeguards:** dollar/financial metrics never predicted (partner-supplied); a feature must appear in ≥ half the comparables to be used; CI-unstable chip when relative CI width > 200%.

### 7. OLS regression engine
**`rcm_mc/finance/regression.py`** (`run_regression`, `run_segmented_regression`, `compute_vif`)
- **Problem:** explain which variables correlate with deal outcomes (NPSR, denial rate, margin).
- **Method:** OLS via `lstsq`. **SEs from `mse × diag(pinv(XᵀX))` with a non-negative variance clamp** — specifically because collinear HCRIS features (VIFs in the hundreds) put tiny negative variances on the diagonal and produced NaN SEs. R², adjusted R², RMSE, MAE; t-distribution two-tailed p-values (Abramowitz-Stegun approx). Optional **log-target** (semi-elasticity). `compute_vif`: `VIF_j = 1/(1−R²_j)`. Segmented variant fits one OLS per segment + baseline, requiring `n_features + 10` dof or the segment is surfaced as `insufficient_n`.
- **Safeguards:** explicit "in-sample diagnostic, not out-of-sample prediction" scope; raises on singular matrix and `n < k+2`; under-powered segments reported, not dropped.

### 8. OLS influence diagnostics
**`rcm_mc/finance/influence.py`** (`compute_influence`, `classify_influence_point`)
- **Problem:** find the few hospitals (Stanford, MD Anderson…) that distort the pooled fit, and label *why*.
- **Method:** hat-matrix diagonal `h_ii` via `einsum` against `pinv(XᵀX)` (no full n×n matrix), clipped [0,1]. Studentized residual = `resid/(RMSE·√(1−h_ii))`; Cook's D = `(stud²/(p+1))·(h/(1−h))`. **Partner-facing labels:** `legitimate_but_different_class` (academic/flagship → DO NOT DELETE), `possible_opportunity`, `data_issue`, `high_influence`, `perfect_leverage`.
- **Safeguards:** a reported Cook's D of `4.89e18` drove the fix — leverage>0.99 → `perfect_leverage` with NaN diagnostics; `1−leverage` floored at 1e-4; Cook's D capped at 1000; pinv for rank-deficient designs.

### 9. Feature-leakage audit
**`rcm_mc/finance/leakage.py`** (`classify_feature_for_target`, `atomic_inputs`, `forecasting_safe_features`)
- **Problem:** stop features that algebraically contain the target (e.g. `revenue_per_bed = npr/beds` predicting `npr`) from inflating R².
- **Method:** a `PROVENANCE` registry records each feature's input formula. Verdicts (most-severe wins): **SELF**, **LEAKS** (target ∈ feature inputs or vice-versa), **FORMULA_RELATED** (shared inputs / accounting-identity cousins), **SAFE**, **UNKNOWN**. `atomic_inputs` walks the provenance DAG transitively to raw HCRIS columns (cycle-guarded, depth-capped at 8) so multi-hop chains are caught. `net_patient_revenue` and `net_income` are treated as **derived** (accounting identities: net = gross − contractual allowances) even though raw in HCRIS, so their components correctly flag as LEAKS.
- **Safeguards:** the whole module exists as a defensibility safeguard — it's what stopped the regression from showing a fake R²≈1.0.

## D. PE-math & deal economics

### 10. PE-math: value bridge, MOIC/IRR, covenant, hold grid
**`rcm_mc/pe/pe_math.py`**
- **Value-creation bridge:** `exit_ebitda = entry + organic(compounded) + rcm_uplift`; organic & RCM valued at **entry multiple**, multiple-expansion on total exit EBITDA. Reconciliation is exact (`entry_ev + Σcomponents == exit_ev`).
- **IRR:** **bisection over [−0.99, 10.0]** (mixed-sign PE cashflows aren't monotone in NPV, so Newton is avoided).
- **MOIC:** `total_distributions / entry_equity`.
- **Covenant check:** `leverage = debt/EBITDA`; headroom in turns; **EBITDA cushion %** = `(EBITDA − trip_EBITDA)/EBITDA`; interest coverage = `EBITDA/(debt×rate)`.
- **Hold-period grid:** MOIC/IRR at P10/P50/P90 uplift bands for each (hold-year × exit-multiple) cell.
- **Safeguards:** validation raises on non-positive entry/multiples/hold; value-destruction (negative uplift) is allowed to model.

### 11. Hold-period optimizer
**`rcm_mc/data_public/hold_period_optimizer.py`**
- For years 1–10: `exit_ebitda = entry × (1+cagr)^y`; exit multiple holds flat through year 3 then **compresses at a sector-specific rate** (health-IT −0.40/yr, hospital/physician −0.35, default −0.25; floored at 60% of entry). Debt amortizes; net MOIC applies 20% carry + management-fee haircut. Reports peak-MOIC year, peak-IRR year, a "sweet spot" (years above 75% of peak MOIC), and a "cliff year."

## E. Scoring & matching (corpus analytics)

### 12. Deal risk scorer (5-factor composite 0–100)
**`rcm_mc/data_public/deal_risk_scorer.py`**
- Weighted composite: **Entry-Multiple 0.30, Payer-Concentration 0.20, Hold-Duration 0.20, Vintage-Cycle 0.15, Size 0.15.** Each component is a 0–100 step function (entry-multiple premium vs sector median; payer-mix **HHI**; flip-risk vs sector-optimal hold; macro-risk vintage years; size sweet-spot $75–500M). Tiers: <25 Low / <50 Medium / <70 High / else Critical. Validated against realized MOIC (the `/deal-risk-scores` risk×return scatter).

### 13. Sponsor track record / consistency score (0–100)
**`rcm_mc/data_public/sponsor_track_record.py`**
- Name normalization (alias map + legal-suffix stripping); per-sponsor median/mean/P25/P75 MOIC & IRR, loss rate (MOIC<1), home-run rate (MOIC>3). **Consistency = `0.40·moic_score + loss_penalty + irr_score + cred_score`** where moic_score = `min(100,(median_moic/2)·50)`, loss_penalty = `25·(1−loss_rate)`, irr_score = `min(20,(median_irr/0.20)·20)` (neutral 10 if no IRR), cred_score = `min(15, n_deals·3)`.

### 14. Comparable-deal matching (weighted similarity)
**`rcm_mc/data_public/deal_comparables_enhanced.py`**
- Weighted similarity (0–1): **EV log-scale 0.30, payer-mix cosine 0.30, vintage 0.20, deal-type Jaccard 0.20.** `EV_sim = exp(−|ln(ev_a)−ln(ev_b)|)`; vintage = `exp(−|Δyr|/3)`. Also `leverage_adj_moic` de-levers realized MOIC to a notional 5× benchmark, and `peer_group_percentiles` ranks the target among comps. Missing dimensions get a neutral 0.5.

### 15. Market concentration (HHI / CR3 / CR5)
**`rcm_mc/data_public/market_concentration.py`**
- Per state-year: **HHI = Σ(share²)** on a 0–1 fractional scale, plus CR3/CR5. Geo-dependency flags providers with >50% revenue from one state. `state_portfolio_fit` blends a weighted expansion score (growth, payment scale, stability, fragmentation).
- **⚠ Two HHI conventions in the codebase:** the deal-risk scorer uses the **0–10000 integer** HHI (`Σ(share×100)²`); this module uses the **0–1 fractional** HHI (`Σ(share²)`). Same index, different scaling — don't mistake "HHI 5000" next to "HHI 0.30" for an error.

## F. Calibration & blending

### 16. Hierarchical Bayesian calibration (partial pooling)
**`rcm_mc/ml/bayesian_calibration.py`**
- **Problem:** estimate hospital KPIs that shrink to peer priors when target data is thin and converge to observed values when rich.
- **Method:** **Beta-Binomial conjugate update** for rate metrics (`α_post = α0 + successes`, etc.; `shrinkage = prior_strength/(prior_strength+n)`; 90% credible interval via normal approx). **Gamma/Normal-Gamma** for continuous metrics. Priors are hospital-type-stratified (large/medium/small/rural). `data_quality` graded strong/moderate/weak/prior_only by observed n. `compute_missing_data_score` treats missingness as **informative** (sellers who withhold denial data often have bad denial rates).
- This is the **CALIBRATED** source — the `data_room_calibrations` posterior blending ML prediction with seller data.

### 17. Value-plan blending
**`rcm_mc/pe/value_plan.py`**
- Builds a target simulator config by **shifting each distribution's mean toward a benchmark by a gap-closure fraction k**, only in the improving direction; preserves the distribution family; blends spread; renormalizes stage mix. k clipped [0,1] with family-appropriate clamps.

---
*This inventory was compiled by reading the implementing modules. For any number a partner or investor questions, open the cited file — the formula and its safeguards are in the code and docstrings.*
