# healthdata_gov — healthdata.gov (HHS-wide Socrata meta-catalog) connector

Self-contained RCM-MC connector for **healthdata.gov**, the U.S. Department
of Health & Human Services' department-wide open-data catalog (Socrata /
SODA — the same platform, and the same live quirks, as the estate's
`cdc_data` connector). Stdlib only; mirrors the `cms_coverage` /
`cdc_data` architecture: declarative endpoints → transport → connector →
normalize → SQLite store → uniform `/v1/query` + lookups + standalone
HTTP surface.

## The domain, verified live (2026-07-06)

* Catalog: `GET /api/views/metadata/v1?limit=N&page=P` → JSON array.
  **23,080 datasets** on the live sweep. Paging is `limit` + **1-based
  `page`**; the documented `offset` param is **silently ignored**
  (identical to data.cdc.gov — an offset loop replays page 1 forever).
  1000/page is reliable (~15-20 s/page); 5000/page hit gateway read
  timeouts.
* Rows: `GET /resource/{4x4}.json` with SoQL (`$limit`/`$offset`/
  `$where`/`$order`, `$order=:id` pinned for stable paging). 404 for an
  unknown 4x4 folds to zero rows.
* Full schema: `GET /api/views/{4x4}.json` (Socrata JSON rows omit null
  fields, so canonical columns are snapshotted from here, not from row
  samples).
* Auth: none required; optional Socrata app token via
  `$HEALTHDATA_APP_TOKEN` (sent as `X-App-Token` only when set — a wrong
  token hard-403s on this platform).

### Meta-catalog anatomy (drives the curation policy)

healthdata.gov is HHS's *aggregator*. Of the 23,080 catalog entries
(live sweep), **20,580 are HHS's own hub records**
(`domain=datahub.hhs.gov` — the hub domain fronted by healthdata.gov):
17,629 unattributed hub records plus ~3k href mirrors whose
`attribution` names the home portal (data.cdc.gov 1,377,
data.medicaid.gov 540, Data.Healthcare.gov 336, data.cms.gov 156, NLM
143, …). The other **2,500 have `domain=healthdata.gov`** and are copies
federated in from state/city portals (data.wa.gov 754,
chhs.data.ca.gov 483, health.data.ny.gov 433, …). Only ~114 hub assets
are row-serving `type=dataset` resources; everything else —
federal-portal mirrors, state-portal copies, charts/maps/stories/`href`
links — **403s on `healthdata.gov/resource/{4x4}.json`** (verified
live; 404 is reserved for unknown ids). Mirrors are already covered by
their home connectors in the estate (cdc_data, cms_open_data,
medicaid_data, provider_data, open_payments, healthcare_gov,
hrsa_data) — so curation here deliberately covers only genuinely native
row-serving datasets, and the catalog table carries `domain` +
`attribution` so mirrors stay identifiable (`catalog-search --hub-only
--unattributed`, `/v1/lookup/hhs-dataset/{id}` → `hhs_hub` +
`attribution`).

Assignment candidates that did NOT survive the native test (all `href`
mirrors or link-only): SAMHSA treatment-facility directories, AHRQ SDOH
database, organ procurement/transplant (HRSA), drug-overdose/naloxone
(all data.cdc.gov), nursing-home COVID (data.cms.gov). Two natives were
rejected on verified grain defects: `ehpz-xc9n` (UAC program; duplicate
`date` rows with conflicting values) and `g89t-x93h` (Project Tycho L1;
duplicate `(epi_week,state,loc,loc_type,disease)`). Both remain pullable
via `fetched_rows`.

## Datasets

| dataset_id | 4x4 | grain (natural key, live-verified) | rows live | cadence |
|---|---|---|---|---|
| `healthdata_gov_catalog` | — | dataset_uid | 23,080 | weekly |
| `healthdata_gov_hospital_capacity_facility` | anag-cw7u | (hospital_pk, collection_week) | 1,045,406 | static¹ |
| `healthdata_gov_hospital_capacity_state_ts` | sgxm-t72h | (state, date) | 81,335 | static¹ |
| `healthdata_gov_covid_pcr_testing` | j8mb-icvb | (state, date, overall_outcome) | 242,970 | static¹ |
| `healthdata_gov_community_profile_county` | di4u-7yu6 | (fips, date) — final snapshot 2023-05-10 | 3,294 | static |
| `healthdata_gov_covid_therapeutics_locator` | rxn6-qnx8 | (provider_name, address1, address2, city, state_code, zip, ndc)² | 69,184 | static |
| `healthdata_gov_hospital_ids` | vz64-k9wr | hhs_id (CCN crosswalk) | 7,621 | static |
| `healthdata_gov_school_learning_modalities` | aitj-yx37 | (district_nces_id, week) | 994,788 | static |
| `healthdata_gov_covid_policy_orders` | gyqz-9u7n | 9-field compose incl. comments/source² | 4,218 | static |
| `healthdata_gov_fetched_rows` | any | {dataset_key}:{row_idx} (+slice signature) | on demand | on_demand |

¹ HHS hospital COVID reporting ended 2024-04; the series are frozen
archives (last `rowsUpdatedAt` 2024-05-03).
² Shorter intuitive keys were tried first and produced live duplicates
(two same-building Kaiser pharmacies; same county/date/type policy rows
differing only in comments/source) — the longer composes are the first
duplicate-free grains, verified with SoQL `$group`/`$having`.

Estate join points: `ccn` (facility capacity + HHS-ID crosswalk ↔ Care
Compare / cost reports), `npi` (therapeutics locator ↔ npi_registry),
county `fips` (community profile ↔ census_acs / cdc_data county tables),
`state`.

## Tables

`healthdata_gov_catalog` (catalog, pk `dataset_uid` — includes `domain`,
`attribution`, `update_frequency`), eight `hhs_*` curated tables (pk
`record_key`, columns = live snapshot from `/api/views/{4x4}.json`, all
TEXT + `source_endpoint`/`ingested_at` meta), and `healthdata_gov_rows`
(generic JSON-blob rows, pk `row_key`, `row_idx` INTEGER). All writes are
natural-key upserts — re-ingest never double-counts.

## Usage

```bash
# registry
python -m connectors.healthdata_gov.cli datasets

# full catalog sync (~24 pages × 1000; reports hub vs state-copy split)
python -m connectors.healthdata_gov.cli --db hd.db discover

# curated fetches (max-pages defaults to 5 as a politeness guard)
python -m connectors.healthdata_gov.cli --db hd.db fetch --dataset hospital_ids --max-pages 8
python -m connectors.healthdata_gov.cli --db hd.db fetch --dataset hospital_capacity_facility \
    --filter state=TX --max-pages 2
python -m connectors.healthdata_gov.cli --db hd.db fetch --dataset covid_pcr_testing \
    --where "date > '2024-01-01'"

# ANY 4x4 on the domain → generic rows table
python -m connectors.healthdata_gov.cli --db hd.db fetch --dataset ehpz-xc9n

# query the local slice (uniform grammar: field__op=value)
python -m connectors.healthdata_gov.cli --db hd.db query \
    healthdata_gov_hospital_ids --filter state=TX --sort ccn --limit 5

# local catalog search; --hub-only drops state-portal copies and
# --unattributed additionally drops federal-portal href mirrors
python -m connectors.healthdata_gov.cli --db hd.db catalog-search --q "hospital capacity" --hub-only --unattributed

# lookups
python -m connectors.healthdata_gov.cli --db hd.db lookup-hospital-capacity 010039
python -m connectors.healthdata_gov.cli --db hd.db lookup-hhs-dataset anag-cw7u

# standalone /v1 surface
python -m connectors.healthdata_gov.cli --db hd.db serve --port 8104
```

HTTP surface: `/health`, `/v1/datasets`, `/v1/query/{dataset_id}`,
`/v1/query/{dataset_id}/aggregate?group_by=…`,
`/v1/lookup/hhs-dataset/{dataset_uid}`,
`/v1/lookup/hospital-capacity/{ccn}`.

## Politeness / limits

Courtesy floor of 0.25 s between requests; 429/5xx retried with
exponential backoff + full jitter honouring `Retry-After`; every fetch is
capped at `max_pages` (default 5, hard cap 3000) so a ~1M-row facility
file pull must be an explicit choice; catalog discover drains ~24 pages
by default (cap 40). Transport timeout is 120 s because live 1000-item
catalog pages take ~15-20 s and larger ones hit gateway limits.

## Tests

```bash
cd /home/user/RCM && python3 -m unittest discover -s connectors/healthdata_gov/tests -t .
```

78 tests, no network — an injectable fake opener models both live paging
shapes (SODA `$limit/$offset`; catalog `limit`+1-based `page` with
`offset` ignored), 429/Retry-After/5xx/404 behavior, and fixtures mirror
live payload shapes probed 2026-07-06.
