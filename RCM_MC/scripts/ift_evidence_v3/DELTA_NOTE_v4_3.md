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
pull), and THIRTEEN confirmed statewide vehicle-license anchors ranked largest
first: Texas (over 5,000), New Jersey (~4,500), Michigan (3,847), North Carolina
(2,500 licensed ALS/BLS vehicles), Indiana (~2,000), Georgia (~1,800, tier-B
legislative), Tennessee (1,300), Arizona (980 registered ground ambulances),
Connecticut (over 900), Minnesota (838 = 804 ground + 34 air), West Virginia
(~523), Idaho (357) and Delaware (169 emergency/911 units). About THIRTY states
now carry a published statewide licensed-SERVICE count, located by a per-state
public sweep and each independently verified against the state EMS authority
(PA 1,205, NY 982, WI 822, TX ~800, IN 800+, IA 724, CA 700+, WA 456, NE 427,
FL 346, MA 318, MT 270, MN 266, WV 269, SC 263, ME 276, ND 255, KY 221, TN 210,
CO 205, KS 162, UT 130+, SD 121, AZ 97, DE 88, RI 83, VT 65, WY 62, plus MO 486
and MI 819). A native bar chart ranks the top-12 jurisdictions by operator floor.
Texas at ~6.3 vehicles per provider (Tennessee ~6.2) confirms the NPPES operator
floor systematically understates fleet size.

**IFT_License_Tracker (the one-grid tracker).** Per US jurisdiction, every public
ambulance/IFT license count in a single grid across four universes that must
never be summed together: the NPPES operator-identity floor (all 51), the
licensed-SERVICE count where a state publishes one (~30 states, PA 1,205 / NY 982 / WI 822 / TX ~800
lead), the licensed-VEHICLE total where published (13 states: TX over 5,000 down
to DE 169), and the EMT and paramedic WORKFORCE with mean wage from BLS OEWS May
2024 (SOC 29-2042 / 29-2043, all states) so wages per state can be backed into.
Every unpublished service or vehicle count is bordered PENDING with the
State_Matrix route that fills it, so the grid is both the evidence and the
worklist. Three landing waves (TX/PA/CA/FL, then MN/CO/WI/TN/IN, then an 18-state
verified sweep) took the grid from 3 to ~30 published service cells and from 2 to
13 published vehicle cells. Every landed number was located by a parallel
per-state sweep and independently re-verified against the state EMS authority in
a separate find-then-refute pass; two candidates that did not survive
(Hawaii, New Hampshire) were dropped, and Georgia was kept only at tier-B with an
"approximate" flag.

**EMS_Workforce_Shortage (the supply behind the fleet).** A fleet is only as
deployable as its crews. This tab pairs the national clinician supply - NREMT
598,843 nationally certified (EMT 400,911; paramedic 149,841) and BLS ~288,580
EMT+paramedic jobs at a $45,260 combined mean wage - with the shortage signals:
20-36% annual turnover (AAA/Newton 360 2024 study), 73% burnout, 37% planning to
leave within five years, replacement cost $5,786 per EMT and $8,620 per
paramedic, plus the states that publish a trend (NY active responders -17.5%
2019-2022; rural MI 500+ vacancies). It cross-references the per-state EMT and
paramedic jobs and wages on IFT_License_Tracker. New facts F635-F636, sources
S458-S461 (NREMT, BLS OOH, AAA, NY Senate), finding 123. The point: a permitted
ambulance with no crew does not roll, so fleet-license counts must be read
against this supply.

**Fleet_Data_Pull_Worklist (the action checklist).** The retrieval instructions
behind the matrix: per jurisdiction, the exact roster pull and per-operator
vehicle-count pull with the public URL, plus the three national routes worked
first - FMCSA Motor Carrier Census (data.transportation.gov Company Census File
az4n-8mr2; POWER_UNITS per USDOT number for interstate NEMT), FMCSA SAFER Company
Snapshot, and NPPES taxonomy 3416. A "fastest wins" panel points at the states
whose vehicle totals or downloadable rosters are already public. This is the
worklist for filling every PENDING cell on IFT_License_Tracker.

**Corporate_Family_Resolution (why the national players are undercounted).** The
two genuinely national ground players - GMR (KKR-owned, parent of AMR) and
Priority Ambulance (PE-backed) - are undercounted in every public dataset because
provider registries have no corporate-family field. This tab proves it from two
public sources joined on NPI: the NPPES ambulance roster (identity) and the CMS
Medicare provider-and-service files (actual paid transports, base-rate ground
HCPCS A0426-A0434), both re-derived at build time. GMR has ZERO Type-2 billing
NPIs under its own name and surfaces as ~570 subsidiary NPIs across 47 states
under local/legacy names; Priority as ~16 across 11 states. The killer panel is
the naive-vs-resolved 2024 leaderboard: raw per-NPI, a single Acadian NPI
(~88,800 transports) tops the list and GMR is invisible (biggest NPI ~30,600,
under 7% of its family); family-resolved, GMR is #1 at ~442,000 transports, about
3x Acadian. A time series (2018-2024) shows US Medicare FFS ground transports
falling ~13.4M to ~9.5M as Medicare Advantage pulls volume out of fee-for-
service - a payer-mix caveat, not proof any operator shrank. New facts (GMR/
Priority family volume, GMR subsidiary NPIs, US Medicare ground transports),
sources cms_mup_provider / gmr_public / priority_public, finding 124.

**Fleet_Scale_Predictors (which public signal predicts real volume).** Rates the
candidate predictors of operator scale on availability and how well each orders
operators by true scale: (1) family-resolved CMS Medicare transport volume - best
public volume proxy, actual paid transports, but Medicare FFS is only ~a quarter
to two-fifths of all-payer volume (a ~x2.5-4 gross-up); (2) fleet (vehicles) -
best capacity proxy, scarce; (3) family-resolved NPI count - good once resolved;
(4) licensed EMTs per company - tracks fleet but noisier (turnover, dual-role);
(5) job postings - weak, churn-confounded flow signal (GMR ~683 vs Priority
~21-44 openings); (6) footprint (metros / health systems) - breadth not volume,
under-ranks dense urban operators. The precondition beneath all of them is
corporate-family resolution. A test-set panel shows the Medicare-volume ranking
reproduces known scale (GMR > Acadian > Superior > Falck > Priority). New sources
operator_scale_public / ems_job_postings, finding 125.

**Fleet_Identity_Map (who owns the fleet).** Extends the volume work into an
ownership map of the whole ambulance-supplier universe, resolved with two public
identity keys joined on NPI: operator brand/legal name and the CMS PECOS
Associate Control ID (which clusters one operator's multi-state enrollments - e.g.
Med-Trans 27 NPIs across 24 states under one control ID). Segmenting 2024 CMS
Medicare ground volume by owner type is decisive: municipal / government / fire is
the largest bucket at ~40% (~5,400 NPIs), independent long tail ~47%, hospital /
health-system ~3%, and named national/regional roll-ups only ~10% - of which GMR
alone is about a third. A named roll-up registry resolves seven consolidators
(GMR, Acadian, Superior, Falck, Priority, plus newly mapped Pafford EMS and
DocGo/Ambulnz), each with NPPES NPIs, states, Medicare volume, and PECOS
control-ID clusters; Rocky Mountain Holdings, an AIR-medical competitor (Air
Methods), is verified as distinct and deliberately not folded into GMR. A
GMR-calibrated volume-to-fleet illustration (~700 transports per ground vehicle
per year) sizes families where a state vehicle registry is not public. New facts
(municipal share, roll-up share), source cms_pecos_enroll, finding 126. The
takeaway for diligence: a national thesis is really a roll-up-of-independents
thesis, and the targets hide in the long tail under local names.

**Fleet_Ownership_Resolved (the exhaustive per-NPI identity layer).** Every
Medicare-billing ambulance operator (the operating fleet, ~6,880 NPIs) was
enriched one-by-one from NPPES (live npi_lookup) with its AUTHORIZED OFFICIAL -
the corporate officer who signs for the license - plus DBAs, subpart flag,
mailing vs practice address, and state Medicaid/license IDs. Corporate families
are then resolved by SHARED OFFICIAL: seed each roll-up by brand, then absorb
every NPI signed by the same officers (excluding third-party billing officials,
flagged by a majority-municipal client book). This absorbs the legacy acquired
names that carry no parent brand, and the effect is large: GMR resolves from
455,696 to 744,574 2024 Medicare ground transports (1.63x, 75 to 149 NPIs -
pulling in Abbott Ambulance, Broward / Palm Beach / Atlantic, City Ambulance of
Eureka), and Priority from 69,311 to 132,935 (1.92x - Central EMS, MedShore,
LifeCare, Utica). Operators that never renamed (Acadian, Superior, Falck,
Pafford, AmeriPro) do not move. The lesson: a name-only census understates the
consolidators by 40-90%, so any market-share or roll-up-target work must resolve
identity by signing official first. New facts (GMR and Priority official-resolved
volume), source nppes_npi_enrichment (the exhaustive per-NPI pull), finding 127.
The enriched dataset ships as npi_operating_fleet_enriched in the pull cache so
the tab is re-derivable. Scope note: the pull covers the Medicare-active operating
fleet; dormant / air-only / non-billing NPIs were deprioritized (no transport
volume).

**Fleet_Ownership_Crosswalk (the subsidiary-to-parent map).** The explicit
ownership map: every Medicare-billing operator that belongs to a national or
regional owner, listed under that parent, with how it was linked - by brand name
or by SHARED SIGNING OFFICIAL. This is the Baptist Ambulance -> Priority, every
AMR / Abbott / Alliance / Rural Metro / Southwest Ambulance NPI -> GMR, every
Ambulnz entity -> DocGo mapping made explicit. ~215 subsidiary NPIs across ~130
distinct local brands roll up to nine parents (GMR / AMR, Acadian, Priority,
Superior, DocGo, Falck, Pafford, Coastal, AmeriPro), together ~1.44M 2024
Medicare ground transports. The linkage key is the NPPES authorized official,
which maps a renamed subsidiary to its parent even when the brand name gives
nothing away; anything absent from the crosswalk is, on the public evidence,
genuinely independent (or municipal / hospital), not a hidden subsidiary. Panel A
totals each parent; Panel B is the full operator -> parent roster. New fact
(operators mapped to a parent), finding 128.

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
