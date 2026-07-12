# IFT Sourced Evidence Master v3.8 - delta note

## Run 4 scoreboard (before -> after)

The order is judged on six externally-checkable outcomes, in priority order.
This revision lands all three must-have outcomes (1-3) in full and is honest
about the rest.

| # | Outcome | Before (v3.7) | After (v3.8) | Status |
|---|---------|---------------|--------------|--------|
| 1 | 4.1 990 sweep reclassification | 7 "transport" appearances incl 4 ED-staffing ($12.9M top row) | 3 classified transport appearances; 4 ED-staffing quarantined | **MET** - check passes |
| 2 | 4.3 mileage-loaded pricing | dollar panels base-only | two price columns (base-only + mileage-loaded), both live, derivation on Derived_Rate_Card | **MET** - check passes |
| 3 | zero RED rows | 2 RED (Input_Cost, Press_Footprint) | 0 RED (Slide_Feed GREEN 28 / AMBER 10 / RED 0) | **MET** - check passes |
| 4 | 4.2 contract corpus scope flags | no scope column | unchanged | NOT STARTED |
| 5 | 4.4 commercial MRF | one schema row | unchanged | NOT STARTED |
| 6 | 4.10/4.12 Study_Synthesis + extract | absent | unchanged | NOT STARTED |

**Honest statement:** this run completed all three must-have outcomes (1, 2, 3)
with verified checks and did not reach outcomes 4-6. The three defects it fixes
were the ones the external audit called worst: a $12.9M ED-staffing contractor
headlined as transport; every dollar panel understating revenue per transport by
the 43-45% mileage share; and two RED (evidence-absent) exhibit rows on the deck
feed.

## Outcome 1 (4.1) - 990 sweep reclassification, MET

`Footprint_990_Sweep` now classifies every transport-keyword hit
(GROUND TRANSPORT / AIR TRANSPORT / ED STAFFING / COURIER-LOGISTICS /
OTHER-AMBIGUOUS) from the verbatim services text plus the contractor name, with
the rules printed on the tab. The seven raw appearances resolve to:
- 4 ED STAFFING (quarantined in a labelled exclusion panel): Wisconsin
  Emergency Medical Service Asso (ER provider coverage, $12.9M + $6.97M),
  Emergency Physicians of NWO (ED staff, $10.5M + $7.56M);
- 2 AIR TRANSPORT (PHI Air Medical) + 1 GROUND TRANSPORT (Mercury Ambulance)
  = 3 classified transport appearances that feed every read panel and finding.

**Check (auditor runs it verbatim):** the strings "EMERGENCY ROOM PROVIDER
COVERAGE" and "EMERGENCY MEDICAL STAFF" appear only in rows classified ED
STAFFING, and in no headline figure, read panel or finding. **PASS** (verified:
0 occurrences outside ED-staffing rows).

## Outcome 2 (4.3) - mileage-loaded pricing, MET

`Derived_Rate_Card` gains a mileage-loading derivation: A0425 miles per
transport computed two ways (MMT_Medicare_Book units/base-services ~14.6, and
the national Medicare_IFT_Series mileage $ per transport), CY2024 measured
(national base C19/B19 vs loaded total E19/B19) and CY2026 forward (A0428 base +
miles x AFS rate), with the loading factor live. `Scenario_Matrix` gains Panel
B2: two price columns per price basis - BASE-ONLY (green link to the measured
base allowed per transport) and MILEAGE-LOADED (the measured total incl
mileage) - both live formulas, and base-only vs loaded floor per volume basis.

**Check:** Scenario_Matrix contains two price columns per price basis
(base-only, mileage-loaded), both live formulas, loading derivation printed on
Derived_Rate_Card. **PASS.**

## Outcome 3 (zero RED rows) - MET

The two RED rows on `Slide_Feed` pointed at two evidence modules that were
written to completion but never wired into the build order, so their tabs never
appeared and the deck-feed status scan (which reads live tab presence) left both
rows RED:
- **`Input_Cost_Index`** (+ `Public_Operator_Benchmarks`) from `sec_b11_inputs`:
  diesel by PADD (EIA weekly retail), the PPI diesel and ECEC compensation
  series (BLS), and the QCEW wage leg, each printed separately against the
  Medicare payment update (no blended basket - house rule); the ambulance-
  industry PPI (BLS `PCU621910621910`) stays a bordered PENDING naming the
  series, because BLS returns "series does not exist" for it.
- **`Press_Footprint_Registry`** (+ `State_EMS_Licensure`) from
  `sec_xb_registries`: dated public press/newsroom rows and the archived-website
  self-claim series (Wayback + Common Crawl), plus the four-state licensure
  universe against PECOS enrollment and Medicare billing.

Both modules now build BEFORE the assembly module, so the Slide_Feed scan sees
their tabs and flips both rows to GREEN. Their fact/source/finding IDs are
assigned LAST (via a build-order-independent `id_order()`), so every already-
shipped ID keeps its number: existing facts F1-F598 are unchanged, the four new
tabs occupy F599-F609 / S419-S435 / findings 104-107 (the exact append points
the order specified).

**Check:** Slide_Feed status counts recompute live to GREEN 28 / AMBER 10 /
**RED 0**. **PASS.**

## Verification
- Two-pass LibreOffice recalc: zero error cells, carried v2.7 cells reproduce,
  all charts pass the V9 gate, format gate PASS, ledgers contiguous
  F1-F609 / S1-S435.
- Firewall leak check clean (new tabs scanned); static live-reference audit
  clean; append-only fidelity confirmed against v3.7 (F1-F598 identical except
  the one 4.1-corrected fact F591, same ID).

## What remains (outcomes 4-6)
- 4.2 contract-corpus scope flags + USAspending award enrichment.
- 4.4 commercial MRF streaming (Medica / BCBS NE / Wellmark first).
- 4.9 targeted per-NPI annual pulls; 4.10 Study_Synthesis; 4.12 deck extract.
