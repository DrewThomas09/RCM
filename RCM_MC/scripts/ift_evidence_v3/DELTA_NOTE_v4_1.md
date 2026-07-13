# IFT Sourced Evidence Master v4.1 - delta note

## Run 6: the institutional wedge - the model's number-one open question

The QN/QM work (v4.0) proved that hospital-billed ground ambulance is
structurally invisible to the Part B carrier file the whole study is built from:
it rides on institutional (UB-04) claims. v4.1 sizes that wedge, two free public
ways, and stages the definitive claims measurement. Appended F619 onward,
sources from S445, findings from 115; no shipped ID renumbered.

## Institutional_Ambulance_Wedge (the home tab)

**Top-down (1A).** MedPAC's mandated report on ground ambulance (March 2025)
reports **11.4 million** Medicare FFS ground transports in 2023, the fee
schedule paying both suppliers and institutional providers. The carrier file
(the QN/QM re-cut) holds **10.72 million**. The residual - about **682,000
transports, ~6.0% of the book** - is billed institutionally and never appears in
any carrier-file exhibit. It is an interim, scope-approximate figure (MedPAC paid
transports vs carrier submitted services; the residual bundles hospital OP,
Part A inpatient-bundled, and SNF consolidated-billing), guarded as such.

**Bottom-up (1C).** HCRIS Worksheet A line-95 ambulance cost centre, FY2019-2023:
**875 hospitals** booked an ambulance operation in 2023 at **$3.27 billion** of
operating cost, implying between **1.2 and 2.4 million** transports of hospital-
run operation across all payers (cost divided by the workbook's GADCS cost-per-
transport range, mean $2,673 to median $1,340). This is the all-payer OPERATION
size - the ceiling context for the Medicare-institutional slice, not the slice
itself. The ambulance cost centre is paid under the fee schedule, so its HCRIS
CHARGE columns are inconsistently populated and were deliberately not used; the
reliable COST is used with the sourced GADCS rate range instead.

## HCRIS_Institutional_Roster

Every hospital ambulance operator in FY2023 (875 CCNs), ranked by ambulance
operating cost, with its Care Compare name, state, footprint flag, and bounded
implied operating volume. The per-facility roster of who runs a hospital-based
ambulance and at what scale - the operates-and-bills population the insourcing
bounds and the QN/QM flag measure from the claims side. Reconciles to the wedge
tab Panel B.

## The definitive route, staged (Workstreams 2-3)

Panel C ships the ResDAC Limited Data Set receiving schema (Hospital Outpatient
+ Inpatient + SNF, 2019-2024; all claim lines with revenue centre 0540-0549 and
HCPCS A0425-A0436), bordered PENDING. Panel D ships the application and
coordination specs verbatim and ready to send:

- **2A ResDAC LDS request** (human: organizational requester + DUA + fee).
- **2B T-MSIS TAF Medicaid** (human: bundle into the same request).
- **3A commercial-extract spec sentence** (human: to the sizing lead before the
  second extract, so the bottoms-up does not inherit the carrier-file wedge).

When the LDS lands, the PENDING cells fill with per-claim institutional transport
counts and dollars by year and the per-CCN institutional billing roster, and
they replace the Panel A interim wedge.

## Verification
- Two-pass LibreOffice recalc: zero error cells; carried v2.7 cells reproduce;
  recompute clean; charts pass the V9 gate; format gate PASS; ledgers contiguous.
- Firewall leak check clean, with the new-cell conversation scan.

## Human action items (this week)
1. Send the 3A commercial-extract sentence to the sizing lead.
2. Request the ResDAC quote and submit the 2A/2B LDS request.

## Not in this pass
Program Statistics mining (1B) and the SNF-specific consolidated-billing
intensity (1D) remain named next steps, along with the twelve-year per-NPI book
carried from Run 5; see the Run_Log open-items register.
