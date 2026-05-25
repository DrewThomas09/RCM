# PEdesk — NetAdvantage / S&P research ingest

NetAdvantage (S&P industry surveys, CFRA reports) is **qualitative research**,
not a transaction database. PEdesk treats it accordingly: user-provided reports
become document-level **source cards** for the Guide / research surfaces — never
a raw-data dump and never a substitute for the Deal Library.

## Rules

- **No bulk scraping, no automatic report downloading.** The user provides
  PDFs / extracted text/tables they are licensed to use.
- **No redistribution** beyond the user's allowed environment; raw reports are
  git-ignored like other licensed vendor data.
- **Quote limits respected.** The Guide *summarizes* and points to the source —
  it does not reproduce full reports.
- **Provenance shown** on every card (report title, publisher, date, the page/
  section a claim came from).
- Research cards are clearly distinct from PEdesk's own data and from public CMS
  data; a qualitative claim is never rendered as a computed metric.

## What to extract (qualitative only)

- Industry margin ranges, growth/structure commentary.
- Regulatory trends and timelines.
- Market structure / competitive dynamics.
- Key risks and diligence questions.

These feed:

- **RAG / Guide source cards** — a partner asks the Guide a sector question and
  gets a summarized answer with a citation to the user's licensed report.
- **Diligence context** — risks/questions surfaced alongside a deal, attributed
  to the source.

## What NOT to do

- Do **not** parse NetAdvantage into `deal_library_transactions` /
  `deal_library_companies` — it has no per-deal records; treating prose as
  structured data would fabricate values.
- Do **not** turn a survey's "typical margin ~X%" into a computed company
  metric. It is a cited reference range, shown as such.

## Suggested shape (when built)

A `research_source_cards` store: `card_id, source_title, publisher, source_date,
section_ref, summary, tags, license_scope_note, ingested_at`. Cards render in
the Guide's Sources tab and in a research catalog, each with its citation. Body
text stays within quote limits; the full report is never stored verbatim for
redistribution.

This is a planned channel — documented here so the qualitative/quantitative
boundary is explicit before any NetAdvantage ingestion is implemented.
