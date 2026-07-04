# NPI Registry (NPPES) connector

A self-contained vertical slice over the **NPPES NPI Registry API v2.1**
(`npiregistry.cms.hhs.gov/api/`) — the US healthcare-provider registry.
Seeded-search connector → normalized canonical tables → registry →
`/v1/query` + `/v1/lookup` + `/v1/validate`. **Stdlib only** (`urllib` +
`json` + `sqlite3` + `time` + `http.server`); no third-party deps, no
API key (the registry is public).

```
discover() ─▶ fetch(spec, seed, cursor) ─▶ raw NPI records
                                                 │
                                           normalize ─▶ canonical SQLite tables
                                                 │              │
                                                 ▼              ▼
                                          registry ─▶ /v1/query/{dataset}
                                                     /v1/lookup/provider|taxonomy
                                                     /v1/validate/npi
```

## The API in one line

NPPES is a **single search endpoint** driven by query params (`state`,
`taxonomy_description`, `organization_name`, `first_name`, …). It returns
at most 200 results per request (`limit`) and `skip` maxes at 1000, so a
single query yields at most **1,200** results. There is no bulk crawl —
you ask a question and page the answer. This connector models ingest as
**seeded searches**: a spec carries seed param dicts, and `fetch` pages
each seed by `skip` (step 200) up to the 1,200 ceiling.

## Layout

| File | Role |
|------|------|
| `endpoints.py` | Seeded-search `EndpointSpec`s (individual / organization) with default seeds. |
| `transport.py` | Throttled JSON transport: 429/`Retry-After`/5xx backoff + jitter, always sends `version=2.1`, injectable opener. |
| `connector.py` | `discover()` + `fetch()` — runs a seed, pages by `skip`, stops on short page or the 1,200 cap. |
| `flatten.py` | Defensive accessors for nested/sparse records (`dig`, `first`, `first_where`, `coalesce`). |
| `normalize.py` | Raw NPI record → `dim_provider` (flattened primary address + taxonomy) + `fact_provider_taxonomy` + `fact_provider_address`. |
| `validate.py` | NPI check-digit validation (Luhn over the `80840` prefix), no I/O. |
| `tables.py` | The 3 canonical tables; SQLite store with idempotent upsert keyed by native id. |
| `registry.py` | Declarative `source=npi_registry` registry rows (one per dataset). |
| `query.py` | The `/v1/query` engine: uniform filter/select/sort/paginate **+ `aggregate()`**. |
| `lookup.py` | `/v1/lookup/provider/{npi}` + `/v1/lookup/taxonomy/{code}` fan-out + `/v1/validate/npi/{npi}`, router-agnostic handler map. |
| `api_server.py` | Standalone stdlib `http.server` `/v1` surface (auto-exposes every registry dataset + the handlers). |
| `cli.py` | `python -m connectors.npi_registry.cli …` |

## Canonical tables

- **`dim_provider`** PK `npi` — one row per provider, with the primary
  practice (LOCATION) address and primary taxonomy flattened on.
- **`fact_provider_taxonomy`** PK `taxonomy_key` (`{npi}:{code}`) — one
  row per taxonomy.
- **`fact_provider_address`** PK `address_key` (`{npi}:{address_purpose}`)
  — one row per address.

Every row carries the `_META` columns `(source_endpoint, ingested_at)`.

## Query datasets

`npi_provider` → `dim_provider`, `npi_provider_taxonomy` →
`fact_provider_taxonomy`, `npi_provider_address` →
`fact_provider_address`. Each registry row carries the shared contract
fields (`dataset_id, connector, base_url, endpoint, default_params,
refresh_cadence, join_keys, target_table, source, source_filter,
date_field`) so a top-level aggregator ingests every connector
uniformly.

## Usage

```bash
# Inspect what's wired
python -m connectors.npi_registry.cli discover
python -m connectors.npi_registry.cli datasets

# Ingest the default seeded crawls into ./data (needs egress)
python -m connectors.npi_registry.cli --root ./data ingest
python -m connectors.npi_registry.cli --root ./data ingest --endpoint provider_individual

# Uniform query — caller never sees NPPES paging
python -m connectors.npi_registry.cli --root ./data query npi_provider \
    --filter state=MD --filter primary_taxonomy_code=207RC0000X \
    --sort -last_updated --limit 20

# Uniform aggregate (cheap market map over canonical tables)
python -m connectors.npi_registry.cli --root ./data aggregate npi_provider \
    --group-by state --limit 20

# Enriched lookups
python -m connectors.npi_registry.cli --root ./data lookup-provider 1234567893
python -m connectors.npi_registry.cli --root ./data lookup-taxonomy 207RC0000X

# Instant NPI check-digit validation (no API call)
python -m connectors.npi_registry.cli validate 1234567893

# Serve the /v1 surface (auto-exposes every registry dataset)
python -m connectors.npi_registry.cli --root ./data serve --port 8098
#   GET /v1/datasets
#   GET /v1/query/npi_provider?state=MD&sort=-last_updated&limit=20
#   GET /v1/query/npi_provider/aggregate?group_by=state
#   GET /v1/lookup/provider/1234567893
#   GET /v1/lookup/taxonomy/207RC0000X
#   GET /v1/validate/npi/1234567893
```

## Tests

```bash
python -m unittest discover -s connectors/npi_registry/tests -t .
```

39 stdlib `unittest` tests cover the transport retry/backoff path, the
seed pager (short-page stop and the 1,200 cap), normalization of both
individual and organization records into the three canonical tables with
composed keys, upsert idempotency, the `/v1/query` engine (equality /
`__like` / `__in` / aggregate / unknown-field rejection / limit clamp),
NPI Luhn validation, and an end-to-end run of the `/v1` surface against a
live `ThreadingHTTPServer`. No test touches the network.
