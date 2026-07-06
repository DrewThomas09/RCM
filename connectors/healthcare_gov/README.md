# healthcare_gov connector — data.healthcare.gov (DKAN, Health Insurance Marketplace)

Self-contained, **stdlib-only** connector for
[data.healthcare.gov](https://data.healthcare.gov), CMS's DKAN 2 open-data
catalog for the federal Health Insurance Marketplace. Mirrors the estate
contract (`endpoints → transport → connector → normalize → tables →
registry → query/lookup → api_server/cli`) established by
`connectors/cms_coverage`.

## API surface (verified live, July 2026)

| Purpose | Endpoint |
|---------|----------|
| Catalog (all 337 datasets, one call, no paging) | `GET /api/1/metastore/schemas/dataset/items` |
| Datastore rows | `GET /api/1/datastore/query/{dataset_id}/0?limit=&offset=&rowIds=true` |

Datastore facts probed during the build:

- **`limit` hard cap is 500** — `limit=501` answers HTTP 400
  ("JSON Schema validation failed"). The connector never asks for more.
- `rowIds=true` adds a 1-based `record_number` to every row; the generic
  rows table uses it as a stable row id.
- Equality filters ride as `conditions[i][property]` / `conditions[i][value]`
  query params (the connector compiles `{"statecode": "TX"}` into these).
- Datasets whose distribution was never imported into the datastore (e.g.
  every **QHP Landscape** file — they ship as ZIPs) answer HTTP 400
  "No datastore storage found …"; the transport surfaces that body in the
  raised error so "not queryable" is distinguishable from "bad query".
- No API key, no documented rate limit. The transport keeps a polite
  0.25 s inter-request floor and retries 429/5xx with exponential backoff +
  jitter (honouring `Retry-After`). Courtesy defaults, not a contract —
  verify before bulk runs.

## Datasets

| dataset_id | table | what it is |
|------------|-------|------------|
| `healthcare_gov_catalog` | `healthcare_gov_catalog` | every catalog dataset's metadata (id, title, periodicity, modified, distribution URL/format, contacts) |
| `healthcare_gov_plan_attributes_py2026` | `healthcare_gov_plan_attributes` | Plan Attributes PUF PY2026 — one row per plan variant, 151 live-snapshotted columns (~22k rows) |
| `healthcare_gov_benefits_cost_sharing_py2026` | `healthcare_gov_benefits_cost_sharing` | Benefits & Cost Sharing PUF PY2026 — plan × benefit cost-sharing (~1.46M rows) |
| `healthcare_gov_rate_puf_py2026` | `healthcare_gov_rates` | Rate PUF PY2026 — premium per plan × rating area × tobacco × age (~2.24M rows) |
| `healthcare_gov_quality_puf_py2026` | `healthcare_gov_plan_quality` | Quality PUF PY2026 — star ratings per plan (~4.3k rows) |
| `healthcare_gov_service_area_puf_py2026` | `healthcare_gov_service_areas` | Service Area PUF PY2026 — service area × county (FIPS) coverage (~8.8k rows) |
| `healthcare_gov_fetched_rows` | `healthcare_gov_rows` | generic on-demand rows for ANY catalog dataset, keyed `{dataset_key}:{row_idx}` |

### How the curated set was selected

The assignment's wishlist was checked against the **live** catalog:

- *QHP Landscape (Individual/SHOP/dental)* — present in the catalog but
  **ZIP-download-only**, no datastore storage for any plan year
  (PY2014–PY2026 all probed) → not API-queryable; still reachable via the
  catalog table's `download_url`.
- *Rate Review / rate filing* — no such dataset exists on this catalog;
  the **Rate PUF** (plan-level premiums) is the closest and is curated.
- *Marketplace enrollment PUF* — not present on this catalog.

So the curated picks are the latest-plan-year (PY2026) PUFs that are
actually datastore-queryable: Plan Attributes, Benefits & Cost Sharing,
Rate, Quality, Service Area. Column tuples in `tables.py` are snapshots
of live samples (DKAN lower-cases the PUF CSV headers; the catalog's
camelCase DCAT keys are snake_cased by `normalize._snake`). Natural
upsert keys were verified unique on live 500-row samples; each composed
key is prefixed with the endpoint key so future plan years can share the
tables without collisions.

## Paging & politeness

One `fetch`/`refresh` call pulls at most `max_pages` pages (default **5**
× 500 rows) — a deliberate cap so an accidental full pull of the 2.2M-row
Rate PUF can't hammer the API. The result carries `next_offset` /
`exhausted`; resume with `--offset` (CLI) or `start_offset=` (API), or
pass a larger `max_pages` deliberately.

## Usage

```bash
# The registry
python -m connectors.healthcare_gov.cli datasets

# Sync the full catalog (337 datasets, one call)
python -m connectors.healthcare_gov.cli --db ./hc.db discover
python -m connectors.healthcare_gov.cli --db ./hc.db catalog-search --q "Rate PUF"

# Curated ingest (paged, capped at --max-pages)
python -m connectors.healthcare_gov.cli --db ./hc.db fetch \
    --dataset plan_attributes_py2026 --filter statecode=TX --max-pages 2

# ANY catalog dataset by DKAN id → generic rows table
python -m connectors.healthcare_gov.cli --db ./hc.db fetch \
    --dataset e4rr-zk4i --max-pages 1

# Query / aggregate the local canonical tables
python -m connectors.healthcare_gov.cli --db ./hc.db query \
    healthcare_gov_plan_attributes_py2026 --filter metallevel=Silver --limit 5
python -m connectors.healthcare_gov.cli --db ./hc.db aggregate \
    healthcare_gov_rate_puf_py2026 --group-by statecode

# Lookups + the /v1 surface
python -m connectors.healthcare_gov.cli --db ./hc.db lookup-plan 21989AK0030001
python -m connectors.healthcare_gov.cli --db ./hc.db lookup-county 48201
python -m connectors.healthcare_gov.cli --db ./hc.db serve --port 8099
```

### `/v1` routes (standalone server)

```
/health
/v1/datasets
/v1/query/{dataset}?<filters>&select=&sort=&limit=&offset=
/v1/query/{dataset}/aggregate?group_by=a,b&<filters>&limit=
/v1/lookup/marketplace-plan/{plan_id}[?limit=N]   # std component or variant id
/v1/lookup/county-plans/{fips}[?limit=N]          # 5-digit county FIPS
```

## Notes & deviations

- `healthcare_gov_rows.row_idx` is stored TEXT like every other column
  (the estate's single-type-model `TableDef` makes all columns TEXT);
  it holds DKAN's `record_number` when available, else the absolute
  fetch offset.
- The quality PUF has no `importdate`/`businessyear` columns, so its
  registry `date_field` is empty.
- Tests are network-free (fake opener fixtures mirroring the live
  shapes above). Run:

```bash
cd /home/user/RCM && python3 -m unittest discover -s connectors/healthcare_gov/tests -t . -v
```
