# cdc_data — data.cdc.gov (Socrata SODA) connector

Self-contained, **stdlib-only** connector over the CDC's Socrata open-data
domain. It connects the **entire catalog** (~1,500 datasets), promotes
twelve flagship datasets to first-class canonical tables, and keeps every
other 4x4 reachable through a generic on-demand rows table — all behind the
same `/v1` contract as the rest of the RCM connector estate.

```
endpoints ─▶ transport ─▶ connector.discover()/fetch()/fetch_dataset() ─▶ raw rows
                                                              │
                                                        normalize ─▶ canonical SQLite tables
                                                              │              │
                                                          registry ─▶ /v1/query/{dataset} + /aggregate
                                                                        /v1/lookup/county-health/{fips}
                                                                        /v1/lookup/cdc-dataset/{4x4}
```

## API facts (verified live 2026-07-06)

- Base: `https://data.cdc.gov`
- **Catalog**: `GET /api/views/metadata/v1?limit=N&page=P` → JSON array of
  dataset metadata (4x4 `id`, `name`, `description`, `category`,
  camelCase timestamps, nested `customFields`). **Live quirk:** this
  endpoint pages by `limit` + **1-based `page`** — the documented
  `offset` param is silently *ignored* on this domain and would replay
  page 1 forever. Stop on a short/empty page (~1,508 datasets ≈ 4 pages
  at 500/page).
- **Rows**: `GET /resource/{4x4}.json?$limit=N&$offset=M&$where=…&col=value`
  (SoQL). Returns a bare JSON array; **null fields are omitted per row**,
  so the canonical column lists in `endpoints.py` were snapshotted from
  `/api/views/{4x4}.json` (the authoritative column metadata), not from
  row samples. Every paged request pins `$order=:id` (Socrata's stable
  system ordering) — pages without an explicit order are not
  deterministic.
- **Auth**: none required for modest volume (shared throttled pool). An
  application token from **`$CDC_APP_TOKEN`** is sent as `X-App-Token`
  when set and buys a dedicated rate allocation. A *wrong* token
  hard-403s (verified live), so the header is only attached when a token
  is genuinely configured.
- Unknown/retired 4x4 → HTTP 404 → treated as zero rows (estate
  convention), not an error.
- Rate posture: courtesy floor of 0.25 s between requests, 429/5xx retried
  with exponential backoff + full jitter, `Retry-After` honoured. These
  are conservative defaults, **not** a documented Socrata contract —
  verify at dev.socrata.com before a bulk run.

## Datasets (14 registry rows)

| dataset_id | 4x4 | target table | grain / natural key |
|---|---|---|---|
| `cdc_data_catalog` | — | `cdc_data_catalog` | one row per dataset on data.cdc.gov (pk = 4x4 id) |
| `cdc_data_places_county` | `swc5-untb` | `cdc_places_county` | PLACES county measure: `state:fips:measure:valuetype` |
| `cdc_data_places_county_ckd` | `h3ej-a9ec` | `cdc_places_county_ckd` | PLACES 2023 county CKD prevalence (pinned `measureid=KIDNEY`): `state:fips:KIDNEY:valuetype` |
| `cdc_data_provisional_deaths_state` | `9bhg-hcku` | `cdc_provisional_deaths_state` | `group:year:month:state:sex:age_group` |
| `cdc_data_vsrr_drug_overdose` | `xkb8-kh2a` | `cdc_vsrr_drug_overdose` | `state:year:month:indicator` |
| `cdc_data_nchs_leading_causes` | `bi63-dtpu` | `cdc_nchs_leading_causes` | `year:state:cause` |
| `cdc_data_weekly_deaths_by_cause` | `u6jv-9ijr` | `cdc_weekly_deaths_by_cause` | `state:mmwr_year:week:cause:type` |
| `cdc_data_monthly_deaths_select_causes` | `9dzk-mvmi` | `cdc_monthly_deaths_select_causes` | national monthly deaths by select cause: `jurisdiction:year:month` |
| `cdc_data_brfss_prevalence` | `dttw-5yxu` | `cdc_brfss_prevalence` | `year:state:class:topic:question:response:breakout` |
| `cdc_data_chronic_disease_indicators` | `hksd-2xuw` | `cdc_chronic_disease_indicators` | `years:state:question:response:valuetype:strat` |
| `cdc_data_life_expectancy_tract` | `5h56-n989` | `cdc_life_expectancy_tract` | `state:county:census_tract` |
| `cdc_data_drug_poisoning_county` | `rpvx-m2md` | `cdc_drug_poisoning_county` | `fips:year` |
| `cdc_data_heart_disease_mortality_county` | `th8y-thx5` | `cdc_heart_disease_mortality` | `fips:year:sex:race` |
| `cdc_data_fetched_rows` | any | `cdc_data_rows` | generic pull: `{dataset_key}:{row_idx}` |

Assignment-id corrections found during live verification: `pj7m-y5uh` is
*not* the Chronic Disease Indicators (it is "Provisional COVID-19 Deaths:
Distribution of Deaths by Race and Hispanic Origin") — the correct CDI id
is `hksd-2xuw`; `ikd3-hr7f` 404s — the live life-expectancy dataset is
`5h56-n989`.

## Kidney-disease surveillance coverage

CDC runs a Chronic Kidney Disease Surveillance System, but it is a **web
application** (ckd.cdc.gov), **not** a Socrata dataset — a full catalog
sweep (all 1,508 datasets, verified live 2026-07-06) finds no standalone
"CKD Surveillance" 4x4, and the one NCHS↔USRDS end-stage-renal-disease
linkage (`jmgj-74h4`) returns **HTTP 403** (restricted micro-data, not
queryable). CKD on data.cdc.gov is therefore spread across several
datasets; this connector curates the three grains that matter and
documents how to reach each:

- **State indicator over time — already curated.** The premier CKD
  surveillance indicator, *incidence of treated end-stage kidney disease*,
  lives inside the curated **`cdc_data_chronic_disease_indicators`**
  (`hksd-2xuw`), topic `Chronic Kidney Disease` (52 jurisdictions, years
  2019–2022, adjusted rate + number; 416 rows live). Slice it:
  ```bash
  python -m connectors.cdc_data.cli --db ./cdc.db query \
      cdc_data_chronic_disease_indicators \
      --filter topic="Chronic Kidney Disease" --filter locationabbr=US
  ```
- **County prevalence — new curated `cdc_data_places_county_ckd`.**
  PLACES county data carries CKD prevalence under **`measureid = KIDNEY`**
  (measure "Chronic kidney disease among adults aged >=18 years", both
  `CrdPrv` and `AgeAdjPrv` value types). **Live verification caveat:** the
  KIDNEY measure was **dropped from PLACES' 2024 and 2025 county
  releases** — the currently-curated `cdc_data_places_county`
  (`swc5-untb`, 2025 release) has **zero** KIDNEY rows
  (`$where=measureid='KIDNEY'` → empty). The most recent PLACES county
  vintage that still carries it is the **2023 release `h3ej-a9ec`**
  (6,154 KIDNEY rows live: ~3,077 counties × 2 value types, year 2021),
  so it is curated here as its own measure-pinned table
  (`default_params={"measureid":"KIDNEY"}`). This table also feeds the
  `chronic_kidney_disease` section of the `county-health` lookup.
- **National mortality over time — new curated
  `cdc_data_monthly_deaths_select_causes`.** `9dzk-mvmi` (Monthly
  Provisional Counts of Deaths by Select Causes, 2020–2023, national, 45
  rows) carries kidney-disease mortality as the first-class column
  **`nephritis_nephrotic_syndrome`** (Nephritis, nephrotic syndrome and
  nephrosis). Kidney disease *as a leading cause of death* is also already
  sliceable inside curated `cdc_data_nchs_leading_causes`
  (`--filter cause_name="Kidney disease"`).
- **Generic-fetch alternative — Diabetes State Burden Toolkit.**
  `ircd-wk4g` (Diabetes State Burden Toolkit – Health Burden) reports a
  state-level `Chronic Kidney Disease` indicator among Medicare
  beneficiaries with diabetes (1,742 rows). It is **not** promoted to a
  first-class table: the source has genuine duplicate composite keys
  (1,742 rows collapse to 1,404 distinct on every candidate natural key),
  so pull it through the generic escape hatch instead:
  ```bash
  python -m connectors.cdc_data.cli --db ./cdc.db fetch --dataset ircd-wk4g \
      --where "short_text_indicator='Chronic Kidney Disease'" --max-pages 1
  ```

Canonical column names are the live Socrata field names run through the
documented normalizer (`flatten.to_column`): lowercase snake_case, and a
field colliding with an SQL keyword gets a `_field` suffix (live `group`
→ column `group_field`) because the uniform query engine interpolates
whitelisted identifiers bare. Everything is stored TEXT (`geolocation`
and `tags` as JSON); only `row_idx` is INTEGER.

## Usage

```bash
# The registry
python -m connectors.cdc_data.cli datasets

# Sync the FULL catalog (~1.5k datasets, ~4 requests) into a db
python -m connectors.cdc_data.cli --db ./cdc.db discover

# Search the synced catalog locally
python -m connectors.cdc_data.cli --db ./cdc.db catalog-search --q "life expectancy"

# Ingest one page of PLACES county data (paging absorbed; polite default
# cap of 5 pages per call — pass --max-pages explicitly for a bulk run)
python -m connectors.cdc_data.cli --db ./cdc.db fetch --dataset places_county \
    --max-pages 1 --filter stateabbr=AL

# SoQL passthrough for anything fancier
python -m connectors.cdc_data.cli --db ./cdc.db fetch --dataset vsrr_drug_overdose \
    --where "state='CA' AND year='2023'" --max-pages 1

# ANY 4x4 on the domain lands in the generic cdc_data_rows table
python -m connectors.cdc_data.cli --db ./cdc.db fetch --dataset 9yie-6ukv --max-pages 1

# Query the canonical tables through the uniform engine
python -m connectors.cdc_data.cli --db ./cdc.db query cdc_data_places_county \
    --filter measureid=CSMOKING --sort=-data_value --limit 5

# Lookups
python -m connectors.cdc_data.cli --db ./cdc.db lookup-county-health 01073
python -m connectors.cdc_data.cli --db ./cdc.db lookup-cdc-dataset swc5-untb

# Standalone /v1 surface
python -m connectors.cdc_data.cli --db ./cdc.db serve --port 8099
```

`/v1` routes (same contract as every estate connector): `/health`,
`/v1/datasets`, `/v1/query/{dataset}` (filter grammar `field__op`, ops
`eq/ne/gt/gte/lt/lte/like/in/between/isnull/notnull`),
`/v1/query/{dataset}/aggregate?group_by=…`, plus the two lookups above.

## Politeness / paging model

`fetch()` absorbs SoQL `$limit`/`$offset` paging entirely; callers never
see it. Each call is bounded by `max_pages` (default **5**; hard cap
1000) so an accidental "fetch BRFSS" (~2M rows live) cannot hammer the
API — BRFSS additionally defaults to a smaller 500-row page. A result
reports `exhausted=False` when the cap cut the pull short.

## Tests

```bash
cd /home/user/RCM && python3 -m unittest discover -s connectors/cdc_data/tests -t . -v
```

Stdlib `unittest`, no network: an injectable fake opener
(`tests/fakes.py`) mirrors the live shapes — including the catalog's
`limit`+`page` quirk and Socrata's omitted-null rows — and scripted
429/5xx transients exercise the retry paths. The API-server suite runs a
real `ThreadingHTTPServer` on a free port.
