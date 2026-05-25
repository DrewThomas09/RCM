# Deal Library — licensed export ingestion

This directory is where you drop **market-data exports you produced under your
own license** (Capital IQ Screening / plug-in workbooks, PitchBook, or any
CSV). The ingestion pipeline normalizes them into PEdesk's Deal Library.

**Compliance (non-negotiable):**
- PEdesk does **not** scrape Capital IQ / NetAdvantage or automate their web UI.
- It ingests only files **you** exported under your license.
- Raw exports and anything derived from them are **git-ignored** (`.gitignore`
  here) — they are proprietary and must not be committed/redistributed.
- Licensed-export data is kept distinct from public CMS data and from your own
  portfolio/deal data, and is never relabeled as public.

## Run

```bash
.venv/bin/python scripts/ingest_deal_library_exports.py \
    --in data/vendor/deal_library \
    --source-system "Capital IQ"
```

Outputs (also git-ignored): `deal_library_companies.csv` (normalized),
`deal_library_ingest_report.json` (rows, missingness by field, unmapped
columns, duplicate candidates). Load into SQLite with
`rcm_mc.data.deal_library.load_companies_csv(store, csv_path)`.

## What the two profiled exports actually are

`Company Screening Report*.xls` are **company** screens — sponsor-backed
healthcare companies (Health Care · sponsor-backed · US/Canada · Operating),
~12.3k rows combined. They are **not** M&A transactions: there are no
buyer/seller/announce-date/deal-value columns. They normalize to the **company
library** schema (`docs/PEDESK_DEAL_LIBRARY_SCHEMA.md`). To populate a
*transactions* table, run a Capital IQ **Transactions** screen instead.

Financial fields are sparse (EV/EBITDA ~97% blank, revenue ~74% blank — these
are private companies). Missing stays **NULL**, never 0. The dense, high-value
columns are **sponsor owner (~99%)**, industry, status, geography/state,
website, and revenue for ~26%.
