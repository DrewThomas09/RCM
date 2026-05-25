# PEdesk public-data discovery backlog

Prioritized, **public/open** datasets that can power diligence analysis, beyond
the Colorado CIVHC files already ingested. Each must be profiled (source,
fields, grain, size, license/public status) *before* ingest, normalized, tested,
registered, and wired only where it actually supports the analysis. No scraping
of protected/license-gated systems; no runtime network calls.

Status: **ingest-now** (clear + high value) · **defer** (valuable, larger/
messier) · **evaluate** (needs a profile pass first).

| # | Dataset | Publisher | Public? | Key fields | Verticals | Diligence pages it could power | Status | Reason |
|---|---|---|---|---|---|---|---|---|
| 1 | NPPES / NPI registry | CMS | yes (bulk public) | NPI, taxonomy, org/indiv, address | physician, dental/DSO, all | Physician supply, entity-resolution (CapIQ↔provider), Target Screener | **ingest-now** | clean, enables provider supply + the CapIQ→CMS join that HCRIS can't (non-hospital) |
| 2 | CMS Care Compare (HH/Hospice/SNF/Dialysis/IRF/LTCH) | CMS | yes | provider id, quality, utilization | post-acute verticals | vertical profile pages, X-Ray context, Deal Quality | **ingest-now** | per-vertical quality/utilization; some already used — extend coverage |
| 3 | CMS MSSP / ACO public-use files | CMS | yes | ACO id, participation, savings | physician/ACO | CMS APM Tracker (real participation), Payer Stress | **defer** | distinguish provider-specific vs market; modest size |
| 4 | FDA / ASHP drug shortage data | FDA / ASHP | yes | product, status, dates | pharma/infusion/supply | Drug Shortage / Supply Chain (LIVE) | **evaluate** | product-level not provider; source freshness; converts an illustrative page |
| 5 | CMS Open Payments | CMS | yes (bulk) | physician, manufacturer, $ | physician/specialty | Partner Economics / relationship context (NOT comp) | **defer** | relationship context only; not productivity/comp — label carefully |
| 6 | Other-state APCDs (MA CHIA, NH, WA, UT) | state agencies | varies | payer cost/quality | all-payer | Cost Structure / Payer Stress (multi-state CONTEXTUAL) | **evaluate** | extends payer benchmarking beyond CO; confirm public status per state |
| 7 | Hospital price transparency MRFs | hospitals (CMS-mandated) | yes (messy) | negotiated/cash rates by payer | hospitals | Ref Pricing expansion, Payer Rate Trends | **evaluate** | high-missingness, non-standard; ingest only with a clear profile; do not fake |
| 8 | HRSA / HPSA shortage areas | HRSA | yes | geography, shortage score | physician/access | workforce/access context, Physician Productivity context | **defer** | market access context; not provider-specific |
| 9 | CMS ownership / PECOS | CMS | yes | owner, org, enrollment | all | owner/operator mapping, sponsor/operator context | **evaluate** | entity-resolution limits; pairs with NPPES |
| 10 | CMS Part B utilization | CMS | yes (bulk) | provider, HCPCS, services, payment | physician/specialty | Physician Productivity (proxy, not wRVU) | **defer** | services/payments ≠ wRVU; label proxy, never fake RVUs |

## Recommended next ingests (in order)

1. **NPPES/NPI** — unlocks the provider entity-resolution that HCRIS can't
   (most CapIQ/Deal-Library companies are non-hospital), plus provider-supply
   context by market. Highest leverage.
2. **Care Compare per-vertical extension** — deepens HH/Hospice/SNF/Dialysis
   vertical pages with real quality/utilization.
3. **FDA/ASHP drug shortage** — converts the Drug Shortage page from
   illustrative to LIVE (product-level, with a provider-join caveat).

## Rules (every candidate)

Profile → verify public/license status → document fields + grain → estimate
size → propose normalized schema → register → ingest → test → wire to one page
→ Guide source card. Distinguish provider-specific from market-level. Preserve
missingness; never fabricate; no runtime network calls.
