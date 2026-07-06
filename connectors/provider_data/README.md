# Provider Data connector — CMS Provider Data Catalog / Care Compare (DKAN)

Self-contained, **stdlib-only** connector for the CMS Provider Data
Catalog (`data.cms.gov/provider-data`) — the DKAN open-data catalog
behind Medicare Care Compare. It ingests the full catalog (234 datasets
live on 2026-07-06), 34 curated flagship datasets into canonical SQLite
tables, and any other catalog dataset on demand into a generic rows
table, then re-exposes everything behind the estate's uniform `/v1`
query surface.

```
endpoints ─▶ transport ─▶ connector.discover()/fetch()/refresh() ─▶ raw pages
                                                                        │
                                                                  normalize ─▶ canonical SQLite tables
                                                                        │              │
                                                                    registry ─▶ /v1/query/{dataset} + /aggregate
                                                                                  /v1/lookup/…
```

## The API (live-verified 2026-07-06)

- **Base**: `https://data.cms.gov/provider-data` — public, no key.
- **Catalog**: `GET /api/1/metastore/schemas/dataset/items` → bare JSON
  array of 234 dataset metadata items (`identifier` 4x4 id, `title`,
  `description`, `theme`, `keyword`, `issued`, `modified`,
  `distribution[0].downloadURL` CSV, `landingPage`).
- **Datastore**: `GET /api/1/datastore/query/{identifier}/0?limit=N&offset=M`
  → `{"results": [...], "count": total, "query": {...}, "schema": {...}}`.
  `count` is always present and reflects the *filtered* total when
  equality conditions are sent
  (`conditions[0][property]=state&conditions[0][value]=TX&conditions[0][operator]==`).
- **Paging bounds**: `limit` hard-maxes at **1500** (larger → HTTP 400).
  This connector defaults to a polite 500/page and caps `fetch` at
  **5 pages** unless the caller raises `max_pages` explicitly — so an
  accidental pull of the 3.4M-row clinician file costs a few requests,
  not an afternoon.
- **Rate limits**: none published; the transport keeps a 0.25 s
  inter-request floor and retries 429/5xx with backoff + jitter
  (`Retry-After` honoured). Courtesy defaults, not a contract — verify
  live before a bulk run.
- An unknown identifier is a 404 with a JSON message; the transport
  folds it into an empty envelope so stale catalog ids degrade
  gracefully.
- **Identifier shapes**: most datasets use 4x4 identifiers, but the
  ESRD QIP payment-year files use bare **slugs** (`complete_qip_data`,
  `tps`, `pppw`) — verified live that the datastore serves them at the
  same query path with the same envelope. Slugs are only reachable
  through their curated keys (the generic fall-through accepts 4x4s
  only, so a typo'd name stays an error, not a speculative fetch).

## Datasets (36 registry rows)

| dataset_id (`provider_data_` +) | identifier | target table | natural key |
|---|---|---|---|
| `catalog` | — | `provider_data_catalog` | identifier |
| `hospital_general` | xubh-q36u | `hospital_general` | facility_id |
| `hcahps_hospital` | dgck-syfz | `hcahps_hospital` | facility_id + hcahps_measure_id |
| `complications_deaths_hospital` | ynj2-r877 | `complications_deaths_hospital` | facility_id + measure_id |
| `timely_effective_care_hospital` | yv7e-xc69 | `timely_effective_care_hospital` | facility_id + measure_id |
| `unplanned_visits_hospital` | 632h-zaca | `unplanned_visits_hospital` | facility_id + measure_id |
| `mspb_hospital` | rrqw-56er | `mspb_hospital` | facility_id |
| `imaging_efficiency_hospital` | wkfw-kthe | `imaging_efficiency_hospital` | facility_id + measure_id |
| `nursing_home_provider_info` | 4pq5-n9py | `nursing_home_provider_info` | ccn |
| `nursing_home_penalties` | g6vv-u9sr | `nursing_home_penalties` | ccn + penalty_date + penalty_type + fine_id |
| `mds_quality_measures` | djen-97ju | `mds_quality_measures` | ccn + measure_code |
| `snf_qrp_provider` | fykj-qjee | `snf_qrp_provider` | ccn + measure_code |
| `home_health_agencies` | 6jpm-sxkc | `home_health_agencies` | ccn |
| `hospice_provider` | 252m-zfp9 | `hospice_provider` | ccn + measure_code |
| `hospice_general` | yc9t-dgbk | `hospice_general` | ccn |
| `dialysis_facilities` | 23ew-n7w9 | `dialysis_facilities` | ccn |
| `irf_general` | 7t8x-u3ir | `irf_general` | ccn |
| `ltch_general` | azum-44iv | `ltch_general` | ccn |
| `dac_national` | mj5m-pzi6 | `dac_national` | npi + ind_enrl_id + org_pac_id + adrs_id |
| `dialysis_state_averages` | 2fpu-cgbb | `dialysis_state_averages` | state |
| `dialysis_national_averages` | 2rkq-ygai | `dialysis_national_averages` | country |
| `ich_cahps_facility` | 59mq-zhts | `ich_cahps_facility` | ccn |
| `ich_cahps_state` | hanv-ru8h | `ich_cahps_state` | state |
| `ich_cahps_national` | utgq-v46w | `ich_cahps_national` | country |
| `esrd_qip_complete` | `complete_qip_data` (slug) | `esrd_qip_complete` | ccn |
| `esrd_qip_tps` | `tps` (slug) | `esrd_qip_tps` | ccn |
| `esrd_qip_pppw` | `pppw` (slug) | `esrd_qip_pppw` | ccn |
| `asc_quality_facility` | 4jcv-atw7 | `asc_quality_facility` | npi + facility_id + year |
| `asc_quality_state` | axe7-s95e | `asc_quality_state` | state + year |
| `asc_quality_national` | wue8-3vwe | `asc_quality_national` | year |
| `oas_cahps_asc_facility` | 48nr-hqxx | `oas_cahps_asc_facility` | facility_id |
| `oas_cahps_asc_national` | tf3h-mrrs | `oas_cahps_asc_national` | start_date + end_date |
| `imaging_efficiency_state` | if5v-4x48 | `imaging_efficiency_state` | state + measure_id |
| `imaging_efficiency_national` | di9i-zzrc | `imaging_efficiency_national` | measure_id |
| `medical_equipment_suppliers` | ct36-nrcq | `medical_equipment_suppliers` | provider_id |
| `fetched_rows` | any | `provider_data_rows` | dataset_key + row_idx |

("ccn" above is the live column `cms_certification_number_ccn`; the
composed key lands in each table's `record_key` primary key. Every key
was verified unique against a FULL live pull of its dataset on
2026-07-06.)

Dataset-selection notes:

- **OAS CAHPS**: the catalog carries six OAS CAHPS files (ASC + hospital
  outpatient departments, each at facility/state/national grain). We
  curate the ASC pair the estate asked for — 48nr-hqxx *is* the ASC
  facility-level file and tf3h-mrrs its national companion (titles
  verified in the live catalog; distinguishable, not duplicates). The
  HOPD trio (yizn-abxn / 6pfg-whmx / s5pj-hua3) and ASC state file
  (x663-bwbj) stay reachable via the generic `fetched_rows` path.
- **ASC quality facility key**: `(facility_id, year)` alone is NOT
  unique live — 98 shared-CCN pairs report under two NPIs, and 3 rows
  carry an empty facility_id (their NPI is populated). Leading with
  `npi` keeps all 5711 live rows: `(npi, facility_id, year)` is
  5711/5711 unique.
- **OAS CAHPS national** has no id column at all — one row per survey
  window, keyed `(start_date, end_date)`.

Curated column tuples were locked from a **live sample** of each
dataset's datastore and snake-cased with `normalize._snake` (which also
runs at ingest, so schema and mapping cannot drift apart). Notable live
hazards handled: `_condition` (timely & effective care), digit-leading
`95_ci_*` columns (dialysis → `n_95_ci_*`), and DKAN's hash-suffixed
truncated headers. `nursing_home_penalties` needs `fine_id` in its key —
the live file contains same-day duplicate fines (verified: 480/500
unique without it).

Everything is stored TEXT (the estate's one-type model) except
`provider_data_rows.row_idx`, declared INTEGER so paging order sorts
numerically.

## Usage

```bash
# The registry (36 datasets)
python -m connectors.provider_data.cli datasets

# Sync the full catalog (~234 rows) into a real db
python -m connectors.provider_data.cli --db ./provider_data.db discover

# Curated fetch: Texas hospitals, one page
python -m connectors.provider_data.cli --db ./provider_data.db \
    fetch --dataset hospital_general --state TX --max-pages 1

# ANY catalog dataset by 4x4 identifier → generic rows table
python -m connectors.provider_data.cli --db ./provider_data.db \
    fetch --dataset 77hc-ibv8 --max-pages 1

# Find datasets to pull
python -m connectors.provider_data.cli --db ./provider_data.db \
    catalog-search --q "ownership"

# Query the ingested slice / serve the /v1 surface
python -m connectors.provider_data.cli --db ./provider_data.db \
    query provider_data_hospital_general --filter state=TX --sort=-hospital_overall_rating
python -m connectors.provider_data.cli --db ./provider_data.db serve --port 8099
```

```python
from connectors.provider_data.connector import ProviderDataConnector
from connectors.provider_data.tables import ProviderDataStore

store = ProviderDataStore("./provider_data.db")
conn = ProviderDataConnector()
conn.refresh(store, "catalog")                                  # 234 rows
conn.refresh(store, "hospital_general", max_pages=20)           # full file
conn.refresh(store, "esrd_qip_tps", max_pages=16)               # slug-identified QIP file
conn.refresh(store, "g62h-syeh", max_pages=1)                   # any dataset
```

## `/v1` routes (standalone server)

```
/health
/v1/datasets
/v1/query/{dataset}?<filters>&select=&sort=&limit=&offset=
/v1/query/{dataset}/aggregate?group_by=a,b&<filters>&limit=
/v1/lookup/hospital/{facility_id}      /v1/lookup/nursing-home/{ccn}
/v1/lookup/home-health/{ccn}           /v1/lookup/hospice/{ccn}
/v1/lookup/dialysis/{ccn}              /v1/lookup/clinician/{npi}
/v1/lookup/pdc-dataset/{identifier}
```

Uniform filter grammar: `field=v` equality or `field__op=v` with
`eq/ne/gt/gte/lt/lte/like/in/between/isnull/notnull`; sort
`field`/`-field`.

## Tests

```bash
cd /home/user/RCM
python3 -m unittest discover -s connectors/provider_data/tests -t . -v
```

Stdlib `unittest`, **no network** — every HTTP path runs against an
in-memory fake opener whose fixtures mirror the live response shapes.
The API-server suite exercises a real `ThreadingHTTPServer` on a free
port.
