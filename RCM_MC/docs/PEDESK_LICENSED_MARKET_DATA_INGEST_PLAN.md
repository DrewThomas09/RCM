# PEdesk — licensed market-data ingest plan

How PEdesk uses commercial market-data platforms (Capital IQ, NetAdvantage,
PitchBook, …) **without scraping them or depending on them at runtime**. This
is the compliance contract behind the Deal Library; the code that implements it
lives in `scripts/ingest_deal_library_exports.py`, `rcm_mc/data/deal_library.py`,
`rcm_mc/data/capiq.py`, and `data/vendor/deal_library/`.

## Non-negotiable posture

- **No scraping.** PEdesk never automates a vendor web UI (Selenium / Playwright /
  bots), never circumvents export caps or rate limits, and never attempts to
  extract a vendor backend. There is **no runtime dependency** on Capital IQ or
  NetAdvantage — the live product never calls them.
- **User-provided licensed exports only.** PEdesk ingests files the user
  produced under their own license (Screening exports, Excel plug-in workbooks,
  NetAdvantage PDFs/tables), plus public/open datasets and the user's own
  deal/company data.
- **Provenance + missingness preserved.** Every ingested row keeps
  `source_system` / `source_file` / `source_sheet` / `source_row_id` and a
  `missing_fields` list. Missing means unavailable → stored as NULL, **never 0**;
  no value is inferred from a blank.
- **Source classes are kept distinct and never relabeled.** Licensed-export data,
  public CMS data, and the user's portfolio/deal data are separate; a licensed
  export is never presented as public data, and a public/derived estimate is
  never presented as an observed licensed fact.
- **No redistribution.** Raw licensed exports and anything derived from them are
  git-ignored (`data/vendor/deal_library/.gitignore`) and stay inside the user's
  licensed environment. Automated/bulk extraction or redistribution is a
  separate S&P entitlement (e.g. Xpressfeed), out of scope for this code.

## Three ingestion channels

**A. Capital IQ Screening exports** — companies / transactions / financial
metrics / valuation multiples / buyer-seller-sponsor data. Excel/CSV, capped
row exports; large pulls come as several batch files partitioned by
time / sector / deal-size / geography (the **user** does this partitioning in
the licensed UI — PEdesk just ingests the resulting files). Each batch should
carry a manifest row (below).

**B. Capital IQ Excel plug-in outputs** — structured metrics for known
identifiers (multiples, financial history, transaction fields, metadata). The
licensed user refreshes and saves the workbook; PEdesk ingests the saved file.
No PEdesk automation of login or the web UI.

**C. NetAdvantage / S&P research** — qualitative industry surveys, margin
ranges, regulatory summaries, macro trends. **Not** a transaction database:
user-provided PDFs/extracted text become document-level RAG source cards
(summarized, quote-limited, provenance shown), never a raw-data dump. See
`docs/PEDESK_NETADVANTAGE_RESEARCH_INGEST.md` (planned) for the source-card
approach.

## Batch manifest

`data/vendor/deal_library/source_manifests/capiq_export_manifest.template.csv`
fields: `batch_id, source_system, export_file, export_date, exported_by,
query_name, time_period, sector_filter, geography_filter, deal_size_filter,
deal_status_filter, row_count, notes`. One row per export so every ingested
record traces back to a named, dated, scoped query.

## Normalization → Deal Library

Exports normalize into the canonical schema in
`docs/PEDESK_DEAL_LIBRARY_SCHEMA.md` (`deal_library_companies`, and
`deal_library_transactions` for a future Transactions screen). The pipeline:
flexible header mapping (`column_aliases.py`), deterministic IDs, money/date
normalization, sponsor parsing, deterministic state derivation, completeness
score, conservative `(clean_name, state)` duplicate flagging, and an ingest
report (rows / missingness-by-field / unmapped columns / dup count).

## Entity resolution to CMS — and its validated limits

`rcm_mc/data/capiq.py` resolves a company name → CMS Medicare **CCN** by fuzzy
match against HCRIS, with a confidence score and a RESOLVED / AMBIGUOUS /
UNMATCHED status (ambiguity surfaced, never guessed). Matched entities can be
enriched with CMS public facility data.

**Validated reality (do not over-promise):** on the first two licensed exports
(sponsor-backed healthcare *companies*), a 120-row sample resolved **0%** to
HCRIS — because HCRIS is **hospitals only** and this universe is largely
non-hospital (VC-backed startups, devices, services, SaaS, physician groups,
REITs, public mega-caps). Useful CMS resolution requires (a) a hospital/provider
-specific export, and/or (b) other registries (NPI, Care Compare for HH/hospice/
SNF/dialysis, Part B) — and even then only the subset that are Medicare
providers will match. The crosswalk is built and correct; its *yield* depends
entirely on the input being provider-like.

## What the data honestly supports (from validation)

The first exports (~12,265 companies) are dense and reliable on **sponsor
ownership (~99%)**, industry (coarse — one value), status, geography/state, and
website (~86%); sparse on financials (revenue ~26%, EBITDA/EV ~2.5%). So PEdesk
uses them for:

- **Deal Library directory + sponsor/sourcing map** (`/deal-library`,
  `/deal-library/sponsors`) — the strong use.
- **Disclosed-financial multiples** (`/deal-library/comps`) — EV/Revenue &
  EV/EBITDA over the ~2% that disclose both, shown as a small-n benchmark
  distribution, **not** a prediction or a curated comp set.

It does **not** support full-universe multiples priors or Monte-Carlo inputs
(financials too sparse) — those need a Capital IQ **Transactions** screen, which
the pipeline + `deal_library_transactions` schema are ready to ingest.

## Find Comps / modeling (when transaction data exists)

When a Transactions export is ingested: comp scoring over the normalized
transactions with transparent match explanations and shown provenance/missing
fields (missing never treated as zero); and benchmark distributions
(P25/median/P75 by vertical) with sample size + missingness shown and a
small-n caveat — benchmark only, never a prediction claim.
