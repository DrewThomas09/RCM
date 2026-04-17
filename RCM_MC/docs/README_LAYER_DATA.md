# Layer: Data Ingestion (`rcm_mc/data/`)

## TL;DR

This layer pulls public hospital data from CMS and IRS into SQLite so
the comparable-hospital finder and benchmark layer have a population
to work with. Four external sources: CMS HCRIS (cost reports), CMS
Care Compare (quality), CMS Medicare Utilization (DRG volumes), IRS
Form 990 Schedule H (non-profit hospital financials).

All HTTP is mockable via a single function — tests never hit real
CMS endpoints.

## What this layer owns

- **`hospital_benchmarks` table** — the benchmark population. One row
  per `(provider_id, source, metric_key, period)` tuple. Unique
  index prevents dupes; upserts on conflict.
- **`data_source_status` table** — per-source freshness tracking
  (last refresh, next refresh, OK / STALE / ERROR).
- **`generated_exports` audit (shared with exports layer).**

## Files

### `_cms_download.py` (~90 lines)

**Purpose.** Tiny download helper — the single HTTP seam.

**Public surface.**
- `cache_dir(source: str) -> Path` — returns `~/.rcm_mc/data/<source>/`
  unless `$RCM_MC_DATA_CACHE` overrides.
- `fetch_url(url, dest, *, timeout=60.0, overwrite=False) -> Path` —
  atomic download (writes to `.part` first, then rename). Raises
  `CMSDownloadError` on any network failure.

**How tests mock it.** Every caller invokes
`_cms_download.fetch_url(...)` via the module attribute. Tests use
`monkeypatch.setattr("rcm_mc.data._cms_download.fetch_url", stub)` to
divert every download with one line.

### `cms_hcris.py` (~260 lines)

**Purpose.** HCRIS cost-report loader. Produces `HCRISRecord` rows
covering bed_count, discharges, CMI, gross/net revenue, operating
margin, payer mix, bad debt, charity care, DSH/IME, teaching status,
location. Flattens each record into multiple `hospital_benchmarks`
rows.

**Public surface.**
- `HCRISRecord` — dataclass with 20+ fields.
- `download_hcris(year=None, ...)` — fetches the `HOSP10FY{year}.zip`
  bundle from CMS.
- `parse_hcris(filepath) -> list[HCRISRecord]` — reads the shipped
  `hcris.csv.gz` (existing `rcm_mc/data/hcris.py` generated this).
  Handles both `.csv` and `.csv.gz`.
- `load_hcris_to_store(store, records)` — writes flattened rows.
- `refresh_hcris_source(store)` — the orchestrator entry point.

**Wraps existing.** The mature `rcm_mc/data/hcris.py` handles
worksheet-coordinate parsing of the raw CMS zip. `cms_hcris.py` is
the benchmark-database loader that wraps it.

### `cms_care_compare.py` (~180 lines)

**Purpose.** CMS Care Compare / Hospital Compare quality metrics.
Merges three CSVs: General Hospital Info (star rating), HCAHPS
(patient experience), Complications & Readmissions.

**Public surface.**
- `CareCompareRecord` — star_rating, readmission_rate,
  mortality_rate, patient_experience_rating, vbp_total_score,
  hac_score, medicare_spending_per_beneficiary.
- `CARE_COMPARE_URLS` dict with three dataset endpoints.
- `download_care_compare(dest_dir=None, overwrite=False) -> dict[kind, path]`.
- `parse_care_compare(files) -> list[CareCompareRecord]`.
- `load_care_compare_to_store(store, records)`.
- `refresh_care_compare_source(store)`.

**Null handling.** CMS CSVs use `"Not Available"` for missing values;
the parser tolerates six sentinels (`""`, `"N/A"`, `"NA"`, etc.).

### `cms_utilization.py` (~160 lines)

**Purpose.** Medicare Inpatient Utilization (IPPS) — one row per
(provider, DRG) with discharge volumes, covered charges, total
payments, Medicare payments. Derives per-hospital metrics.

**Public surface.**
- `UtilizationRecord` — provider_id, drg_code, drg_description,
  total_discharges, average_covered_charges, etc.
- `download_medicare_utilization()`, `parse_utilization()`.
- `compute_provider_metrics(records) -> dict[provider, dict]` —
  computes:
  - `total_medicare_discharges` (sum across DRGs)
  - `top_drg_volume` (largest single DRG)
  - `avg_charge_to_payment_ratio` (discharge-weighted)
  - `service_line_concentration` (Herfindahl-Hirschman index across
    DRGs — high = specialized, low = generalist)
- `load_utilization_to_store(store, records)`.
- `refresh_utilization_source(store)`.

### `irs990_loader.py` (~180 lines)

**Purpose.** IRS Form 990 Schedule H loader for non-profit hospitals
(~58% of US hospitals file). Wraps the existing
`rcm_mc/data/irs990.py` ProPublica fetcher.

**Public surface.**
- `IRS990Record` — ein, name, fiscal_year, total_revenue,
  total_expenses, charity_care_at_cost, bad_debt_expense,
  medicare/medicaid_surplus_or_shortfall, executive_compensation
  (top 5).
- `download_990_index(year, query="hospital")` — ProPublica search
  (NTEE E20/E21/E22 for hospital/hospital-system nonprofits).
- `parse_990_schedule_h(ein, *, fetcher=None)` — resolve one EIN,
  accepts an injected fetcher for tests.
- `refresh_from_ein_list(store, eins, ein_to_ccn=None, fetcher=None)`.
- `refresh_irs990_source(store)` — reads `ein_list.json` from the
  cache dir; skips gracefully when absent.

### `data_refresh.py` (~370 lines)

**Purpose.** Orchestrator + both persistence tables. The public
"refresh the benchmark DB" entry point.

**Tables.**
```sql
CREATE TABLE hospital_benchmarks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider_id TEXT NOT NULL,
    source TEXT NOT NULL,    -- HCRIS | CARE_COMPARE | UTILIZATION | IRS990
    metric_key TEXT NOT NULL,
    value REAL,              -- numeric metrics
    text_value TEXT,         -- string-valued metrics (state, city)
    period TEXT,
    loaded_at TEXT NOT NULL,
    quality_flags TEXT       -- JSON list
);
CREATE UNIQUE INDEX ux_hb_dedup
  ON hospital_benchmarks(provider_id, source, metric_key, period);

CREATE TABLE data_source_status (
    source_name TEXT PRIMARY KEY,
    last_refresh_at TEXT,
    record_count INTEGER,
    next_refresh_at TEXT,
    status TEXT,             -- OK | STALE | ERROR
    error_detail TEXT,
    interval_days INTEGER
);
```

**Public surface.**
- `KNOWN_SOURCES = ("hcris", "care_compare", "utilization", "irs990")`.
- `save_benchmarks(store, rows, *, source, period)` — upsert, handles
  both numeric and string-valued metrics.
- `query_hospitals(store, *, state, beds_min, beds_max, limit) ->
  list[dict]` — the comparable-pool query the packet builder uses.
- `refresh_all_sources(store, *, sources=None, refreshers=None) ->
  RefreshReport` — sequential, tolerates per-source failures.
- `schedule_refresh(store, interval_days=30)` — seeds status rows.
- `mark_stale_sources(store)` — flips past-due rows to STALE.

**Design note.** Each refresher is an injected callable `(store) ->
int records_loaded`. This makes mocking trivial in tests:

```python
dr.refresh_all_sources(store, refreshers={
    "hcris": lambda s: 10,
    "care_compare": lambda s: 20,
    ...
})
```

### Legacy modules

These existed before the benchmark-DB layer and remain untouched:

- **`hcris.py`** — Raw HCRIS zip parser (worksheet coordinates,
  status-rank dedup). Generates the shipped `hcris.csv.gz`.
- **`irs990.py`** — ProPublica JSON fetcher with disk cache +
  cross-check report.
- **`intake.py`** — Partner seller-data wizard (builds `actual.yaml`).
- **`ingest.py`** — Messy seller data pack → canonical CSVs.
- **`data_scrub.py`** — Winsorization + standardization for the
  simulator kernel.
- **`sources.py`** — observed/prior/assumed source tagging on config.
- **`lookup.py`** (currently at `lookup 2.py` due to a macOS Finder
  artifact — see [README_BUILD_STATUS.md](README_BUILD_STATUS.md)).

## How it fits the system

```
┌────────────────────────────┐     ┌────────────────────────────┐
│  CMS HCRIS zip              │     │  data.cms.gov CSV portal   │
│  cms.gov/downloads/...zip   │     │  xubh-q36u, 632h-zaca, ... │
└──────────┬─────────────────┘     └──────────┬─────────────────┘
           │                                   │
           │                                   │
           ▼          (via _cms_download)       ▼
┌────────────────────────────┐     ┌────────────────────────────┐
│  cms_hcris.py               │     │  cms_care_compare.py        │
│  cms_utilization.py         │     │  irs990_loader.py           │
└──────────┬─────────────────┘     └──────────┬─────────────────┘
           │                                   │
           └─────────────────┬─────────────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │  data_refresh.py     │ ← orchestrator + tables
                  │  save_benchmarks()   │
                  │  query_hospitals()   │
                  └──────────┬──────────┘
                             │
                             ▼
           ┌──────────────────────────────────┐
           │  hospital_benchmarks (SQLite)    │
           │  ~6K hospitals × dozens of metrics│
           └─────────────┬────────────────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │ comparable_finder    │ ← consumer
              │ find_comparables()   │
              └──────────────────────┘
```

## CLI

- `rcm-mc data status` — print a freshness table.
- `rcm-mc data refresh --source all` — hit all four sources. Limited
  to 1 refresh per source per hour via the in-memory rate limiter
  in `rcm_mc/infra/rate_limit.py`.

## API

- `GET /api/data/sources` — freshness rows.
- `GET /api/data/hospitals?state=IL&beds_min=300&beds_max=600` —
  comparable pool query.
- `POST /api/data/refresh/<source>` — kick off a single refresh.

## Current state

### Strong points
- Single mockable HTTP seam (`_cms_download.fetch_url`). No test ever
  hits real CMS.
- Partial-failure tolerant orchestrator — one bad source leaves the
  others intact, tags the failed one ERROR with the exception string.
- String + numeric metrics share the same table via `text_value`
  column — no parallel schema.
- 28 tests cover the full surface.

### Weak points
- **HCRIS refresh is semi-manual.** Relies on the shipped
  `hcris.csv.gz` rather than doing the full zip-to-parquet pipeline
  inline. Partners need to run `rcm-mc hcris refresh` separately to
  regenerate.
- **IRS 990 ein_list.json is seed-required.** No automated EIN
  discovery; partners provide the list manually.
- **Care Compare schema drift.** CMS occasionally renames columns
  (`Facility ID` vs. `Provider ID`); our aliases handle the cases
  we've seen but not proactively.
- **Medicaid MCO distribution.** Not captured — `MANAGED_GOVERNMENT`
  collapses state-specific Medicaid managed care detail.
- **Utilization parser skips non-IPPS OPPS data.** Outpatient DRGs
  (APCs) would need a separate dataset.
