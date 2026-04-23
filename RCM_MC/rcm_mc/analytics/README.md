# Analytics

Advanced analytics for initiative impact measurement and service line profitability. Provides causal inference, counterfactual modeling, and DRG-level P&L decomposition — all numpy-only.

---

## `causal_inference.py` — Causal Impact Measurement

**What it does:** Measures the causal impact of an RCM initiative using three methods: Interrupted Time Series (ITS), Difference-in-Differences (DiD), and pre-post comparison. Produces a dollar estimate of the initiative's actual impact rather than just correlational change.

**How it works:** (1) **ITS**: fits a piecewise linear regression `y = β₀ + β₁t + β₂·post + β₃·t_post` to the metric time series (quarterly snapshots), where `post` is an indicator for post-initiative periods. `β₂` is the level shift and `β₃` is the slope change attributable to the intervention. Uses `finance/regression.py` for HC3 robust standard errors. (2) **DiD**: compares the treatment deal's metric change against a control group of comparable deals (from `ml/comparable_finder.py`) that didn't run the initiative. `DiD_estimate = (treated_after - treated_before) - (control_after - control_before)`. (3) **Pre-post**: simple mean comparison with bootstrap CI. Returns a `CausalEstimate` with all three estimates and their CIs; the preferred method is selected by sample size.

**Data in:** Quarterly metric snapshots from `deals/deal_sim_inputs.py`; control group from `ml/comparable_finder.py`; initiative timing from `rcm/initiative_tracking.py`.

**Data out:** `CausalEstimate` for the initiative impact panel.

---

## `counterfactual.py` — Counterfactual EBITDA Modeling

**What it does:** "What would EBITDA be today if we hadn't executed the denial management initiative?" Provides the counterfactual baseline for attributing realized value creation.

**How it works:** Uses the causal estimate from `causal_inference.py` to model what the metric's trajectory would have been without the intervention (projecting the pre-intervention trend forward). Feeds the counterfactual metrics through the v1 bridge to compute counterfactual EBITDA. Returns `actual_ebitda - counterfactual_ebitda` as the initiative's causal EBITDA contribution. Accounts for ramp curves (the initiative's effect builds over time according to `pe/ramp_curves.py`).

**Data in:** `CausalEstimate` from `causal_inference.py`; actual EBITDA trajectory from `deals/deal_sim_inputs.py`; bridge from `pe/rcm_ebitda_bridge.py`.

**Data out:** Counterfactual EBITDA contribution for value creation attribution.

---

## `service_lines.py` — DRG-Level Service Line P&L

**What it does:** Maps DRG codes to service line categories and computes per-service-line P&L from claim-level data. Answers "which service lines are profitable, and which are subsidized?"

**How it works:** `_DRG_TO_SERVICE_LINE` dict maps ~500 DRG codes to 12 service line categories (cardiac, orthopedics, oncology, neurology, behavioral health, maternity, NICU, ED, medical/surgical, rehabilitation, LTACH, other). For each service line: aggregates case volumes, average payment per case, average cost per case (from HCRIS cost center data), and margin. Returns a `ServiceLinePnL` summary used by the Market Analysis tab.

**Data in:** DRG volume data from `data/cms_utilization.py`; cost center data from `data/cms_hcris.py`; DRG weights from `data/drg_weights.py`.

**Data out:** `ServiceLinePnL` for the Market Analysis tab and pe_intelligence service-line concentration analysis.

---

## `demand_analysis.py` — Service Demand Forecasting

**What it does:** Forecasts inpatient and outpatient volume by service line using demographic trends and market share assumptions.

**How it works:** Combines: (1) county-level population aging projections (from Census Bureau data, static table); (2) disease prevalence trends (from `data/disease_density.py`); (3) current market share from `data/market_intelligence.py`. Projects volume 5 years forward using a linear demand model with demographic adjustment factors per service line (e.g., cardiac volumes grow 2% per year with aging population). Returns a `DemandForecast` for the market analysis panel.

**Data in:** Current discharge volumes from `data/cms_utilization.py`; demographic data (static Census table); disease prevalence from `data/disease_density.py`.

**Data out:** `DemandForecast` per service line for the market analysis panel.

---

## Key Concepts

- **Causal, not correlational**: `causal_inference.py` uses ITS and DiD specifically to isolate the initiative's causal effect from confounding trends.
- **Counterfactual attribution**: `counterfactual.py` separates value creation that would have happened anyway (market growth) from value creation attributable to the intervention.
- **No external ML libs**: All regression is closed-form numpy via `finance/regression.py`.
