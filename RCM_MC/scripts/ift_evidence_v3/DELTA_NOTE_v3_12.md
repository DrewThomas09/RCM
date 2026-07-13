# IFT Sourced Evidence Master v3.12 - delta note

## Presentation polish: semantic status fills + zebra banding

v3.12 is a pure formatting pass. It changes no cell value, chart, finding or
ledger entry, so it is invisible to the carried-cell fidelity gate, the
recompute gate and the firewall leak check. The ledgers stay F1-F609 / S1-S435
and the chart count stays 237.

## What changed

1. **Semantic status fills (424 cells).** Every cell whose entire value is a
   `GREEN` / `AMBER` / `RED` / `PENDING` status token now carries a matching
   fill and font, so the exhibit register (Slide_Feed) and the quality gates
   read at a glance instead of as plain text:
   - GREEN - light green fill, dark green text
   - AMBER - light amber fill, brown text
   - RED - light red fill, dark red text
   - PENDING - light grey fill (the bordered-PENDING markers keep their border)

   The match is on the whole cell, so legend sentences ("Status rule: GREEN =
   ...") are left alone, and the 7,290 per-row `OK` QA flags on the microdata
   tabs are deliberately not touched (colouring them would be noise).

2. **Zebra banding (3,948 cells across 4 tables).** The long reference tables -
   Source_Register (435 sources), Source_Index, Findings and Slide_Feed - now
   get alternating row shading in the same grey already shipped on Fact_Ledger
   and Verification_Log, so the whole book bands identically. Banding is
   block-aware (it restarts under each panel header) and never overwrites a
   header or a status fill. Prose tabs (Investor_QA) are excluded on purpose -
   banding narrative paragraphs reads as noise, not structure.

3. **Header font (173 cells).** Navy and teal section-header cells are
   normalized to white bold so every table header reads the same.

## What did NOT change
The money columns were already currency-formatted (`$#,##0`, `$#,##0.00`) and
the share columns already `0.0%` by the section builders, so no number format
was altered. No new tab, no new text, no data.

## Verification
- Two-pass LibreOffice recalc: zero error cells; carried v2.7 data cells
  reproduce; recompute clean; all 237 charts pass the V9 gate; format gate PASS
  on all tabs; ledgers contiguous F1-F609 / S1-S435.
- Firewall leak check clean; static live-reference audit clean; repo invariants
  pass.

## Not in this pass
The remaining Run 4 tail (commercial-rate MRF, per-NPI annual trajectory) is
unchanged; see DELTA_NOTE_v3_9.md.
