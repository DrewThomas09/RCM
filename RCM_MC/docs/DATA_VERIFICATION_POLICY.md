# Data Verification Policy

Every PEdesk page that renders figures must **disclose its data basis**. No page
quietly relies on fake, synthetic, demo, seed, or hardcoded values without a
visible label. This is enforced by `scripts/audit_page_data_sources.py`
(report: `docs/reports/PAGE_DATA_SOURCE_AUDIT.md`) and a regression test.

## Required disclosure (one of)

`LIVE` · `DERIVED` · `CMS PUBLIC DATA` · `HCRIS PUBLIC DATA` ·
`CIVHC PUBLIC DATA` · `LICENSED REPORT DERIVED` · `LICENSED MARKET DATA DERIVED` ·
`BENCHMARK CORPUS` · `SEED / ILLUSTRATIVE CORPUS` · `USER DATA REQUIRED` ·
`DATA REQUIRED` · `ILLUSTRATIVE` · `EXPERIMENTAL`

## How disclosure is expressed in code

- **`ck_source_purpose(purpose=, universe=, source=, next_action=)`** — the
  diligence source/purpose header band (preferred for analyzers).
- **`ck_illustrative_note("<figures>")`** — the inline illustrative banner for
  seed-corpus / hardcoded-figure pages.
- A `universe="…"` chip, or an explicit `DATA REQUIRED` / `EXPORT REQUIRED`
  string for pages awaiting a real source.

A page that renders `ck_kpi_block` / `ck_value_anchor` / tables or calls a
`compute_*` model **and** carries none of the above is **flagged NO_DISCLOSURE**
and must be fixed (add the matching label; never fabricate a source).

## Tier taxonomy (single source of truth)

`rcm_mc/diligence/surface_status.py` — green (real) / navy (calculator on your
inputs) / yellow (illustrative seed corpus) / red (synthetic/hardcoded). The
`/tools` circles and `docs/PEDESK_DILIGENCE_SURFACE_STATUS.md` both read it.

## Non-negotiables

No fake data; no synthetic presented as real; no demo presented as live; no
unsupported "corpus-calibrated" / invented-benchmark / invented-model-performance
language; no screenshots as canonical data when exports exist; no raw licensed
PDFs served; no long verbatim report reproduction. Real numbers only carry a
real source label; everything else is labeled illustrative / data-required.
