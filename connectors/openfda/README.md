# openFDA PEDesk connector

The full openFDA (`api.fda.gov`) vertical slice for PEDesk: connector →
raw landing → normalized canonical tables → registry → `/v1/query` +
`/v1/lookup` → data-quality tests. Self-contained, resumable, and
parallel-safe. **Stdlib only** (`urllib` + `json` + `sqlite3` + `time`);
no pandas/pyarrow/duckdb, no new runtime dependencies.

```
discover() ─▶ fetch(endpoint, params, cursor) ─▶ raw lake (parquet|jsonl)
                                                      │
                                                normalize ─▶ canonical SQLite tables
                                                      │              │
                                              crosswalk (NDC→RxCUI,   │
                                              device product_code)    ▼
                                                            registry ─▶ /v1/query/{dataset}
                                                                       /v1/lookup/drug|device
```

## Layout

| File | Role |
|------|------|
| `endpoints.py` | One declarative `EndpointSpec` per source endpoint (id field, date field, count field, target table). |
| `transport.py` | Throttled JSON transport: 429/`Retry-After`/5xx backoff + jitter, `$OPENFDA_API_KEY`, injectable opener. |
| `connector.py` | `discover()` + `fetch()` — date-window chunking, skip-cap handling, partition fallback, `count=` aggregation. |
| `flatten.py` | Defensive accessors for nested/sparse records (`dig`, `first`, `flatten`, unmapped-field audit). |
| `normalize.py` | Per-endpoint mappers → canonical rows; deterministic company rollup; `ndc11`. |
| `tables.py` | The 8 canonical tables + 3 crosswalk/rollup helpers; SQLite store with idempotent upsert. |
| `crosswalk.py` | NDC→RxCUI (wireable, deferred when no RxNorm) + device `product_code` dimension + company persistence. |
| `registry.py` | Declarative `source=openfda` registry rows (one per dataset). |
| `query.py` | The `/v1/query` engine: uniform filter / select / sort / paginate **+ `aggregate()` group-by/count** (cheap market maps). |
| `lookup.py` | `/v1/lookup/drug/{ndc}` + `/v1/lookup/device/{product_code}` enriched fan-out + router-agnostic handler map. |
| `market_map.py` | Diligence aggregates: clearance timeline + competitive entry by `product_code`, MAUDE intensity (per-UDI-normalized), drug risk by NDC. |
| `rxnorm_adapter.py` | Concrete NDC→RxCUI resolver backed by RxNav (injectable opener, cached, graceful) — plugs into the crosswalk seam. |
| `dq.py` | DQ checks: count reconciliation, null-key, NDC→RxCUI coverage. |
| `state.py` | `STATE.md` (resume), `PROGRESS.md` (append-only), `DECISIONS.md`. |
| `raw_store.py` | Raw landing zone (parquet when `pyarrow` present, else JSONL). |
| `pipeline.py` | Orchestrator: backfill + nightly incremental, never-block-on-one-endpoint, end-of-run retry. |
| `api_server.py` | Standalone stdlib `http.server` `/v1` surface (auto-exposes every registry dataset + the lookup handlers) — no router core touched. |
| `cli.py` | `python -m connectors.openfda.cli …` |

## Endpoints ingested

**Drug:** `drug/ndc`, `drug/label`, `drug/event` (FAERS), `drug/enforcement`
(recalls), `drug/drugsfda`.
**Device:** `device/classification`, `device/510k`, `device/pma`,
`device/event` (MAUDE), `device/recall` + `device/enforcement`,
`device/udi` (GUDID).
Food and all other endpoints are out of scope.

## Canonical tables

`dim_drug_product`, `fact_drug_adverse_event`, `fact_drug_recall`,
`dim_drug_approval`, `dim_device`, `fact_device_adverse_event`,
`fact_device_recall`, `dim_device_udi`
— plus `xwalk_ndc_rxcui`, `xwalk_device_product_code`, `dim_company`.

Diligence signals preserved: device clearance timeline by `product_code`
(`lookup_device → clearance_timeline`), MAUDE counts by `product_code`
normalized by UDI units (`adverse_events.per_udi_unit`), FAERS + recalls
keyed to NDC (`lookup_drug`), drugsfda approval moat (`dim_drug_approval`).

## Usage

```bash
# Inspect what's wired
python -m connectors.openfda.cli discover
python -m connectors.openfda.cli registry

# Full historical backfill (date-window chunked) into ./data
python -m connectors.openfda.cli --root ./data backfill
python -m connectors.openfda.cli --root ./data backfill --endpoint device_510k

# Nightly incremental (recent date window only, nightly-cadence endpoints)
python -m connectors.openfda.cli --root ./data incremental --lookback-days 7

# Uniform query — caller never sees openFDA paging
python -m connectors.openfda.cli --root ./data query openfda_device_510k \
    --filter product_code=DXY --sort -decision_date --limit 20

# Uniform aggregate (cheap market map over canonical tables)
python -m connectors.openfda.cli --root ./data aggregate openfda_device_510k \
    --group-by product_code --limit 20

# Diligence market maps
python -m connectors.openfda.cli --root ./data market-map clearance_timeline --product-code DXY
python -m connectors.openfda.cli --root ./data market-map competitive_entry
python -m connectors.openfda.cli --root ./data market-map maude_intensity
python -m connectors.openfda.cli --root ./data market-map drug_risk

# Enriched lookups
python -m connectors.openfda.cli --root ./data lookup-drug 0002-1200
python -m connectors.openfda.cli --root ./data lookup-device DXY

# Resolve NDC->RxCUI live via RxNav during a backfill (needs egress)
python -m connectors.openfda.cli --root ./data backfill --resolve-rxnorm

# Data-quality suite (+ live count reconciliation)
python -m connectors.openfda.cli --root ./data dq --reconcile

# Serve the /v1 surface (auto-exposes every registry dataset)
python -m connectors.openfda.cli --root ./data serve --port 8099
#   GET /v1/datasets
#   GET /v1/query/openfda_device_510k?product_code=DXY&sort=-decision_date&limit=20
#   GET /v1/query/openfda_device_510k/aggregate?group_by=product_code
#   GET /v1/lookup/drug/0002-1200
#   GET /v1/lookup/device/DXY
```

Set `OPENFDA_API_KEY` to raise the daily cap (optional — the connector
degrades gracefully without one).

## Resumability

`STATE.md` holds a machine-readable cursor + counters per endpoint. Every
`fetch` step persists it, so a hard kill resumes from the last window.
Re-running is idempotent (upsert keyed by native id). `PROGRESS.md` is an
append-only event log; `DECISIONS.md` records every judgement call.

## Tests

```bash
python -m unittest discover -s connectors/openfda/tests -t .
```

33 stdlib `unittest` tests cover the transport retry/backoff path, the
full pagination state machine (windowing, adaptive shrink, skip-cap →
partition fallback), normalization + company rollup, upsert idempotency,
the `/v1/query` engine (incl. identifier-injection rejection), both lookup
handlers, the DQ checks, and an end-to-end resumable pipeline run against
an in-memory fake openFDA server.

## Contract conformance

- **Connector interface** — `discover()` / `fetch(endpoint, params,
  cursor) -> (rows, next_cursor)` with pagination, rate-limit, retries
  internal. ✔
- **Registry** — every dataset is one declarative row
  `{dataset_id, connector, base_url, endpoint, default_params,
  refresh_cadence, join_keys, target_table}`; `/v1/query/{dataset}`
  auto-exposes anything in it. ✔
- **Crosswalk** — appends the device `product_code` dimension and the
  NDC→RxCUI table; does not rewrite NPI/NUCC/FIPS/CPT/MS-DRG/NDC. ✔
- **API contract** — `/v1/query` gives uniform filter/select/sort/
  paginate; openFDA's native paging is absorbed at ingest. ✔

See `DECISIONS.md` for the gotchas (skip cap, rate limits, parquet
degradation, deferred RxCUI, live-verify caveat) and how each is handled.
