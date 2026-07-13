# IFT Sourced Evidence Master v4.0 - delta note

## Run 5: the billing-flag pass plus the closing tail

v4.0 adds five public evidence layers, all appended (no shipped ID renumbered):
facts from F610, sources from S436, findings from 108. The scoreboard against
the six ordered checks:

| # | Check | Status |
|---|-------|--------|
| 1 | QM/QN series exists and reconciles | DONE |
| 2 | SNF-bundling row in the reconciliation with a primary cite | DONE |
| 3 | Software landscape ships fully public-cited | DONE |
| 4 | Hospital-team prevalence panel (HCRIS + registry) | DONE |
| 5 | MRF landed or formally closed; twelve-year book | MRF CLOSED (3 logged attempts); 12-yr book PENDING (named) |
| 6 | Deck extract ships | DONE |

## Check 1 - Modifier_QM_QN_Series (the highest-value work)

Medicare carrier ambulance lines carry a SECOND HCPCS modifier naming the billing
relationship: QN (furnished directly by a provider of services) and QM (under
arrangement). The existing PSPS cache aggregated only the initial (origin-
destination) modifier, so QN/QM were never captured. A fresh pull re-cut all
seven ground A-codes by the second modifier, by year 2010-2024 (105 slices,
manifested). New tab **Modifier_QM_QN_Series**: services, allowed dollars and
shares by flag by year, the BLS/ALS/SCT split, an origin-destination joint cut,
and a live reconciliation row that ties this cut's totals back to the existing
PSPS series (delta zero). Wired into **Insourcing_Bounds** as a third measured
leg beside the H1/H2 name bounds and the Care Compare roster.

The honest read: a provider of services is the flagged biller on **0.120% of
2024 ground transports** (up nearly ninefold from 0.014% in 2010). This is a
STRICT floor - an order of magnitude below even the name-rule hospital-billed
floor (1.44%) - because QN/QM modifier compliance is incomplete; it shows no
acuity skew (flat across BLS/ALS/SCT). It confirms the DIRECTION of the
insourcing bounds name-free, not their level. F610-F614, findings 108-109.

## Check 2 - Payment_Rules (SNF consolidated billing)

New tab **Payment_Rules** states, from primary CMS sources (SSA 1888(e), 42 CFR
411.15(p)/409.27(c), Pub. 100-04 Ch. 6), that ambulance transports of a resident
in a covered Part A SNF stay are bundled into the SNF payment and never generate
a carrier claim - a rule-defined claims-invisibility channel. Exclusions (the
admission and discharge legs, and offsite dialysis and intensive-outpatient
round trips) stay separately billable and DO appear, which is why the dialysis
channel counts real transports. No magnitude asserted; the wedge is PENDING with
T-MSIS TAF named. Finding 110.

## Check 3 - IFT_Software_Landscape

New tab **IFT_Software_Landscape**: 14 platforms across the EMS-operations layer
(ImageTrend, ESO/Logis, ZOLL, Traumasoft, AngelTrack, Beyond Lucid, Julota,
CentralSquare, Tyler, First Due, Golden Hour) and the hospital transfer-center
layer (Central Logic/ABOUT, Motient, TeleTracking), each row cited to a public
URL with retrieval date, install bases labeled CLAIMED. A workflow panel
documents the request-cascade (VectorCare broadcast-to-ranked-vendors, Central
Logic preferred-vendor requests, Motient sourcing) and the acceptance-versus-
completion SLA split (the peer-reviewed AutoLaunch study). F615-F616, findings
111-112.

## Check 4 - Hospital_Ambulance_Prevalence

New tab answering how many hospitals field their own ambulance: a strict HCRIS
floor (**14.3%** of hospital cost-report filers book a Worksheet A line-95
ambulance cost centre - about one in seven) and a loose, collision-inflated
registry ceiling (~52% name-match to an ambulance NPI). The measured answer to
the guess that few do: they do not - hospital-fielded ambulance is common.
F617-F618, finding 113.

## Check 5 - MRF closed; twelve-year book named

**MRF_Attempt_Log** records three genuine attempts (Medica HTTP 403, BCBS
Nebraska 404 + a 2.5 KB index stub, Wellmark 403) and formally closes the
commercial-rate row as PENDING, with the balance-billing statutory pegs named as
the interim anchor. No fourth deferral. The twelve-year per-NPI book extension is
the named next pull (Run_Log open-items register); the Medicare book stays three
vintages this pass.

## Check 6 - deck extract

`IFT_Deck_Feed_Extract_v4_0.xlsx` ships, values-only.

## Verification
- Two-pass LibreOffice recalc: zero error cells; carried v2.7 data cells
  reproduce; recompute clean; charts pass the V9 gate; format gate PASS; ledgers
  contiguous.
- Firewall leak check clean, with the Run 5 addition: every new cell scanned for
  language traceable to any interview or conversation (none), and every workflow
  and market-practice description confirmed to cite a public document.
