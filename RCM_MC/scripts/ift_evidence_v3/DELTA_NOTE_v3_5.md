# IFT Sourced Evidence Master v3.5 - delta note

**The pass:** the completion pass. v3.4 turned the evidence inventory into
deal-grade analysis but deferred four items to a usage limit and to portal
blocks. v3.5 closes them from public sources: the footprint-wide nonprofit
990 sweep, the SNF return-leg quality layer, the CMS Hospital-at-Home
participant list, and the full ten-state Medicaid rate card. Built on the
merged v3.4 base.

## Scale delta
| | v3.4 | v3.5 | added |
|---|---|---|---|
| Tabs | 318 | 321 | +3 |
| Facts | F585 | F596 | +11 |
| Sources | S409 | S417 | +8 |
| Findings (module, live-ref) | 99 | 102 | +3 |
| Charts | 223 | 227 | +4 |
| Formulas (recalc, 0 errors) | 55,236 | 55,285 | +49 |
| Size | 31MB | 31MB | - |
| Printed pages (est.) | ~13,100 | ~13,118 | - |

Fact IDs F1-F596 and source IDs S1-S417 are contiguous with no gaps; the
v2.7 base and every v3.0-v3.4 tab are byte-for-byte unchanged (10,464 carried
cells recalculate with 0 diffs).

## Tabs added (v3.5)
- **Footprint 990 sweep (X-C.1):** Footprint_990_Sweep - the footprint-wide
  extension of the E.3 cohort sweep. ProPublica Nonprofit Explorer + IRS 990
  e-file XML, every reachable multi-hospital nonprofit system operating in
  the ten-state footprint. Unlike the 9-system cohort (which disclosed zero
  transport contractors in its top five), the regional filers DO name
  transport vendors: seven transport-contractor appearances across four
  operators ($2.06M to $12.9M), including Mercury Ambulance (UofL Health KY,
  ground) and PHI Air Medical (Centra VA, air). The information floor is
  stark - one filer discloses 2,090 contractors over $100K with five named.
- **SNF return-leg quality (X-A.4):** SNF_Return_Leg_Quality - CMS SNF
  Quality Reporting Program provider data (dataset fykj-qjee), two claims-
  based, risk-standardized measures that bracket the post-acute return leg:
  discharge-to-community (a completed episode, less future transport) and
  potentially preventable 30-day post-discharge readmission (the SNF-to-
  hospital bounce-back, more transport). Names the worst-decile footprint
  SNFs by CCN, city and provider so they join to the corridor and hub-spoke
  maps.
- **Hospital-at-Home participants (B.7):** Hospital_at_Home_Participants -
  the CMS Acute Hospital Care at Home (AHCAH) approved-facility list,
  machine-readable, sliced to the footprint and joined to the research
  cohort. Home-based acute care is a structural substitute for one leg of
  IFT demand; this names the facilities running it in the study footprint.

## Tabs extended (v3.5)
- **Medicaid_Rate_Card (B.3):** extended from six footprint states
  (NE/IA/KS/MO/OH/WI) to the full ten plus Virginia by adding MN, IN, KY and
  VA from each state's published fee schedule. Virginia non-emergency is
  broker-billed (DMAS NEMT) and is recorded with the broker-carve caveat
  rather than as a direct fee.

## Anchors that moved
- None. Fact IDs F586+ and source IDs S410+ append after the v3.4 maxima.
  The carried v2.7 evidence base and every v3.0-v3.4 tab are byte-for-byte
  unchanged; v3.5 is purely additive.

## What v3.5 closes from the v3.4 "insufficient evidence" list
v3.4 shipped four items as bordered PENDING with the dataset named. v3.5
retrieves three of them from public sources and completes the fourth:
- SNF QRP (X-A.4): retrieved. The full measure table was paginated from the
  CMS Provider Data Catalog datastore and pivoted per CCN.
- Hospital-at-Home participants (B.7): retrieved. The CMS AHCAH list was
  machine-readable this pass.
- Footprint-wide 990 sweep (X-C.1): completed. 78 systems attempted, 64
  resolved, 128 filings parsed.
- Medicaid rate card: completed to the full ten-state footprint plus VA.

Still bordered PENDING with the dataset named (genuinely non-public or
license-gated, unchanged from v3.4): IFT-specific facility-pay share
(claims-vendor panel), commercial MRF rates (Transparency-in-Coverage
stream-parse), formal trauma/stroke/STEMI designations (ACS/TJC JS-gated),
and the MA-encounter / T-MSIS / HCUP / AHA / NEMSIS request drafts (B.14).

## Verification
- Firewall leak check (D.3): scanned every cell of the tabs added since
  v3.3; zero customer/account language, zero survey statistics, zero em
  dashes (leak_check.json).
- Two-pass LibreOffice recalc: zero error cells, carried v2.7 cells
  reproduce (0 diffs), all charts pass the V9 house-style gate, IDs
  contiguous.
- Adversarial static audit (audit_agent_work.py): every module finding
  resolves to a live numeric reference; zero cross-tab links to blank or
  missing cells.
