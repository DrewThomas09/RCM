# Finance

Reimbursement and revenue-realization modeling. Encodes the economic structure of how hospitals get paid — making the EBITDA impact of operational metrics sensitive to payer mix and reimbursement method rather than applying uniform multipliers.

---

## `reimbursement_engine.py` — Reimbursement and Revenue-Realization Engine

**What it does:** The financial engine that makes the v2 bridge work. Models how each hospital's specific payer mix and reimbursement method mix translates operational improvements (denial recovery, AR reduction) into actual EBITDA impact. A 1% denial reduction on a commercial-heavy DRG hospital is worth more than the same improvement on a capitated rural health system.

**How it works:** Builds a `ReimbursementProfile` for the hospital by: (1) parsing the payer mix fractions from the deal profile; (2) inferring the reimbursement method distribution — if not observed, infers from payer mix (commercial → mostly FFS/DRG, Medicare → DRG-prospective, Medicaid → per-diem or cost-based, MA → DRG with discounts); (3) applies `MethodSensitivity` entries encoding each method's sensitivity to each RCM lever on a 0.0–1.0 scale (e.g., DRG_PROSPECTIVE has full sensitivity to denial recovery, CAPITATION has near-zero sensitivity since denied claims don't change capitation revenue). Computes a weighted-average `RealizationPath` per lever — the fraction of the nominal improvement that translates to actual cash. Tags all inferred fields with `source='inferred_from_profile'` in the provenance dict.

**Data in:** Deal profile payer mix fractions from the `DealAnalysisPacket`; reimbursement method observations (optional, from analyst override or document reader); `MethodSensitivity` table (static, defined in the module).

**Data out:** `ReimbursementProfile` dataclass consumed by `pe/value_bridge_v2.py` to weight lever impacts; `RealizationPath` per lever fed into the v2 MC.

---

## `dcf_model.py` — Discounted Cash Flow Model

**What it does:** Builds a 5-year DCF model for a deal, projecting free cash flow using the EBITDA bridge as the starting point and adjusting for capex, working capital, debt service, and taxes.

**How it works:** Takes the `ValueBridgeResult` recurring EBITDA delta and adds: organic growth ramp (configurable CAGR), capex (% of revenue from HCRIS industry median), D&A (% of revenue), changes in net working capital (from the v2 WC release schedule), and debt service from `pe/debt_model.py`. Computes unlevered FCF per year, discounts at the WACC (analyst input or benchmark), sums to intrinsic value. Reconciles DCF value with the bridge EV for the "multiple implied by DCF" check.

**Data in:** `ValueBridgeResult` from `pe/value_bridge_v2.py`; capex/D&A benchmarks from `hospital_benchmarks`; debt schedule from `pe/debt_model.py`.

**Data out:** `DCFResult` with year-by-year FCF table, intrinsic value, and implied EV multiple.

---

## `denial_drivers.py` — Denial Driver Analytics

**What it does:** Decomposes the total denial rate into its constituent root causes (eligibility, prior auth, coding, timely filing, duplicate claims) and models the EBITDA impact of fixing each category.

**How it works:** Uses the claim analytics data (from `data/claim_analytics.py`) if available; otherwise falls back to industry distribution benchmarks. For each denial category: computes the avoidable share (the fraction fixable through operational improvement), the appeal overturn rate, and the net revenue per recovered claim. Sums to a total denial improvement opportunity by category. Used by the RCM Profile tab's denial breakdown chart.

**Data in:** `ClaimAnalytics` from `data/claim_analytics.py`; industry denial distribution benchmarks from `hospital_benchmarks`.

**Data out:** Per-category denial opportunity analysis for the RCM Profile tab.

---

## `lbo_model.py` — Leveraged Buyout Model

**What it does:** Full LBO model: builds the sources/uses table, models the entry equity check, projects the debt schedule, and computes exit equity and MOIC/IRR.

**How it works:** Takes entry EV, debt structure (TL B + revolver + mezzanine), hold years, and exit multiple. Computes equity check as `entry_EV − total_debt`. Projects EBITDA using the bridge + organic growth ramp. Applies mandatory amortization and optional cash sweep. Computes exit equity as `exit_EV − remaining_debt`. Returns `LBOResult` with MOIC, IRR, and a year-by-year sources/uses/leverage table.

**Data in:** Entry EV and deal terms from analyst input; projected EBITDA from the bridge; debt schedule from `pe/debt_model.py`.

**Data out:** `LBOResult` with MOIC, IRR, and full LBO schedule.

---

## `market_analysis.py` — Market and Competitive Position Analysis

**What it does:** Analyzes the hospital's competitive position and market attractiveness as inputs to the investment thesis.

**How it works:** Aggregates: HHI market concentration (from `data/market_intelligence.py`), payer mix trend (from `benchmark_evolution.py`), volume trend (from `cms_utilization.py`), and service-line mix analysis (from `analytics/service_lines.py`). Scores the market on attractiveness (growing volume, improving payer mix, defensive competitive position) and threat (high HHI = monopoly risk, MA penetration trend, Medicaid work-requirement exposure). Returns a `MarketAnalysis` for the deal workbench.

**Data in:** CMS utilization and HCRIS data from `hospital_benchmarks`; market intelligence from `data/market_intelligence.py`.

**Data out:** `MarketAnalysis` for the deal workbench Market Analysis tab.

---

## `regression.py` — Financial Regression Utilities

**What it does:** Regression helpers for financial modeling: OLS regression with heteroskedasticity-robust standard errors, F-test, and confidence intervals. Used internally by the analytics layer.

**How it works:** Closed-form OLS `β = (XᵀX)⁻¹Xᵀy` with HC3 robust standard errors (leverage-adjusted residuals). Returns `RegressionResult` with coefficients, standard errors, t-stats, p-values, R², and F-stat. No sklearn — pure numpy. Used by `analytics/causal_inference.py` for the ITS and DiD estimators.

**Data in:** Numpy arrays `(X, y)` from the calling analytics module.

**Data out:** `RegressionResult` with full OLS output.

---

## `three_statement.py` — Simplified Three-Statement Financial Model

**What it does:** Projects a simplified income statement, balance sheet, and cash flow statement over the hold period. Provides context for the LBO model and LP reporting.

**How it works:** Takes entry financials (revenue, EBITDA, D&A, NWC, debt) and projects forward using: revenue growth rate, EBITDA margin improvement from the bridge, capex schedule, NWC improvement from AR reduction. Ties income statement to cash flow to balance sheet. Returns annual statements for the 5-year hold period.

**Data in:** Entry financials from the deal profile; bridge EBITDA improvement from `pe/value_bridge_v2.py`; capex benchmarks from `hospital_benchmarks`.

**Data out:** Three-statement model for the deal workbench and diligence package.

---

## `life_sciences.py` — Life-Sciences Valuation Engine (rNPV)

**What it does:** Prices life-sciences assets (therapeutics, devices, diagnostics) the way the sector actually values them — with a **risk-adjusted NPV (rNPV)** driven by clinical trial success probabilities, not an EBITDA multiple. The rest of `finance/` prices recurring-cash-flow services businesses; a pre-revenue drug asset has negative near-term cash flow, a binary clinical outcome, and a finite patent-protected life, so it needs a fundamentally different model. Pure-Python (`math` + `numpy` for the Monte Carlo), zero new dependencies.

**Core rNPV.** `AssetRNPVConfig` → `value_asset_rnpv()` schedules the remaining development phases from the asset's `current_phase`, risks each future cash flow by the cumulative probability of reaching it, and discounts to today. Development spend is weighted by the probability of *reaching* that phase; commercial cash flow by the full cumulative **Likelihood of Approval (LoA)**. Returns `rnpv_musd` (the headline), `npv_success_musd` (the approval-case upside), the LoA, a year-by-year projection, and a `provenance` dict tagging every benchmark default vs. analyst input.

**Clinical framework.** `PHASE_SUCCESS_TABLE` encodes phase-transition probabilities by `TherapeuticArea`, calibrated so the cumulative Phase-1 LoA reproduces the published BIO 2011–2020 range (ALL ≈ 7.9%; hematology highest ~24%; oncology/CNS lowest ~5–6%; vaccines high). Sourced from Wong/Siah/Lo (2019), BIO/Informa (2021), and DiMasi (2016) — all analyst-overridable.

**Peak-sales, endogenously.** `EpidemiologyFunnel` builds peak sales bottom-up (population → diagnosed → treated → eligible → captured × net price × adherence) instead of pulling a number from the air. `competition_adjusted_peak_sales()` splits a class-level TAM among expected entrants by **order of entry** (first movers anchor share; late entrants split the residual) and differentiation.

**Deal economics.** `LicensingDeal` (upfront + risked milestones + tiered royalties) overlays a licensing structure and splits the asset's rNPV between **licensor and licensee** — the number both sides argue over.

**Dynamic / stochastic layers.**
- `monte_carlo_rnpv()` — full binary-outcome simulation: each clinical gate is a Bernoulli trial; failures are worth the *negative* sunk development cost; successes draw a stochastic peak. The **mean reconciles to the analytic rNPV** — the point estimate is just the expected value of a violently skewed, bimodal distribution. Returns P10/P50/P90, P(positive), P(reaches market), and conditional expectations.
- `sensitivity_tornado()` / `sensitivity_grid()` — one- and two-way sensitivity (the diligence tornado + heatmap).
- `breakeven_peak_sales()` / `breakeven_loa()` — solve for the peak sales, or the *implied probability of success*, at which rNPV hits zero — i.e., what the price makes you believe.
- `real_options_value()` — a staged-abandonment decision tree: rNPV assumes you always continue; reality lets you kill a program after a weak readout. Quantifies that walk-away option's premium.
- `expected_value_blend()` — probability-weighted expected rNPV across a bear/base/bull scenario set.

**Company / portfolio.** `value_pipeline()` (sum-of-the-parts across assets net of platform G&A and cash), `runway_analysis()` (cash runway + next-raise sizing — the first question in any pre-profit biotech deal).

**Adjacent subsectors.** `cdmo_capacity_model()` (CDMO/CRO capacity, utilization, operating leverage, book-to-bill) and `diagnostics_unit_economics()` (razor/razor-blade instrument + consumable annuity).

**Side-by-side (`compare_*`).** `compare_assets()`, `compare_scenarios()`, and `compare_assets_deep()` (adds the Monte-Carlo distribution rows) align any number of assets or scenarios on the same metric rows with deltas vs. a base, and render to `to_dict()` or a markdown table.

**Data in:** analyst inputs (phase, therapeutic area, peak sales, deal terms) with benchmark defaults filling every gap. **Data out:** `RNPVResult` / `MonteCarloResult` / `Comparison` dataclasses, each with a `to_dict()` for UI/API/export.

---

## Key Concepts

- **rNPV over multiples**: Life sciences values a binary, finite-life asset by probability-weighting each future cash flow — not by applying a multiple to today's (often negative) EBITDA. The point rNPV is the *expected value* of a bimodal distribution; `monte_carlo_rnpv` shows the whole shape.
- **Method-sensitive economics**: A 1% denial rate reduction is worth more on a DRG-prospective hospital than a capitated one — the reimbursement engine makes this structure explicit and auditable.
- **Mechanism tables over opaque functions**: Every reimbursement method has a `MethodSensitivity` entry encoding its sensitivity to each RCM lever on a 0–1 scale. Analysts can read and defend every cell.
- **Transparent inference**: Whenever a gap is filled (method distribution, discount, timing), the field is tagged in the profile's `provenance` dict so renderers show `inferred_from_profile` vs. `observed`.
