# `connectors/oig_leie` — HHS OIG List of Excluded Individuals/Entities (LEIE)

Self-contained connector for the HHS Office of Inspector General's
exclusion list — the compliance dataset behind provider-exclusion
screening: individuals and entities excluded from Medicare, Medicaid and
all federal health care programs. Billing for services ordered or
rendered by an excluded party is not reimbursable, so RCM diligence
screens every provider (by NPI, and by name when no NPI is on record)
against this list.

Stdlib only, no API key, self-contained (no imports from other
connectors). Mirrors the estate architecture: declarative endpoints +
registry, streaming CSV transport with retry/backoff, normalize →
SQLite upsert, uniform `/v1/query` engine, lookup handlers, standalone
`/v1` HTTP server.

## Source (verified live 2026-07-06)

OIG publishes no query API — only CSV downloads under
`https://oig.hhs.gov/exclusions/downloadables/`:

| File | What it is | Size |
| --- | --- | --- |
| `UPDATED.csv` | **Full-replacement** database, refreshed monthly (~83k rows) | ~15 MB |
| `{yyyy}/{yy}{mm}excl.csv` | Monthly supplement: exclusions **added** that month | usually 14–70 KB |
| `{yyyy}/{yy}{mm}rein.csv` | Monthly supplement: **reinstatements** that month | a few KB |

All three publish the identical 18-column header:
`LASTNAME,FIRSTNAME,MIDNAME,BUSNAME,GENERAL,SPECIALTY,UPIN,NPI,DOB,ADDRESS,CITY,STATE,ZIP,EXCLTYPE,EXCLDATE,REINDATE,WAIVERDATE,WVRSTATE`.

Supplement quirks confirmed against the live index
(https://oig.hhs.gov/exclusions/exclusions_list.asp):

* **Not every month publishes a file** (e.g. there is no `2505excl.csv`
  and no `2601rein.csv`). A fetch without an explicit month therefore
  walks back from the current UTC month (up to 6 months) to the newest
  published file; a 404 on an explicit month means "nothing published".
* One observed supplement (`2026/2605excl.csv`) was anomalously the
  full cumulative file rather than a delta. Harmless here: supplements
  upsert into the cumulative table under the same natural key, so a
  cumulative "delta" just re-writes existing rows.

## Value normalization (the part screening correctness depends on)

* `NPI` — the LEIE writes `0000000000` when the NPI is unknown (~85% of
  the historic file). Normalized to `''` so an NPI join can never
  "match" tens of thousands of unrelated rows. The `exclusion` lookup
  additionally refuses to match an empty/all-zero query NPI.
* Dates (`DOB`, `EXCLDATE`, `REINDATE`, `WAIVERDATE`) — published as
  `yyyymmdd` with `00000000` for null. Normalized to ISO `yyyy-mm-dd`
  (sortable with plain string compares) or `''`.

## Datasets

| dataset_id | table | what |
| --- | --- | --- |
| `oig_leie_exclusions` | `oig_exclusions` | The full-replacement list (`UPDATED.csv`) |
| `oig_leie_supplement` | `oig_exclusions` | Monthly *new exclusions*, merged into the same cumulative table |
| `oig_leie_reinstatements` | `oig_reinstatements` | Monthly reinstatements (providers **removed** from the LEIE) |

Design notes:

* **The full file REPLACES; supplements merge.** `UPDATED.csv` is a
  *full-replacement* publication: it is the complete current list, so a
  provider reinstated since the last pull is **absent** from it. A
  complete (uncapped) `fetch --dataset exclusions` therefore atomically
  replaces the `oig_exclusions` table — one transaction deletes the
  previous full+supplement rows and writes the fresh snapshot
  (`"mode": "replace"` in the fetch report). Merging it instead would
  keep reinstated providers flagged excluded forever. Deletion only
  happens when the download demonstrably covered the whole file:
  * a **row-capped** pull (`--max-rows` smaller than the file) merges
    only and reports/prints an explicit partial-merge `warning`
    (`"mode": "merge"`);
  * a **failed or truncated download** (connection drop mid-body —
    detected via `Content-Length` byte accounting in the transport)
    raises and never touches the table;
  * a full file that parses to **0 usable rows** is refused as a
    replacement (merge-only + warning) — an empty compliance list is
    upstream breakage, not mass reinstatement.
* **Shared cumulative table, no `source_filter` pinning.** The full file
  and the supplement are one logical dataset (the supplement is
  incremental adds), so unlike the estate's usual shared-table slicing,
  both registry rows leave `source_filter` empty — a query for
  `oig_leie_exclusions` must see providers excluded since the last full
  pull. Provenance is still recorded per row in `source_endpoint`
  (`exclusions`, `supplement:2026-05`, …) and is filterable
  (`source_endpoint__like=supplement%`).
* **Reinstatements live in their own table** because a reinstated
  provider is *absent* from the current full file — mixing them into
  `oig_exclusions` would re-flag cleared providers.
* **Upsert key** (`exclusion_key`) composes
  `lastname:firstname:midname:busname:dob:excldate:npi:address` from the
  *normalized* values. Validated against the full live file (83,464
  rows, 2026-06-30 vintage): 31 residual duplicate keys / 32 excess rows
  remain — 25 byte-identical source lines plus 6 differing only in city
  spelling or specialty — which the idempotent upsert collapses
  harmlessly. `ADDRESS` is in the key because without it 31 *distinct*
  multi-location business exclusions would collapse to one row.
  `reinstatement_key` appends `reindate` (rows accumulate across months
  and re-exclusion/re-instatement cycles exist).
* `join_keys = ["npi"]` — the screening join to NPPES / Care Compare /
  Open Payments providers. Remember the empty-NPI caveat above; name
  screening is the fallback.

## Ingest caps & politeness

Single-file downloads, streamed: a `max_rows`-capped fetch stops reading
mid-stream. The default cap (100,000) deliberately **covers the whole
full file** — a compliance list must not be silently partial — while
still bounding a runaway pull; `--full` removes the cap explicitly.
Requests are throttled (1s floor) and retried on 429/5xx/transport
errors with exponential backoff + full jitter, honouring `Retry-After`.
`refresh_cadence` is monthly (OIG updates the list monthly).

## CLI

```bash
# All storage via the GLOBAL --db flag (defaults to :memory:)
python -m connectors.oig_leie.cli --db leie.db datasets
python -m connectors.oig_leie.cli --db leie.db discover

# Full list (default --max-rows 100000 covers the whole file)
python -m connectors.oig_leie.cli --db leie.db fetch --dataset exclusions
python -m connectors.oig_leie.cli --db leie.db fetch --dataset exclusions --full

# Monthly supplements: explicit month, or newest published (walk-back)
python -m connectors.oig_leie.cli --db leie.db fetch --dataset supplement --year 2026 --month 5
python -m connectors.oig_leie.cli --db leie.db fetch --dataset reinstatements

# Uniform query + screening lookups
python -m connectors.oig_leie.cli --db leie.db query oig_leie_exclusions \
    --filter state=FL --filter excldate__gte=2024-01-01 --sort -excldate
python -m connectors.oig_leie.cli --db leie.db lookup-exclusion 1972902351
python -m connectors.oig_leie.cli --db leie.db lookup-exclusion-name SMITH --first JOHN

# Standalone /v1 surface
python -m connectors.oig_leie.cli --db leie.db serve --port 8099
```

## HTTP surface

```
GET /health
GET /v1/datasets
GET /v1/query/{dataset}?<filters>&select=&sort=&limit=&offset=
GET /v1/query/{dataset}/aggregate?group_by=a,b&<filters>&limit=
GET /v1/lookup/exclusion/{npi}[?limit=N]
GET /v1/lookup/exclusion-name/{name}[?first=F&limit=N]
```

`/v1/lookup/exclusion/{npi}` answers with the exclusion rows **and** any
reinstatement rows for that NPI (`excluded` boolean, counts, rows); an
empty/all-zero NPI returns `matchable=false` with zero rows instead of a
dangerous wildcard match. `/v1/lookup/exclusion-name/{name}` LIKE-matches
over `lastname` and `busname` together with an optional `first=` prefix
narrowing (individuals only), plus an `excltype` breakdown.

## Tests

```bash
cd /home/user/RCM && python3 -m unittest discover -s connectors/oig_leie/tests -t . -v
```

No network: every fixture in `tests/fakes.py` mirrors the real 18-column
shape and sentinel quirks sampled live on 2026-07-06. Live smoke is
manual-only via the CLI (see above).

## Changelog

* **2026-07-06** — a complete (uncapped) refresh of
  `oig_leie_exclusions` now atomically **replaces** the
  `oig_exclusions` table instead of merging, so providers reinstated
  since the previous pull stop being flagged (no schema change; run
  `fetch --dataset exclusions --full` once on an existing db to purge
  stale rows). Row-capped pulls still merge and now report an explicit
  partial-merge warning. The transport also verifies downloads against
  `Content-Length` and retries `IncompleteRead`, so a mid-body
  connection drop can never ingest (or replace with) a truncated file,
  and defends against negative/garbage `Retry-After` headers.
