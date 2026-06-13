# NPPES Connector — Provider Universe & Taxonomy Crosswalk

The authoritative producer of the **provider (NPI) dimension** and the
**NUCC taxonomy crosswalk** for PEDesk. Other sources (CMS claims/
utilization) reference NPIs but treat `dim_provider` here as the source of
truth. This slice is self-contained: connector → raw landing → normalized
canonical tables → registry → `/v1/query` + `/v1/lookup/provider/` → DQ.

## What it ingests

| Dataset (`dataset_id`)        | Source                                   | Target table                  |
|-------------------------------|------------------------------------------|-------------------------------|
| `nppes_monthly_full`          | NPPES monthly full-replacement file      | `dim_provider`                |
| `nppes_weekly_incremental`    | NPPES weekly incremental files           | `dim_provider` (upsert)       |
| `nppes_othername`             | Other-name file (Type-2 org other names) | `nppes_other_name`            |
| `nppes_practice_location`     | Non-primary practice-location file       | `dim_provider_address`        |
| `nppes_endpoint`              | FHIR endpoint file                       | `dim_provider_endpoint`       |
| `nucc_taxonomy`               | NUCC taxonomy code set (CSV)             | `dim_taxonomy`                |
| `npi_registry_api`            | NPI Registry API v2.1 (lookups only)     | `dim_provider`                |
| `nppes_provider_taxonomy`     | derived                                  | `bridge_provider_taxonomy`    |
| `nppes_provider_affiliation`  | derived (heuristic)                      | `bridge_provider_affiliation` |

The **monthly file is the backbone** (the API cannot full-dump 8M+
providers). The API caps at 200 rows/request and blocks paging past ~1,200
records for one query, so it is reserved for targeted lookups and
incremental verification — the connector enforces that ceiling.

## Canonical tables

- **`dim_provider`** — NPI, entity type, name fields, credential, enumeration
  /deactivation/reactivation dates, status, sole proprietor, org legal
  business name, authorized official.
- **`bridge_provider_taxonomy`** — NPI × taxonomy (one-to-many, one primary)
  with license number/state.
- **`dim_taxonomy`** — taxonomy code → grouping/classification/specialization
  from the NUCC code set.
- **`dim_provider_address`** — practice / mailing / secondary-practice
  addresses; `fips_county`, `latitude`, `longitude` NULL-stubbed pending the
  Census geocoder (owned by a separate session), wireable.
- **`bridge_provider_affiliation`** — derived individual→org links with a
  `method` and `confidence` (see DECISIONS.md D6).
- **`dim_provider_endpoint`** — FHIR endpoints.

## Architecture

```
connector.py   discover() / fetch(endpoint, params, cursor) -> (rows, next_cursor)
               pagination + rate-limit (429/Retry-After) + retry/backoff internal
registry.py    one declarative row per dataset (source=nppes)
parse.py       streaming parsers (generators) for the real NPPES/NUCC headers
landing.py     raw landing: parquet (pyarrow) or gzipped NDJSON, partitioned
normalize.py   chunked, idempotent upserts keyed by NPI; invalid NPIs quarantined
affiliation.py heuristic org-affiliation builder with confidence
dq.py          Luhn / deactivation / taxonomy-resolution / dup-NPI / reconciliation
api.py         /v1/query engine + /v1/lookup/provider handlers (mountable plugin)
pipeline.py    orchestrator + filesystem-as-memory (STATE.md, nppes_load_state)
synth.py       synthetic verification universe (real headers)
cli.py         python -m connectors.nppes.cli {build,discover,lookup,query}
```

## Run it

```bash
# Build the universe (synthetic, offline — network is blocked here) + DQ
python -m connectors.nppes.cli build --db nppes.db

# Ingest a staged REAL dissemination file through the identical path
python -m connectors.nppes.cli build --db nppes.db \
    --monthly NPPES_monthly.csv --nucc nucc_taxonomy_2026.csv \
    --weekly week1.csv --weekly week2.csv \
    --othername othername_pfile.csv --endpoint endpoint_pfile.csv

python -m connectors.nppes.cli discover
python -m connectors.nppes.cli lookup --db nppes.db --npi 1003456789
python -m connectors.nppes.cli query  --db nppes.db --dataset dim_provider \
    --filter entity_type=2 --filter state=TX --limit 10
```

## API surface (programmatic)

```python
from connectors.nppes import api, pipeline
from connectors.nppes.store import NppesStore

store = NppesStore("nppes.db")
api.query_dataset(store, "dim_provider",
                  filters={"organization_name__like": "%HOSPITAL%",
                           "entity_type__eq": 2},
                  select=["npi", "organization_name"], sort=["-npi"], limit=20)
api.lookup_provider(store, "1003456789")          # full provider view
api.search_providers(store, state="TX", taxonomy_code="207Q00000X")
api.mount_router(host_router, store)              # plugin-mount /v1 routes (no core edits)
```

## Diligence value — CDD analytics (`cdd.py` + `report.py`)

The canonical tables are the raw material; `cdd.py` turns them into the
signals a commercial-diligence analyst asks for, and `report.py` composes
them into an IC-ready market-structure brief.

| Function | CDD question it answers |
|---|---|
| `tam_by_taxonomy_geography` | How big is the market? (provider count by geo × specialty — the TAM spine) |
| `market_concentration` | How consolidated is it? (HHI per geo × specialty, DOJ/FTC banded) |
| `fragmentation_scan` | Is there roll-up runway? (independent share × low HHI × firm count) |
| `affiliation_footprint` | Who are the platforms? (orgs ranked by captive-provider volume) |
| `rollup_targets` | What are the add-on candidates? (sub-scale independent orgs) |
| `roster_integrity` | What's the revenue-base risk? (deactivation/reactivation rates) |

```bash
# One-shot IC-ready brief for a thesis
python -m connectors.nppes.cli cdd report --db nppes.db \
    --geo TX --classification "Internal Medicine" --out brief.md

# Individual metrics as JSON
python -m connectors.nppes.cli cdd concentration --db nppes.db --geo-level state
python -m connectors.nppes.cli cdd rollup --db nppes.db --geo TX
```

Provider count by taxonomy × geography is the spine of market-structure /
TAM analysis (`bridge_provider_taxonomy` + `dim_provider_address`).
Affiliation reconstructed from shared practice address + legal/other org
name approximates referral and captive-volume relationships. Deactivation/
reactivation flags drive roster-integrity checks. All CDD metrics are also
mounted under `/v1/lookup/market/{metric}` when a router hook is present.

## Tests

```bash
python -m pytest tests/test_nppes_universe_*.py -q
```

See **STATE.md** (load state + row counts + DQ), **DECISIONS.md** (every
autonomous decision), and **PROGRESS_LOG.md** (append-only run log).
