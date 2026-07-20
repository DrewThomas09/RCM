# IFT Sourced Evidence Master v4.3 - delta note

## Run 7: the national brand-name invisibility test - why GMR and Priority read as near-zero in NPPES, and why fleet (not licensed EMTs) is the scale unit

Finding #46 established that the ambulance supplier universes must never be mixed
(PECOS-enrolled 10,465 / billing NPIs 8,721 / QCEW establishments 5,820 / state-
licensed), and the NE/IA sweep already carried the local demonstration that one
NPI is not one truck (the AMR-Omaha NPI 1336315225 masking a historical
~35 vehicles / ~90 employees; the MMT estate of 24 active org NPIs against a
claimed 500+ vehicles; 21 base NPIs for the single GMR air entity Rocky Mountain
Holdings). Run 7 takes that same undercount and tests it at the **national brand
level** against the live NPPES API, then answers the sizing question it forces:
if you cannot count the operator, what do you count? Appended F624-F632,
sources S448-S454, finding 118; no shipped ID renumbered.

## Named_Operator_Undercount (the new tab, Panel A - OBSERVED, tier A)

Live NPPES NPI Registry API (v2.1) organization searches, `enumeration_type=NPI-2`,
run 2026-07-20 (NPPES name search covers Legal Business Name + DBA + former + other
names). The two real national private ground platforms are **Global Medical
Response (GMR)** and **Priority Ambulance** (Knoxville, TN - see the disambiguation
note below):

| Fact | `organization_name` query | NPIs returned | Reading |
|---|---|---:|---|
| F624 | `Global Medical Response` | **0** | The parent has no operating NPI - it is a holding company and bills only through subsidiaries. |
| F625 | `Rural/Metro` and `Rural Metro` | **0** | A major GMR ground brand - nothing under its own name. |
| F626 | `American Medical Response` | **65** | Fragmented across ~15 distinct legal names (AMR *of Connecticut / Massachusetts / Texas / Southern California / West / Mid-Atlantic / Northwest / Tennessee* …) **plus** local-brand DBAs that only matched because "American Medical Response" is a *former/other* name on those records (Randle Eastern, LifeFleet Southeast, Mercy Inc, Metro Ambulance, ParaMed, Hank's Acquisition Corp). |
| F627 | `Priority Ambulance` | **3** | All three are **"Shoals Ambulance LLC"** - one Priority regional brand. The other 21 brands do not carry the Priority name. |

This is the AMR-Omaha exhibit at national scale: the operator you would name in a
deal memo returns single digits to a few dozen NPIs, none of them tied to the
parent, because **NPPES enumerates the local legal operating entity and carries no
parent / ultimate-owner field.**

## Operator_Scale_Reference (Panel B - CLAIMED, tier C - company self-reports)

Carried only to size what the name search misses; never study evidence, labeled
CLAIMED throughout (same discipline as the vendor scale claims on the Komodo tab):

- **F628 - GMR (parent, incl. AMR):** "more than 7,000 ground ambulances and
  support vehicles," 382 air bases, "nearly six million patient encounters" last
  year (GMR fleet-expansion release, S449).
- **F629 - AMR (GMR's 911/IFT ground arm):** ~34,000 employees, "more than 27,000"
  paramedics/EMTs/RNs and other professionals, "more than 4.4 million" transports/yr,
  40 states + DC (amr.net / AMR profile, S450-S451).
- **F630 - Priority Ambulance:** ~400 emergency and non-emergency vehicles, 4,300
  employees, "more than 1,600 licensed paramedics and EMTs," 610,000 transports/yr,
  **22 brands across 15 states** - and Priority states it *deliberately preserves*
  each acquired company's name (priorityambulance.com/about, S452).

The gap is the finding: GMR runs 7,000+ vehicles / ~6M transports and its name
returns **0** NPIs; Priority runs ~400 vehicles / 610K transports across 22 brands
and its name returns **3**. A name-keyed roll-up in NPPES undercounts consolidated
scale by ~10-50x and misses the parent entirely.

## Fleet_vs_Labor_Predictor (Panel C - the sizing answer)

The whitespace the workstream had left open (the MMT 200,000+ missions / 500+
vehicles was carried but **deliberately never divided**). Run 7 answers *which
denominator recovers scale* using the two national anchors, and quarantines the
ratios themselves as MODELED:

- **F631 (DERIVED / MODELED -> Excluded_Not_Sourced):** transports per **vehicle**/yr
  = Priority 610,000 / 400 ≈ **1,525**; GMR 6.0M / 7,000 ≈ **857** (GMR's 7,000
  includes support vehicles and the 6.0M includes air encounters, so the true
  ground-ambulance ratio is higher and closer to Priority's). What would make it
  citable: company-actual ground-only unit counts x ground-only transports, or a
  Komodo/ResDAC per-unit pull.
- **F632 (DERIVED / MODELED -> Excluded_Not_Sourced):** transports per **licensed
  EMT/medic**/yr = Priority 610,000 / 1,600 ≈ **381**; AMR 4.4M / 27,000 ≈ **163**
  - and the denominators are **not comparable** (Priority reports "licensed
  paramedics and EMTs"; AMR reports "paramedics, EMTs, RNs *and other
  professionals*"). What would make it citable: a consistent field-EMT definition
  per operator, which no public dataset supplies.

**The answer: fleet is the better predictor of real transport volume.**
1. **Physical constraint -> stable ratio.** A unit can only run so many trips/day
   (unit-hour utilization targets ~0.30-0.50 for 911, higher for IFT - the study's
   own UHU lever, `ift_unit_economics.py`). Volume = capacity x utilization, and
   vehicles are the capacity unit, so `fleet x transports-per-vehicle` recovers
   scale in a bounded band.
2. **Availability and consistency.** Vehicle counts are independently observable -
   state EMS vehicle **permits**, DOT registrations, disclosed fleet - and counted
   the same way everywhere. "Licensed EMTs per company" is **not** consistently
   reported and is **not derivable from NPPES**: individual EMTs/medics rarely hold
   NPIs (they bill under the org), and those who do are not employer-linked. The
   labor pool exists nationally (399,868 NREMT EMTs vs 149,643 paramedics,
   `ift_service_levels.py`) but cannot be attributed to a company from the registry.
3. **Staffing ratios are noisy.** Single- vs dual-medic, 911 vs IFT mix, urban vs
   rural, and heavy part-time/per-diem staffing swing EMT-per-transport widely (the
   163 vs 381 spread, on non-comparable denominators). Vehicles do not carry that
   definitional slop.

**Honesty on strength:** with only two true national players this is a *structural*
argument (physical constraint + data availability), corroborated by two anchors -
not a fitted correlation. To *measure* it, assemble a panel of ~20-50 services with
(permitted vehicles, licensed-EMT count, transport volume) from state EMS vehicle
permits x CMS Medicare ambulance utilization (A0425-A0434) x disclosures, and
regress volume on each. Prediction: fleet R^2 materially > EMT R^2, EMT adding
signal only after conditioning on fleet (as a utilization proxy). This regression
is a next step, not a shipped result.

## Disambiguation note (paper-trail hygiene)

The national "Priority" here is **Priority Ambulance** (Knoxville, TN; Enhanced
Equity / Kohlberg-backed; 22 brands; 610K transports). It is **not** the repo's
existing "Priority Medical Transport" (North Platte, NE; acquired by AmeriPro /
Whistler Capital, Feb 2025) in `ift_npi_landscape.py`. Two different companies
sharing the word "Priority"; Run 7's F627/F630 are the Knoxville national roll-up.

## The firewall, held exactly

The NPPES counts (F624-F627) are a **primary pull we ran ourselves** - tier A,
OBSERVED, reproducible by re-running the four name queries against the public NPPES
API. The operator scale figures (F628-F630) are **company self-reports** - PUBLIC-
WEB / CLAIMED (tier C), carried to size the gap, never quoted as market
measurement. The two ratios (F631-F632) are **MODELED** and sit on
Excluded_Not_Sourced with "what would make it citable," exactly as the study
quarantines every derived-but-uncited number. No fleet self-report is used as a
measurement; the 11.3M Medicare IFT book and the ~10,600-organization anchor stand
unchanged. NEMSIS's 34.2M all-EMS-events figure (S453) is carried only as
all-events context and is **not** mixed with the Medicare IFT book (universe rule).

## Verification
- The four NPPES brand queries re-run deterministically against the live API and
  return the same counts (0 / 0 / 65 / 3); the AMR fragmentation and the Priority
  "Shoals Ambulance LLC" mapping are inspectable in the returned items.
- ID ledgers contiguous: F624-F632 appended after F623; S448-S454 after S447;
  finding 118 after 117. No shipped ID renumbered.
- Universe firewall held: fleet/EMT self-reports labeled CLAIMED; ratios
  quarantined MODELED; all-EMS-events kept separate from the Medicare IFT book.

## Human action items
1. Assemble the fleet-vs-labor regression panel (state vehicle permits x CMS
   A0425-A0434 utilization x disclosures) to convert the structural argument into a
   measured R^2.
2. Build the parent -> local-entity ownership crosswalk (SEC/PE deal history, CMS
   PECOS ownership, state licensing, press) so GMR/Priority roll up correctly - the
   step NPPES cannot do.

## Not in this pass
No `sec_*.py` workbook tab was added this pass; the delta note registers the facts,
sources, and finding for the next workbook build to absorb (Named_Operator_Undercount
+ Fleet_vs_Labor_Predictor tabs). The readable standalone version of this analysis is
`RCM_MC/docs/IFT_FLEET_VS_LABOR_MEMO.md`.
