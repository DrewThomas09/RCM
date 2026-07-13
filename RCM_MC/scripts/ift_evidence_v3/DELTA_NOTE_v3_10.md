# IFT Sourced Evidence Master v3.10 - delta note

## Editorial pass: professional register on every title and subtitle

v3.10 is presentation only. It rewrites the title (A1) and subtitle (A2/A3) of
every tab out of the conversational house style into a declarative one. No data,
finding, ledger, chart or read-panel content changes; the ledgers stay
F1-F609 / S1-S435 and no ID moves.

### What was removed
- **The "The question: ..." subtitle frame** - present on 313 of 328 tabs
  (including 40 carried v2.7 tabs, where the frame originated). Each subtitle
  now leads with what the exhibit shows and its source, not a rhetorical
  scoping question. Where a leading interrogative was followed by a substantive
  sourced remainder, the question is dropped and the remainder kept; the tab's
  title and read panel already state its scope.
- **Title flourishes** - `" - the decision record"`, `", measured:"`,
  `": the full certified registry"`, and the `"X - the Y"` construction are
  reduced to plain descriptive names (e.g. `Methodology - the decision record`
  -> `Methodology`; `Fragmentation, measured: the US ...` ->
  `Fragmentation: the US ...`; `Hospitals: the full certified registry` ->
  `Hospitals: certified registry`).
- **Rhetorical asides** - "stated plainly", "at a glance", "in one page", and
  the "This tab is / carries ..." self-reference are stripped.

### Marquee tabs
Methodology and Study_Synthesis carried the conversational register into their
subtitle bodies ("why should anyone trust this workbook?", "this is the deck
spine - the walk from ..."), so both get a bespoke declarative subtitle.

### Totals
- 117 titles and 313 subtitles rewritten.
- Title-block edits on carried v2.7 tabs are recorded to
  `professionalize_changes.json` and excluded from the V1 carried-cell
  fidelity gate, because a title/subtitle is presentation, not evidence. Every
  carried v2.7 DATA cell remains byte-identical.

## How it works
The pass (`professionalize.py`) runs last in the build, after the CIM format
pass, over the assembled workbook. It applies a systematic rule set for the
long tail (strip the meta-frame, drop the interrogative scope, clean the
flourishes) plus a small curated map of bespoke titles and subtitles for the
marquee tabs. Because it runs before the LibreOffice recalc, the deck-feed
extract inherits the professionalized text.

## Verification
- Two-pass LibreOffice recalc: zero error cells; carried v2.7 DATA cells
  reproduce (title-block presentation cells excluded); recompute clean; all
  charts pass the V9 gate; format gate PASS on all tabs; ledgers contiguous
  F1-F609 / S1-S435.
- Firewall leak check clean; static live-reference audit clean; repo invariants
  pass (Methodology body unchanged, so its rebuild assertions still hold).

## Not in this pass
Body prose (read panels, section banners, table cells) is out of scope - this
pass is titles and subtitles only. The remaining Run 4 tail (commercial-rate
MRF, the per-NPI annual trajectory) is unchanged; see DELTA_NOTE_v3_9.md.
