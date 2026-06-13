# NPPES Connector — DECISIONS

Every autonomous decision taken while building this slice, with rationale.
This session ran unattended; ambiguities were resolved here and work
continued rather than pausing.

## D1 — Network is blocked; verify against a synthetic universe
Every outbound host (CMS `download.cms.gov`, `npiregistry.cms.hhs.gov`,
`www.nucc.org`, even `example.com`) returns **HTTP 403** in this
environment; only PyPI is reachable. The real 8M-row monthly file therefore
cannot be downloaded and the live API cannot be hit.

**Decision:** build the full pipeline for the *real* file shapes (the
production parsers use the real NPPES/NUCC column headers), and verify it
end-to-end against a representative **synthetic universe** generated with
those same headers (`synth.py`). The live `fetch()`/`discover()` paths are
implemented and unit-tested with mocked HTTP; when they cannot reach the
network they **degrade gracefully** (return empty rows + a logged
`FetchEvent`) instead of crashing the session. Pointing
`pipeline.run(monthly_path=...)` at a staged real dissemination file ingests
the real universe through the identical code path. The API cap is verified
live by `connector.verify_api_cap()` when reachable, falling back to the
documented 200/request + ~1,200 depth ceiling otherwise.

## D2 — Stdlib-only canonical store (SQLite), parquet landing optional
The runtime here has no pandas/duckdb/polars/pyarrow installed by default,
and the surrounding codebase is deliberately stdlib-first.

**Decision:** the **canonical** tables live in **SQLite** (stdlib) — the
contract's read patterns (point lookups by NPI, filtered scans by
taxonomy/geography, `/v1/query` filter/sort/paginate) are exactly what an
indexed relational store serves cheaply, with zero hard dependency. **Raw
landing** honors "land to parquet, partitioned, streamed": it writes real
**parquet** via `pyarrow` when present (auto-selected; verified working,
partitioned `entity_type=<n>/state=<ST>/`), and falls back to
**gzipped NDJSON** with the identical partition layout otherwise. Nested
taxonomy/address structures are JSON-encoded at landing so both formats
round-trip losslessly. The chosen format is recorded in STATE.md.

## D3 — FIPS county + lat/long left NULL, wireable (Census geocoder dep)
Geocoding provider addresses to FIPS county is owned by a separate session
(Census geocoder), which is not available here.

**Decision:** `dim_provider_address.fips_county`, `latitude`, `longitude`
are populated **NULL** with `geocode_status='pending'`. The columns exist
and are indexed so the geocoder can upsert into them later without a schema
change. We do **not** block on this dependency and do **not** write the FIPS
crosswalk key (owned elsewhere).

## D4 — Invalid NPIs are quarantined, never dropped
NPIs are validated with the Luhn check over the `80840` ISO-7812 prefix
(`luhn.py`). Rows failing validation are written to `nppes_invalid_npi`
(with reason + compact payload) and **excluded from `dim_provider`**, rather
than silently discarded. The row-count reconciliation accounts for them
(`accounted = loaded + quarantined`).

## D5 — Taxonomy modeled as a one-to-many bridge
A provider can carry up to 15 taxonomy codes with exactly one primary. We
model `bridge_provider_taxonomy` (NPI × taxonomy) with a `primary_flag`,
license number, and license state — never a single taxonomy column. The
DQ suite asserts at most one primary per NPI.

## D6 — Affiliation heuristic + confidence
`bridge_provider_affiliation` is **derived/heuristic**. We link a Type-1
individual to a Type-2 organization when they **share a normalized practice
address** (`upper(line_1)` stripped of punctuation + zip5). Confidence:
`0.45 / sqrt(n_orgs_at_address)`, floored at 0.20 (co-location is weaker
when many orgs share a suite). When a significant token of the individual's
surname also appears in the org's legal business name **or** one of its
other-organization names, the pair is boosted to `min(0.92, conf + 0.30)`
and tagged `shared_address+name`. Address-only evidence is tagged
`shared_practice_address`. A name match with no co-location is **not**
emitted (too weak alone). Every row stores `method`, `confidence` (0–1), and
human-readable `evidence`. The bridge is rebuilt from scratch each run
(idempotent) and never writes back into `dim_provider`.

## D7 — Idempotency via upsert keyed by NPI; weeklies de-duplicated
The monthly file is a full replacement; weeklies are incrementals (new,
changed, deactivated). We load the monthly base, then apply weeklies **in
order** as `ON CONFLICT(npi) DO UPDATE` upserts, newest-`Last Update Date`
wins (stale updates are skipped). Applied weekly ids are tracked in
`nppes_load_state.weeklies_applied` so a resumed run skips them. Taxonomy
and primary-address sets are delete-then-insert per NPI so a re-load
converges even when a weekly drops a taxonomy.

## D8 — Deactivation/reactivation status derivation
`status='deactivated'` iff a deactivation date is present with no later
reactivation date; otherwise `active`. This drives the roster-integrity DQ
check (a terminated provider that affects a target's revenue base).

## D9 — No `/v1` router core to edit → mountable plugin handlers
The repo's HTTP server is a stdlib `http.server`; there is no `/v1` router
core exposing a dataset registry, and the contract forbids editing the
router core. **Decision:** ship the query engine + lookup handlers as
**framework-agnostic pure functions** (`api.py`) plus a `mount_router()`
helper that registers `/v1/lookup/provider/{npi}`,
`/v1/lookup/provider/search`, and `/v1/query/{dataset}` onto any host router
that exposes a plugin hook (`add_route`/`register`/…). If no hook exists the
functions remain directly importable/callable. The `/v1/query` engine
resolves a registry `dataset_id` (or a canonical table name) to its
`target_table` and applies a uniform, **allow-listed** filter/select/sort/
paginate — so callers never see NPPES's native response shape and adding a
dataset is a registry row, not new routing code.

## D10 — Scope discipline (files not touched)
We did **not** modify: the existing `rcm_mc/pricing/` NPPES code (the Myelin
pricing service's narrow Type-2 slice), the CMS/DKAN connector or its fact
tables, the Tuva dbt core, openFDA/RxNorm, or the `/v1` router core. We own
only `connectors/nppes/` and the NPPES tests. The CMS facts that reference
NPIs join to *our* `dim_provider`; we never write into their tables. We did
not rewrite the FIPS/CPT/MS-DRG/NDC↔RxCUI crosswalk keys.

## D11 — Committed synthetic fixtures
`fixtures/` holds a deterministic (seed=7) synthetic dissemination set
(monthly, one weekly, NUCC subset, other-name, practice-location, endpoint)
so the slice is reproducible and the tests run offline. This is clearly
labeled verification data, not real provider data. `data/` (the built DB +
landing zone) is git-ignored — it is a derived artifact, rebuildable with
`python -m connectors.nppes.cli build`.

## D12 — CDD analytics layer (cdd.py + report.py)
The canonical dimensions answer "who/where" but not the diligence "so what".
Added a read-only analytics layer turning them into commercial-diligence
signal: TAM by taxonomy × geography, market concentration (HHI scored on the
DOJ/FTC bands, using each org's captive-provider share as a revenue proxy
since billed revenue is out of NPPES scope), fragmentation / roll-up scoring,
incumbent-platform ranking, sub-scale roll-up targets, and roster integrity.
`report.py` composes these into an IC-ready market-structure brief. All
metrics are SQL-expressed (window-function firm assignment) so they stay
bounded on the real 8M universe, and geography swaps from practice-state to
the Census `fips_county` by changing one column once that dependency lands.
Exposed via `cli.py cdd …` and mounted at `/v1/lookup/market/{metric}`.
The synthetic universe was made more realistic (a long tail of solo
practices + independent providers at unique addresses) so the fragmentation
and roll-up signals are non-degenerate — real provider markets are never
all-campus.
