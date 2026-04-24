# PE (Private Equity Math)

Private equity deal math: value creation bridges, returns analysis, debt modeling, waterfall distributions, hold-period tracking, and fund-level attribution. Converts simulated RCM EBITDA uplift into the metrics a PE investment committee underwrites on.

---

## `pe_math.py` — Core PE Returns Math

**What it does:** Computes the value-creation bridge, MOIC, IRR (bisection on non-integer hold years), covenant headroom, and a hold-period sensitivity grid (P10/P50/P90 MOIC per hold-year/exit-multiple cell). The audit-defensible math kernel a director can walk through on a whiteboard.

**How it works:** `value_creation_bridge()` computes entry EV + organic EBITDA growth + RCM uplift + multiple expansion = exit EV — the four items sum to the exit EV exactly (reconciliation invariant). IRR is computed by Newton-bisection on the IRR equation `0 = -entry_equity + exit_equity / (1+r)^hold` with a 100-iteration cap. The hold grid calls `moic()` at each cell for P10/P50/P90 bridge input levels. Pure `stdlib + dataclasses` — no pandas in the math kernel.

**Data in:** Entry EBITDA, RCM uplift (from the bridge), entry/exit multiples, hold years — all analyst inputs or bridge outputs. Payer mix is not consumed here (it feeds the v2 bridge instead).

**Data out:** `BridgeResult` and `ReturnsResult` dataclasses passed to the MC engine and all report renderers.

---

## `pe_integration.py` — rcm-mc run Auto-Compute Hook

**What it does:** Auto-compute hook called by `rcm-mc run` (the CLI simulation command). Materializes the bridge, returns, hold grid, and covenant JSON from simulation output in a single function call.

**How it works:** Reads simulation results from the `SimulationResult` object, extracts the P10/P50/P90 EBITDA drag estimates, calls `pe_math.value_creation_bridge()` and `pe_math.compute_returns()` at each percentile, and formats the output as a structured JSON dict for the run output folder. Also writes the hold-period grid as a CSV table.

**Data in:** `SimulationResult` from `core/kernel.py`; PE configuration (entry multiple, debt terms, hold year assumption) from the YAML config.

**Data out:** `pe_results.json` and `hold_grid.csv` in the run output folder.

---

## `value_bridge_v2.py` — Unit-Economics EBITDA Bridge (v2)

**What it does:** The primary EBITDA bridge used in the Deal Analysis Packet. Weights every lever by the hospital's payer mix and reimbursement method, so a denied commercial claim recovery is correctly worth more than a denied Medicaid claim recovery.

**How it works:** Reads a `ReimbursementProfile` (from `finance/reimbursement_engine.py`) carrying payer-method exposures. For each of the seven levers, computes four separate economic flows: (1) `recurring_revenue` — rate-weighted claim recovery or rate improvement; (2) `recurring_cost` — operational cost savings; (3) `one_time_wc` — working capital release from AR reduction (never multiplied into EV); (4) `financing_benefit` — interest savings on the WC release. Payer revenue leverage weights: Commercial=1.00, MA=0.80, Medicare FFS=0.75, Managed Gov=0.55, Medicaid=0.50, Self-pay=0.40. Cross-lever dependency adjustment (via `lever_dependency.py`) reduces overlapping revenue flows. Returns `ValueBridgeResult` with `total_recurring_ebitda_delta`, `enterprise_value_from_recurring` (at exit multiple), `total_one_time_wc_release` (reported separately, never in EV), and `rationale`.

**Data in:** Current and target metrics from the `DealAnalysisPacket` profile; `ReimbursementProfile` from `finance/reimbursement_engine.py`; `BridgeAssumptions` (exit multiple, evaluation month) from the analyst.

**Data out:** `ValueBridgeResult` written into `DealAnalysisPacket.v2_bridge`.

---

## `rcm_ebitda_bridge.py` — Legacy v1 Research-Band Bridge

**What it does:** The original 7-lever EBITDA bridge with uniform research-band-calibrated coefficients. Retained as a calibration floor and for regression testing. 29 locked regression tests verify output bands for a $400M NPR Medicare-heavy reference hospital.

**How it works:** Each lever applies a coefficient calibrated so that a benchmark improvement (e.g., denial rate 12% → 5% on $400M NPR) lands in the research-published band. The denial rate lever: `ΔEBITDA = (Δpp/100) × NPR × 0.35 + rework_saved` where 0.35 is the sized avoidable share. Each lever's formula is similarly documented with its research basis. Returns a `BridgeOutput` with per-lever EBITDA delta, total EBITDA delta, and per-exit-multiple EV impacts (10×/12×/15×).

**Data in:** Current and target metrics from the deal profile; NPR and claim volume from the hospital's revenue figures.

**Data out:** `BridgeOutput` written into `DealAnalysisPacket.v1_bridge` and used as the simulation bridge in `mc/ebitda_mc.py`.

---

## `lever_dependency.py` — Cross-Lever Dependency Walk

**What it does:** Prevents double-counting revenue recovery when causally linked levers are both fired (e.g., "fix eligibility denials" + "fix all denials" would double-count the eligibility-denial recovery).

**How it works:** Performs a topological walk of the `domain/econ_ontology.py` causal DAG. For each child lever fired alongside a parent lever, reduces the child's revenue component: `adj_revenue = revenue × (1 − min(0.75, Σα_hint))` where `α_hint ∈ {0.60, 0.35, 0.15}` for "strong / moderate / weak" causal overlap. The 0.75 cap (`_MAX_TOTAL_OVERLAP`) prevents over-reduction. Only the revenue flow is reduced — cost savings, WC release, and financing benefit are independent pathways. Adjustments only shrink, never inflate.

**Data in:** Active lever set from the bridge configuration; causal edges from `domain/econ_ontology.py`.

**Data out:** Adjusted lever impacts returned to `value_bridge_v2.py` for final aggregation.

---

## `ramp_curves.py` — Per-Lever Implementation Ramp Curves

**What it does:** Replaces the single-scalar ramp assumption with per-lever-family S-curves, so Year 1 is not overstated and Year 3 is not understated.

**How it works:** Each lever family has a logistic S-curve parameterized by `(t_25, t_50, t_75, t_full)` in months. `ramp(t) = 1 / (1 + exp(-k × (t - t_50)))`, clipped to [0,1]. Default curves: denial management hits 25%/75%/100% at 3/6/12 months; payer renegotiation at 6/12/24 months; CDI/coding at 4/9/18 months; AR/collections at 2/4/12 months. At `evaluation_month=36` every default curve returns exactly 1.0 (identity lock tested as a regression invariant). Used by the v2 bridge and value creation plan.

**Data in:** `evaluation_month` from `BridgeAssumptions`; lever family from the lever definition in `domain/econ_ontology.py`.

**Data out:** Scalar ramp factor [0.0, 1.0] applied to each lever's economic flows.

---

## `attribution.py` — One-At-A-Time Dollar Attribution

**What it does:** Decomposes the total EBITDA uplift into dollar contributions by driver bucket (denials, underpayments, AR days, coding/CDI, appeals). Used for the bridge waterfall chart.

**How it works:** Runs N+1 simulations: one baseline plus one per driver bucket with that bucket's target metrics zeroed back to current. The difference between the baseline total and each "zeroed" run is that bucket's marginal attribution. Normalizes to sum to total (handles interaction effects by residualizing into the "interaction" bucket). Returns a `Attribution` dict suitable for the waterfall chart renderer.

**Data in:** Full deal bridge configuration; simulation engine from `core/kernel.py`.

**Data out:** `Attribution` dict for the `/api/analysis/<id>/attribution` endpoint.

---

## `breakdowns.py` — Per-Payer and Per-Root-Cause Breakdowns

**What it does:** Splits simulation results by payer class and denial root-cause category, answering "how much of the EBITDA impact comes from commercial denials vs. Medicare denials?"

**How it works:** Re-runs the simulation with payer-specific inputs isolated. Aggregates drag contributions by payer class (commercial, Medicare FFS, MA, Medicaid, managed gov, self-pay) and by denial root cause (eligibility, authorization, coding, timely filing, duplicate). Returns a structured breakdown dict used by the deal workbench's RCM Profile tab.

**Data in:** Per-payer simulation configurations; root-cause denial distribution from the calibrated config or HCRIS proxies.

**Data out:** Payer and root-cause breakdown dicts for the RCM Profile tab.

---

## `debt_model.py` — Multi-Tranche Debt Trajectory

**What it does:** Models a multi-tranche debt stack (TL B + revolver + mezzanine) over the hold period, computing mandatory amortization, optional cash sweeps, leverage ratios, interest coverage, and covenant compliance by year.

**How it works:** Takes the entry debt structure (tranche sizes, margins, amortization schedules). For each year: computes EBITDA (from the bridge + organic growth ramp), applies mandatory amortization, applies optional sweep (excess cash flow above a reserve floor), recomputes leverage (Debt/EBITDA) and coverage (EBITDA/Interest) ratios, flags covenant breaches. Returns a year-by-year `DebtSchedule` used for the covenant headroom panel on the workbench.

**Data in:** Entry debt terms from the deal configuration; projected EBITDA path from the bridge + ramp curves.

**Data out:** `DebtSchedule` per-year table; used by `pe_math.py` covenant headroom calculation.

---

## `fund_attribution.py` — Fund-Level Value Creation Attribution

**What it does:** Decomposes fund-level MOIC into three buckets: RCM operational improvement, organic EBITDA growth, and exit-multiple expansion. Used in LP reporting.

**How it works:** For each portfolio company: retrieves entry EBITDA, hold-period realized EBITDA, entry and exit multiples from `portfolio/store.py`. Computes organic growth contribution (market CAGR × entry EBITDA × entry multiple), RCM contribution (realized RCM uplift × entry multiple), and multiple expansion contribution (ΔEBITDA at exit × Δmultiple). Aggregates across the portfolio weighted by invested capital. Returns a `FundAttribution` with dollar amounts and percentage contributions.

**Data in:** Portfolio deal snapshots from `portfolio/store.py`; organic growth assumption from fund-level config.

**Data out:** `FundAttribution` for the LP quarterly report.

---

## `hold_tracking.py` — Hold-Period KPI Variance Tracking

**What it does:** Tracks per-initiative actual vs. underwritten metric performance over the hold period. Flags cumulative drift and classifies each initiative as on-track / at-risk / behind.

**How it works:** Compares quarterly actual metric snapshots (analyst-entered via the deal page) against the underwritten trajectory from the value creation plan's ramp curves. Computes absolute variance, percentage variance, and cumulative drift (running total of quarters missed × severity). Classifies using thresholds: ≤5% miss = on-track, 5–15% = at-risk, >15% = behind. Returns a `VarianceReport` per initiative and a deal-level health signal.

**Data in:** Quarterly actual metrics from `deals/deal_sim_inputs.py`; underwritten targets from the value creation plan stored in `analysis_runs`.

**Data out:** `VarianceReport` for the deal page variance panel and `deals/health_score.py`.

---

## `predicted_vs_actual.py` — Diligence Prediction vs. Realized Performance

**What it does:** Compares what the ridge predictor forecast at diligence against actual realized metrics at close and in-hold, generating a confidence interval coverage report.

**How it works:** Loads diligence-era `PredictedMetric` objects (with conformal CIs) from the cached analysis run. Loads realized actual values from the deal's quarterly snapshots. For each metric: checks whether the actual value fell within the predicted 90% CI. Reports empirical coverage rate across the portfolio and flags systematic biases (e.g., denial rates consistently predicted too optimistically).

**Data in:** Historical `DealAnalysisPacket` predicted metrics from `analysis_store.py`; realized actuals from `deals/deal_sim_inputs.py`.

**Data out:** `CoverageReport` for the `/api/portfolio/prediction-accuracy` endpoint.

---

## `remark.py` — Hold-Period Re-Mark

**What it does:** Re-underwrites a held deal from its current actual EBITDA run-rate and records a before/after snapshot. Used for quarterly re-marks and LP reporting.

**How it works:** Takes the deal's current actual EBITDA (from the most recent quarterly snapshot). Recomputes MOIC and IRR at current EBITDA vs. remaining hold years and exit multiple assumption. Records a `Remark` snapshot with entry price, current implied value, IRR-to-date, remaining upside to original thesis, and a one-sentence status note. Appends to `portfolio/portfolio_snapshots.py`.

**Data in:** Current actual EBITDA from `deals/deal_sim_inputs.py`; entry price and debt terms from the deal's initial snapshot; exit multiple assumption from fund config.

**Data out:** `Remark` snapshot for the deal page and LP update.

---

## `value_creation.py` — Value Creation Simulation with Ramp

**What it does:** Runs multi-year value creation simulation applying linear (or S-curve) ramp effects across user-specified hold-year scenarios. Generates the year-by-year EBITDA trajectory.

**How it works:** For each year in the hold period: applies the ramp factor from `ramp_curves.py` to each initiative's target improvement. Feeds ramped metrics through the v1 bridge to get year-specific EBITDA uplifts. Aggregates to cumulative EBITDA, EV at exit, and MOIC across 3–5 year exit scenarios. Returns a `ValueCreationResult` with year-by-year EBITDA table and MOIC matrix.

**Data in:** Initiative targets from the deal's value creation plan; ramp curves from `ramp_curves.py`; bridge from `rcm_ebitda_bridge.py`.

**Data out:** `ValueCreationResult` for the hold-period projection panel.

---

## `value_creation_plan.py` — 100-Day Value Creation Plan Builder

**What it does:** Auto-generates a 100-day operational plan from the v2 bridge lever impacts, sequencing initiatives in dependency-aware order with ramp curves.

**How it works:** Takes the `ValueBridgeResult` lever impacts and sorts initiatives by: (1) independence (levers with no causal predecessors first), (2) EBITDA impact magnitude (largest first within tier), (3) time-to-realization (shorter-ramp levers before longer ones). Assigns each initiative a 30/60/90/100-day milestone, a responsible owner role, and a "quick win vs. sustained improvement" classification. Returns a structured `ValueCreationPlan` with a phased initiative timeline.

**Data in:** `ValueBridgeResult` from `value_bridge_v2.py`; lever dependencies from `lever_dependency.py`; ramp timing from `ramp_curves.py`.

**Data out:** `ValueCreationPlan` for the 100-day plan panel and diligence package.

---

## `value_plan.py` — Target Config Builder for Value Creation Scenarios

**What it does:** Builds a YAML config dict for a "value creation scenario" — the analyst's target state — from distribution moment inputs (mean, std). Validates that distribution parameters are internally consistent before running MC.

**How it works:** Accepts mean/std pairs for each target metric, calls `core/distributions.py` parameter converters to validate that Beta(α,β) and lognormal(μ,σ) parameters are numerically valid, and returns a config dict suitable for passing to the MC engine. Raises descriptive errors when inputs would produce degenerate distributions (e.g., std > mean for a Beta-distributed rate).

**Data in:** Analyst-entered target mean/std pairs from the workbench or CLI.

**Data out:** Validated config dict for the MC engine.

---

## `value_tracker.py` — Hold-Period Value Creation Tracking

**What it does:** Tracks realized value creation progress quarter-by-quarter against the original underwriting plan, computing "value created to date" and "remaining value to create."

**How it works:** For each completed quarter: takes actual EBITDA improvement, maps it to the corresponding bridge lever using initiative tracking data, computes cumulative realized vs. planned EBITDA delta. Computes "value created to date" as realized delta × entry multiple. Computes "remaining opportunity" as (target delta − realized delta) × exit multiple. Returns a `ValueTracker` with a running tally suitable for the LP update and board materials.

**Data in:** Quarterly actual EBITDA from `deals/deal_sim_inputs.py`; underwritten plan from the value creation plan in `analysis_runs`; entry/exit multiples from deal config.

**Data out:** `ValueTracker` for the deal page progress panel and LP quarterly report.

---

## `waterfall.py` — GP/LP Waterfall Distribution

**What it does:** Computes a standard American 4-tier carried-interest waterfall: return of capital, preferred return, GP catch-up, and carried interest split.

**How it works:** Takes total proceeds, invested capital, preferred return rate (typically 8%), GP catch-up percentage, and carried interest rate (typically 20%). Sequentially allocates proceeds: (1) return of capital to LPs; (2) preferred return to LPs at the hurdle rate; (3) GP catch-up until GP has received its target carry share; (4) remaining split at the carry rate. Returns a `WaterfallResult` with dollar amounts at each tier and effective LP/GP return multiples.

**Data in:** Total exit proceeds from `pe_math.py`; waterfall structure from the fund's LPA terms (analyst input or fund config).

**Data out:** `WaterfallResult` for the returns analysis panel.

---

## Key Concepts

- **v1 vs. v2 bridge**: The v1 bridge applies uniform research-band coefficients (retained for calibration and regression testing). The v2 bridge weights every lever by payer mix and reimbursement method — a denied commercial claim recovery is worth 2.5× a Medicaid denial recovery.
- **Four economic flavors**: Each lever contributes recurring revenue uplift, recurring cost savings, one-time working capital release, and/or ongoing financing benefit. Only recurring flows are multiplied into enterprise value.
- **Cross-lever dependency**: Causally linked levers are adjusted in topological order to prevent double-counting revenue recovery.
- **Reconciliation invariant**: Entry EV + organic + RCM uplift + multiple expansion = exit EV exactly in all bridge computations.
