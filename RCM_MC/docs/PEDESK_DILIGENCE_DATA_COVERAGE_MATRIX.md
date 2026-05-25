# PEdesk diligence data coverage matrix

Which real datasets power which diligence pages/verticals. Maintained as the
data-expansion loop wires more sources in. Status legend: **LIVE** (real
source-backed), **CONTEXTUAL** (real market/state framing, not provider-
specific), **DERIVED** (computed from real fields), **DATA-REQUIRED** (needs
user/company data), **ILLUSTRATIVE** (calculator/prototype, not evidence).

| Dataset | Source | Geography | Years | Normalized files | Loader | Registry key | Pages connected (status) | Metrics | Missingness | Caveats | Next to wire |
|---|---|---|---|---|---|---|---|---|---|---|---|
| HCRIS hospital cost reports | CMS | US | multi | `data/hcris.csv.gz` | `data/hcris.py`, `diligence/hcris_xray` | — | HCRIS X-Ray (LIVE); Payer Stress / Cost Structure / Debt Service (LIVE on CCN attach) | beds, opex, margin, NPR, payer-day mix | varies | hospital-only | CMS X-Ray cross-links |
| CO Cost of Care | CIVHC / CO APCD | Colorado | 2017–21 | `vendor/payer_data/cost_of_care_*.csv` | `data/payer_data.py` | `civhc_coc_fy23_*` | Cost Structure (CONTEXTUAL); Colorado market intel | spend, member-months, PPPY by payer×region×claim | none | all-payer aggregate, not facility opex; CO-only | Payer Rate Trends |
| CO APM adoption | CIVHC / CO APCD | Colorado | 2022–24 | `vendor/payer_data/apm_public.csv` | `data/payer_data.py` | `civhc_apm_fy26` | CMS APM Tracker (LIVE); Payer Stress (CONTEXTUAL) | %APM, %FFS, LAN categories by payer×year | ~17% on some %/LAN; Unknown payer NaN | market-level not provider; CO-only | vertical APM context |
| CO Medicare RBP | CIVHC / CO APCD | Colorado | 2021–24 | `vendor/payer_data/reference_based_pricing.csv` | `data/payer_data.py` | `civhc_rbp_fy26` | Ref Pricing (LIVE); Payer Stress (CONTEXTUAL) | provider % of Medicare, claims, payer min/med/max | ~1% | provider-level (resolvable to CCN); CO-only | entity-resolve to CCN |
| Deal Library (CapIQ) | Capital IQ (licensed) | US/Canada | latest | `data/vendor/deal_library/*` (git-ignored) | `data/deal_library.py` | — | Deal Library / sponsors / comps (LIVE); Find Comps (candidate) | company, sponsor, EV/EBITDA/rev (sparse), est. vertical | financials ~97% blank | licensed (not committed); company not transaction set | Transactions screen |
| FDA drug shortages | openFDA (FDA) | US (national) | 2017–26 | `vendor/drug_data/fda_drug_shortages.csv` | `data/drug_shortage_data.py` | `openfda_drug_shortages` | Drug Shortage (LIVE section) | shortage status, therapeutic category, company, availability | availability ~31% | public domain (CC0); product-level, not provider-specific; build-time snapshot | provider/formulary join |
| CMS MIPS clinician perf | CMS Provider Data Catalog | US (national) | 2023 | `vendor/mips/*.csv` (PII-free aggregates) | `data/mips_data.py` | `cms_mips_py2023` | Physician Productivity / Quality Scorecard / Clinical Outcomes (physician-sector benchmark) | MIPS final-score distribution by source, 5-band histogram, category sub-scores | scores missing excluded | public; **PII dropped at ingest**, aggregates only; distribution not a payment figure | TIN/NPI roster join |
| CMS SNF enforcement | CMS Care Compare (NH) | US (national) | 2026 | `data/snf_quality.csv` | `data/snf.py` (`snf_enforcement_summary`) | (snf spine) | Regulatory Risk (nursing-sector benchmark) | % fined, median/total fine, payment-denial/penalty rates | fields missing excluded | public; sector base rate, not deal exposure | per-deal enforcement history |
| CMS provider enrollment (supply) | data.cms.gov | US (by state) | 2026 | `vendor/provider_supply/*.csv` | `data/provider_supply.py` | `cms_ffs_provider_enrollment` | Market context (supply density), market profile KPI | enrolled counts by state × provider type | PII dropped | public; FFS Medicare-enrolled only; primary-care is keyword approx | per-capita (needs pop denom) |
| CMS SNF/Hospital Change of Ownership | data.cms.gov | US (by state) | 2016–2025 | `vendor/{snf,hospital}_chow/*.csv` | `data/snf_chow.py` | `cms_snf_chow`, `cms_hospital_chow` | Market context (consolidation velocity), market profile KPI | ownership-change counts by state × year | identifiers dropped | public; consolidation signal, NOT a PE flag; not deal values | PE-buyer classification |
| Public company comps | `market_intel.public_comps` | US | — | (vendored) | `market_intel` | — | HCRIS X-Ray public comps (LIVE) | EV/EBITDA, multiples | — | curated public set | — |
| Seed deal corpus | bundled illustrative | — | — | `data_public` `_SEED_DEALS`/`extended_seed` | `data_public.deals_corpus` | — | /library, sponsor-league, sector-intel (**ILLUSTRATIVE**, labeled) | synthetic deals | — | **illustrative seed data, not ingested** | — |

## Verticals

| Vertical | Real data in PEdesk | Pages | Gaps / next dataset |
|---|---|---|---|
| Hospitals | HCRIS + CO RBP/cost | HCRIS X-Ray, Ref Pricing, Cost Structure | per-service price transparency |
| Home Health / Hospice / SNF / Dialysis / IRF / LTCH | CMS Care Compare (existing) | vertical profile pages | payer/cost by vertical |
| Physician / specialty | CMS MIPS quality distribution; HRSA shortage context | Physician Productivity / Quality Scorecard / Clinical Outcomes (NAVY calculators + real benchmark) | NPPES supply, Part B utilization, deal-specific TIN/NPI roster |
| Dental / Behavioral / ASC | — | (illustrative) | public source TBD |

## Next datasets (see discovery backlog)

Other-state APCDs (MA CHIA, WA, NH), CMS price transparency MRFs, CMS
MSSP/ACO participation, HRSA/HPSA shortage, FDA/ASHP drug shortage, CMS Open
Payments, NPPES taxonomy supply, CMS ownership/PECOS — each profiled before
ingest, wired only where it actually supports the analysis.
