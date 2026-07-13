# IFT Sourced Evidence Master v4.2 - delta note

## Run 6.5: the Komodo linkage spec - the one licensed dataset that closes the public dead-ends

Every public route the study could take has now been walked. Several ended at a
wall the public record cannot pass: the commercial IFT rate sits behind payer
machine-readable files that would not retrieve (MRF_Attempt_Log), all-payer
transport volume and payer mix are invisible in Medicare data, the institutional
wedge is only estimable top-down from Medicare (Institutional_Ambulance_Wedge),
and the real facility-to-facility transfer network cannot be built from public
claims. v4.2 names the single licensed asset that would clear every one of those
walls - Komodo Health's all-payer Healthcare Map - and ships it exactly as the
ResDAC receiving schema was shipped in v4.1: as a named LINKAGE PLAN, not a data
source. Appended F622-F623, source S447, finding 117; no shipped ID renumbered.

## Komodo_Linkage_Spec (the new tab)

**What Komodo is (Panel A, CLAIMED, tier C).** Komodo's Healthcare Map is an
all-payer, closed-and-open claims asset. Its public marketing describes "more
than 330 million" US patient lives, "160 million closed, linkable lives per
year," and "over 100 million" patients covered by Medicare, Medicare Advantage
and Medicaid plus commercial and self-insured plans, with insurance status on
"more than 200 million" lives via Komodo Patient Insurance. These are Komodo's
own figures, cited to komodohealth.com and its press releases, carried only to
size what an engagement would reach - never as study evidence, and labeled
CLAIMED throughout.

**The linkage keys (Panel B).** The model already keys on every join Komodo
needs: the resolved MMT estate and participant NPIs (provider), ground ambulance
A0425-A0436 with the QN/QM and origin-destination modifiers (service), revenue
centres 0540-0549 and place of service (the institutional grain of the wedge),
payer/plan via KPI (the all-payer dimension no public file carries), and closed-
life longitudinal linkage (the sending-to-receiving patient journey). Each key
points at the workbook tab it joins from.

**What Komodo closes (Panel C, all outputs PENDING).** Six currently-open or
carrier-limited items, each mapped to the Komodo query that fills it: the
commercial rate (the MRF dead-end), all-payer volume beyond the 11.3M Medicare
book, the institutional wedge measured all-payer rather than inferred Medicare-
only, payer mix per operator, the real transfer-flow network, and the subject
company's all-payer book. Every output cell is bordered PENDING an engagement.

**Receiving schema (Panel D, PENDING).** Eight Komodo extract fields mapped to
the exhibit each one fills on landing - the same discipline as the ResDAC
schema, so that on the day an extract arrives the fills are mechanical.

## The firewall, held exactly

Komodo is LICENSED and commercial - it is not public and not reproducible - so it
sits OUTSIDE the study's public-source firewall as evidence. This tab is the plan
for an engagement, not the engagement: a Komodo engagement is a commercial
contract and data license (a human action item), not a public pull. Nothing here
measures the IFT market from Komodo. The public estimates already in the workbook
- the ~581K institutional wedge, the balance-billing rate pegs, the Medicare-FFS
book - stand until a Komodo extract replaces them. The only Komodo values printed
are the vendor's own public scale claims, labeled CLAIMED (tier C).

## Verification
- Two-pass LibreOffice recalc: zero error cells; carried v2.7 cells reproduce;
  recompute clean; charts pass the V9 gate; format gate PASS; ledgers contiguous.
- Firewall leak check clean, with the new-cell conversation scan; the Komodo tab
  carries no customer/account/client-list language and no survey statistics.

## Human action item (this week)
1. Request a Komodo Healthcare Map scoping call and quote for the ambulance
   HCPCS x payer x revenue-centre extract described on Panel D.

## Not in this pass
Program Statistics mining (1B) and the SNF-specific consolidated-billing
intensity (1D) remain named next steps, along with the twelve-year per-NPI book
carried from Run 5; see the Run_Log open-items register.
