# v3 section-builder contract

You are authoring ONE python module that builds a group of new tabs for the
"IFT Sourced Evidence Master v3.0" Excel workbook. Read
`/tmp/claude-0/-home-user-RCM/3de345a1-c58f-5ce6-b747-7cbb0636d5d9/scratchpad/V3_DESIGN.md`
first — it defines the product rule, your tabs, and the non-negotiables.

## File and API
Write `scratchpad/sections/sec_<key>.py` exporting:

```python
SHEETS = [
    {'name': 'Tab_Name', 'tab_color': 'FF1F6F8B'},   # in creation order
    ...
]

def build(wb, ctx) -> dict:
    ...
```

- `wb` is an `openpyxl.Workbook` (create sheets with `wb.create_sheet(name)` in
  SHEETS order).
- `ctx` keys: `lib` (the v3lib module — SheetBuilder, fonts, number formats,
  add_chart, cagr_formula), `repo`='/home/user/RCM', `cache`=path of
  ift_v3_cache (live-pull JSON artifacts + manifest.json), `accessed`='10 Jul 2026'.
- Return dict:
  - `facts`: list of dicts — the headline figures of your tabs for the Fact_Ledger:
    `{'metric','year','value_ref' ('Tab!B10') or 'value' (literal),'unit',
      'basis' (GOV|SOURCED|ACADEMIC|PUBLIC-WEB|DERIVED),'tier' ('A'|'B'),
      'source_keys': [...], 'locator','lives_on','cross_check'}`
    5–15 facts per tab: the numbers someone would quote.
  - `sources`: list — every dataset/document you cite:
    `{'key' (short slug, unique),'publisher','document','vintage','locator',
      'supplies','url','tier','accessed','powers':[tab names]}`
  - `excluded`: list — anything you deliberately kept out:
    `{'figure','value','source_label','why_excluded','what_would_make_citable'}`
  - `meta`: `{'notes': str, 'row_counts': {tab: n}}`

## Rendering rules (v2.7 house style — use v3lib.SheetBuilder)
1. Every tab: `title(...)` then `subtitle("The question: ...")` — one plain-English
   question the tab settles — then `blank()`, then `headers([...])`.
2. Every VALUE row carries a Basis cell chip (GOV / SOURCED / ACADEMIC /
   PUBLIC-WEB / DERIVED). Value cells hardcoded from a source use kind='src'
   (blue). Derived cells MUST be Excel formulas, kind='fml' (never pasted
   results). Cross-tab references kind='link'.
3. Source citations: cite the ORIGINAL publisher document/dataset with exact
   locator (dataset, vintage, table/field). The repo accessor or cache file that
   supplied it goes in an "Extraction" note (sheet foot `note(...)` or a column),
   not in the citation. Number formats from v3lib (FMT_INT, FMT_USD, FMT_PCT1...).
4. Time series: per-row/segment trend-eligibility flags where breaks exist;
   CAGR rows as live formulas via `lib.cagr_formula` with the window named.
   NEVER trend across a flagged break.
5. Every tab with a numeric series gets >=1 native chart via `lib.add_chart`
   (anchor to the right of or below the table). Chart series must reference
   live ranges on your tabs.
6. CMS small-cell suppression: counts derived from suppressed files are floors —
   say so in a note row.
7. Tier rule: 'A' only for values extracted directly from a primary dataset we
   pulled ourselves (cache artifacts) or a vendored file with provenance
   registry; 'B' for values carried from repo modules citing a document we did
   not reopen. Set basis 'SOURCED' for the latter per v2.7 convention.
8. HARD RULE — zero ILLUSTRATIVE numbers. The inventories name the banned
   figures (e.g. $6.5B TAM, $18-22B market, per-trip $450-1,700, 55/45 pay mix,
   2-4x commercial multiple, lever composites +2.9/+3.0/+6.0/+7.0%/yr, band %s,
   SAM/SOM 165.8x, demand_forecast 'rough' age-band CAGRs as GOV). If a table
   mixes sourced and modeled columns, carry the sourced columns and EXCLUDE the
   modeled ones, recording them in `excluded`.
9. Column-width discipline: pass col_widths so text columns are readable
   (~30-60 for prose, 10-14 for numbers). Wrap prose rows (`wrap=True`).

## Imports for repo data
```python
import sys
sys.path.insert(0, '/home/user/RCM/RCM_MC')   # rcm_mc package
sys.path.insert(0, '/home/user/RCM')          # connectors package
```
Call accessors at build time; degrade gracefully (if an accessor returns
None/unavailable, note it in meta and skip that block — never invent).

## Test loop (MANDATORY before you finish)
```
cd /tmp/claude-0/-home-user-RCM/3de345a1-c58f-5ce6-b747-7cbb0636d5d9/scratchpad
python3 harness.py <key>            # builds only your section, validates, saves
```
Fix every error/warning it prints. It checks: module loads, sheets build, facts/
sources schemas, value_ref cells exist and are non-empty, source keys referenced
by facts exist, charts present on series tabs, banned-figure scan. Then open the
saved test workbook with openpyxl and sanity-check 3 cells yourself.

Your final message: <=30 lines — per-tab row counts, fact/source counts,
anything you could NOT source (and therefore dropped), open risks.
