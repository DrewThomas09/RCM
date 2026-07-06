# `connectors/bls_qcew` — BLS Quarterly Census of Employment & Wages

Self-contained connector for the BLS **QCEW open CSV slice API** — the
labor-market ground truth for healthcare markets: quarterly establishment
counts, monthly employment levels, and wages for every county / MSA /
state × NAICS industry × ownership, derived from state UI tax records.
Stdlib-only (`urllib` + `csv` + `sqlite3` + `http.server`), mirrors the
`cms_coverage` / `hrsa_data` architecture exactly.

## Source API

No key, no JSON envelope, no paging — pre-cut CSV files behind stable URLs:

```
https://data.bls.gov/cew/data/api/{year}/{qtr}/industry/{naics}.csv
    one row per area x ownership for that industry
https://data.bls.gov/cew/data/api/{year}/{qtr}/area/{area_fips}.csv
    one row per industry x ownership for that county/MSA/state
```

Docs: <https://www.bls.gov/cew/additional-resources/open-data/csv-data-slices.htm>

**Availability window (verified live 2026-07-06):** quarterly slices
exist for **2014 Q1 through 2025 Q4**. 2013 and earlier → 404 (older
QCEW lives in ZIP archives, not this API); 2026 Q1 → 404 (not out yet).
BLS publishes a quarter ~5 months after it ends. The pinned defaults
(`LATEST_YEAR = 2025`, `LATEST_QTR = "4"` in `endpoints.py`) are the
newest published quarter; bump them when a new quarter ships — a stale
pin still works, it just isn't the newest data.

Both slice kinds publish the identical 42-column quarterly row shape
(verified live against `/2025/4/industry/622.csv` and
`/2025/4/area/48453.csv`): the 8 dimension columns
(`area_fips,own_code,industry_code,agglvl_code,size_code,year,qtr,disclosure_code`),
8 measures (`qtrly_estabs`, `month1-3_emplvl`, `total_qtrly_wages`,
`taxable_qtrly_wages`, `qtrly_contributions`, `avg_wkly_wage`), 9 `lq_*`
location quotients and 17 `oty_*` over-the-year changes. **All columns
are kept.** Headers are already snake_case; the schema is the live
header snapshot verbatim (tests assert every column is a fixed point of
the documented `snake()` rule).

**Annual averages are out of scope**: `qtr=a` slices exist but publish
a *different* column set (`annual_avg_estabs`, `avg_annual_pay`, …)
that would corrupt the quarterly table, so `qtr` is validated to 1-4
and the error message says why.

**Rate limits:** none published for these files. The transport keeps a
0.5 s inter-request courtesy floor, retries 429/5xx/transport errors
with exponential backoff + full jitter (honouring `Retry-After`), and
treats 404 as a signal (year/qtr/code outside the window) with an
actionable error, not a transient.

## Datasets

| dataset_id | slice | default slice | table |
|---|---|---|---|
| `bls_qcew_industry_area` | one NAICS industry across all areas | industry **62** (Health Care & Social Assistance), 2025 Q4 | `qcew_industry_area` |
| `bls_qcew_area_industry` | one area across all industries | area **US000** (national), 2025 Q4 | `qcew_industry_area` |

Useful healthcare slice codes: NAICS `62` sector, `621` ambulatory,
`622` hospitals, `623` nursing/residential care, `6216` home health.
Area codes: `48453` (county), `48000` (state), `C4266` (MSA), `US000`
(national).

Both datasets share the physical table (identical row shape) and are
pinned apart by `source_endpoint` — the cms_coverage shared-table +
`source_filter` pattern.

### Upsert key (one deliberate deviation from the assignment's literal pk)

`qcew_key = "{slice}:{area_fips}:{own_code}:{industry_code}:{year}:{qtr}"`.

The natural observation key is the last five parts (verified unique
within every live slice sampled: `size_code` is always 0 in
industry/area slices, `agglvl_code` is determined by the area/industry
pair). The leading slice token is added because the SAME observation
legitimately arrives through both slices — fetching `industry/622` and
`area/48453` for one quarter overlaps on Travis County's hospital rows
(verified live). Without the prefix, the second fetch would rewrite
`source_endpoint` and silently *move* rows out of the other dataset's
`source_filter` slice; with it, each dataset stays independently
complete and idempotent (same reason `hrsa_data` keys HPSA rows by
discipline). Lookups collapse the cross-slice duplicates by grouping on
the natural observation key.

QCEW revises each quarter once (and re-states with each annual
processing round); re-fetching a quarter upserts revised values in
place under the same key.

## Usage

```bash
# registry / slice kinds
python -m connectors.bls_qcew.cli datasets
python -m connectors.bls_qcew.cli discover

# ingest: hospitals (622) everywhere, 2024 Q1
python -m connectors.bls_qcew.cli --db qcew.db fetch \
    --dataset industry_area --industry 622 --year 2024 --qtr 1

# ingest: everything in Travis County TX, latest published quarter
python -m connectors.bls_qcew.cli --db qcew.db fetch \
    --dataset area_industry --area 48453

# uniform query surface
python -m connectors.bls_qcew.cli --db qcew.db query bls_qcew_industry_area \
    --filter own_code=5 --filter avg_wkly_wage__gte=2000 \
    --sort -avg_wkly_wage --limit 10

# lookups
python -m connectors.bls_qcew.cli --db qcew.db lookup-labor-market 48453
python -m connectors.bls_qcew.cli --db qcew.db lookup-industry-employment 622

# HTTP surface
python -m connectors.bls_qcew.cli --db qcew.db serve --port 8099
```

`--db` is a single **global** flag (defaults to `:memory:`; pass a file
path to persist between commands). `fetch` defaults to a 50,000-row cap
per slice — every live slice probed is well under it (biggest: industry
62, ~11k rows/quarter), so the default is a full pull in practice;
`--full` removes the cap.

## HTTP routes

```
GET /health
GET /v1/datasets
GET /v1/query/{dataset}?<filters>&select=&sort=&limit=&offset=
GET /v1/query/{dataset}/aggregate?group_by=a,b&<filters>&limit=
GET /v1/lookup/labor-market/{area_fips}[?year=&qtr=&limit=N]
GET /v1/lookup/industry-employment/{naics}[?year=&qtr=&limit=N]
```

* **labor-market** — one area's healthcare labor market
  (`industry_code LIKE '62%'` — every NAICS 62* code is Health Care &
  Social Assistance) for the newest ingested quarter (or a pinned one):
  per-industry × ownership employment/wages, ownership breakdown.
* **industry-employment** — one NAICS code's footprint across areas:
  top areas by employment, ownership breakdown. Counts, never sums —
  areas nest (national ⊃ state ⊃ county), so summing across areas
  would double-count.

Filter grammar: `field=v`, `field__gte=v`, `field__like=%25v%25`,
`field__in=a&…` etc. (uniform estate grammar). Note rows with QCEW
disclosure code `N` are suppressed at the source (measures published as
0) and are returned as-is.

## Tests

```bash
cd /home/user/RCM && python3 -m unittest discover -s connectors/bls_qcew/tests -t . -v
```

No network: all fixtures in `tests/fakes.py` mirror the live header row
and quoting convention (quoted dimension cells, bare numerics) sampled
2026-07-06, including the cross-slice overlap and a
disclosure-suppressed row.
