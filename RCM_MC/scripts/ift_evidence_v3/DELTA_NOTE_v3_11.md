# IFT Sourced Evidence Master v3.11 - delta note

## Visual pass: more charts + formatting tidy

v3.11 adds charts to the load-bearing measured series that carried numbers but
no visual, and tidies inconsistent body spacing. No data, finding, ledger or
read-panel content changes; the ledgers stay F1-F609 / S1-S435.

## Charts added (7, on 6 tabs)

Each is a native house-style chart built through the same `v3lib.add_chart`
helper the section modules use, so it is a LIVE range reference (it recomputes
with the workbook) and passes the V9 chart-integrity gate (title, single value
axis, category axis on the correct side, no smoothed lines, no secondary axis):

| Tab | Chart |
|-----|-------|
| Medicare_IFT_Series | Line - Medicare FFS interfacility transports per year, 2010-2024 |
| Medicare_IFT_Series | Line - Medicare FFS interfacility allowed dollars per year (incl mileage) |
| MMT_Medicare_Book | Bar - MMT Medicare FFS allowed dollars by vintage (2013/2019/2024) |
| Acute_IFT_Series | Line - acute-to-acute ED-origin transfer episodes per year, 2007-2023 |
| EMS_Transports | Bar - NEMSIS activations by type of service, 2024 |
| Facility_Pay_Layer | Bar - ambulance revenue per NPI by payer (GADCS mean) |
| RSNAT_Series | Bar - RSNAT prior-authorization cumulative Medicare savings by report |

The workbook chart count rises from 230 to 237. They were placed on the highest-
value analytical tabs - the demand spine, the subject-company book, the transfer
series, the type-of-service split, the payer mix and the prior-auth savings -
not on the raw provider-level microdata tabs (which have tens of thousands of
rows and are not chartable).

## Formatting tidy

A whitespace pass collapses the inconsistent double-spacing left by earlier dash
sanitization (e.g. "map  -  16 connectors" -> "map - 16 connectors") in body
text, restricted to v3-authored tabs so carried v2.7 evidence cells stay
byte-identical.

## Verification
- Two-pass LibreOffice recalc: zero error cells; carried v2.7 data cells
  reproduce; recompute clean; all 237 charts pass the V9 gate; format gate PASS
  on all tabs; ledgers contiguous F1-F609 / S1-S435.
- Firewall leak check clean; static live-reference audit clean; repo invariants
  pass.

## Not in this pass
The remaining Run 4 tail (commercial-rate MRF, per-NPI annual trajectory) is
unchanged; see DELTA_NOTE_v3_9.md.
