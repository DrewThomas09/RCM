# IFT Sourced Evidence Master v3.6 - delta note

**The pass:** the return-leg structure pass. v3.5 measured the SNF return-leg
quality rates (X-A.4); v3.6 asks the structural question an operator cares
about - do a SNF's ownership, scale, and star rating predict how much
return-leg (bounce-back) transport it generates? It joins the CMS SNF Quality
Reporting Program claims measures to the CMS Nursing Home provider-info file
on the CMS Certification Number (a 1:1 join over all reporting SNFs) and
cross-tabs the bounce-back and discharge-to-community rates by ownership,
certified-bed scale, and 5-star rating. Built on the merged v3.5 base (#1945).

This revision also **restores the verification gate script**: the v3.5 package
had picked up `verify.py` in a stale form (a short chart-audit exploration
script had overwritten it in the scratchpad after the last clean run, and the
package step copied that). The deliverable workbook was unaffected - it was
built by the assembler and the gates had run clean on the pre-fix build - but
the committed script could not reproduce the gates. v3.6 restores the full
325-line gate script and re-runs it for real against the whole workbook (all
v3.5 content plus the new tab), which also retroactively validates the three
small v3.5 audit fixes.

## Scale delta
| | v3.5 | v3.6 | added |
|---|---|---|---|
| Tabs | 321 | 322 | +1 |
| Facts | F596 | F598 | +2 |
| Sources | S417 | S418 | +1 |
| Findings (module, live-ref) | 102 | 103 | +1 |
| Charts | 227 | 228 | +1 |
| Formulas (recalc, 0 errors) | 55,285 | 55,294 | +9 |
| Size | 31MB | 31MB | - |

The formula delta (+9) is the eight live formulas the new tab adds plus the
one v3.5 fix (the SNF national worst-decile share became an E/B formula) that
the restored gate now recalculates for real - it lands with zero errors,
which retroactively confirms the v3.5 fix.

## New tab
- **SNF_ReturnLeg_Structure (X-A.5)** - joins the SNF QRP claims measures
  (dataset fykj-qjee) to the CMS Nursing Home provider-info file (dataset
  4pq5-n9py) on the CCN, over all reporting SNFs, and cross-tabs the
  risk-standardized potentially-preventable readmission (PPR = bounce-back
  transport demand) and discharge-to-community (DTC) rates by:
  - ownership bucket (For profit / Non profit / Government),
  - certified-bed scale band, and
  - overall 5-star rating.
  Headline structure: for-profit SNFs carry a higher median bounce-back rate
  and send fewer patients home than non-profit, and the 5-star rating is a
  clean monotonic gradient - the return-leg transport demand concentrates in
  for-profit, lower-rated SNFs. National medians plus a footprint slice, a
  for-profit vs non-profit gap panel with live formulas, and a chart.

## Anchors that moved
- None. Fact IDs F597+ and source IDs S418+ append after the v3.5 maxima. The
  v2.7 base and every v3.0-v3.5 tab are byte-for-byte unchanged; v3.6 is
  purely additive (one new analysis tab plus the restored gate script).

## Verification
- The RESTORED gate script re-run for real (two-pass LibreOffice recalc):
  zero error cells, carried v2.7 cells reproduce (0 diffs), all charts pass
  the V9 house-style gate, ledgers contiguous.
- Firewall leak check clean; static live-reference audit clean.
- Repo invariant tests pass.
