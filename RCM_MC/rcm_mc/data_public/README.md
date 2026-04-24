# data_public/

**The corpus-intelligence engine layer.** 318 files — the largest single directory in the repo. Every module here is an analytical engine consumed by the `ui/data_public/` corpus-browser surface (~1:1 mapping: `<topic>.py` ↔ `ui/data_public/<topic>_page.py`).

## What's here

| Category | Files | What it is |
|----------|-------|-----------|
| **Corpus seed data** | 104 | `extended_seed_N.py` — curated deal batches (~20 real transactions each from SEC EDGAR + Modern Healthcare + Becker's + PE press releases). `deals_corpus.py` = 35 core seeds. **Not code, pure data.** |
| **Corpus infrastructure** | 8 | `corpus_loader.py` (canonical entry — `load_corpus_deals(mode=...)`), `corpus_provenance`, `corpus_health_check`, `corpus_export`, `corpus_cli`, `corpus_red_flags`, `corpus_report`, `corpus_vintage_risk_model` |
| **Scrapers** | 5 (in `scrapers/`) | Feed the corpus — `cms_data.py`, `news_deals.py`, `pe_portfolios.py` (KKR/Apollo/Carlyle/Bain), `sec_filings.py` (EDGAR EFTS) |
| **CMS ported suite** | ~15 | Modules ported from sibling `cms_medicare-master/cms_api_advisory_analytics.py` — `cms_advisory_memo`, `cms_api_client`, `cms_benchmark_calibration`, `cms_market_analysis`, `cms_opportunity_scoring`, `cms_provider_ranking`, `cms_stress_test`, `market_concentration`, `provider_regime`, `provider_trend_reliability`, etc. |
| **Capital / fund economics** | 10+ | `cap_structure`, `capital_call_tracker`, `capital_efficiency`, `capital_pacing`, `capital_schedule`, `dpi_tracker`, `fund_attribution`, `lp_dashboard`, `lp_reporting`, `mgmt_fee_tracker`, `nav_loan_tracker` |
| **Deal scoring / risk** | 7 | `deal_entry_risk_score`, `deal_quality_score`, `deal_quality_scorer`, `deal_risk_matrix`, `deal_risk_scorer`, `deal_scorer`, `deal_teardown_analyzer`. **Heavy overlap — consolidation candidate.** |
| **Payer family** | 7 | `payer_concentration`, `payer_contracts`, `payer_intelligence`, `payer_mix_shift_model`, `payer_sensitivity`, `payer_shift`, `payer_stress`. **Heavy overlap — consolidation candidate.** |
| **Exit / hold family** | 5 | `exit_modeling` (4 routes), `exit_multiple`, `exit_readiness`, `hold_optimizer`, `hold_period_optimizer` (near-duplicate of hold_optimizer) |
| **Sector / sponsor analytics** | 6 | `sector_correlation`, `sector_intelligence`, `sponsor_analytics`, `sponsor_heatmap`, `sponsor_track_record`, `size_analytics` |
| **Regulatory / reimbursement** | 5 | `regulatory_risk`, `reimbursement_risk_model`, `risk_adjustment`, `ma_contracts`, `ma_star_tracker`, `medicaid_unwinding`, `nsa_tracker`, `tracker_340b`, `drug_pricing_340b` |
| **Physician / workforce** | 6 | `phys_comp_plan`, `physician_labor`, `physician_productivity`, `workforce_planning`, `workforce_retention`, `working_capital` |
| **Value creation family** | 4 | `value_creation`, `value_creation_plan`, `vcp_tracker` (dup of VCP), `value_backtester` |
| **Vintage analytics** | 3 | `vintage_analysis`, `vintage_analytics`, `vintage_cohorts`. **Three near-duplicates — consolidation candidate.** |
| **Rest** | ~100 | ACO / antitrust / biosimilars / board governance / clinical outcomes / compliance / ESG / PMI / quality / QoE / tax / etc. |

## The canonical entry point

**Every corpus-reading module goes through `corpus_loader.load_corpus_deals(mode=...)`.** Modes select provenance filter (seed-only / extended / all / specific vintage). Returns a list of deal dicts. This is the single point of contract between the seed data and every downstream analytic.

## The relationship to `ui/data_public/`

**Strict naming convention** — `data_public/<topic>.py` (engine) ↔ `ui/data_public/<topic>_page.py` (render wrapper). The UI files are thin; the math lives here.

## Known duplicates (consolidation candidates)

1. `deal_quality_score.py` + `deal_quality_scorer.py`
2. `hold_optimizer.py` + `hold_period_optimizer.py`
3. `vintage_analysis.py` + `vintage_analytics.py` + `vintage_cohorts.py` (3!)
4. `value_creation_plan.py` + `vcp_tracker.py`
5. `tax_structure.py` + `tax_structure_analyzer.py`
6. 7 overlapping payer modules
7. 7 overlapping deal-scoring modules
8. **Name collision**: `data_public/pe_intelligence.py` vs `pe_intelligence/` top-level package (distinct purposes, same name)

## Refreshing the corpus

- Add new batch: new `extended_seed_N.py` with ~20 deals. Follow the shape in `extended_seed_2.py`. Register in `corpus_loader` if not auto-discovered.
- Refresh cadence: every 3-6 months as new public deals close.
- Sources for new deals: SEC EDGAR 8-K / SC TO-T / DEFM14A, Modern Healthcare, Becker's Hospital Review, Healthcare Finance News, PE firm press releases.

## Ports from `cms_medicare-master/`

Many `cms_*` and `provider_*` modules are ports from the sibling project. See docstring attribution (`DrewThomas09/cms_medicare`). The plotting + Basemap layers (`plot_methods.py`, `state_maps.py`, `zip_calc.py`) were **intentionally not ported** — UI uses inline SVG, not matplotlib/Basemap.

## Tests

No dedicated `test_data_public_*` prefix — each engine is covered by its matching `tests/test_<topic>.py` file.
