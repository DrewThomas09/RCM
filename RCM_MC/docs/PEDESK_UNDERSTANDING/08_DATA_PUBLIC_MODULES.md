# 08 · The data_public analytic modules (~150)

> PE Desk has ~150 single-purpose analytic pages reached via the Cmd-K palette and `/module-index`. They look uniformly polished, but they are **not uniformly live** — and that distinction is the most important thing in this whole reference. This file explains the shared pattern, tags every module by data source, and is explicit about which are computed vs **curated/illustrative**.

---

## ⚠ Read this first: live vs curated

Each module is a thin two-file unit (engine + page). They fall into **four data-source classes**, and you must know which one a given page is before quoting its numbers to anyone:

| Class | What it means | Safe to quote as real? |
|---|---|---|
| **[corpus]** | Computed live from the realized-deal corpus (`public_deals` / seed files) | Yes — but the corpus has a real/synthetic split (see below) |
| **[CMS]** | Computed live from CMS public DataFrames (Medicare payments, etc.) | Yes |
| **[calc]** | A query-param calculator (your inputs → math, no stored data) | Yes — it's your inputs |
| **[curated]** | **Hardcoded illustrative data** — named "Project Cypress / Redwood" deals, fixed payer/state lists. The corpus is loaded **only for a "Corpus Deals" count badge**; the analytic content is *not* computed from live deals. | **No — illustrative only** |

**The majority of the "tracker"-style modules are [curated].** They are demo/illustrative surfaces that show realistic-looking numbers built from hardcoded dataclass lists. They are not wired to live data. (Full classification lists at the bottom of this file.) If a partner or LP asks "is this our portfolio's real 340B exposure?" the honest answer for a curated module is "no — that's an illustrative template."

> This is not a defect per se — these were built as the analytic *surface* ahead of the data wiring — but it must be stated plainly so nobody mistakes a curated tracker for a live one.

---

## The shared pattern

**Route:** `server.py` has a long `if path == "/<slug>":` ladder that lazy-imports the page and returns HTML, e.g.
```python
if path == "/base-rates":
    from .ui.data_public.base_rates_page import render_base_rates
    return self._send_html(render_base_rates(_qp))
```
**Engine ↔ page split:** `data_public/<topic>.py` (pure compute, returns dataclasses) + `ui/data_public/<topic>_page.py` (`render_<topic>(params) -> str`).
**Render:** `chartis_shell` + `ck_page_title` + a `ck_kpi_block` strip + (often) `ck_value_anchor` ($-opportunity lead) + inline SVG charts + `ck_table`.
**Discovery:** the Cmd-K palette (`_DEFAULT_PALETTE_MODULES`) and `/module-index` (a hand-maintained catalog of ~40 highlighted modules with `corpus_dependent` flags) and `/corpus-dashboard` / `/corpus-coverage`.
**Empty states:** corpus pages emit `—` for missing percentiles; curated pages can never be empty (data is hardcoded); calculators fall back to defaults.

> **Caveat:** each engine rolls its own `_load_corpus()` with inconsistent ranges (`range(2,46)`, `(2,89)`, `(2,122)`…), so the "Corpus Deals" count can differ page to page. The canonical provenance-aware loader is `corpus_loader.load_corpus_deals(mode=…)`, but most pages don't use it yet.

---

## Catalog by theme
(tag = data source; see the table above)

**Valuation / returns:** `base-rates` [corpus], `market-rates` [corpus], `peer-valuation` [corpus], `comparables`/`find-comps` [corpus], `multiple-decomp` [corpus], `entry-multiple`/`exit-multiple` [corpus], `subsector-benchmarks` [corpus], `qoe-analyzer` [corpus], `return-attribution` [corpus], `capital-efficiency` [corpus], `value-backtester` [corpus], `peer-transactions` [curated].

**Debt / capital:** `leverage-intel` [corpus], `underwriting-model` [corpus+calc], `lbo-stress`/`cap-structure` [calc], `covenant-monitor` [corpus]; `covenant-headroom`, `debt-service`, `debt-financing`, `dividend-recap`, `refi-optimizer`, `direct-lending`, `nav-loan-tracker` [curated].

**Risk / red flags:** `deal-risk-scores` [corpus], `risk-matrix` [corpus], `redflag-scanner` [corpus], `deal-quality` [corpus], `concentration-risk` [corpus]; `regulatory-risk`, `cyber-risk`, `litigation-tracker`, `fraud-detection`, `key-person` [curated].

**Payer / revenue:** `payer-intel` [corpus], `payer-stress` [corpus], `reimbursement-risk` [corpus]; `payer-shift` [calc/curated]; `payer-concentration`, `payer-contracts`, `payer-rate-trends`, `nsa-tracker`, `ref-pricing`, `risk-adjustment`, `ma-contracts`, `ma-star-tracker`, `aco-economics`, `medicaid-unwinding`, `revenue-leakage` [curated].

**Operations / workforce / clinical:** `provider-network` [corpus]; `physician-labor`, `physician-productivity`, `phys-comp-plan`, `workforce-planning`/`-retention`, `locum-tracker`, `clinical-outcomes`, `quality-scorecard`, `patient-experience`, `unit-economics`, `cost-structure`, `working-capital`, `cin-analyzer`, `tech-stack`, `ai-operating-model`, `clinical-ai-tracker`, `hcit-platform`, `supply-chain`, `gpo-supply-tracker`, `drug-shortage`, `tracker-340b`, `biosimilars-opp` [curated].

**Deal lifecycle / exit:** `value-creation` [corpus], `rollup-economics`/`bolton-analyzer` [corpus], `hold-optimizer`/`hold-analysis` [corpus+calc], `acq-timing` [corpus], `deal-postmortem` [corpus], `ic-memo` [corpus]; `deal-origination`/`-pipeline`/`-sourcing`, `vdr-tracker`, `pmi-playbook`/`-integration`, `value-creation-plan`/`vcp-tracker`, `denovo-expansion`, `growth-runway`, `sellside-process`, `earnout`/`escrow-earnout` [curated].

**Sector / market:** `sector-intel`/`-momentum`/`-correlation` [corpus], `antitrust-screener` [corpus], `msa-concentration` [corpus/CMS], `market-concentration` [CMS]; `geo-market`, `competitive-intel`, `telehealth-econ`, `trial-site-econ`, `demand-forecast` [curated].

**Portfolio / LP / fund ops:** `lp-dashboard`/`lp-reporting` [corpus], `fund-attribution` [corpus], `mgmt-fee-tracker` [corpus], `vintage-perf` [corpus], `sponsor-league`/`-heatmap` [corpus], `gp-benchmarking`/`irr-dispersion`/`portfolio-optimizer`/`portfolio-sim`/`scenario-mc` [corpus/calc]; `dpi-tracker`, `capital-pacing`/`-call`/`-schedule`, `fundraising-tracker`, `coinvest-pipeline`, `secondaries-tracker`, `continuation-vehicle`, `vintage-cohorts`, `treasury-tracker`, `board-governance`, `operating-partners` [curated].

**Real estate / ESG / tax / compliance:** `esg-dashboard` [corpus]; `tax-structure(-analyzer)` [calc]; `real-estate`, `medical-realestate`, `reit-analyzer`, `esg-impact`, `health-equity`, `tax-credits`, `insurance-tracker`, `rw-insurance`, `hospital-anchor`, `compliance-attestation` [curated].

---

## Deep-dives (the substantive ones)

### `deal_risk_scorer.py` — 5-factor 0–100 [corpus, live]
Reads every corpus deal. **Weights:** entry-multiple 0.30, payer-concentration 0.20, hold-duration 0.20, vintage-cycle 0.15, size 0.15. Each component is a 0–100 step function (entry-multiple premium vs sector median; payer **HHI on 0–10,000 scale**; flip-risk vs sector-optimal hold = P50 hold among MOIC≥2.5 deals; macro-risk vintage years; size sweet-spot $75–500M). Tier <25 Low / <50 Medium / <70 High / else Critical. Validated against realized MOIC.

### `hold_period_optimizer.py` — multiple-compression curve [calc + corpus overlay]
For years 1–10: `exit_ebitda = entry·(1+cagr)^y`; multiple flat through year 3 then compresses at a sector rate (health-IT −0.40/yr … default −0.25, floored at 60% of entry); `gross_moic = (exit_ev − amortized_debt)/entry_equity`; net MOIC applies 20% carry + fee drag. Optimal = peak-MOIC year, peak-IRR year, sweet-spot (≥75% of peak MOIC), cliff year. Optionally overlays corpus P25/P50/P75 hold when ≥3 sector deals.

### `base_rates.py` / `market_rates.py` — P25/P50/P75/P90 by segment [corpus, live]
Linear-interpolation percentiles over filtered corpus deals for 8 metrics (EV, EV/EBITDA, margin, revenue, hold, MOIC, IRR, commercial share), rolled up by sector / size bucket / vintage / commercial-share bucket. Missing percentile → `—`. **Percentiles, not means** (fat-tailed returns).

### `payer_intelligence.py` — payer-regime returns [corpus, live]
Segments corpus deals by commercial share into 4 regimes (Gov-heavy <30%, Balanced 30–50%, Commercial-mix 50–70%, Commercial >70%); per regime: count, MOIC P25/P50/P75, IRR P50, loss rate; plus rank-correlation of commercial%→MOIC and medicaid%→MOIC. This is the empirical basis for the deal-page reasonableness payer regimes (§03).

### `market_concentration.py` — HHI/CR3/CR5 [CMS, live]
Real Medicare-payment DataFrame in. Per state-year-provider-type: `shares = payment/total`, **`HHI = Σ(share²)` on the 0–1 fractional scale** (≠ the 0–10,000 scale used by `deal_risk_scorer` and `market_structure`), CR3/CR5 = top-3/5 share sums. `state_portfolio_fit` blends growth/scale/stability/fragmentation weights summing to 1.0.

### `medicaid_unwinding.py` — PHE redetermination [CURATED — illustrative]
Six hardcoded `_build_*` lists (12 named "Project ___" deals, 15 states, coverage-shift dicts). Computes pre-PHE lives, disenrolled, net revenue impact (~−$76M across the 12 illustrative deals), back-to-Medicaid average, bad-debt-risk flag when self-pay shift ≥35%. **Numbers are illustrative, not your portfolio.**

### `telehealth_econ.py` — virtual-care economics [CURATED — illustrative]
Hardcoded visit types / parity matrix / regulatory cliffs. `gross_margin = reimbursement − direct_cost`; blended GM; revenue-at-risk per regulatory cliff (e.g. Medicare PHE flexibilities $28.5M). **Illustrative.**

### `tax_credits.py` — R&D/ITC/QOZ/WOTC [CURATED — illustrative]
Hardcoded credit/incentive/QOZ/WOTC lists. **Total annual benefit** = `state_annual + wotc_annual + transfer_pricing_annual + R&D_gross/5` (R&D amortized over 5 yrs). **Illustrative.**

---

## Honesty classification (which modules are which)

**Genuinely corpus-computed (live):** market_rates/base_rates, payer_intelligence, payer_sensitivity, payer_mix_shift_model, payer_stress, deal_risk_scorer, deal_risk_matrix, deal_quality_scorer, deal_teardown_analyzer, hold_optimizer, sponsor_track_record/heatmap/analytics, vintage_analytics, size_analytics, sector_intelligence/correlation, subsector_benchmarks, return_attribution, leverage_analytics, covenant_monitor, mgmt_fee_tracker, qoe_analyzer, multiple_decomp, exit_multiple, capital_efficiency, value_creation, comparables, deal_comparables_enhanced, backtester, value_backtester, redflag_scanner, concentration_analytics, provider_network, reimbursement_risk_model, lp_dashboard, fund_attribution, portfolio_analytics, esg_dashboard.

**Genuinely CMS/DataFrame-driven (live):** the `cms_*` family + market_concentration, provider_regime, provider_trend_reliability.

**Calculators (your inputs, no stored data):** hold_period_optimizer, lbo_stress, lbo_entry_optimizer, cap_structure, scenario_mc, portfolio_sim, tax_structure(_analyzer).

**Curated / illustrative (NOT live — hardcoded demo data):** medicaid_unwinding, telehealth_econ, tax_credits, nsa_tracker, payer_concentration, payer_contracts, ma_contracts, ma_star_tracker, aco_economics, drug_pricing_340b, tracker_340b, biosimilars_opp, drug_shortage, supply_chain, gpo_supply_tracker, cyber_risk, health_equity, esg_impact, regulatory_risk, litigation_tracker, insurance_tracker, rw_insurance, fraud_detection, key_person, physician_labor, physician_productivity, phys_comp_plan, mgmt_comp, partner_economics, workforce_planning/retention, locum_tracker, clinical_outcomes, quality_scorecard, patient_experience, digital_front_door, tech_stack, ai_operating_model, clinical_ai_tracker, hcit_platform, cin_analyzer, trial_site_econ, direct_employer, denovo_expansion, demand_forecast, competitive_intel, real_estate, medical_realestate, reit_analyzer, hospital_anchor, board_governance, operating_partners, diligence_vendors, compliance_attestation, capex_budget, treasury_tracker, fundraising_tracker, capital_call_tracker, capital_pacing, capital_schedule, coinvest_pipeline, nav_loan_tracker, secondaries_tracker, continuation_vehicle, dpi_tracker, dividend_recap, escrow_earnout, earnout, debt_financing, debt_service, covenant_headroom, refi_optimizer, direct_lending, sellside_process, vdr_tracker, transition_services, pmi_integration, pmi_playbook, value_creation_plan, vcp_tracker, peer_transactions, vintage_cohorts, payer_shift, ref_pricing, risk_adjustment, zbb_tracker, ic_memo.

> If you're demoing to an investor, lead with the **live** modules (sponsor league, base rates, payer intelligence, deal-risk scores, comparables, market concentration) and frame the curated trackers as "the analytic templates we light up per deal."

---
*Next: `09_HOSPITAL_PAGES.md` — the per-hospital surfaces (`/hospital/<ccn>/*`).*
