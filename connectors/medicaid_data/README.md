# medicaid_data — data.medicaid.gov (DKAN) connector

Self-contained, **stdlib-only** connector for
[data.medicaid.gov](https://data.medicaid.gov), CMS's Medicaid open-data
portal (a DKAN instance, same platform family as provider-data). It
connects the **entire 541-dataset catalog** three ways:

1. **`catalog`** — the full DKAN metastore synced into
   `medicaid_data_catalog` (identifier, title, description, themes,
   keywords, periodicity, modified, distribution CSV URL, and a
   ready-to-fetch `api_url` per dataset).
2. **Curated flagships** — 13 first-class datasets with canonical tables
   whose columns were snapshotted from **live API samples (2026-07-06)**:
   NADAC (2026 + 2025), SDUD (2025 + 2024), NADAC Comparison, ACA Federal
   Upper Limits, Drug Rebate Program products, monthly + new-adult-group +
   managed-care enrollment, 2024 managed-care programs, financial
   management, and quality measures.
3. **`fetched_rows`** — a generic escape hatch: ANY catalog UUID can be
   pulled on demand into `medicaid_data_rows` (row JSON keyed by
   `{dataset_key}:{row_idx}`) and queried through the same `/v1` engine.

## API facts (verified live 2026-07-06)

| Surface | Route | Shape |
|---|---|---|
| Catalog | `GET /api/1/metastore/schemas/dataset/items` | bare JSON **array** of 541 DCAT items |
| Datastore | `GET /api/1/datastore/query/{uuid}/0?limit=N&offset=M` | `{"results": [...], "count": TOTAL, "schema": {...}, "query": {...}}` |
| Filters | `conditions[i][property/value/operator]` query params | server-side equality pushdown |
| Errors | unknown UUID → HTTP 404 + message | transport folds to empty envelope |

Column names arrive already lower-snake-cased from DKAN (including its
hash-suffixed names for long CSV headers, e.g.
`populations_enrolled_..._0778`) and are used **verbatim** in
`tables.py` — no renaming layer to drift. Past-the-end offsets return an
empty `results` list, which the pager treats as exhaustion.

No API key. No published rate limit — `transport.py` keeps a polite
0.25 s inter-request floor and retries 429/5xx with exponential backoff +
full jitter (honouring `Retry-After`). These are courtesy defaults, not a
documented contract; verify before a bulk run.

## The shared-table pattern (NADAC/SDUD year files)

CMS publishes NADAC and SDUD as **one dataset per year, each with its own
UUID but an identical schema**. Registering every year as a separate
table would fragment queries, so all years land in one canonical table
each (`medicaid_nadac`, `medicaid_sdud`) with:

- `source_endpoint` = the dataset key (`nadac_2026`, `sdud_2024`, …) —
  each registry row's `source_filter` pins `/v1/query/{dataset}` to
  exactly its year slice;
- composed upsert keys **prefixed with the dataset key**
  (`nadac_2026:{ndc}:{effective_date}:{as_of_date}`) so slices can never
  collide and re-ingests stay idempotent.

NADAC note: weekly files re-list an `(ndc, effective_date)` pair in every
snapshot where the rate is still current, so `as_of_date` is part of the
key — without it, upserts would silently collapse weekly snapshots.

## Datasets (15 registry rows)

| dataset_id (`medicaid_data_` +) | table | ~rows live | key fields |
|---|---|---|---|
| `catalog` | `medicaid_data_catalog` | 541 | identifier |
| `nadac_2026` / `nadac_2025` | `medicaid_nadac` (shared) | 787k / 1.6M | ndc, effective_date, as_of_date |
| `sdud_2025` / `sdud_2024` | `medicaid_sdud` (shared) | 5.3M / 5.3M | utilization_type, state, ndc, year, quarter |
| `nadac_comparison` | `medicaid_nadac_comparison` | 3.4M | ndc, effective/start/end dates, reason |
| `aca_federal_upper_limits` | `medicaid_aca_ful` | 2.2M | ndc, year, month |
| `drug_products_rebate` | `medicaid_rebate_drug_product` | 2.0M | ndc, year, quarter |
| `enrollment_monthly` | `medicaid_enrollment_monthly` | 11k | state, reporting_period, P/U |
| `enrollment_new_adult_group` | `medicaid_enrollment_new_adult_group` | 8k | state, period, update stamps |
| `mc_enrollment_summary` | `medicaid_mc_enrollment_summary` | 513 | state, year |
| `managed_care_by_state_2024` | `medicaid_managed_care_program` | 183 | state, program, type |
| `financial_management_data` | `medicaid_financial_management` | 16k | state, year, program, category |
| `quality_measures_2024` | `medicaid_quality_measure` | 11k | state, year, program, measure, … |
| `fetched_rows` | `medicaid_data_rows` | on demand | dataset_key, row_idx |

Deliberately **not** curated: the date-versioned "Pricing Comparison for
Blood Disorder Treatments" snapshots (a new UUID every 6 months, 48 rows
each, footnote-suffixed money columns) — reachable any time via
`fetch --dataset <uuid>` into `medicaid_data_rows`. New NADAC/SDUD years
get new UUIDs too; promote them with a one-line `endpoints.py` addition
when published.

## Paging guard

Several curated datasets are **millions of rows**. `fetch_all()`/CLI
`fetch` default to `max_pages=5` (× 500 rows/page); a full drain must be
an explicit `--max-pages` choice. Equality `--filter col=value` pairs are
pushed down to DKAN as `conditions`, so a filtered ingest (one state, one
NDC) doesn't pull the whole year file.

## Usage

```bash
# The registry (all 15 datasets)
python -m connectors.medicaid_data.cli datasets

# Sync the full catalog (~541 rows, one HTTP call)
python -m connectors.medicaid_data.cli --db ./medicaid.db discover

# Search the synced catalog
python -m connectors.medicaid_data.cli --db ./medicaid.db catalog-search --q "managed care"

# Ingest one page of NADAC 2026 (500 rows), then a filtered SDUD slice
python -m connectors.medicaid_data.cli --db ./medicaid.db fetch --dataset nadac_2026 --max-pages 1
python -m connectors.medicaid_data.cli --db ./medicaid.db fetch --dataset sdud_2025 --filter state=AK --max-pages 2

# Any catalog UUID → generic rows
python -m connectors.medicaid_data.cli --db ./medicaid.db fetch --dataset 190326eb-878c-4aaf-ae2b-1082bf34ff70 --max-pages 1

# Query + serve the /v1 surface
python -m connectors.medicaid_data.cli --db ./medicaid.db query medicaid_data_nadac_2026 --filter ndc=24385005452 --sort -as_of_date
python -m connectors.medicaid_data.cli --db ./medicaid.db serve --port 8099
```

### `/v1` routes (standalone server)

```
/health
/v1/datasets
/v1/query/{dataset}?<filters>&select=&sort=&limit=&offset=
/v1/query/{dataset}/aggregate?group_by=a,b&<filters>&limit=
/v1/lookup/ndc-cost/{ndc}              latest NADAC costs + rate changes + rebate status
/v1/lookup/state-drug/{state}          SDUD profile: top drugs by Medicaid spend
/v1/lookup/medicaid-dataset/{uuid}     catalog row + curated/generic connection status
```

Filter grammar (uniform across the estate): `field=v` equality or
`field__op=v` with `eq/ne/gt/gte/lt/lte/like/in/between/isnull/notnull`;
sort `field` / `-field`.

## Tests

```bash
cd /home/user/RCM
python3 -m unittest discover -s connectors/medicaid_data/tests -t . -v
```

Stdlib `unittest`, **no network**: `tests/fakes.py` is an in-memory DKAN
fake (catalog array + limit/offset datastore paging + conditions
pushdown + scripted 429/5xx) whose fixtures are hand-trimmed copies of
real API rows. The API-server suite exercises the real HTTP path on a
free port.
