# CMS Coverage connector

The CMS Coverage API (`api.coverage.cms.gov`, the Medicare Coverage
Database) vertical slice: connector → normalized canonical tables →
registry → `/v1/query` + `/v1/lookup` → standalone HTTP surface.
Self-contained and parallel-safe. **Stdlib only** (`urllib` + `json` +
`sqlite3` + `time` + `http.server`); no pandas/pyarrow/duckdb/requests,
no new runtime dependencies. Mirrors `connectors/openfda/` exactly.

```
discover() ─▶ fetch(endpoint, params, cursor) ─▶ normalize ─▶ canonical SQLite tables
                                                                    │
                                                          registry ─▶ /v1/query/{dataset}
                                                                     /v1/lookup/document|contractor
```

## Layout

| File | Role |
|------|------|
| `endpoints.py` | One declarative `EndpointSpec` per source endpoint (path, coverage level, document type, pagination shape, target table). |
| `transport.py` | Throttled JSON transport: 429/`Retry-After`/5xx backoff + jitter, optional `$CMS_COVERAGE_API_KEY`, injectable opener. |
| `connector.py` | `discover()` + `fetch()` — `next_page_token` cursor paging for national/local docs, single-shot fetch for contractors. |
| `flatten.py` | Defensive accessors for sparse records (`dig`, `first`, `coalesce`, unmapped-field audit). |
| `normalize.py` | Per-coverage-level mappers → canonical rows; composed `document_key` / `contractor_key`. |
| `tables.py` | The 2 canonical tables + SQLite store with idempotent upsert. |
| `registry.py` | Declarative `source=cms_coverage` registry rows (one per dataset). |
| `query.py` | The `/v1/query` engine: uniform filter / select / sort / paginate **+ `aggregate()` group-by/count**. |
| `lookup.py` | `/v1/lookup/document/{id}` + `/v1/lookup/contractor/{id}` enriched fan-out + router-agnostic handler map. |
| `api_server.py` | Standalone stdlib `http.server` `/v1` surface (auto-exposes every registry dataset + the lookup handlers) — no router core touched. |
| `cli.py` | `python -m connectors.cms_coverage.cli …` |

## Endpoints ingested

**National coverage:** `national-coverage-ncd` (NCD),
`national-coverage-nca` (NCA), `national-coverage-cal` (CAL),
`national-coverage-medcac` (MEDCAC),
`national-coverage-technology-assessment` (TA).
**Local coverage:** `local-coverage-lcd` (LCD),
`local-coverage-proposed-lcd` (Proposed LCD),
`local-coverage-article` (Article).
**Dimension:** `metadata/contractors` (Medicare Administrative Contractors).

> **Verify live.** The national/local report paths and their query
> params are the best-known mapping and should be confirmed at the CMS
> Medicare Coverage Database developer portal before a bulk run — the
> same "verify live" disclaimer `connectors/openfda` carries for
> `open.fda.gov`. The rate floor in `transport.py` is a courtesy default,
> not a documented contract; the API is public and needs no key.

## Pagination

National and local list endpoints return
`{"result": {"count", "total", "next_page_token", "items"}}` and are paged
by echoing the opaque base64 `next_page_token` back as `page_token` until
it is absent. The contractor endpoint returns everything in one
`{"count", "items"}` call. `fetch()` advances one page and hands back a
JSON-serialisable cursor; `fetch_all()` drives the loop to exhaustion.

## Canonical tables

- `dim_coverage_document` — PK `document_key` = `{document_type}:{document_id}:{document_version}`;
  every national + local document, `coverage_level` in (`national`, `local`),
  with the contractor association for local docs.
- `dim_medicare_contractor` — PK `contractor_key` = `{contractor_id}:{contractor_version}`.

Both keep TEXT columns and the `(source_endpoint, ingested_at)` metadata
convention; every write is an idempotent upsert keyed by the native id.

## Usage

```bash
# Inspect what's wired
python -m connectors.cms_coverage.cli discover
python -m connectors.cms_coverage.cli datasets

# Uniform query — caller never sees the API's native paging
python -m connectors.cms_coverage.cli query cms_coverage_national_ncd \
    --filter chapter=240 --sort -last_updated_sort --limit 20

# Enriched lookups
python -m connectors.cms_coverage.cli lookup-document 169
python -m connectors.cms_coverage.cli lookup-contractor 236

# Serve the /v1 surface (auto-exposes every registry dataset)
python -m connectors.cms_coverage.cli serve --port 8098
#   GET /v1/datasets
#   GET /v1/query/cms_coverage_national_ncd?chapter=240&sort=-last_updated_sort
#   GET /v1/query/cms_coverage_national_ncd/aggregate?group_by=chapter
#   GET /v1/lookup/document/169
#   GET /v1/lookup/contractor/236
```

Set `CMS_COVERAGE_API_KEY` only if a future gated deployment requires it —
the connector degrades gracefully without one.

## Tests

```bash
python3 -m unittest discover -s connectors/cms_coverage/tests -t .
```

Stdlib `unittest` tests cover the transport retry/backoff path, the
`next_page_token` pagination state machine (and the single-shot
contractor fetch), normalization + composed keys, upsert idempotency, the
`/v1/query` engine (incl. identifier-injection rejection and limit
clamping), and an end-to-end run against a live `ThreadingHTTPServer`.

## Contract conformance

- **Connector interface** — `discover()` / `fetch(endpoint, params,
  cursor)` with pagination, rate-limit, retries internal. ✔
- **Registry** — every dataset is one declarative row
  `{dataset_id, connector, base_url, endpoint, default_params,
  refresh_cadence, join_keys, target_table, source, source_filter,
  date_field}`; `/v1/query/{dataset}` auto-exposes anything in it. ✔
- **API contract** — `/v1/query` gives uniform filter/select/sort/
  paginate + aggregate; the API's native paging is absorbed at ingest. ✔
