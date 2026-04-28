# V5 Fidelity Report

Audited 325 renderer files in `rcm_mc/ui/`. 
Passing threshold: **70/100**.

- **5 above threshold** — chartis-grade
- **320 below threshold** — needs editorial cycle

Run `python tools/v5_fidelity_audit.py` to refresh.

---

## Above threshold

| Score | File | LOC | Primitives | Notes |
|---|---|---|---|---|
| 84 | `rcm_mc/ui/my_dashboard_page.py` | 309 | 23 (7.4/100) | — |
| 74 | `rcm_mc/ui/data_public/deals_library_page.py` | 263 | 18 (6.8/100) | no italic-serif highlight (chartis cadence missing) |
| 71 | `rcm_mc/ui/chartis/corpus_backtest_page.py` | 385 | 14 (3.6/100) | high inline-style count: 27 |
| 70 | `rcm_mc/ui/escalations_page.py` | 148 | 15 (10.1/100) | no italic-serif highlight (chartis cadence missing) |
| 70 | `rcm_mc/ui/research_page.py` | 223 | 10 (4.5/100) | no italic-serif highlight (chartis cadence missing) |

## Below threshold

Sorted highest score first — these pages are partially editorial. Lowest scorers are the next ports.

| Score | File | LOC | Primitives | Notes |
|---|---|---|---|---|
| 68 | `rcm_mc/ui/notes_search_page.py` | 219 | 9 (4.1/100) | no italic-serif highlight (chartis cadence missing) |
| 65 | `rcm_mc/ui/alerts_page.py` | 249 | 17 (6.8/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 11 |
| 65 | `rcm_mc/ui/chartis/stress_page.py` | 246 | 9 (3.7/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 11 |
| 65 | `rcm_mc/ui/data_public/value_backtester_page.py` | 260 | 9 (3.5/100) | high inline-style count: 101; high non-ck-class <div> count: 27 |
| 64 | `rcm_mc/ui/data_public/multiple_decomp_page.py` | 281 | 10 (3.6/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 13 |
| 64 | `rcm_mc/ui/data_public/payer_stress_page.py` | 291 | 9 (3.1/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 12 |
| 63 | `rcm_mc/ui/data_public/acq_timing_page.py` | 279 | 10 (3.6/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 15 |
| 62 | `rcm_mc/ui/data_public/market_rates_page.py` | 289 | 9 (3.1/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 16 |
| 62 | `rcm_mc/ui/data_public/portfolio_sim_page.py` | 266 | 9 (3.4/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 16 |
| 61 | `rcm_mc/ui/data_public/capital_efficiency_page.py` | 247 | 10 (4.0/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 15 |
| 61 | `rcm_mc/ui/data_public/deal_risk_scores_page.py` | 232 | 10 (4.3/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 16 |
| 60 | `rcm_mc/ui/data_public/hold_optimizer_page.py` | 347 | 9 (2.6/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 12 |
| 60 | `rcm_mc/ui/data_public/sector_correlation_page.py` | 269 | 8 (3.0/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 16 |
| 57 | `rcm_mc/ui/chartis/market_structure_page.py` | 271 | 8 (3.0/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 20 |
| 57 | `rcm_mc/ui/chartis/sponsor_track_record_page.py` | 289 | 9 (3.1/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 24 |
| 57 | `rcm_mc/ui/data_public/risk_matrix_page.py` | 281 | 9 (3.2/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 26 |
| 56 | `rcm_mc/ui/bankruptcy_survivor_page.py` | 196 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC) |
| 54 | `rcm_mc/ui/chartis/deal_screening_page.py` | 370 | 9 (2.4/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 21 |
| 54 | `rcm_mc/ui/data_public/diligence_checklist_page.py` | 188 | 7 (3.7/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 30 |
| 54 | `rcm_mc/ui/data_public/leverage_intel_page.py` | 232 | 9 (3.9/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 33 |
| 54 | `rcm_mc/ui/data_public/sector_intel_page.py` | 250 | 9 (3.6/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 32 |
| 54 | `rcm_mc/ui/data_public/size_intel_page.py` | 199 | 10 (5.0/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 32 |
| 54 | `rcm_mc/ui/data_public/vintage_perf_page.py` | 219 | 10 (4.6/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 33 |
| 53 | `rcm_mc/ui/data_public/corpus_dashboard_page.py` | 294 | 11 (3.7/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 44 |
| 53 | `rcm_mc/ui/data_public/sponsor_league_page.py` | 271 | 8 (3.0/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 44 |
| 52 | `rcm_mc/ui/chartis/white_space_page.py` | 305 | 9 (3.0/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 28; high non-ck-class <div> count: 14 |
| 52 | `rcm_mc/ui/data_public/data_sources_admin_page.py` | 242 | 10 (4.1/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 41; high non-ck-class <div> count: 15 |
| 52 | `rcm_mc/ui/data_public/payer_intel_page.py` | 277 | 9 (3.2/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 41; high non-ck-class <div> count: 12 |
| 52 | `rcm_mc/ui/data_public/portfolio_optimizer_page.py` | 230 | 9 (3.9/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 34; high non-ck-class <div> count: 14 |
| 52 | `rcm_mc/ui/settings_ai_page.py` | 252 | 9 (3.6/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 35; high non-ck-class <div> count: 14 |
| 51 | `rcm_mc/ui/chartis/home_page.py` | 649 | 9 (1.4/100) | high inline-style count: 74; high non-ck-class <div> count: 44 |
| 51 | `rcm_mc/ui/chartis/rcm_benchmarks_page.py` | 332 | 7 (2.1/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 21 |
| 51 | `rcm_mc/ui/data_public/biosimilars_opp_page.py` | 155 | 9 (5.8/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 77; high non-ck-class <div> count: 19 |
| 51 | `rcm_mc/ui/data_public/capital_pacing_page.py` | 201 | 11 (5.5/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 82; high non-ck-class <div> count: 18 |
| 51 | `rcm_mc/ui/data_public/capital_schedule_page.py` | 286 | 9 (3.1/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 64; high non-ck-class <div> count: 19 |
| 51 | `rcm_mc/ui/data_public/cms_sources_page.py` | 248 | 9 (3.6/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 45; high non-ck-class <div> count: 18 |
| 51 | `rcm_mc/ui/data_public/cost_structure_page.py` | 250 | 9 (3.6/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 60; high non-ck-class <div> count: 18 |
| 51 | `rcm_mc/ui/data_public/diligence_vendors_page.py` | 155 | 9 (5.8/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 75; high non-ck-class <div> count: 19 |
| 51 | `rcm_mc/ui/data_public/direct_employer_page.py` | 158 | 9 (5.7/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 76; high non-ck-class <div> count: 19 |
| 51 | `rcm_mc/ui/data_public/direct_lending_page.py` | 154 | 9 (5.8/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 73; high non-ck-class <div> count: 19 |
| 51 | `rcm_mc/ui/data_public/fund_attribution_page.py` | 267 | 9 (3.4/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 62; high non-ck-class <div> count: 16 |
| 51 | `rcm_mc/ui/data_public/hcit_platform_page.py` | 159 | 9 (5.7/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 73; high non-ck-class <div> count: 19 |
| 51 | `rcm_mc/ui/data_public/health_equity_page.py` | 137 | 9 (6.6/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 62; high non-ck-class <div> count: 16 |
| 51 | `rcm_mc/ui/data_public/mgmt_comp_page.py` | 266 | 9 (3.4/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 65; high non-ck-class <div> count: 17 |
| 51 | `rcm_mc/ui/data_public/module_index_page.py` | 130 | 9 (6.9/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 52; high non-ck-class <div> count: 16 |
| 51 | `rcm_mc/ui/data_public/msa_concentration_page.py` | 163 | 9 (5.5/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 78; high non-ck-class <div> count: 19 |
| 51 | `rcm_mc/ui/data_public/nsa_tracker_page.py` | 180 | 9 (5.0/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 83; high non-ck-class <div> count: 19 |
| 51 | `rcm_mc/ui/data_public/peer_valuation_page.py` | 259 | 9 (3.5/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 76; high non-ck-class <div> count: 19 |
| 51 | `rcm_mc/ui/data_public/physician_labor_page.py` | 157 | 9 (5.7/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 73; high non-ck-class <div> count: 19 |
| 51 | `rcm_mc/ui/data_public/physician_productivity_page.py` | 281 | 9 (3.2/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 65; high non-ck-class <div> count: 19 |
| 51 | `rcm_mc/ui/data_public/quality_scorecard_page.py` | 252 | 9 (3.6/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 75; high non-ck-class <div> count: 19 |
| 51 | `rcm_mc/ui/data_public/real_estate_page.py` | 268 | 9 (3.4/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 73; high non-ck-class <div> count: 17 |
| 51 | `rcm_mc/ui/data_public/redflag_scanner_page.py` | 189 | 9 (4.8/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 78; high non-ck-class <div> count: 19 |
| 51 | `rcm_mc/ui/data_public/ref_pricing_page.py` | 284 | 9 (3.2/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 74; high non-ck-class <div> count: 18 |
| 51 | `rcm_mc/ui/data_public/regulatory_risk_page.py` | 271 | 9 (3.3/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 80; high non-ck-class <div> count: 19 |
| 51 | `rcm_mc/ui/data_public/trial_site_econ_page.py` | 157 | 9 (5.7/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 75; high non-ck-class <div> count: 19 |
| 51 | `rcm_mc/ui/data_public/working_capital_page.py` | 292 | 9 (3.1/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 65; high non-ck-class <div> count: 19 |
| 50 | `rcm_mc/ui/chartis/portfolio_analytics_page.py` | 492 | 12 (2.4/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 36 |
| 50 | `rcm_mc/ui/chartis/red_flags_page.py` | 446 | 14 (3.1/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 49; high non-ck-class <div> count: 20 |
| 50 | `rcm_mc/ui/data_public/aco_economics_page.py` | 205 | 9 (4.4/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 94; high non-ck-class <div> count: 24 |
| 50 | `rcm_mc/ui/data_public/ai_operating_model_page.py` | 175 | 9 (5.1/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 86; high non-ck-class <div> count: 23 |
| 50 | `rcm_mc/ui/data_public/antitrust_screener_page.py` | 202 | 9 (4.5/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 99; high non-ck-class <div> count: 26 |
| 50 | `rcm_mc/ui/data_public/base_rates_page.py` | 262 | 9 (3.4/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 85; high non-ck-class <div> count: 22 |
| 50 | `rcm_mc/ui/data_public/board_governance_page.py` | 188 | 9 (4.8/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 87; high non-ck-class <div> count: 22 |
| 50 | `rcm_mc/ui/data_public/capex_budget_page.py` | 205 | 9 (4.4/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 99; high non-ck-class <div> count: 22 |
| 50 | `rcm_mc/ui/data_public/capital_call_tracker_page.py` | 211 | 9 (4.3/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 101; high non-ck-class <div> count: 22 |
| 50 | `rcm_mc/ui/data_public/cin_analyzer_page.py` | 208 | 9 (4.3/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 98; high non-ck-class <div> count: 22 |
| 50 | `rcm_mc/ui/data_public/clinical_ai_tracker_page.py` | 209 | 9 (4.3/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 93; high non-ck-class <div> count: 22 |
| 50 | `rcm_mc/ui/data_public/clinical_outcomes_page.py` | 285 | 9 (3.2/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 91; high non-ck-class <div> count: 22 |
| 50 | `rcm_mc/ui/data_public/cms_apm_tracker_page.py` | 197 | 9 (4.6/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 91; high non-ck-class <div> count: 22 |
| 50 | `rcm_mc/ui/data_public/cms_data_browser_page.py` | 191 | 9 (4.7/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 89; high non-ck-class <div> count: 22 |
| 50 | `rcm_mc/ui/data_public/coinvest_pipeline_page.py` | 208 | 9 (4.3/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 101; high non-ck-class <div> count: 22 |
| 50 | `rcm_mc/ui/data_public/competitive_intel_page.py` | 284 | 9 (3.2/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 78; high non-ck-class <div> count: 20 |
| 50 | `rcm_mc/ui/data_public/compliance_attestation_page.py` | 230 | 9 (3.9/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 99; high non-ck-class <div> count: 22 |
| 50 | `rcm_mc/ui/data_public/covenant_headroom_page.py` | 199 | 9 (4.5/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 85; high non-ck-class <div> count: 21 |
| 50 | `rcm_mc/ui/data_public/cyber_risk_page.py` | 194 | 9 (4.6/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 92; high non-ck-class <div> count: 26 |
| 50 | `rcm_mc/ui/data_public/deal_origination_page.py` | 188 | 9 (4.8/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 84; high non-ck-class <div> count: 21 |
| 50 | `rcm_mc/ui/data_public/deal_pipeline_page.py` | 267 | 9 (3.4/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 75; high non-ck-class <div> count: 21 |
| 50 | `rcm_mc/ui/data_public/deal_postmortem_page.py` | 187 | 10 (5.3/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 85; high non-ck-class <div> count: 26 |
| 50 | `rcm_mc/ui/data_public/deal_sourcing_page.py` | 199 | 9 (4.5/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 94; high non-ck-class <div> count: 22 |
| 50 | `rcm_mc/ui/data_public/debt_financing_page.py` | 212 | 9 (4.2/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 100; high non-ck-class <div> count: 22 |
| 50 | `rcm_mc/ui/data_public/demand_forecast_page.py` | 216 | 9 (4.2/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 87; high non-ck-class <div> count: 24 |
| 50 | `rcm_mc/ui/data_public/denovo_expansion_page.py` | 187 | 9 (4.8/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 81; high non-ck-class <div> count: 21 |
| 50 | `rcm_mc/ui/data_public/digital_front_door_page.py` | 187 | 9 (4.8/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 90; high non-ck-class <div> count: 22 |
| 50 | `rcm_mc/ui/data_public/dpi_tracker_page.py` | 200 | 9 (4.5/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 97; high non-ck-class <div> count: 22 |
| 50 | `rcm_mc/ui/data_public/drug_pricing_340b_page.py` | 230 | 9 (3.9/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 103; high non-ck-class <div> count: 24 |
| 50 | `rcm_mc/ui/data_public/drug_shortage_page.py` | 169 | 9 (5.3/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 80; high non-ck-class <div> count: 23 |
| 50 | `rcm_mc/ui/data_public/escrow_earnout_page.py` | 222 | 9 (4.1/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 103; high non-ck-class <div> count: 22 |
| 50 | `rcm_mc/ui/data_public/esg_dashboard_page.py` | 291 | 9 (3.1/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 81; high non-ck-class <div> count: 26 |
| 50 | `rcm_mc/ui/data_public/esg_impact_page.py` | 241 | 9 (3.7/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 110; high non-ck-class <div> count: 25 |
| 50 | `rcm_mc/ui/data_public/fraud_detection_page.py` | 185 | 9 (4.9/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 91; high non-ck-class <div> count: 26 |
| 50 | `rcm_mc/ui/data_public/fundraising_tracker_page.py` | 207 | 9 (4.3/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 96; high non-ck-class <div> count: 22 |
| 50 | `rcm_mc/ui/data_public/geo_market_page.py` | 288 | 9 (3.1/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 77; high non-ck-class <div> count: 21 |
| 50 | `rcm_mc/ui/data_public/gpo_supply_tracker_page.py` | 210 | 9 (4.3/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 96; high non-ck-class <div> count: 22 |
| 50 | `rcm_mc/ui/data_public/hospital_anchor_page.py` | 206 | 9 (4.4/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 98; high non-ck-class <div> count: 22 |
| 50 | `rcm_mc/ui/data_public/ic_memo_generator_page.py` | 193 | 9 (4.7/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 88; high non-ck-class <div> count: 26 |
| 50 | `rcm_mc/ui/data_public/insurance_tracker_page.py` | 193 | 9 (4.7/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 90; high non-ck-class <div> count: 21 |
| 50 | `rcm_mc/ui/data_public/lbo_stress_page.py` | 196 | 9 (4.6/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 76; high non-ck-class <div> count: 21 |
| 50 | `rcm_mc/ui/data_public/litigation_tracker_page.py` | 202 | 9 (4.5/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 99; high non-ck-class <div> count: 22 |
| 50 | `rcm_mc/ui/data_public/locum_tracker_page.py` | 217 | 9 (4.1/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 94; high non-ck-class <div> count: 21 |
| 50 | `rcm_mc/ui/data_public/lp_dashboard_page.py` | 417 | 19 (4.6/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 91; high non-ck-class <div> count: 27 |
| 50 | `rcm_mc/ui/data_public/lp_reporting_page.py` | 195 | 9 (4.6/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 93; high non-ck-class <div> count: 22 |
| 50 | `rcm_mc/ui/data_public/ma_contracts_page.py` | 242 | 10 (4.1/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 102; high non-ck-class <div> count: 24 |
| 50 | `rcm_mc/ui/data_public/ma_star_tracker_page.py` | 209 | 9 (4.3/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 95; high non-ck-class <div> count: 22 |
| 50 | `rcm_mc/ui/data_public/medicaid_unwinding_page.py` | 204 | 9 (4.4/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 97; high non-ck-class <div> count: 22 |
| 50 | `rcm_mc/ui/data_public/medical_realestate_page.py` | 198 | 9 (4.5/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 94; high non-ck-class <div> count: 22 |
| 50 | `rcm_mc/ui/data_public/nav_loan_tracker_page.py` | 192 | 9 (4.7/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 95; high non-ck-class <div> count: 22 |
| 50 | `rcm_mc/ui/data_public/operating_partners_page.py` | 210 | 9 (4.3/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 100; high non-ck-class <div> count: 22 |
| 50 | `rcm_mc/ui/data_public/partner_economics_page.py` | 225 | 9 (4.0/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 106; high non-ck-class <div> count: 24 |
| 50 | `rcm_mc/ui/data_public/patient_experience_page.py` | 224 | 9 (4.0/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 89; high non-ck-class <div> count: 24 |
| 50 | `rcm_mc/ui/data_public/payer_concentration_page.py` | 213 | 9 (4.2/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 86; high non-ck-class <div> count: 21 |
| 50 | `rcm_mc/ui/data_public/payer_contracts_page.py` | 209 | 9 (4.3/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 98; high non-ck-class <div> count: 22 |
| 50 | `rcm_mc/ui/data_public/peer_transactions_page.py` | 199 | 9 (4.5/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 96; high non-ck-class <div> count: 22 |
| 50 | `rcm_mc/ui/data_public/phys_comp_plan_page.py` | 217 | 9 (4.1/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 92; high non-ck-class <div> count: 21 |
| 50 | `rcm_mc/ui/data_public/platform_maturity_page.py` | 159 | 9 (5.7/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 79; high non-ck-class <div> count: 23 |
| 50 | `rcm_mc/ui/data_public/pmi_integration_page.py` | 213 | 9 (4.2/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 99; high non-ck-class <div> count: 22 |
| 50 | `rcm_mc/ui/data_public/pmi_playbook_page.py` | 176 | 10 (5.7/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 84; high non-ck-class <div> count: 23 |
| 50 | `rcm_mc/ui/data_public/provider_retention_page.py` | 234 | 9 (3.8/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 98; high non-ck-class <div> count: 24 |
| 50 | `rcm_mc/ui/data_public/refi_optimizer_page.py` | 199 | 9 (4.5/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 101; high non-ck-class <div> count: 26 |
| 50 | `rcm_mc/ui/data_public/reinvestment_page.py` | 226 | 9 (4.0/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 83; high non-ck-class <div> count: 21 |
| 50 | `rcm_mc/ui/data_public/reit_analyzer_page.py` | 212 | 9 (4.2/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 90; high non-ck-class <div> count: 21 |
| 50 | `rcm_mc/ui/data_public/risk_adjustment_page.py` | 202 | 9 (4.5/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 95; high non-ck-class <div> count: 22 |
| 50 | `rcm_mc/ui/data_public/rollup_economics_page.py` | 275 | 10 (3.6/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 118; high non-ck-class <div> count: 27 |
| 50 | `rcm_mc/ui/data_public/rw_insurance_page.py` | 203 | 9 (4.4/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 99; high non-ck-class <div> count: 22 |
| 50 | `rcm_mc/ui/data_public/secondaries_tracker_page.py` | 179 | 9 (5.0/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 84; high non-ck-class <div> count: 22 |
| 50 | `rcm_mc/ui/data_public/sellside_process_page.py` | 215 | 9 (4.2/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 102; high non-ck-class <div> count: 22 |
| 50 | `rcm_mc/ui/data_public/specialty_benchmarks_page.py` | 186 | 9 (4.8/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 93; high non-ck-class <div> count: 22 |
| 50 | `rcm_mc/ui/data_public/sponsor_heatmap_page.py` | 245 | 9 (3.7/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 91; high non-ck-class <div> count: 21 |
| 50 | `rcm_mc/ui/data_public/supply_chain_page.py` | 229 | 9 (3.9/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 96; high non-ck-class <div> count: 24 |
| 50 | `rcm_mc/ui/data_public/tax_credits_page.py` | 202 | 9 (4.5/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 98; high non-ck-class <div> count: 22 |
| 50 | `rcm_mc/ui/data_public/tax_structure_analyzer_page.py` | 175 | 9 (5.1/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 86; high non-ck-class <div> count: 26 |
| 50 | `rcm_mc/ui/data_public/telehealth_econ_page.py` | 170 | 9 (5.3/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 85; high non-ck-class <div> count: 22 |
| 50 | `rcm_mc/ui/data_public/tracker_340b_page.py` | 196 | 9 (4.6/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 94; high non-ck-class <div> count: 22 |
| 50 | `rcm_mc/ui/data_public/transition_services_page.py` | 284 | 9 (3.2/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 78; high non-ck-class <div> count: 21 |
| 50 | `rcm_mc/ui/data_public/treasury_tracker_page.py` | 201 | 9 (4.5/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 96; high non-ck-class <div> count: 22 |
| 50 | `rcm_mc/ui/data_public/value_creation_plan_page.py` | 294 | 9 (3.1/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 79; high non-ck-class <div> count: 21 |
| 50 | `rcm_mc/ui/data_public/vcp_tracker_page.py` | 212 | 9 (4.2/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 98; high non-ck-class <div> count: 22 |
| 50 | `rcm_mc/ui/data_public/vdr_tracker_page.py` | 224 | 9 (4.0/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 93; high non-ck-class <div> count: 22 |
| 50 | `rcm_mc/ui/data_public/vintage_cohorts_page.py` | 213 | 9 (4.2/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 99; high non-ck-class <div> count: 22 |
| 50 | `rcm_mc/ui/data_public/workforce_planning_page.py` | 298 | 9 (3.0/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 85; high non-ck-class <div> count: 21 |
| 50 | `rcm_mc/ui/data_public/workforce_retention_page.py` | 194 | 9 (4.6/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 92; high non-ck-class <div> count: 22 |
| 50 | `rcm_mc/ui/data_public/zbb_tracker_page.py` | 167 | 9 (5.4/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 81; high non-ck-class <div> count: 23 |
| 49 | `rcm_mc/ui/chartis/archetype_page.py` | 380 | 8 (2.1/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 20; high non-ck-class <div> count: 14 |
| 49 | `rcm_mc/ui/chartis/investability_page.py` | 349 | 8 (2.3/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 27 |
| 49 | `rcm_mc/ui/data_public/cap_structure_page.py` | 315 | 9 (2.9/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 71; high non-ck-class <div> count: 18 |
| 49 | `rcm_mc/ui/data_public/earnout_page.py` | 309 | 9 (2.9/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 85; high non-ck-class <div> count: 24 |
| 49 | `rcm_mc/ui/data_public/exit_timing_page.py` | 408 | 10 (2.5/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 32 |
| 49 | `rcm_mc/ui/data_public/key_person_page.py` | 307 | 9 (2.9/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 86; high non-ck-class <div> count: 21 |
| 49 | `rcm_mc/ui/data_public/revenue_leakage_page.py` | 301 | 9 (3.0/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 79; high non-ck-class <div> count: 22 |
| 49 | `rcm_mc/ui/data_public/tech_stack_page.py` | 302 | 9 (3.0/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 84; high non-ck-class <div> count: 21 |
| 49 | `rcm_mc/ui/data_public/unit_economics_page.py` | 306 | 9 (2.9/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 74; high non-ck-class <div> count: 22 |
| 48 | `rcm_mc/ui/chartis/payer_intelligence_page.py` | 344 | 9 (2.6/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 32; high non-ck-class <div> count: 12 |
| 48 | `rcm_mc/ui/chartis/pe_intelligence_hub_page.py` | 364 | 9 (2.5/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 26; high non-ck-class <div> count: 17 |
| 48 | `rcm_mc/ui/data_public/comparables_page.py` | 305 | 7 (2.3/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 37 |
| 48 | `rcm_mc/ui/data_public/continuation_vehicle_page.py` | 323 | 9 (2.8/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 90; high non-ck-class <div> count: 24 |
| 48 | `rcm_mc/ui/data_public/dividend_recap_page.py` | 319 | 9 (2.8/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 83; high non-ck-class <div> count: 21 |
| 48 | `rcm_mc/ui/data_public/exit_multiple_page.py` | 291 | 7 (2.4/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 52 |
| 48 | `rcm_mc/ui/data_public/exit_readiness_page.py` | 315 | 9 (2.9/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 77; high non-ck-class <div> count: 21 |
| 48 | `rcm_mc/ui/data_public/scenario_mc_page.py` | 320 | 9 (2.8/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 76; high non-ck-class <div> count: 22 |
| 47 | `rcm_mc/ui/chartis/ic_packet_page.py` | 525 | 14 (2.7/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 56; high non-ck-class <div> count: 22 |
| 47 | `rcm_mc/ui/data_public/deal_quality_page.py` | 313 | 7 (2.2/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 62 |
| 47 | `rcm_mc/ui/data_public/provider_network_page.py` | 278 | 7 (2.5/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 55; high non-ck-class <div> count: 15 |
| 46 | `rcm_mc/ui/data_public/backtest_page.py` | 540 | 12 (2.2/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 49; high non-ck-class <div> count: 11 |
| 46 | `rcm_mc/ui/data_public/bolton_analyzer_page.py` | 363 | 9 (2.5/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 75; high non-ck-class <div> count: 18 |
| 46 | `rcm_mc/ui/data_public/debt_service_page.py` | 353 | 9 (2.5/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 97; high non-ck-class <div> count: 24 |
| 46 | `rcm_mc/ui/data_public/growth_runway_page.py` | 349 | 9 (2.6/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 82; high non-ck-class <div> count: 24 |
| 46 | `rcm_mc/ui/data_public/mgmt_fee_tracker_page.py` | 266 | 7 (2.6/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 63; high non-ck-class <div> count: 28 |
| 46 | `rcm_mc/ui/data_public/payer_shift_page.py` | 343 | 9 (2.6/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 76; high non-ck-class <div> count: 23 |
| 46 | `rcm_mc/ui/data_public/tax_structure_page.py` | 351 | 9 (2.6/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 95; high non-ck-class <div> count: 26 |
| 46 | `rcm_mc/ui/data_public/value_creation_page.py` | 305 | 7 (2.3/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 51; high non-ck-class <div> count: 14 |
| 45 | `rcm_mc/ui/data_public/underwriting_page.py` | 318 | 8 (2.5/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 63; high non-ck-class <div> count: 31 |
| 44 | `rcm_mc/ui/exports_index_page.py` | 130 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing) |
| 44 | `rcm_mc/ui/portfolio_map.py` | 111 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing) |
| 43 | `rcm_mc/ui/data_public/underwriting_model_page.py` | 347 | 7 (2.0/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 64; high non-ck-class <div> count: 14 |
| 42 | `rcm_mc/ui/data_public/covenant_monitor_page.py` | 350 | 7 (2.0/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 64; high non-ck-class <div> count: 18 |
| 42 | `rcm_mc/ui/data_public/deal_search_page.py` | 326 | 6 (1.8/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 52; high non-ck-class <div> count: 12 |
| 42 | `rcm_mc/ui/deal_timeline.py` | 213 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing) |
| 42 | `rcm_mc/ui/portfolio_heatmap.py` | 139 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 7 |
| 41 | `rcm_mc/ui/analysis_landing.py` | 151 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); high inline-style count: 31; high non-ck-class <div> count: 16 |
| 41 | `rcm_mc/ui/chartis/partner_review_page.py` | 652 | 13 (2.0/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 68; high non-ck-class <div> count: 25 |
| 41 | `rcm_mc/ui/data_public/qoe_analyzer_page.py` | 357 | 7 (2.0/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 63; high non-ck-class <div> count: 31 |
| 41 | `rcm_mc/ui/global_search.py` | 486 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing) |
| 40 | `rcm_mc/ui/deal_profile_page.py` | 1456 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); high inline-style count: 109; high non-ck-class <div> count: 76 |
| 40 | `rcm_mc/ui/diligence_benchmarks.py` | 725 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); high inline-style count: 104; high non-ck-class <div> count: 47 |
| 40 | `rcm_mc/ui/ebitda_bridge_page.py` | 901 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); high inline-style count: 108; high non-ck-class <div> count: 95 |
| 40 | `rcm_mc/ui/feature_importance_viz.py` | 268 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 9 |
| 40 | `rcm_mc/ui/portfolio_overview.py` | 414 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); high inline-style count: 63; high non-ck-class <div> count: 62 |
| 40 | `rcm_mc/ui/regulatory_calendar_page.py` | 973 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); high inline-style count: 46; high non-ck-class <div> count: 99 |
| 40 | `rcm_mc/ui/risk_workbench_page.py` | 1202 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); high inline-style count: 54; high non-ck-class <div> count: 30 |
| 40 | `rcm_mc/ui/source_page.py` | 70 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 9 |
| 40 | `rcm_mc/ui/v5_status_page.py` | 117 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 11 |
| 39 | `rcm_mc/ui/dashboard_v2.py` | 192 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high non-ck-class <div> count: 22 |
| 39 | `rcm_mc/ui/data_public/concentration_risk_page.py` | 130 | 2 (1.5/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 28; high non-ck-class <div> count: 16 |
| 39 | `rcm_mc/ui/pressure_page.py` | 83 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 7; high non-ck-class <div> count: 13 |
| 38 | `rcm_mc/ui/data_public/payer_rate_trends_page.py` | 230 | 2 (0.9/100) | low ck_* primitive density (0.9/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 23; high non-ck-class <div> count: 14 |
| 38 | `rcm_mc/ui/hold_dashboard.py` | 230 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 9; high non-ck-class <div> count: 15 |
| 38 | `rcm_mc/ui/scenarios_page.py` | 62 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 13 |
| 38 | `rcm_mc/ui/surrogate_page.py` | 56 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 13 |
| 37 | `rcm_mc/ui/data_public/return_attribution_page.py` | 179 | 2 (1.1/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 34; high non-ck-class <div> count: 11 |
| 37 | `rcm_mc/ui/data_public/sector_momentum_page.py` | 168 | 2 (1.2/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 30 |
| 37 | `rcm_mc/ui/v3_status_page.py` | 201 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 14 |
| 36 | `rcm_mc/ui/insights_page.py` | 134 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 16 |
| 36 | `rcm_mc/ui/metric_glossary_page.py` | 104 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 17 |
| 36 | `rcm_mc/ui/portfolio_risk_scan_page.py` | 424 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 17 |
| 36 | `rcm_mc/ui/verticals_page.py` | 166 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 15 |
| 35 | `rcm_mc/ui/calibration_page.py` | 161 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 20 |
| 35 | `rcm_mc/ui/data_public/entry_multiple_page.py` | 197 | 2 (1.0/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 30; high non-ck-class <div> count: 15 |
| 35 | `rcm_mc/ui/data_public/irr_dispersion_page.py` | 194 | 2 (1.0/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 30; high non-ck-class <div> count: 15 |
| 34 | `rcm_mc/ui/chartis/forgot_page.py` | 121 | 0 (0.0/100) | missing chartis_shell — bypassing editorial chrome; low ck_* primitive density (0.0/100LOC) |
| 34 | `rcm_mc/ui/data_explorer.py` | 230 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 18 |
| 34 | `rcm_mc/ui/data_public/gp_benchmarking_page.py` | 190 | 2 (1.1/100) | no italic-serif highlight (chartis cadence missing); high inline-style count: 42; high non-ck-class <div> count: 16 |
| 34 | `rcm_mc/ui/library_page.py` | 299 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 19 |
| 33 | `rcm_mc/ui/data_public/corpus_coverage_page.py` | 210 | 2 (1.0/100) | low ck_* primitive density (1.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 43; high non-ck-class <div> count: 16 |
| 33 | `rcm_mc/ui/data_public/deal_flow_heatmap_page.py` | 259 | 2 (0.8/100) | low ck_* primitive density (0.8/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 32; high non-ck-class <div> count: 13 |
| 33 | `rcm_mc/ui/data_public/hold_analysis_page.py` | 233 | 2 (0.9/100) | low ck_* primitive density (0.9/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 47; high non-ck-class <div> count: 16 |
| 33 | `rcm_mc/ui/data_refresh_page.py` | 208 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 24 |
| 32 | `rcm_mc/ui/data_public/find_comps_page.py` | 314 | 2 (0.6/100) | low ck_* primitive density (0.6/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 60; high non-ck-class <div> count: 13 |
| 32 | `rcm_mc/ui/data_public/ic_memo_page.py` | 350 | 3 (0.9/100) | low ck_* primitive density (0.9/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 68; high non-ck-class <div> count: 24 |
| 32 | `rcm_mc/ui/settings_pages.py` | 199 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 22 |
| 32 | `rcm_mc/ui/team_page.py` | 110 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 18; high non-ck-class <div> count: 18 |
| 31 | `rcm_mc/ui/data_public/rcm_red_flags_page.py` | 312 | 2 (0.6/100) | low ck_* primitive density (0.6/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 58; high non-ck-class <div> count: 19 |
| 31 | `rcm_mc/ui/waterfall_page.py` | 107 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 16; high non-ck-class <div> count: 25 |
| 30 | `rcm_mc/ui/cli_runs_page.py` | 172 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 31 |
| 30 | `rcm_mc/ui/denial_page.py` | 119 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 20; high non-ck-class <div> count: 23 |
| 30 | `rcm_mc/ui/hospital_stats_page.py` | 227 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 21; high non-ck-class <div> count: 21 |
| 29 | `rcm_mc/ui/conference_page.py` | 390 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 25; high non-ck-class <div> count: 19 |
| 29 | `rcm_mc/ui/deal_dashboard.py` | 361 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 24; high non-ck-class <div> count: 19 |
| 29 | `rcm_mc/ui/pe_returns_page.py` | 105 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 13; high non-ck-class <div> count: 43 |
| 29 | `rcm_mc/ui/sensitivity_dashboard.py` | 330 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 31 |
| 29 | `rcm_mc/ui/sponsor_detail_page.py` | 401 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 28 |
| 28 | `rcm_mc/ui/comparable_outcomes_page.py` | 363 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 33 |
| 28 | `rcm_mc/ui/data_catalog_page.py` | 206 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 30; high non-ck-class <div> count: 11 |
| 28 | `rcm_mc/ui/demand_page.py` | 172 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 23; high non-ck-class <div> count: 25 |
| 28 | `rcm_mc/ui/ic_packet_page.py` | 618 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 43; high non-ck-class <div> count: 11 |
| 28 | `rcm_mc/ui/model_quality_dashboard.py` | 221 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 36; high non-ck-class <div> count: 11 |
| 27 | `rcm_mc/ui/deal_profile_v2.py` | 566 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 46; high non-ck-class <div> count: 14 |
| 27 | `rcm_mc/ui/diligence_page.py` | 142 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 26; high non-ck-class <div> count: 23 |
| 27 | `rcm_mc/ui/fund_learning_page.py` | 136 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 26; high non-ck-class <div> count: 23 |
| 26 | `rcm_mc/ui/bayesian_page.py` | 148 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 26; high non-ck-class <div> count: 24 |
| 26 | `rcm_mc/ui/chartis/login_page.py` | 369 | 0 (0.0/100) | missing chartis_shell — bypassing editorial chrome; low ck_* primitive density (0.0/100LOC); high non-ck-class <div> count: 35 |
| 26 | `rcm_mc/ui/compare_page.py` | 342 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 39; high non-ck-class <div> count: 17 |
| 26 | `rcm_mc/ui/deal_comparison.py` | 280 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 33; high non-ck-class <div> count: 16 |
| 26 | `rcm_mc/ui/market_analysis_page.py` | 156 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 24; high non-ck-class <div> count: 31 |
| 26 | `rcm_mc/ui/news_page.py` | 427 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 36; high non-ck-class <div> count: 18 |
| 26 | `rcm_mc/ui/quick_import.py` | 173 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 31; high non-ck-class <div> count: 17 |
| 25 | `rcm_mc/ui/advanced_tools_page.py` | 244 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 33; high non-ck-class <div> count: 48 |
| 25 | `rcm_mc/ui/analysis_workbench.py` | 2719 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 57; high non-ck-class <div> count: 209 |
| 25 | `rcm_mc/ui/analytics_pages.py` | 235 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 27; high non-ck-class <div> count: 46 |
| 25 | `rcm_mc/ui/bear_case_page.py` | 637 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 35; high non-ck-class <div> count: 85 |
| 25 | `rcm_mc/ui/bridge_audit_page.py` | 821 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 46; high non-ck-class <div> count: 78 |
| 25 | `rcm_mc/ui/command_center.py` | 355 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 70; high non-ck-class <div> count: 50 |
| 25 | `rcm_mc/ui/competitive_intel_page.py` | 343 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 30; high non-ck-class <div> count: 25 |
| 25 | `rcm_mc/ui/counterfactual_page.py` | 753 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 23; high non-ck-class <div> count: 58 |
| 25 | `rcm_mc/ui/covenant_lab_page.py` | 972 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 54; high non-ck-class <div> count: 76 |
| 25 | `rcm_mc/ui/dashboard_page.py` | 2207 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 146; high non-ck-class <div> count: 42 |
| 25 | `rcm_mc/ui/dashboard_v3.py` | 530 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 47; high non-ck-class <div> count: 21 |
| 25 | `rcm_mc/ui/data_dashboard.py` | 219 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 29; high non-ck-class <div> count: 31 |
| 25 | `rcm_mc/ui/data_room_page.py` | 304 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 49; high non-ck-class <div> count: 37 |
| 25 | `rcm_mc/ui/deal_autopsy_page.py` | 745 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 49; high non-ck-class <div> count: 53 |
| 25 | `rcm_mc/ui/deal_mc_page.py` | 562 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 57; high non-ck-class <div> count: 38 |
| 25 | `rcm_mc/ui/deal_quick_view.py` | 138 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 38; high non-ck-class <div> count: 20 |
| 25 | `rcm_mc/ui/denial_prediction_page.py` | 441 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 60; high non-ck-class <div> count: 46 |
| 25 | `rcm_mc/ui/diligence_checklist_page.py` | 496 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 22; high non-ck-class <div> count: 45 |
| 25 | `rcm_mc/ui/engagement_pages.py` | 441 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 89; high non-ck-class <div> count: 20 |
| 25 | `rcm_mc/ui/exit_timing_page.py` | 725 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 72; high non-ck-class <div> count: 54 |
| 25 | `rcm_mc/ui/hcris_xray_page.py` | 970 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 74; high non-ck-class <div> count: 85 |
| 25 | `rcm_mc/ui/home_v2.py` | 423 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 64; high non-ck-class <div> count: 67 |
| 25 | `rcm_mc/ui/hospital_history.py` | 305 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 34; high non-ck-class <div> count: 30 |
| 25 | `rcm_mc/ui/hospital_profile.py` | 378 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 61; high non-ck-class <div> count: 69 |
| 25 | `rcm_mc/ui/ic_memo_page.py` | 471 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 58; high non-ck-class <div> count: 40 |
| 25 | `rcm_mc/ui/management_scorecard_page.py` | 518 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 47; high non-ck-class <div> count: 63 |
| 25 | `rcm_mc/ui/market_data_page.py` | 416 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 43; high non-ck-class <div> count: 64 |
| 25 | `rcm_mc/ui/market_intel_page.py` | 597 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 45; high non-ck-class <div> count: 34 |
| 25 | `rcm_mc/ui/memo_page.py` | 169 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 20; high non-ck-class <div> count: 44 |
| 25 | `rcm_mc/ui/methodology_page.py` | 320 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 65; high non-ck-class <div> count: 30 |
| 25 | `rcm_mc/ui/ml_insights_page.py` | 510 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 107; high non-ck-class <div> count: 76 |
| 25 | `rcm_mc/ui/model_validation_page.py` | 211 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 27; high non-ck-class <div> count: 35 |
| 25 | `rcm_mc/ui/models_page.py` | 527 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 69; high non-ck-class <div> count: 67 |
| 25 | `rcm_mc/ui/onboarding_wizard.py` | 592 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 28; high non-ck-class <div> count: 54 |
| 25 | `rcm_mc/ui/payer_stress_page.py` | 866 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 67; high non-ck-class <div> count: 85 |
| 25 | `rcm_mc/ui/pe_tools_page.py` | 243 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 35; high non-ck-class <div> count: 42 |
| 25 | `rcm_mc/ui/physician_attrition_page.py` | 988 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 90; high non-ck-class <div> count: 90 |
| 25 | `rcm_mc/ui/physician_eu_page.py` | 484 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 35; high non-ck-class <div> count: 48 |
| 25 | `rcm_mc/ui/pipeline_page.py` | 240 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 39; high non-ck-class <div> count: 29 |
| 25 | `rcm_mc/ui/portfolio_bridge_page.py` | 287 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 29; high non-ck-class <div> count: 30 |
| 25 | `rcm_mc/ui/portfolio_monitor_page.py` | 347 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 45; high non-ck-class <div> count: 34 |
| 25 | `rcm_mc/ui/predictive_screener.py` | 347 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 33; high non-ck-class <div> count: 33 |
| 25 | `rcm_mc/ui/quant_lab_page.py` | 257 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 37; high non-ck-class <div> count: 26 |
| 25 | `rcm_mc/ui/regression_page.py` | 560 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 52; high non-ck-class <div> count: 37 |
| 25 | `rcm_mc/ui/scenario_modeler_page.py` | 379 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 36; high non-ck-class <div> count: 30 |
| 25 | `rcm_mc/ui/seeking_alpha_page.py` | 605 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 27; high non-ck-class <div> count: 56 |
| 25 | `rcm_mc/ui/thesis_pipeline_page.py` | 597 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 31; high non-ck-class <div> count: 56 |
| 25 | `rcm_mc/ui/value_tracking_page.py` | 230 | 0 (0.0/100) | low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 32; high non-ck-class <div> count: 26 |
| 20 | `rcm_mc/ui/_workbook_style.py` | 424 | 0 (0.0/100) | missing chartis_shell — bypassing editorial chrome; low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing) |
| 20 | `rcm_mc/ui/chartis/app_page.py` | 220 | 0 (0.0/100) | missing chartis_shell — bypassing editorial chrome; low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing) |
| 20 | `rcm_mc/ui/compare.py` | 360 | 0 (0.0/100) | missing chartis_shell — bypassing editorial chrome; low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing) |
| 20 | `rcm_mc/ui/csv_to_html.py` | 209 | 0 (0.0/100) | missing chartis_shell — bypassing editorial chrome; low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing) |
| 20 | `rcm_mc/ui/validators.py` | 224 | 0 (0.0/100) | missing chartis_shell — bypassing editorial chrome; low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing) |
| 19 | `rcm_mc/ui/chartis/_app_focused_deal_bar.py` | 150 | 0 (0.0/100) | missing chartis_shell — bypassing editorial chrome; low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing) |
| 19 | `rcm_mc/ui/chartis/_app_metric_catalog.py` | 195 | 0 (0.0/100) | missing chartis_shell — bypassing editorial chrome; low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing) |
| 19 | `rcm_mc/ui/chartis/_app_what_block.py` | 41 | 0 (0.0/100) | missing chartis_shell — bypassing editorial chrome; low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing) |
| 18 | `rcm_mc/ui/chartis/_app_deals_table.py` | 142 | 0 (0.0/100) | missing chartis_shell — bypassing editorial chrome; low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing) |
| 18 | `rcm_mc/ui/chartis/_app_deliverables.py` | 228 | 0 (0.0/100) | missing chartis_shell — bypassing editorial chrome; low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing) |
| 18 | `rcm_mc/ui/chartis/_sanity.py` | 541 | 0 (0.0/100) | missing chartis_shell — bypassing editorial chrome; low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing) |
| 17 | `rcm_mc/ui/chartis/_app_alerts.py` | 134 | 0 (0.0/100) | missing chartis_shell — bypassing editorial chrome; low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing) |
| 17 | `rcm_mc/ui/chartis/_app_kpi_strip.py` | 223 | 0 (0.0/100) | missing chartis_shell — bypassing editorial chrome; low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing) |
| 16 | `rcm_mc/ui/chartis/_app_ebitda_drag.py` | 251 | 0 (0.0/100) | missing chartis_shell — bypassing editorial chrome; low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing) |
| 16 | `rcm_mc/ui/chartis/_app_pipeline_funnel.py` | 144 | 0 (0.0/100) | missing chartis_shell — bypassing editorial chrome; low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing) |
| 16 | `rcm_mc/ui/data_public/corpus_flags_panel.py` | 200 | 0 (0.0/100) | missing chartis_shell — bypassing editorial chrome; low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high non-ck-class <div> count: 13 |
| 16 | `rcm_mc/ui/provenance.py` | 397 | 0 (0.0/100) | missing chartis_shell — bypassing editorial chrome; low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 7 |
| 15 | `rcm_mc/ui/_web_components.py` | 711 | 0 (0.0/100) | missing chartis_shell — bypassing editorial chrome; low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 6; high non-ck-class <div> count: 11 |
| 14 | `rcm_mc/ui/chartis/_app_covenant_heatmap.py` | 370 | 0 (0.0/100) | missing chartis_shell — bypassing editorial chrome; low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 6; high non-ck-class <div> count: 15 |
| 12 | `rcm_mc/ui/power_chart.py` | 589 | 0 (0.0/100) | missing chartis_shell — bypassing editorial chrome; low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 14 |
| 11 | `rcm_mc/ui/chartis/_app_initiative_tracker.py` | 319 | 0 (0.0/100) | missing chartis_shell — bypassing editorial chrome; low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 8; high non-ck-class <div> count: 22 |
| 11 | `rcm_mc/ui/loading.py` | 279 | 0 (0.0/100) | missing chartis_shell — bypassing editorial chrome; low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 14 |
| 10 | `rcm_mc/ui/power_table.py` | 527 | 0 (0.0/100) | missing chartis_shell — bypassing editorial chrome; low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 19 |
| 6 | `rcm_mc/ui/json_to_html.py` | 323 | 0 (0.0/100) | missing chartis_shell — bypassing editorial chrome; low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 8; high non-ck-class <div> count: 50 |
| 5 | `rcm_mc/ui/chartis/_helpers.py` | 385 | 0 (0.0/100) | missing chartis_shell — bypassing editorial chrome; low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 26 |
| 0 | `rcm_mc/ui/chartis/marketing_page.py` | 423 | 0 (0.0/100) | missing chartis_shell — bypassing editorial chrome; low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 61; high non-ck-class <div> count: 36 |
| 0 | `rcm_mc/ui/thesis_card.py` | 283 | 0 (0.0/100) | missing chartis_shell — bypassing editorial chrome; low ck_* primitive density (0.0/100LOC); no italic-serif highlight (chartis cadence missing); high inline-style count: 47; high non-ck-class <div> count: 35 |
