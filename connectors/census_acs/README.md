# Census ACS connector

The US Census American Community Survey 5-year API (`api.census.gov`)
vertical slice: connector → normalized canonical tables → registry →
`/v1/query` + `/v1/lookup` → standalone HTTP surface. Self-contained and
parallel-safe. **Stdlib only** (`urllib` + `json` + `sqlite3` + `time` +
`http.server`); no pandas/pyarrow/duckdb/requests, no new runtime
dependencies. Mirrors `connectors/cms_coverage/` exactly.

```
discover() ─▶ fetch(profile, year, state) ─▶ normalize (join B+S tables) ─▶ canonical SQLite tables
                                                                                  │
                                                                        registry ─▶ /v1/query/{dataset}
                                                                                   /v1/lookup/county-demographics|state-demographics
```

## API key — REQUIRED for data pulls

> **Verified live 2026-07-06:** `api.census.gov` now requires an API key
> on **every** data request — keyless queries 302-redirect to
> `/data/missing_key.html` regardless of volume. (The old "small
> keyless volumes per IP per day" allowance is gone; only the metadata
> endpoints — `variables.json`, `geography.json` — remain keyless.)
> Keys are free: <https://api.census.gov/data/key_signup.html>. Export
> it as `CENSUS_API_KEY`; the transport merges it into every URL and
> raises an actionable error naming the env var when it is absent or
> rejected. Fetch defaults stay modest either way (two requests per
> profile refresh, 0.5 s inter-request floor).

## Layout

| File | Role |
|------|------|
| `endpoints.py` | One declarative `EndpointSpec` per geography profile (county / state / CBSA) + the **declared** variable→column mappings. |
| `transport.py` | Throttled array-of-arrays transport: 429/`Retry-After`/5xx backoff + jitter, `$CENSUS_API_KEY` handling with a clear missing-key error, HTTP 204 → empty, injectable opener. |
| `connector.py` | `discover()` + `fetch()` (detail **and** subject GETs per profile) + `refresh()` (fetch → normalize → upsert). |
| `normalize.py` | The array-of-arrays → dict core (`rows_from_table`), the detail⋈subject geo join, jam-value → NULL, composed natural keys. |
| `tables.py` | The 3 canonical tables + SQLite store with idempotent upsert. |
| `registry.py` | Declarative `source=census_acs` registry rows (one per dataset). |
| `query.py` | The `/v1/query` engine: uniform filter / select / sort / paginate **+ `aggregate()` group-by/count**. |
| `lookup.py` | `/v1/lookup/county-demographics/{fips5}` + `/v1/lookup/state-demographics/{fips2}` enriched fan-out + router-agnostic handler map. |
| `api_server.py` | Standalone stdlib `http.server` `/v1` surface (auto-exposes every registry dataset + the lookup handlers) — no router core touched. |
| `cli.py` | `python -m connectors.census_acs.cli …` |

## Datasets

| dataset_id | for= | table | natural key |
|------------|------|-------|-------------|
| `census_acs_county_profile` | `county:*` (`in=state:XX` optional) | `census_acs_county` | `{fips5}:{year}` |
| `census_acs_state_profile` | `state:*` (or `state:XX`) | `census_acs_state` | `{state_fips}:{year}` |
| `census_acs_cbsa_profile` | `metropolitan statistical area/micropolitan statistical area:*` | `census_acs_cbsa` | `{cbsa_code}:{year}` |

Every profile is built from **two calls per vintage** — the detail
dataset (`/data/{year}/acs/acs5`, B-tables) and the subject dataset
(`/data/{year}/acs/acs5/subject`, S-tables) — joined on the geography
columns. The ACS API is unpaged (one call returns every geography row),
so there is no native paging to absorb; the two-call join is the
absorbed complexity instead. Default vintage: **2023** (`--year` to
override; refresh cadence is annual — new vintages land each December).

### Variables (verified live for the 2023 vintage, 2026-07-06)

| variable | column | notes |
|----------|--------|-------|
| `B01001_001E` | `total_pop` | total population |
| `B01002_001E` | `median_age` | |
| `B19013_001E` | `median_hh_income` | 2023 inflation-adjusted dollars |
| `B17001_002E` | `poverty_count` | persons below poverty level |
| `S0101_C01_030E` | `pop_65_plus` | count, 65 years and over (replaces the twelve-variable `B01001_020E..049E` sum — one verified subject cell, same number) |
| `S2701_C05_001E` | `uninsured_rate` | **percent** uninsured, civilian noninstitutionalized |

Verification used the keyless metadata endpoints
(`…/acs/acs5/variables/{id}.json`, `…/acs/acs5/subject/variables/{id}.json`);
the CBSA geography string was confirmed present in both datasets'
`geography.json`. ACS *jam values* (negative sentinels like
`-666666666` = median not computable) are normalized to NULL at ingest,
so numeric casts downstream never see them. Estimates are stored TEXT
(the estate's one-type model); cast explicitly when comparing.

## Usage

```bash
# Inspect what's wired
python -m connectors.census_acs.cli datasets
python -m connectors.census_acs.cli discover

# Ingest (needs $CENSUS_API_KEY) — Texas counties, then serve
export CENSUS_API_KEY=...
python -m connectors.census_acs.cli --db ./census.db fetch \
    --dataset county_profile --year 2023 --state 48
python -m connectors.census_acs.cli --db ./census.db fetch --dataset state_profile
python -m connectors.census_acs.cli --db ./census.db fetch --dataset cbsa_profile

# Uniform query — caller never sees the Census URL grammar
python -m connectors.census_acs.cli --db ./census.db query census_acs_county_profile \
    --filter state_fips=48 --sort -total_pop --limit 10

# Enriched lookups
python -m connectors.census_acs.cli --db ./census.db lookup-county 48201
python -m connectors.census_acs.cli --db ./census.db lookup-state 48

# Serve the /v1 surface (auto-exposes every registry dataset)
python -m connectors.census_acs.cli --db ./census.db serve --port 8099
#   GET /v1/datasets
#   GET /v1/query/census_acs_county_profile?state_fips=48&sort=-total_pop
#   GET /v1/query/census_acs_county_profile/aggregate?group_by=state_fips
#   GET /v1/lookup/county-demographics/48201
#   GET /v1/lookup/state-demographics/48
```

`--db` defaults to `:memory:` (fetch still prints counts — handy for a
smoke test); point it at a file to persist between commands.

## Tests

```bash
python3 -m unittest discover -s connectors/census_acs/tests -t .
```

Stdlib `unittest` tests cover the transport retry/backoff path (incl.
the missing-key HTML/302 detection and 204-empty), the two-call
fetch + state narrowing + CBSA geography encoding, the array-of-arrays
normalize core (declared renames, jam values, detail⋈subject join),
upsert idempotency across vintages, the `/v1/query` engine (incl.
identifier-injection rejection and limit clamping), and an end-to-end
run against a live `ThreadingHTTPServer`. Tests never touch the network.

## Contract conformance

- **Connector interface** — `discover()` / `fetch(endpoint, params)` /
  `refresh(store, endpoint)`; the two-call join and key handling are
  internal. ✔
- **Registry** — every dataset is one declarative row
  `{dataset_id, connector, base_url, endpoint, default_params,
  refresh_cadence, join_keys, target_table, source, source_filter,
  date_field}`; `/v1/query/{dataset}` auto-exposes anything in it. ✔
- **API contract** — `/v1/query` gives uniform filter/select/sort/
  paginate + aggregate; the Census URL grammar is absorbed at ingest. ✔
