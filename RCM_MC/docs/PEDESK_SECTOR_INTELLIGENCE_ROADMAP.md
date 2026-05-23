# PEdesk Sector Intelligence — data roadmap

PEdesk started hospital-centric. PE deal flow, though, is heavier in
outpatient, home health, hospice, dental/DSO, ASC, physician groups, and
post-acute. This roadmap plans the expansion **honestly**: it states, per
sector, what free public data actually answers a PE diligence question —
and where CMS only gives a Medicare proxy or provider-supply signal, not
commercial economics.

Guiding principle: don't ask *"what CMS data do we have?"* — ask *"what PE
diligence question can this free public data answer, and what must the deal
team still verify?"*

This is a **planning doc** (Phase 1). No new data is downloaded here. The
build order and per-sector first-pages are below.

## What PEdesk already has in-repo (audit, 2026-05-23)

Reusable infrastructure from the hospital work: provider loaders, the
state tile-grid + hospital-point map renderers (`ui/us_map.py`), the
geocoded CCN→lat/lon crosswalk (`data/hospital_coords.csv`), the Guide/RAG
context system, the editorial page kit, and the data-confidence/provenance
discipline.

| Dataset / loader | Module | Sector reach |
|---|---|---|
| HCRIS cost reports | `data/hcris.py`, `data/cms_hcris.py` | Hospitals |
| Hospital General Info | `data/cms_hospital_general.py` | Hospitals |
| Care Compare | `data/cms_care_compare.py` | **Hospital-only** (3 hospital datasets) |
| **Provider of Services (POS)** | `data/cms_pos.py` | **Cross-sector certification spine** — categorizes all Medicare-certified provider types by `PRVDR_CTGRY_CD` (HHA, hospice, SNF, ASC, dialysis, …). The natural backbone for new verticals. |
| Medicare Part B (physician/practitioner) | `data/cms_part_b.py` | Outpatient / physician |
| Medicare Part D (prescriber) | `data/cms_part_d.py` | Rx / specialty pharmacy proxy |
| OPPS outpatient | `data/cms_opps_outpatient.py` | Outpatient (HOPD) payment |
| Utilization / quality metrics | `data/cms_utilization.py`, `data/cms_quality_metrics.py` | Multi |
| MA enrollment, Open Payments, HRRP, DRG weights | various `data/cms_*.py` | Hospital/market |
| Geocoded hospital coords | `data/hospital_coords.csv` | Hospitals (geocode method reusable for any CCN/address set) |

**Not yet in-repo (need one-time sourcing later):** NPPES/NPI registry,
Home Health Compare, Hospice Compare, ASC quality, Nursing Home Compare,
IRF/LTCH Compare, Dialysis Facility Compare, DMEPOS supplier file.

## The shared spine (build once, reuse per sector)

A normalized provider registry so every vertical reuses one pattern:

```
provider_registry: provider_id, source_system, npi, ccn, pac_id, tin/ein?,
  facility_name, organization_name, sector, subsector, taxonomy, address,
  city, state, zip, county, lat, lon, ownership, certification_type,
  source_date, source_confidence
+ provider_quality_metrics / provider_utilization_metrics /
  provider_payment_metrics / sector_market_summary
```

Per sector, the same surface: **Market map → Provider universe → Quality/
risk → Utilization/payment → Deal use cases → Data limitations.**

Shared IDs: **NPI** (outpatient/dental/physician/suppliers), **CCN**
(Medicare-certified facilities), **PAC ID** (groups), ZIP/county/state
(geography), **HCPCS** (service mix), **taxonomy** (specialty).

## Per-sector plans

Data-level legend: **P** = provider/registry, **C** = claims/utilization,
**Q** = quality, **B** = benchmark/payment.

### 1. Home Health — *first expansion*
- **Datasets:** Home Health Care Compare (CCN, agency, quality-of-care &
  patient-survey star ratings, ACH/ED-use, improvement measures) `Q`; POS
  (certification spine, in-repo) `P`; HHA utilization/payment PUF (episodes,
  beneficiaries, visits, $/episode) `C/B`.
- **IDs:** CCN (+ state/zip/county for the map).
- **Limitations:** Medicare-certified agencies only; commercial/private-pay
  home care under-represented.
- **First page:** **Home Health Screener** (`/home-health`) + market map +
  agency profile. Strong, PE-relevant first non-hospital vertical.
- **In-repo:** POS spine ✓; Compare + PUF need sourcing.

### 2. Hospice — *paired with home health*
- **Datasets:** Hospice Care Compare (CCN, HIS measures, CAHPS hospice
  survey, visits in last days) `Q`; Hospice utilization/payment PUF
  (beneficiaries, days by level of care, $/beneficiary, LOS proxies,
  live-discharge signal) `C/B`; POS `P`.
- **IDs:** CCN.
- **Limitations:** Medicare hospice only; LOS/live-discharge are proxies.
- **First page:** **Hospice Screener** (`/hospice`) — quality/CAHPS, LOS
  proxy, payment intensity, density, provider age, ownership.
- **In-repo:** POS spine ✓; Compare + PUF need sourcing.

### 3. Outpatient / ASC / Physician Groups — *second major vertical*
- **Datasets:** NPPES/NPI (org+individual universe, taxonomy) `P`; Medicare
  Physician & Other Practitioners PUF (NPI×HCPCS volume, charges, allowed,
  paid, place of service) `C/B`; ASC Quality Reporting (`Q`); Doctors &
  Clinicians/Care Compare (group quality) `Q`; PFS/OPPS/ASC payment files
  (site-of-service economics) `B`.
- **IDs:** NPI, PAC ID, CCN (ASC), HCPCS, taxonomy.
- **Limitations:** Medicare slice only — commercial volume/rates unobserved;
  site-of-service mix matters (OPPS vs PFS vs ASC).
- **First page:** **Outpatient Specialty Market Screener** (`/outpatient`)
  — provider density, fragmentation, top groups, procedure mix, Medicare
  exposure proxy, site-of-service view.
- **In-repo:** Part B ✓, OPPS ✓, Part D ✓; NPPES + ASC quality need sourcing.

### 4. Dental / DSO — *provider-supply oriented*
- **Datasets:** NPPES dental taxonomies (general/pedo/ortho/oral surgery/
  perio/endo/prostho) `P`; Medicare Physician PUF (oral surgeons who bill
  Medicare only) `C`; HRSA dental HPSA shortage geography (non-CMS, free)
  `P`; state dental boards / APCDs (coverage varies) `P/C`.
- **IDs:** NPI, taxonomy, ZIP/county.
- **Limitations (state this in the UI):** *"Dental market data is
  provider-supply oriented. Routine commercial dental revenue is not fully
  observable in CMS data."*
- **First page:** **Dental Market Density** (`/dental`) — NPI counts by
  specialty, org-vs-individual mix, new-provider growth, HPSA overlay — NOT
  financial benchmarking.
- **In-repo:** none specific; NPPES + HPSA need sourcing.

### 5. Post-Acute & alternate sites — *sector family*
- **SNF / Nursing Home:** Nursing Home Care Compare (star ratings, staffing,
  inspections, penalties, ownership) `Q`; SNF PUF `C/B`; POS `P`. First page:
  SNF quality/staffing/survey-risk + density.
- **IRF / LTCH:** Care Compare quality (discharge-to-community, readmits,
  functional improvement) `Q`; POS `P`.
- **Dialysis:** Dialysis Facility Compare (strong CMS data — quality, star
  ratings, ownership, geography) `Q/P`.
- **Home Infusion / DME:** NPPES supplier taxonomy `P`; DMEPOS supplier file
  `P`; Part B J-code (drug) utilization `C`; ASP/drug pricing `B`; Part D for
  specialty Rx `C`. Angle = supplier universe + drug/service-mix proxy +
  reimbursement exposure, **not** "perfect infusion revenue."
- **In-repo:** POS spine ✓, Part B/D ✓; the Compare/supplier files need sourcing.

## Build order

1. **Phase 1 (this PR):** this roadmap + audit. No data downloaded.
2. **Phase 2:** Home Health + Hospice (Compare + PUF; screener + map + profile + Guide contexts).
3. **Phase 3:** Outpatient / ASC / Physician groups (NPPES subset + Part B PUF + ASC quality).
4. **Phase 4:** Dental / DSO (NPPES dental + HPSA; density page, supply-oriented).
5. **Phase 5:** Infusion / DME (NPPES supplier + DMEPOS + Part B J-codes).
6. **Phase 6:** Broader post-acute (SNF, IRF, LTCH, Dialysis).

Each new dataset follows the hospital precedent: one-time vendored/cached
source with provenance, a loader normalizing into the shared registry, and
honest data-confidence labels (observed vs Medicare-proxy vs supply-only).

## Per-sector diligence questions PEdesk should answer

How big is the local market? Who are the providers? How fragmented?
What quality/compliance risks? What reimbursement exposure? Which public
benchmark applies? What's observed vs estimated vs unknown? What must the
deal team verify with target documents?

## Honesty labels (reused from the maps/trust work)

Every sector page must say which it is:
- **Strong public data** (e.g. dialysis, hospice/HH Compare, hospital)
- **Medicare-only proxy** (Part B/D volume — not commercial)
- **Provider-supply data** (NPPES counts — not revenue)
- **Not commercial revenue** (dental, cash-pay outpatient)
- **Needs target docs to verify**

## Not in scope for Phase 1
No new data downloads, no uploads, no memory, no actions/mutations, no
external runtime APIs. This doc is the plan; builds come in later phases,
each gated on a vetted, vendored data source.
