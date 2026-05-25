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
| Public company comps | `market_intel.public_comps` | US | — | (vendored) | `market_intel` | — | HCRIS X-Ray public comps (LIVE) | EV/EBITDA, multiples | — | curated public set | — |
| Seed deal corpus | bundled illustrative | — | — | `data_public` `_SEED_DEALS`/`extended_seed` | `data_public.deals_corpus` | — | /library, sponsor-league, sector-intel (**ILLUSTRATIVE**, labeled) | synthetic deals | — | **illustrative seed data, not ingested** | — |

## Verticals

| Vertical | Real data in PEdesk | Pages | Gaps / next dataset |
|---|---|---|---|
| Hospitals | HCRIS + CO RBP/cost | HCRIS X-Ray, Ref Pricing, Cost Structure | per-service price transparency |
| Home Health / Hospice / SNF / Dialysis / IRF / LTCH | CMS Care Compare (existing) | vertical profile pages | payer/cost by vertical |
| Physician / specialty | — | Physician Productivity (DATA-REQUIRED) | NPPES supply, Part B utilization |
| Dental / Behavioral / ASC | — | (illustrative) | public source TBD |

## Next datasets (see discovery backlog)

Other-state APCDs (MA CHIA, WA, NH), CMS price transparency MRFs, CMS
MSSP/ACO participation, HRSA/HPSA shortage, FDA/ASHP drug shortage, CMS Open
Payments, NPPES taxonomy supply, CMS ownership/PECOS — each profiled before
ingest, wired only where it actually supports the analysis.
