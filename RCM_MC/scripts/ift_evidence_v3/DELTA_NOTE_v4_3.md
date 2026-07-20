# IFT Sourced Evidence Master v4.3 - delta note

## Run 7: fleet-license identification for IFT and all ambulance transport

The workbook could size the Medicare book, the institutional wedge and the
transfer network, but it never answered the operational question a diligence
desk hits first on any ambulance target: how do you identify an operator's
FLEET - the number of ambulances it is licensed to run - and its license
footprint, from public records only? v4.3 ships that method and the public
evidence that supports it, as three appended tabs. No shipped ID is renumbered:
new facts start at F624, sources at S448, findings at 118.

## The three new tabs

**Fleet_License_Route_Map (the method).** "Fleet license" is not one object. It
decomposes into four, and the map prints each one's public route, what it
yields, and whether it yields a per-operator VEHICLE count:

1. The state SERVICE/agency license - operator identity and authorized levels
   (BLS/ALS/specialty care/air). Identity, not vehicles.
2. The per-VEHICLE permit issued under that service license at a level
   (ALS/BLS/dual). This is the only object that equals fleet SIZE. Public in a
   few states (verification lookups, statewide totals); portal-/FOIA-only in
   most.
3. PERSONNEL licensure (EMT/paramedic/MICP) - a crew-capacity proxy, not trucks.
4. The federal routes, none of which counts trucks: NPPES ambulance-organization
   taxonomy (3416 root) for identity, PECOS/Medicare Part B enrollment and MUP
   A0425-A0436 for billing, and FMCSA USDOT/MCS-150 for the self-reported
   power-unit count of INTERSTATE non-emergency carriers only.

Panel B is the ordered identification recipe (resolve NPPES identity -> confirm
the service license -> count the vehicle permits -> cross-check Medicare volume
-> catch interstate NEMT in FMCSA). Panel C explains why no national fleet
registry exists: vehicle permitting is a state function run 51 different ways.

**Fleet_License_State_Matrix (the coverage).** All 51 jurisdictions (50 states +
DC): the state EMS licensing authority, the service-roster public route, the
per-vehicle permit regime, the VERIFIED NPPES operator floor, whether a
per-operator fleet count is publicly retrievable, the public source, and the
honest access status. All 51 jurisdictions (50 states + DC) now carry a CONFIRMED, individually
located public route: the state EMS licensing authority and the specific public
lookup, portal, or downloadable roster where an operator's service license (and,
where published, its vehicle permits) can be pulled. The NPPES operator floor
remains the verified public anchor on every row. Several confirmed states publish
a DOWNLOADABLE licensed-service roster (KY as XLSX+PDF; MA, AR and AZ as PDF; MO
as Socrata open data; RI, SD, CT via public lookups). Confirmed per-VEHICLE
permit regimes span FL, MT, NJ, WA, IL, CO, MI, UT, MS and VT (each licenses or
permits individual ambulances); AZ authorizes by Certificate of Necessity. The
matrix records, per state, exactly which artifact a human pulls to get the full
per-operator vehicle list.

**Fleet_Size_Evidence (the landed numbers).** The NPPES ambulance-organization
operator floor per jurisdiction (Type-2 NPIs under taxonomy 3416*, computed live
from the manifested NPPES roster - about 19,400 organizations across the 51
jurisdictions), the national taxonomy split (land/unspecified/air/water), the
Missouri open-data service counts (from the manifested data.mo.gov Socrata
pull), and two confirmed statewide vehicle-license anchors: New Jersey (~4,500
licensed EMS vehicles and ~1,700 MICPs) and Michigan (3,847 licensed life-support
vehicles across 819 agencies, 2019 - about 4.7 vehicles per agency). A native bar
chart ranks the top-12 jurisdictions by operator floor. Two independent states
now show several licensed vehicles per operator, confirming the NPPES operator
floor systematically understates fleet size.

## The guardrail, held throughout

The NPPES floor is an IDENTITY floor, not a fleet count: one operator may hold
many vehicle permits under one NPI, and one NPI is never one ambulance. Every
panel that uses it prints that confound in place, and the New Jersey anchor
(~4,500 statewide vehicles against 724 NPPES operators) is framed as an
illustration of the gap, not a per-operator fleet estimate. Where a per-operator
vehicle count is not public, the cell is bordered PENDING and names the state
vehicle-permit registry that would fill it.

## Firewall

Public sources only. NPPES, state EMS offices (FL, MT, NJ, WA, TX, MO and the
NREMT/NASEMSO state-office index), and FMCSA SAFER. No operator is described as a
customer or prospect of any company; the NPPES floor and the state rosters are
public identity/licensure records.

## Verification
- Two-pass LibreOffice recalc: zero error cells; carried v2.7 cells reproduce;
  charts pass the V9 gate; ledgers contiguous through the new tail.
- The new counts are re-derivable at build time from the manifested caches
  (nppes_ambulance_roster, state_ems_rosters), not hardcoded.

## Human action items / open items (next runs)
1. Promote PORTAL/FOIA jurisdictions to CONFIRMED as each state's specific public
   vehicle-permit route is located and verified.
2. Land per-operator vehicle-permit counts where a state publishes a verification
   lookup or a downloadable registry (WA, FL vehicle permits, TX vehicle data).
3. Add the FMCSA MCS-150 power-unit pull for the resolved interstate-NEMT
   operators as a second, independent fleet figure.
