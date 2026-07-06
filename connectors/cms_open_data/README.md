# CMS Open Data connector

The CMS Open Data platform (`data.cms.gov`, data-api v1) vertical slice:
connector → normalized canonical tables → registry → `/v1/query` +
`/v1/lookup` → standalone HTTP surface. Self-contained and parallel-safe.
**Stdlib only** (`urllib` + `json` + `sqlite3` + `time` + `http.server`);
no pandas/pyarrow/duckdb/requests, no new runtime dependencies. Mirrors
`connectors/cms_coverage/` exactly.

```
discover() ─▶ catalog (158 datasets)      fetch(dataset) ─▶ normalize ─▶ canonical SQLite tables
                    │                                                            │
                    └──▶ UUID re-resolution                            registry ─▶ /v1/query/{dataset}
                                                                                  /v1/lookup/practice|prescriber|
                                                                                  facility-cost|ownership|cms-dataset|
                                                                                  facility-universe
```

Three layers make "every dataset connected" true:

1. **Catalog** (`cms_open_data_catalog`) — `discover()` syncs the DCAT
   `data.json` document: one row per dataset data.cms.gov publishes
   (158 at snapshot time) with title, description, themes, periodicity,
   modified date, temporal coverage, latest data-api URL + UUID, landing
   page, data dictionary and contact.
2. **53 curated flagships** — each a first-class registry row with its own
   canonical table whose columns were snapshotted from **live API samples**
   (size=5 probes, 2026-07-06) and snake_cased with the deterministic
   `normalize._snake` (lowercase; non-alphanumeric runs → `_`; no
   camelCase splitting). Composed natural keys make every write an
   idempotent upsert.
3. **Generic on-demand rows** (`cms_open_data_rows`) — any other catalog
   dataset can be pulled by slug or UUID via
   `connector.fetch_dataset()` / `cli fetch --dataset <slug|uuid>` and
   stays queryable through the uniform engine (rows land as `row_json`
   keyed `{dataset_key}:{row_idx}`, filter on `dataset_key` +
   `row_json__like`).

## Layout

| File | Role |
|------|------|
| `endpoints.py` | One declarative `EndpointSpec` per dataset (kind, pinned UUID, exact catalog title, natural key, snapshotted snake_cased columns). GENERATED from live samples — the schema source of truth. |
| `transport.py` | Throttled JSON transport: 429/`Retry-After`/5xx backoff + jitter, 404→empty (rotated UUIDs), injectable opener. |
| `connector.py` | `discover()` / `fetch()` / `fetch_dataset()` / `refresh()` — absorbs the API's `size`/`offset` paging; UUID re-resolution from the synced catalog. |
| `normalize.py` | `_snake` (THE name contract) + catalog/curated/generic mappers; composed `row_key` / `dataset_key`. |
| `tables.py` | `TABLES` (55 defs derived from the endpoint specs) + SQLite store with idempotent upsert. |
| `registry.py` | Declarative `source=cms_open_data` registry rows (one per dataset). |
| `query.py` | The `/v1/query` engine: uniform filter / select / sort / paginate **+ `aggregate()` group-by/count** (copied from cms_coverage). |
| `lookup.py` | Six enriched `/v1/lookup` fan-outs + router-agnostic handler map. |
| `api_server.py` | Standalone stdlib `http.server` `/v1` surface (auto-exposes every registry dataset + the lookup handlers). |
| `cli.py` | `python -m connectors.cms_open_data.cli …` |

## The API, in two calls

```
GET https://data.cms.gov/data.json                                   # DCAT catalog
GET https://data.cms.gov/data-api/v1/dataset/{uuid}/data?size=&offset=&filter[COL]=v
GET https://data.cms.gov/data-api/v1/dataset/{uuid}/data/stats       # {found_rows, total_rows}
```

* Rows come back as a **bare JSON array** of objects, keys = original
  column names, values all strings.
* Native filtering is `filter[COL]=value` equality plus `keyword=` search
  — used only for targeted pulls at fetch time (with ORIGINAL column
  names); the uniform `field__op` grammar applies post-ingest in SQLite
  (with snake_cased names).
* **UUIDs rotate**: the `{uuid}` addresses one *version* of a dataset and
  changes when CMS publishes a new data year. Curated specs pin the UUID
  live at snapshot time and re-resolve the current one from the synced
  catalog by title at fetch time (pin is the fallback), so a stale pin
  degrades to last-known-version instead of breaking. A rotated/unknown
  UUID 404s — the transport folds that to "no rows".
* No API key. Politeness: default page size 1000 (API max 5000, PBJ
  nurse staffing defaults to 500), default `max_pages=5` hard cap per
  fetch so an accidental pull of a 28M-row dataset stays a bounded probe
  — raise `--max-pages` deliberately. No documented rate limit; the
  transport keeps a 0.25s inter-request floor (courtesy default, not a
  contract — verify at data.cms.gov/api-docs before bulk runs).

## Datasets

`cms_open_data_catalog` (the catalog itself) + `cms_open_data_fetched_rows`
(the generic store) + 53 curated flagships (live `total_rows` at snapshot
time; the dataset_id prefix `cms_open_data_` is left off the keys below):

| key | title | live rows | cadence |
|-----|-------|-----------|---------|
| `mup_physician_by_provider` | Medicare Physician & Other Practitioners - by Provider | 1,296,739 | annual |
| `mup_physician_by_provider_service` | Medicare Physician & Other Practitioners - by Provider and Service | 9,781,673 | annual |
| `mup_physician_by_geo_service` | Medicare Physician & Other Practitioners - by Geography and Service | 268,350 | annual |
| `mup_partd_prescriber_by_provider` | Medicare Part D Prescribers - by Provider | 1,416,883 | annual |
| `mup_partd_prescriber_by_provider_drug` | Medicare Part D Prescribers - by Provider and Drug | 28,023,892 | annual |
| `mup_partd_prescriber_by_geo_drug` | Medicare Part D Prescribers - by Geography and Drug | 117,661 | annual |
| `part_b_spending_by_drug` | Medicare Part B Spending by Drug | 799 | annual |
| `part_d_spending_by_drug` | Medicare Part D Spending by Drug | 14,536 | annual |
| `mup_inpatient_by_provider` | Medicare Inpatient Hospitals - by Provider | 3,044 | annual |
| `mup_inpatient_by_provider_service` | Medicare Inpatient Hospitals - by Provider and Service | 145,879 | annual |
| `mup_inpatient_by_geo_service` | Medicare Inpatient Hospitals - by Geography and Service | 26,571 | annual |
| `mup_outpatient_by_provider_service` | Medicare Outpatient Hospitals - by Provider and Service | 116,182 | annual |
| `mup_outpatient_by_geo_service` | Medicare Outpatient Hospitals - by Geography and Service | 89,021 | annual |
| `mup_dme_by_supplier_service` | Medicare DMEPOS - by Supplier and Service | 463,784 | annual |
| `geo_variation_state_county` | Medicare Geographic Variation - by National, State & County | 36,994 | annual |
| `market_saturation_state_county` | Market Saturation & Utilization State-County | 1,030,290 | annual |
| `market_saturation_cbsa` | Market Saturation & Utilization Core-Based Statistical Areas | 228,484 | annual |
| `medicare_monthly_enrollment` | Medicare Monthly Enrollment | 573,769 | monthly |
| `ma_geo_variation` | Medicare Advantage Geographic Variation - National & State | 378 | annual |
| `hospital_cost_report` | Hospital Provider Cost Report (HCRIS) | 6,103 | annual |
| `snf_cost_report` | Skilled Nursing Facility Cost Report | 14,933 | annual |
| `hha_cost_report` | Home Health Agency Cost Report | 10,715 | annual |
| `hospital_all_owners` | Hospital All Owners (PECOS) | 147,332 | monthly |
| `snf_all_owners` | Skilled Nursing Facility All Owners | 280,207 | monthly |
| `hospital_enrollments` | Hospital Enrollments | 9,175 | monthly |
| `hospital_service_area` | Hospital Service Area | 1,156,702 | annual |
| `ffs_provider_enrollment` | Medicare FFS Public Provider Enrollment | 2,981,799 | quarterly |
| `pbj_daily_nurse_staffing` | Payroll Based Journal Daily Nurse Staffing | 1,321,304 | quarterly |
| `medicare_telehealth_trends` | Medicare Telehealth Trends | 36,120 | quarterly |
| `pac_snf_by_geo_provider` | Post-Acute Care: SNF by Geography and Provider | 14,214 | annual |
| `pac_hha_by_geo_provider` | Post-Acute Care: HHA by Geography and Provider | 8,519 | annual |
| `pac_hospice_by_geo_provider` | Post-Acute Care: Hospice by Geography and Provider | 5,824 | annual |
| `opt_out_affidavits` | Opt Out Affidavits | 56,300 | monthly |
| `order_and_referring` | Order and Referring | 2,013,841 | semiweekly |
| `revoked_providers` | Revoked Medicare Providers and Suppliers | 7,059 | quarterly |
| `price_transparency_enforcement` | Hospital Price Transparency Enforcement Activities and Outcomes | 12,334 | monthly |
| `lab_fee_private_payer_rates` | Clinical Lab Fee Schedule Private Payer Rates and Volumes | 967,129 | annual |
| `opioid_treatment_programs` | Opioid Treatment Program Providers | 1,544 | weekly |
| `medicaid_spending_by_drug` | Medicaid Spending by Drug | 18,511 | annual |
| `fqhc_enrollments` | FQHC Enrollments | 11,063 | quarterly |
| `rhc_enrollments` | Rural Health Clinic Enrollments | 5,530 | quarterly |
| `ltc_facility_characteristics` | Long-Term Care Facility Characteristics | 14,701 | quarterly |
| `acos` | Accountable Care Organizations | 511 | annual |
| `dialysis_facilities` | Medicare Dialysis Facilities | 12,456,456 | annual |
| `esrd_agg_group_performance` | ESRD Facility Aggregation Group Performance | 433 | semiannual |
| `cec_model_data` | Comprehensive ESRD Care Model Data | 37 | annual |
| `home_infusion_therapy_providers` | Home Infusion Therapy Providers | 1,882 | biweekly |
| `pos_qies` | Provider of Services File - QIES | 44,429 | quarterly |
| `pos_internet_qies` | Provider of Services File - Internet QIES | 77,283 | quarterly |
| `pos_clinical_labs` | Provider of Services File - Clinical Laboratories | 676,051 | quarterly |
| `physician_supplier_procedure_summary` | Physician/Supplier Procedure Summary | 14,377,293 | annual |
| `rbcs` | Restructured BETOS Classification System (HCPCS→RBCS) | 18,882 | annual |
| `asm_participants` | Ambulatory Specialty Model Participants | 6,637 | annual |

> "Medicare Geographic Variation - by Hospital Referral Region" and
> "Kidney Care Choices Model" were on the wishlist but are
> **ZIP-download only** in data.json (no API distribution — the data-api
> cannot serve them; re-verified live 2026-07-06), so both are
> catalog-only here.

Dataset notes (live probes, 2026-07-06):

* `dialysis_facilities` is long-format: one row per facility × measure ×
  year (keyed `CCN:year:Measure_ID`), hence the 12.4M rows.
* The certified-facility universe is split across TWO Provider of
  Services files: legacy **QIES** carries hospitals, RHCs, FQHCs, CMHCs
  and PRTFs (`PRVDR_CTGRY_CD` = 01/06/12/19/21 live); **Internet QIES**
  (iQIES, different schema — 182 lowercase columns vs QIES's 473
  UPPERCASE, so it gets its own table, not a shared slice) carries HHAs,
  SNF/NFs, hospices, ASCs, ESRD facilities, CORFs, OPTs, portable x-ray
  and OPOs under its own `prvdr_type_id` scheme. Both retain terminated
  providers — filter `pgm_trmntn_cd = '00'` for active ones. Both
  default to `size=500` pages (wide rows).
* `physician_supplier_procedure_summary` (PSPS) is a 14.4M-row claims
  summary keyed by the full 8-dim grain (HCPCS × modifiers × specialty ×
  carrier × locality × type/place of service). Small `size=500` default;
  pull it filter-driven (e.g. `--filter HCPCS_CD=99213`), not wholesale.
* `rbcs` is the HCPCS→RBCS crosswalk; assignment history rows mean a
  HCPCS code can appear more than once (keyed through
  `RBCS_Analysis_Start/End_Dt`; `rbcs_latest_assignment = '1'` marks the
  current assignment).

## Canonical tables

- `cms_open_data_catalog` — PK `dataset_key` = the title slug
  (`_snake(title)`).
- `cms_open_data_<key>` (curated) — PK `row_key` =
  `{key}:{natural key values…}` composed from the ORIGINAL column values
  in `normalize.py` (e.g. `hospital_cost_report:747534`,
  `mup_physician_by_provider_service:1003000126:99223:F`).
- `cms_open_data_rows` (generic) — PK `row_key` =
  `{dataset_key}:{row_idx}`; `row_idx` carries INTEGER affinity so paging
  windows sort numerically; `dataset_key` is mirrored into
  `source_endpoint` for slice pinning.

All tables keep TEXT columns and the `(source_endpoint, ingested_at)`
metadata convention; every write is an idempotent upsert keyed by the
native id.

## Usage

```bash
# Sync the catalog (every dataset data.cms.gov publishes)
python -m connectors.cms_open_data.cli discover --db ./cms.db
python -m connectors.cms_open_data.cli catalog-search --q "cost report" --db ./cms.db

# Curated ingest — native paging absorbed; max-pages caps the pull
python -m connectors.cms_open_data.cli fetch --dataset part_b_spending_by_drug --db ./cms.db
python -m connectors.cms_open_data.cli fetch --dataset mup_physician_by_provider \
    --filter Rndrng_Prvdr_State_Abrvtn=MD --max-pages 10 --db ./cms.db

# ANY catalog dataset, on demand, by slug or UUID → cms_open_data_rows
python -m connectors.cms_open_data.cli fetch \
    --dataset accountable_care_organization_participants --db ./cms.db

# Uniform post-ingest query (snake_cased columns, field__op grammar)
python -m connectors.cms_open_data.cli query cms_open_data_part_b_spending_by_drug \
    --filter hcpcs_cd=90371 --select hcpcs_cd,brnd_name,tot_spndng_2023 --db ./cms.db

# Serve the /v1 surface (auto-exposes all 55 registry datasets)
python -m connectors.cms_open_data.cli serve --db ./cms.db --port 8103
#   GET /v1/datasets
#   GET /v1/query/cms_open_data_acos?aco_service_area__like=%CA%
#   GET /v1/query/cms_open_data_acos/aggregate?group_by=aco_service_area
#   GET /v1/lookup/practice/1003000126        (utilization + enrollment + opt-out)
#   GET /v1/lookup/prescriber/1003000126      (Part D profile + top drugs)
#   GET /v1/lookup/facility-cost/110130       (HCRIS across hospital/SNF/HHA)
#   GET /v1/lookup/ownership/440058           (PECOS owners via CCN or enrollment id)
#   GET /v1/lookup/cms-dataset/hospital_provider_cost_report
#   GET /v1/lookup/facility-universe/AL       (POS QIES+iQIES counts by category)
```

## Tests

```bash
python3 -m unittest discover -s connectors/cms_open_data/tests -t .
```

Stdlib `unittest`, no network: transport retry/backoff/404 paths, the
size/offset paging loop + `max_pages` truncation, catalog normalization,
UUID re-resolution (catalog wins, pin is fallback), curated natural-key
composition per PK style, generic row_json records, upsert idempotency,
the `/v1/query` engine (slice pinning, ops, clamping, injection
rejection), and an end-to-end run against a live `ThreadingHTTPServer`
covering every route.

## Contract conformance

- **Connector interface** — `discover()` / `fetch(dataset, params)` /
  `refresh(store, dataset)` with pagination, rate-limit, retries
  internal. ✔
- **Registry** — every dataset is one declarative row
  `{dataset_id, connector, base_url, endpoint, default_params,
  refresh_cadence, join_keys, target_table, source, source_filter,
  date_field}`; `/v1/query/{dataset}` auto-exposes anything in it. ✔
- **API contract** — `/v1/query` gives uniform filter/select/sort/
  paginate + aggregate; the API's native paging is absorbed at ingest. ✔
