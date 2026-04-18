# Data Sources

All external data sources wired up in the platform. URLs below are
the canonical public endpoints actually fetched by the loaders in
[`rcm_mc/data/`](../RCM_MC/rcm_mc/data/).

## CMS HCRIS — Hospital Cost Reports

**What** — Medicare cost-report filings from every US hospital
(~5,000 facilities × annual filings). Total revenue, operating
expenses, uncompensated care, bad debt, discharges, beds.

**Loader** —
[`RCM_MC/rcm_mc/data/cms_hcris.py`](../RCM_MC/rcm_mc/data/cms_hcris.py)
+ [`RCM_MC/rcm_mc/data/hcris.py`](../RCM_MC/rcm_mc/data/hcris.py).

**Portal** —
`https://data.cms.gov/provider-compliance/cost-report/hospital-provider-cost-report`

**Download URL** — derived via `HCRIS_URL_TEMPLATE.format(year=YYYY)`
(defined in `hcris.py`), pointing at `downloads.cms.gov` annual
zip files.

**Schema** — parsed into `HCRISRecord` dataclass with `provider_id`,
`fiscal_year`, `total_revenue`, `operating_expenses`,
`uncompensated_care`, `bad_debt`, `discharges`, `beds`.

**Destination** — `hospital_benchmarks` SQLite table keyed by
`(provider_id, source='hcris', metric_key, period)`.

**Known limits** — refresh is semi-manual (annual files, no
incremental API); schema drift between years requires loader tweaks.

## CMS Care Compare

**What** — Star ratings, HCAHPS patient-experience scores,
complications, readmissions, mortality per provider.

**Loader** —
[`RCM_MC/rcm_mc/data/cms_care_compare.py`](../RCM_MC/rcm_mc/data/cms_care_compare.py).

**URLs** — from `CARE_COMPARE_URLS`:

| Kind | URL |
|---|---|
| General | `https://data.cms.gov/provider-data/api/1/datastore/query/xubh-q36u/0/download?format=csv` |
| HCAHPS | `https://data.cms.gov/provider-data/api/1/datastore/query/632h-zaca/0/download?format=csv` |
| Complications | `https://data.cms.gov/provider-data/api/1/datastore/query/ynj2-r877/0/download?format=csv` |

**Schema** — `CareCompareRecord` with star rating, HCAHPS bundle,
complication / readmission / mortality rates.

**Failure semantics** — one failing URL does **not** kill the batch;
the others still load. Partial failures surface in
`data_source_status`.

## CMS Utilization (Medicare Inpatient)

**What** — IPPS DRG volumes per provider per year. Used to compute a
Herfindahl-Hirschman Index (HHI) for service-line concentration.

**Loader** —
[`RCM_MC/rcm_mc/data/cms_utilization.py`](../RCM_MC/rcm_mc/data/cms_utilization.py).

**URL** — from `UTILIZATION_URL`:
`https://data.cms.gov/provider-summary-by-type-of-service/...`

**Schema** — `UtilizationRecord` with provider ID, DRG code,
discharges, charges, payments.

**Derived metric** — HHI concentration score written back to
`hospital_benchmarks` as `metric_key='service_line_hhi'`.

**Known limits** — skips OPPS (outpatient prospective payment
system); inpatient only.

## IRS Form 990 — Non-Profit Hospitals

**What** — Charity-care dollars, Medicare surplus, executive
compensation, from the IRS Form 990 filings of non-profit hospitals.

**Loader** —
[`RCM_MC/rcm_mc/data/irs990_loader.py`](../RCM_MC/rcm_mc/data/irs990_loader.py).

**Upstream API** — ProPublica Nonprofit Explorer:
`https://projects.propublica.org/nonprofits/api/v2/search.json`

**Filter** — NTEE codes `E20` (general hospital), `E21` (specialty
hospital), `E22` (rehabilitation / psychiatric).

**Schema** — `IRS990Record` with EIN, fiscal year, charity care,
bad debt, Medicare surplus, top-5 exec comp.

**Known limits** — needs a seeded `ein_list.json` mapping HCRIS
provider IDs to EINs; refresh is semi-manual.

## SEC EDGAR

**What** — Revenue, margin, leverage, and capital structure for ~25
public hospital systems, from XBRL filings.

**Loader** —
[`RCM_MC/rcm_mc/data/sec_edgar.py`](../RCM_MC/rcm_mc/data/sec_edgar.py).

**Coverage** — public operators (HCA, Tenet, Community Health,
UHS, Acadia, Encompass, and others). Backs the peer-valuation layer
in [`rcm_mc/data_public/peer_valuation.py`](../RCM_MC/rcm_mc/data_public/peer_valuation.py).

## Shared download helper

Every CMS / external fetch goes through
[`RCM_MC/rcm_mc/data/_cms_download.py`](../RCM_MC/rcm_mc/data/_cms_download.py)
— single HTTP seam, atomic file writes, respectful retry, cache
directory under the configured data root.

## Storage table

```sql
CREATE TABLE hospital_benchmarks (
    provider_id   TEXT,
    source        TEXT,     -- 'hcris' | 'care_compare' | 'utilization' | 'irs990'
    metric_key    TEXT,
    value         REAL,
    text_value    TEXT,
    period        TEXT,     -- e.g., '2023FY'
    loaded_at     TEXT,
    quality_flags TEXT,
    UNIQUE(provider_id, source, metric_key, period)
);
```

Unique index on `(provider_id, source, metric_key, period)` makes
re-ingestion idempotent.

## CLI / API

- `rcm-mc data refresh --source all` — triggered refresh.
- `rcm-mc data status` — last-refresh-per-source.
- `GET /api/data/sources` — same status, JSON.
- `GET /api/data/hospitals?state=IL&beds_min=300` — query benchmarks.

## Public deals corpus

[`rcm_mc/data_public/deals_corpus.py`](../RCM_MC/rcm_mc/data_public/deals_corpus.py)
— **1,055 publicly-disclosed hospital / DSO / behavioral /
physician-services deals** across 105 seed files (`deals_corpus.py`
with 50 + `extended_seed_1.py` through `extended_seed_104.py`).

Source attribution on every row: SEC filings, press releases,
investor presentations, 10-Ks, Bloomberg company profiles,
Businesswire releases.

Schema:

```sql
CREATE TABLE public_deals (
    deal_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id          TEXT NOT NULL UNIQUE,
    source             TEXT NOT NULL DEFAULT 'seed',
    deal_name          TEXT NOT NULL,
    year               INTEGER,
    buyer              TEXT,
    seller             TEXT,
    ev_mm              REAL,
    ebitda_at_entry_mm REAL,
    hold_years         REAL,
    realized_moic      REAL,
    realized_irr       REAL,
    payer_mix          TEXT,     -- JSON
    notes              TEXT,
    ingested_at        TEXT NOT NULL
);
```

Separate SQLite file from the main portfolio store — the corpus is
read-mostly, append-occasionally, and may be shared across platform
instances as a static reference dataset.

## Coverage gaps

Per [`RCM_MC/docs/README_LAYER_DATA.md`](../RCM_MC/docs/README_LAYER_DATA.md):

- No Medicaid MCO distribution; collapses into `MANAGED_GOVERNMENT`.
- No OPPS (outpatient prospective payment system).
- IRS 990 requires seeded `ein_list.json`.
- Care Compare schema drifts across CMS releases.
- HCRIS refresh is semi-manual.

## Not a data source

What the loaders **do not** do:

- They do not fetch seller-supplied diligence material. That is an
  analyst upload via `document_reader.py` / `intake.py` into the
  deal's own store — never commingled with public benchmarks.
- They do not call out to LLMs. Every ingestion path is a
  parser over structured files.
- They do not phone home. There is no telemetry, no analytics, no
  licensing check.
