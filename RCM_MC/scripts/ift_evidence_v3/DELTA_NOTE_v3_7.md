# IFT Sourced Evidence Master v3.7 - delta note

**The pass:** the CIM-grade presentation pass (Run 3, Block U). The standard:
any tab, screenshotted at 100% zoom, must be pasteable into a confidential
information memorandum appendix without edits - a titled, sourced, cleanly
formatted exhibit, not a working file. v3.7 makes that true everywhere and
locks it in with a committed gate. No evidence changed; this is presentation
only. Built on the merged v3.6 base.

## What changed
- **`cim_format.py` - the presentation pass**, run last on every build. On
  EVERY tab (including the carried v2.7 and early-v3 tabs the SheetBuilder
  never touched): gridlines off, a section tab colour, freeze panes below the
  title block, cursor at A1, 100% zoom, and an explicit number format on every
  numeric cell - counts get thousands separators, the Fact_Ledger value column
  gets a value-preserving grouped format, years stay bare, and literal
  None/nan artifacts are cleared.
- **`format_gate.py` - the committed format gate** (Block U.6), run beside the
  verification gates. It fails the build if any tab has gridlines on, no tab
  colour, no freeze panes, no bold A1 title, a numeric cell left on General
  format holding a raw float or a non-year large integer, or any None/nan
  text. From this revision on, no build ships without the format gate passing.
- **`Style_Standard` tab** (Block U.1) - the written standard the gate
  enforces, stated in one reference tab.

## What the audit found and fixed (before -> after)
- Gridlines on: 25 tabs -> 0
- Tabs without a section colour: 26 -> 0
- Tabs without freeze panes: 2 -> 0
- Numeric cells on General format (raw floats / unformatted counts): ~195
  across Fact_Ledger, Verification_Log, Certification_Series, Pull_Manifest
  -> 0
- Literal None/nan text cells: 1 -> 0
- Formula-as-text cells: 0 (the pipeline already stores all 55k+ formulas as
  live formulas; the earlier-version bug the order cited is already fixed)

## Scale delta
| | v3.6 | v3.7 | added |
|---|---|---|---|
| Tabs | 322 | 323 | +1 (Style_Standard) |
| Facts | F598 | F598 | - |
| Sources | S418 | S418 | - |
| Charts | 228 | 228 | - |
| Size | 31MB | ~31MB | - |

Facts, sources, findings and charts are unchanged - v3.7 touches presentation
only. The one new tab is documentation (Style_Standard), carrying no facts.

## Verification
- Two-pass LibreOffice recalc: zero error cells, carried v2.7 cells reproduce
  (0 diffs), all charts pass the V9 house-style gate, ledgers contiguous.
- Format gate: PASS on every tab (format_gate.json).
- Firewall leak check clean; static live-reference audit clean.
- Render proof: a sample of exhibit tabs rendered to PDF via LibreOffice and
  visually inspected for clipping, overflow and density (Render_Proof_v3_7.pdf).
