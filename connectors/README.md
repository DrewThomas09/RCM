# RCM connectors — public healthcare API estate

A set of self-contained, **stdlib-only** connectors that ingest public
healthcare APIs into canonical SQLite tables and re-expose them behind one
uniform `/v1` query surface. Adding a data source is a new connector package
here; nothing else in RCM-MC has to change.

Every connector is an independent vertical slice built to the **same
contract** (modelled on `openfda/`):

```
endpoints ─▶ transport ─▶ connector.discover()/fetch() ─▶ raw pages
                                                              │
                                                        normalize ─▶ canonical SQLite tables
                                                              │              │
                                                          registry ─▶ /v1/query/{dataset} + /aggregate
                                                                        /v1/lookup/…
```

## Connectors

| Connector | Package | API | Base URL | Datasets |
|-----------|---------|-----|----------|----------|
| openFDA | `connectors/openfda` | FDA drug + device (NDC, labels, FAERS, recalls, 510(k), PMA, MAUDE, UDI, …) | `api.fda.gov` | 12 |
| CMS Coverage | `connectors/cms_coverage` | Medicare Coverage Database — NCD/NCA/CAL/MEDCAC/TA, LCD/Proposed-LCD/Article, MAC contractors | `api.coverage.cms.gov` | 9 |
| NPI Registry | `connectors/npi_registry` | NPPES v2.1 — provider search/lookup, taxonomies, addresses, NPI validation | `npiregistry.cms.hhs.gov/api` | 3 |
| ICD-10 | `connectors/icd10` | ICD-10-CM diagnoses + ICD-10-PCS procedures (NLM Clinical Tables) | `clinicaltables.nlm.nih.gov/api` | 2 |

**26 datasets across 4 connectors** — see the live list with
`python -m connectors.cli datasets`.

## The uniform contract

Because every connector exposes the same shapes, one thin adapter
(`connectors/_spi.py`) drives all of them and the estate-level modules treat
them as a single database:

- `connectors.<name>.registry` — a `RegistryRow` dataclass with **identical
  field names** (`dataset_id, connector, base_url, endpoint, default_params,
  refresh_cadence, join_keys, target_table, source, source_filter,
  date_field`) plus `registry_rows()` / `registry_as_dicts()` /
  `by_dataset_id()` / `dataset_ids()`.
- `connectors.<name>.tables` — one `*Store` SQLite wrapper with idempotent,
  native-id-keyed upsert.
- `connectors.<name>.query` — `query()` / `aggregate()` / `QueryError` with
  the same `field__op` grammar and `as_dict` result shapes.
- `connectors.<name>.lookup` — `v1_handlers(store) -> {route_template: fn}`.
- `connectors.<name>.api_server` / `cli` — a standalone `/v1` server and CLI.

## Estate-level surface

| File | Role |
|------|------|
| `_spi.py` | Uniform `Adapter` over each connector + the generic lookup-route binder. |
| `registry.py` | The **one database of every API dataset**: `all_registry_rows()`, `all_dataset_ids()`, `dataset_owner()`, `connectors_summary()`, `catalog()`. |
| `api_server.py` | One stdlib `/v1` server mounting every connector (query dispatched to the owner; lookups delegated). |
| `cli.py` | `python -m connectors.cli connectors｜datasets｜catalog｜serve`. |

### Unified `/v1` routes

```
/health
/v1/connectors                       one row per connector (label, base URLs, datasets)
/v1/datasets                         every dataset (merged registries)
/v1/query/{dataset}?<filters>&select=&sort=&limit=&offset=
/v1/query/{dataset}/aggregate?group_by=a,b&<filters>&limit=
/v1/lookup/{noun}/{id}               drug｜device｜company｜document｜contractor｜provider｜taxonomy｜code｜category
/v1/validate/npi/{npi}
/v1/search/{code_type}?q=&limit=      (ICD-10)
```

The uniform filter grammar (every dataset): `{"field": v}` equality, or
`field__op` — `eq/ne/gt/gte/lt/lte/like/in/between/isnull/notnull`; sort with
`field` / `-field`.

## Usage

```bash
# See the whole estate
python -m connectors.cli connectors
python -m connectors.cli datasets --connector cms_coverage
python -m connectors.cli catalog            # full JSON catalog

# Serve everything behind one endpoint (in-memory demo, or a dir of DBs)
python -m connectors.cli serve --db :memory:
python -m connectors.cli serve --db ./var/connectors

# Ingest with a connector's own CLI, then query via the unified surface
python -m connectors.cms_coverage.cli discover
```

```python
from connectors import registry as estate
estate.catalog()["n_datasets"]          # 26
estate.dataset_owner("icd10_cm")         # 'icd10'

from connectors.api_server import open_stores, make_server
stores = open_stores(":memory:")
server, port = make_server(stores)       # one /v1 surface over all connectors
```

## Design notes

- **Stdlib only** — `urllib` + `json` + `sqlite3` + `http.server`. No
  pandas/requests/pyarrow/duckdb; no new runtime dependencies.
- **Injectable transport opener** — every retry / backoff / parse path is unit
  tested against an in-memory fake; tests never touch the network.
- **Self-contained connectors** — a connector never imports another; only
  `_spi.py` reaches across them, so each stays independently testable and any
  connector can be dropped in or out without touching the others.
- **Rate floors / endpoint paths** documented per connector are conservative
  best-known mappings — verify live limits before a bulk run (each connector's
  `transport.py` / `README` carries the disclaimer).

## Tests

```bash
# Whole estate (per-connector suites + the unified surface)
python -m unittest \
  connectors.openfda.tests.test_transport connectors.openfda.tests.test_api_server \
  connectors.cms_coverage.tests.test_api_server connectors.npi_registry.tests.test_api_server \
  connectors.icd10.tests.test_api_server \
  connectors.tests.test_registry connectors.tests.test_spi connectors.tests.test_api_server
```
