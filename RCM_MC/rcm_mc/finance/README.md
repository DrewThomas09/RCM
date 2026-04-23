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

## Key Concepts

- **Method-sensitive economics**: A 1% denial rate reduction is worth more on a DRG-prospective hospital than a capitated one — the reimbursement engine makes this structure explicit and auditable.
- **Mechanism tables over opaque functions**: Every reimbursement method has a `MethodSensitivity` entry encoding its sensitivity to each RCM lever on a 0–1 scale. Analysts can read and defend every cell.
- **Transparent inference**: Whenever a gap is filled (method distribution, discount, timing), the field is tagged in the profile's `provenance` dict so renderers show `inferred_from_profile` vs. `observed`.
