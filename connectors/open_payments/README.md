# Open Payments connector (`connectors/open_payments`)

CMS **Open Payments** (Sunshine Act) — every payment or transfer of value
from drug/device manufacturers and GPOs to physicians, non-physician
practitioners and teaching hospitals, published at
[openpaymentsdata.cms.gov](https://openpaymentsdata.cms.gov). The portal
runs **DKAN** (the same open-data engine as `data.medicaid.gov`):

- **Catalog**: `GET /api/1/metastore/schemas/dataset/items` → 74 datasets
  (JSON list; each `identifier` is the dataset UUID).
- **Datastore**: `GET /api/1/datastore/query/{identifier}/0?limit=N&offset=M`
  → `{"count", "query", "results", "schema"}` envelope, plus
  `conditions[i][property|value|operator]` server-side filters.
  `limit` is hard-capped at **500** (400 above), `count=false` /
  `schema=false` trim the envelope. All verified live 2026-07-06.

No API key, no documented rate limit — the transport keeps a polite
0.25s inter-request floor and 429/5xx backoff (courtesy defaults, not a
contract; verify before bulk runs).

## ⚠ Scale warning (the load-bearing constraint)

General Payment Data years exceed **15M rows** (2024: 15,498,687 live).
This connector NEVER defaults to a full pull:

- `fetch()` defaults to `max_pages=3` × 500 rows and hard-caps
  `max_pages` at 200 (100k rows/call) even when asked for more;
- fetches are **filter-driven**: filters become DKAN `conditions`
  evaluated server-side (`recipient_state`, `covered_recipient_npi`,
  `applicable_manufacturer_or_applicable_gpo_making_payment_name__like`, …);
- a fetch that stops with a full last page reports `truncated=True`.

## Datasets (11 registry rows, `open_payments_*`)

| dataset_id | table | what |
|---|---|---|
| `open_payments_catalog` | `open_payments_catalog` | all 74 datasets: id, title, theme, modified, download/api URLs (synced by `discover`) |
| `open_payments_general_payments_2024` | `op_general_payment` | 2024 general payments — **all 91 native columns** |
| `open_payments_research_payments_2024` | `op_research_payment` | 2024 research payments — **all 252 native columns** (5 PI slots) |
| `open_payments_ownership_payments_2024` | `op_ownership_payment` | 2024 physician ownership/investment interests (30 cols) |
| `open_payments_profiles` | `op_profile` | covered-recipient profiles (entity_id-keyed) |
| `open_payments_recipient_profile_supplement` | `op_profile_supplement` | physician profile supplement (profile_id-keyed) |
| `open_payments_summary_dashboard` | `op_summary_dashboard` | national metrics by program year |
| `open_payments_payments_by_recipient_nature_2024` | `op_payments_by_recipient_nature` | totals per recipient × nature code |
| `open_payments_payments_by_entity_nature_2024` | `op_payments_by_entity_nature` | totals per reporting entity × nature code |
| `open_payments_state_payment_totals` | `op_state_payment_totals` | state × year × nature × recipient-type totals |
| `open_payments_fetched_rows` | `open_payments_rows` | **generic slot**: any of the 74 datasets by UUID as JSON rows |

Curated columns are byte-for-byte live snapshots (DKAN already serves
lowercase snake_case; the documented mapping is identity). Detail files
upsert on the native `record_id`; pre-aggregated tables use composed
natural keys built in `normalize.py` (e.g.
`{country}:{state}:{year}:{nature}:{recipient_type}`). Everything is
TEXT — the query layer CASTs where it needs numbers.

Program-year files get a **new UUID** each publication cycle; older
years are pulled through the generic slot with the UUID from the synced
catalog (no code changes).

## Usage

```bash
# Sync the catalog (74 rows, one cheap GET)
python -m connectors.open_payments.cli discover --db ./op.db

# Find any dataset, then pull it on demand by UUID (generic rows)
python -m connectors.open_payments.cli catalog-search --q "2023 General" --db ./op.db
python -m connectors.open_payments.cli fetch --dataset <uuid> --state VT --max-pages 1 --db ./op.db

# Filter-driven curated fetch (server-side conditions; 2570 VT rows live)
python -m connectors.open_payments.cli fetch --dataset general_payments_2024 \
    --state VT --max-pages 2 --db ./op.db
python -m connectors.open_payments.cli fetch --dataset ownership_payments_2024 \
    --npi 1234567893 --db ./op.db      # --npi maps to physician_npi here

# Query / serve the uniform /v1 surface
python -m connectors.open_payments.cli query open_payments_general_payments_2024 \
    --filter recipient_state=VT --sort=-date_of_payment --limit 5 --db ./op.db
python -m connectors.open_payments.cli serve --db ./op.db --port 8099
```

`--state`/`--npi` map onto the right native column per dataset
(`recipient_state`/`covered_recipient_npi` on general/research,
`physician_npi` on ownership, `entity_npi` on profiles, `state_code` on
state totals). Arbitrary native filters: `--filter field=value` or
`--filter field__like=%MERCK%` (`eq/ne/gt/gte/lt/lte/like`).

### `/v1` routes (standalone server)

```
/health
/v1/datasets
/v1/query/{dataset}?<filters>&select=&sort=&limit=&offset=
/v1/query/{dataset}/aggregate?group_by=a,b&<filters>&limit=
/v1/lookup/physician-payments/{npi}     general payments + by-nature totals for an NPI
/v1/lookup/manufacturer/{name}          payments by manufacturer/GPO name (substring)
/v1/lookup/op-dataset/{identifier}      catalog row by UUID (or title fragment)
```

## Tests

```bash
cd /home/user/RCM
python3 -m unittest discover -s connectors/open_payments/tests -t . -v
```

Stdlib-only, no network: `tests/fakes.py` is an in-memory DKAN
(catalog list + datastore envelope + conditions + the live limit-500
rejection + scripted 429/5xx). Live smoke is manual:
`discover` + one filtered `fetch --max-pages 1`.
