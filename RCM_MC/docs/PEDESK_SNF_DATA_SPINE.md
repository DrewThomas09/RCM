# PEdesk SNF / Nursing Home data spine — audit & ingest plan

**Status:** Phase 1 audit (this PR, #600). **No data is vendored here and no
UI is built.** This document names the exact CMS public datasets to ingest,
their keys/grains/fields/limits, the normalized local files + loader API to
build, and the next-PR plan. It mirrors how the Home Health / Hospice spine
was built (vendored CSV snapshots → local loaders → screener → profiles →
market intelligence), and follows the honesty discipline in
[`PEDESK_SECTOR_INTELLIGENCE_ROADMAP.md`](PEDESK_SECTOR_INTELLIGENCE_ROADMAP.md).

> **Verify-at-ingest note.** Dataset *names* and *contents* below are stable
> CMS Care Compare facts. Provider Data Catalog **slugs/CSV URLs rotate**
> (and files are re-published monthly), so the exact download IDs are marked
> *(confirm at ingest)* — they are resolved against
> data.cms.gov/provider-data at vendor time, not asserted here. This audit
> made **no runtime network calls**.

## Why SNF next

SNF is the most CMS-ready remaining post-acute sector for PE diligence: CMS
**Nursing Home Care Compare** publishes a rich, monthly, public-domain
archive — provider identity, four component **5-star ratings**, staffing
hours, health-inspection survey results, **penalties/fines/enforcement**,
**ownership**, **Special Focus Facility** status, and bed/resident counts.
Unlike dental (supply-only) it supports a genuine quality + compliance +
competition read. It is **Medicare/Medicaid-certified facilities only** and
**not commercial revenue** — see Limitations.

## Existing repo audit (2026-05-23)

- **No SNF / nursing-home / skilled-nursing data files or loaders exist**
  (`rcm_mc/data/` has none; the only `snf`/`nursing` matches are incidental
  sub-sector mentions in `ui/sector_intelligence_page.py` and
  `pe_intelligence/` benchmark text).
- Reusable infra already in-repo (same as HH/Hospice used): the sector
  screener scaffold (`ui/sector_screener.py`), provider-profile scaffold
  (`ui/sector_provider_profile.py`), market-intel layer
  (`ui/sector_market_intel.py`), the state tile-grid map
  (`ui/us_map.py`), the Guide context registry
  (`assistant/context/manual_page_contexts.py`), and the data-confidence /
  provenance discipline. **SNF can reuse all of it** — the work is the data
  spine + thin per-sector wrappers, not new UI machinery.
- `data/cms_pos.py` (Provider of Services) already categorizes
  Medicare-certified provider types including SNF — useful as a
  cross-check on the certification universe, but the Care Compare archive
  below is the richer spine.

## Candidate CMS datasets

All from **CMS Nursing Home Care Compare** (data.cms.gov/provider-data,
theme: *"Nursing homes including rehab services"*), published as a single
monthly ZIP with a data dictionary. **Public domain** (U.S. Government work)
— suitable for one-time vendoring like the HH/Hospice files. Refresh:
**monthly** (some components quarterly).

### 1. Provider Information — **the spine (first ingest target)**
- **File:** `NH_ProviderInfo_<Month><Year>.csv` *(confirm slug at ingest)*
- **Primary key:** **CMS Certification Number (CCN)** — 6-char "Federal
  Provider Number". One row per facility (~14,000–15,000 nursing homes).
- **Row grain:** one certified nursing home.
- **Useful fields (diligence-relevant):**
  - *Identity/location:* provider name, legal business name, address, city,
    state, ZIP, **county**, phone, provider type (Medicare/Medicaid/both),
    "resides in hospital" flag.
  - *Size:* **number of certified beds**, **average number of residents per
    day** (census proxy).
  - *Ratings (1–5 stars):* **overall rating**, **health-inspection rating**,
    **staffing rating**, **RN-staffing rating**, **quality-measure (QM)
    rating** (often split long-stay / short-stay).
  - *Staffing detail:* reported + case-mix-adjusted nurse/aide hours per
    resident day.
  - *Compliance/enforcement summary (counts live here too):* total weighted
    health-survey score, # substantiated complaints, # facility-reported
    incidents, **# fines**, **total $ amount of fines**, **# payment
    denials**, **total # of penalties**.
  - *Risk flags:* **Special Focus Facility (SFF)** status + SFF-candidate,
    **abuse icon**, "most recent health inspection more than 2 years ago",
    **ownership changed in last 12 months**, automatic-sprinkler coverage,
    resident/family council.
  - *Ownership:* **ownership type** (For-Profit / Non-Profit / Government,
    with corp/individual/partnership detail).
  - *Dates:* date first approved to provide Medicare/Medicaid.
- **Why it's the first target:** like `home_health_providers.csv` +
  `home_health_quality.csv`, this **single file** already carries identity,
  location, ownership, size, the four star ratings, and penalty-summary
  counts — enough to ship a screener, profiles, and most market intelligence
  on its own. Deeper files (below) enrich the profile later.
- **Production-vendor?** **Yes** — first.

### 2. Penalties / Enforcement
- **File:** `NH_Penalties_<Month><Year>.csv` *(confirm at ingest)*
- **PK:** composite — CCN + penalty date + penalty type. **Grain:** one row
  per penalty action.
- **Useful fields:** penalty date, **penalty type** (civil money penalty /
  payment denial), **fine amount ($)**.
- **Use:** the enforcement timeline on a provider profile (Provider
  Information only has the rolled-up counts/totals).
- **Vendor?** Yes, **Phase 2 of the spine** (profile deep-dive).

### 3. Health Deficiencies / Citations (survey results)
- **File:** `NH_HealthCitations_<Month><Year>.csv` *(confirm at ingest)*
- **PK:** composite — CCN + survey date + deficiency tag (F-tag) +
  scope/severity. **Grain:** one row per cited deficiency.
- **Useful fields:** deficiency category, **F-tag**, **scope/severity code**
  (A–L), standard vs complaint survey, correction status/date.
- **Use:** survey-risk detail (which deficiencies, how severe) on the
  profile; severity mix as a compliance signal.
- **Vendor?** Optional / later — larger file; counts already summarized in
  Provider Information for the screener.

### 4. Ownership (entity detail)
- **File:** `NH_Ownership_<Month><Year>.csv` *(confirm at ingest)*
- **PK:** composite — CCN + owner name + role. **Grain:** one row per
  owner/role per facility.
- **Useful fields:** owner name, **owner type** (individual / organization),
  **role** (e.g. 5%+ direct/indirect owner, officer, managing employee),
  **ownership %**, association date.
- **Use:** PE-relevant ownership structure / roll-up & chain detection
  beyond the single "ownership type" field in Provider Information.
- **Vendor?** Optional / later (chain analysis is a strong SNF angle but a
  Phase-3 feature).

### 5. Quality Measures (MDS + claims-based)
- **Files:** `NH_QualityMsr_MDS_*.csv`, `NH_QualityMsr_Claims_*.csv`
  *(confirm at ingest)*
- **PK:** composite — CCN + measure code + resident type (long/short-stay).
  **Grain:** one row per provider per measure.
- **Useful fields:** measure code/description, short- vs long-stay,
  adjusted score, national/state comparison.
- **Use:** granular quality drill-down. The **QM star rating** in Provider
  Information already summarizes these, so this is later/optional.
- **Vendor?** Optional / later.

### Supporting (not spine)
- **State & US Averages** (`NH_StateUSAverages_*`) — handy for benchmark
  lines, but the market-intel layer already computes state averages from the
  provider rows, so not required.
- **Provider of Services (POS)** — already in-repo (`data/cms_pos.py`);
  cross-checks the certified-SNF universe.
- **SNF VBP / SNF QRP** — readmission/QRP programs; out of scope for the
  spine, possible far-future enrichment.

## Proposed normalized local files

Same pattern as `home_health_*` / `hospice_*`: compact, vendored CSV
snapshots under `rcm_mc/data/`, each row carrying `source` + `source_date`.
**Phase 2A (next PR after this audit) vendors only the first two**, both
derived from the single Provider Information file:

| File | Derived from | Grain | Key fields |
|---|---|---|---|
| `snf_providers.csv` | Provider Information | one SNF (PK `ccn`) | ccn, provider_name, address, city, state, zip, county, ownership, certified_beds, avg_residents_per_day, provider_type, sff_status, changed_ownership_12mo, abuse_icon, certification_date, source, source_date |
| `snf_quality.csv` | Provider Information | one SNF (PK `ccn`) | overall_rating, health_inspection_rating, staffing_rating, rn_staffing_rating, qm_rating, weighted_health_survey_score, num_fines, total_fines_usd, num_payment_denials, num_substantiated_complaints, source, source_date |

Deferred to later spine PRs (only if/when the profile/chain features need them):

| File | Derived from | Grain |
|---|---|---|
| `snf_enforcement.csv` | Penalties | one penalty action |
| `snf_inspections.csv` | Health Deficiencies | one cited deficiency |
| `snf_ownership.csv` | Ownership | one owner/role per facility |

> **Note on `total_fines_usd`:** this is a CMS **enforcement penalty** total
> (fines/CMPs levied by regulators), **not** facility revenue or financials.
> Label it as such in any UI.

## Proposed loader API (`rcm_mc/data/snf.py`)

Mirrors `data/home_health.py` / `data/hospice.py` exactly (stdlib `csv`,
`functools.lru_cache`, local files only — **no runtime network**):

```python
load_snf_providers()        -> Dict[ccn, SnfProvider]          # frozen dataclass
load_snf_quality()          -> Dict[ccn, Dict[str, float|None]]
snf_providers_for_state(st) -> List[SnfProvider]               # filtered + name-sorted
snf_provider_by_ccn(ccn)    -> Optional[SnfProvider]           # convenience lookup
load_snf_summary_by_state() -> Dict[state, {facilities, rated, avg_overall_rating}]
```

Headline metric = **overall 5-star rating** (`higher_is_better=True`).
Locality = **county** (Provider Information includes it — so SNF gets true
county competition, unlike Home Health which only has city).

## Proposed UI phases (do NOT build in this PR)

Each reuses the existing scaffolds; the work is thin wrappers + Guide context.

- **#601 — SNF screener + state maps** (`/nursing-homes` or `/snf`): reuse
  `sector_screener.py` — KPI cards, state tile-grid map shaded by facility
  count / avg overall rating, per-state tables. Headline = overall rating;
  table columns: name, CCN, county, ownership, overall ★, health-inspection
  ★, staffing ★, SFF flag.
- **#602 — SNF provider profiles** (`/snf/<ccn>`): reuse
  `sector_provider_profile.py` — identity, the four star ratings vs state
  avg + percentile, beds/census, penalties summary, SFF/abuse flags, peers.
- **#603 — SNF market intelligence**: reuse `sector_market_intel.py` —
  state market summary, ownership mix (For-Profit vs Non-Profit vs Gov),
  rating distribution/quartiles, **county competition** table, plus an
  SFF/penalty concentration read.

## Limitations — what NOT to claim

State these in any future SNF UI (same discipline as HH/Hospice):

- **Medicare/Medicaid-certified nursing homes only.** Private-pay-only
  facilities and non-certified beds are not represented.
- **Public quality, staffing, and survey data — NOT commercial revenue,
  payor mix, or facility financials.** "Total fines" is a regulatory
  **penalty** figure, not revenue.
- **Star ratings are CMS's methodology**, refreshed monthly; the
  health-inspection component is largely state-survey-driven and can lag.
- **Self-reported / auditable inputs:** staffing is now PBJ-based (payroll)
  but some measures remain self-reported; treat as a screening signal, not
  audited truth.
- **Not all competitors are visible:** assisted-living, independent senior
  living, and private-pay SNFs are outside CMS certification.
- **It is market/quality/compliance diligence context — NOT a final
  investment recommendation**, and not a substitute for target documents.

## Recommended first ingest target & next-PR plan

1. **First ingest = Provider Information** → vendor `snf_providers.csv` +
   `snf_quality.csv` (one source file, two normalized files), build
   `rcm_mc/data/snf.py` with the loader API above. *(This is the next PR
   after this audit — gated on your approval to vendor data; mirrors HH/
   Hospice Phase 2A.)*
2. **#601** SNF screener + state map (reuse `sector_screener.py`).
3. **#602** SNF provider profiles (reuse `sector_provider_profile.py`).
4. **#603** SNF market intelligence (reuse `sector_market_intel.py`).
5. **Later/optional:** vendor Penalties → `snf_enforcement.csv` (profile
   enforcement timeline); Ownership → `snf_ownership.csv` (chain/roll-up
   analysis); Health Deficiencies → `snf_inspections.csv` (survey-risk
   detail).

No data was vendored, no UI built, and no production behavior changed in
this audit PR.
