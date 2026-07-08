"""Interfacility Transport (IFT) — Ground.

The interfacility SLICE of the ground-ambulance market: medically-supervised
movement of patients BETWEEN facilities (hospital→hospital up-transfers,
hospital→SNF/IRF/LTCH discharge legs, SNF→hospital returns, facility-origin
dialysis round-trips). The TAM is deliberately narrow — US GROUND interfacility
ambulance only, the interfacility cut of HCPCS A0426/A0428 (BLS), A0427/A0429
(ALS-emerg), A0433 (ALS2), A0434 (SCT) + A0425 ground mileage — and it EXCLUDES
911/scene response, air ambulance, and NEMT. Those exclusions are stated on the
masthead and in Market size, because the biggest sizing error in this vertical is
reading a whole-ambulance ($21-22B) or NEMT ($18B) number as if it were the
ground-IFT prize.

This module is authored around the two facts an IC needs first: (1) the economics
are NOT the fee schedule — an IFT operator lives on the health-system CONTRACT
layered on top (per-transport rate + availability retainer + exclusivity), and
(2) the single per-market question that decides every deal is INSOURCE-vs-
OUTSOURCE — does the anchor system run its own fleet or contract it out.

Sizing spine (all honestly labelled): the national ground-IFT TAM is built
top-down in :mod:`ift_analytics` from the GOV MedPAC $4.0B Medicare-FFS ambulance
anchor (→ ground → interfacility → all-payer gross-up → ~$6.5B central, $5-8B,
ILLUSTRATIVE); the bottom-up SAM is built from the real 20-metro target footprint
in :mod:`ift_geo` (SOURCED hospital + post-acute structure) × labelled levers.
The geographic deep-dive — every metro, its anchor systems, its insource-vs-
outsource read and its moat — lives on the NEW ``/ift-markets`` page (a separate
renderer), linked from Connections.

``interfacility_transport`` is a canonical subsector (a ``CANONICAL_SUBSECTORS``
row under "Other services"), so the dossier registers and renders in FULL at
``/market/interfacility_transport``, is listed on the ``/market`` index, and
never falls back to the scaffold.
"""
from __future__ import annotations

from .. import (
    CmsTrend, Competition, Connection, CostDriver, GrowthLever, HowItWorks,
    Kpi, MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule,
    Segment, Source, TamHeadline, UnitEconomics, VolumeDriver,
    register,
)
from .. import ift_analytics as _ift
from .. import ift_geo as _geo

# ── Computed sizing (single source of truth — keeps the prose in lockstep with
#    the analytics; every figure keeps its honesty label). All degrade-safe. ──
_TAM = _ift.ground_tam()
try:
    _SAM = _ift.sam_formula()
except Exception:  # noqa: BLE001 — degrade to worded fallbacks, never raise at import
    _SAM = None
try:
    _ROLL = _geo.footprint_rollup()
except Exception:  # noqa: BLE001
    _ROLL = None
try:
    _CMS_TAKEAWAY = _ift.cms_trend_takeaway()
except Exception:  # noqa: BLE001
    _CMS_TAKEAWAY = ""
try:
    _STATE_NOTE = _ift.state_note()
except Exception:  # noqa: BLE001
    _STATE_NOTE = ""


def _rng_b(t) -> str:
    """Format a ($B_low, $B_high) tuple as '$L.LL-H.HHB'."""
    try:
        return f"${t[0]:,.2f}-{t[1]:,.2f}B"
    except Exception:  # noqa: BLE001
        return "—"


_TAM_CENTRAL = getattr(_TAM, "allpayer_tam_bn_central", 6.5)
_TAM_LOW = getattr(_TAM, "allpayer_tam_bn_low", 5.0)
_TAM_HIGH = getattr(_TAM, "allpayer_tam_bn_high", 8.0)
_FFS_ANCHOR = getattr(_TAM, "medicare_ffs_ambulance_bn", 4.0)
_FFS_GROUND = getattr(_TAM, "medicare_ffs_ground_bn", (3.40, 3.52))
_FFS_IFT = getattr(_TAM, "medicare_ffs_ground_ift_bn", (1.02, 1.41))

_SAM_C = (_SAM.sam_dollars_central / 1e6) if (_SAM and _SAM.available) else 92.1
_SAM_LO = (_SAM.sam_dollars_low / 1e6) if (_SAM and _SAM.available) else 46.8
_SAM_HI = (_SAM.sam_dollars_high / 1e6) if (_SAM and _SAM.available) else 147.9
_SAM_DEMAND = (_SAM.total_demand_missions) if (_SAM and _SAM.available) else 335_321
_SAM_SERV = (_SAM.total_serviceable_missions) if (_SAM and _SAM.available) else 70_634
_SAM_BEDSHARE = ((_SAM.bed_share_of_national or 0) * 100) if (_SAM and _SAM.available) else 5.1

_N_METROS = getattr(_ROLL, "n_metros", 20) if _ROLL else 20
_N_REGIONS = getattr(_ROLL, "n_regions", 6) if _ROLL else 6
_FP_HOSP_SHARE = ((_ROLL.hospitals_national_share or 0) * 100) if (_ROLL and _ROLL.available) else 24.9
_FP_SNF_SHARE = ((_ROLL.snf_beds_national_share or 0) * 100) if (_ROLL and _ROLL.available) else 22.2
_FP_STATE_HOSP = getattr(_ROLL, "footprint_state_hospitals", 1153) if _ROLL else 1153
_FP_HOSP_NAT = getattr(_ROLL, "n_hospitals_national", 4630) if _ROLL else 4630
_FP_STATE_SNFB = getattr(_ROLL, "footprint_state_snf_beds", 347_674) if _ROLL else 347_674
_FP_SNFB_NAT = getattr(_ROLL, "snf_beds_national", 1_569_384) if _ROLL else 1_569_384
_FP_METRO_HOSP = getattr(_ROLL, "n_hospitals", 166) if _ROLL else 166


REPORT = MarketReport(
    slug="interfacility_transport",
    name="Interfacility Transport (IFT) — Ground",
    care_setting="Other services",
    naics="621910",
    one_line_def=(
        "Medically-supervised movement of patients BETWEEN facilities by ground "
        "ambulance — hospital-to-hospital up-transfers, hospital-to-post-acute "
        "discharge legs, and facility-origin recurring round-trips — the "
        "interfacility slice of the Medicare Ambulance Fee Schedule (BLS/ALS/"
        "ALS2/SCT + ground mileage), EXCLUDING 911/scene response, air ambulance, "
        "and NEMT."),
    tam_headline=TamHeadline(
        value=float(_TAM_CENTRAL), unit="$B", growth_pct=5.5,
        basis_label="ILLUSTRATIVE",
        basis_note=(
            f"US GROUND interfacility-ambulance TAM ≈ ${_TAM_CENTRAL:.1f}B central "
            f"(range ${_TAM_LOW:.0f}-{_TAM_HIGH:.0f}B), all-payer, EXCLUDING NEMT "
            "and air. It is a modeled ~5× all-payer gross-up of the "
            f"{_rng_b(_FFS_IFT)} Medicare-FFS ground-IFT slice, itself built off "
            f"the GOV MedPAC anchor of ${_FFS_ANCHOR:.1f}B Medicare-FFS ambulance "
            "spend (2023) — the $6.5B is NEVER GOV, it is the ILLUSTRATIVE central. "
            "Growth is the modeled composite (price ~+2-4% × volume ~+2-4%, "
            "consolidation on top)."),
    ),
    executive_summary=[
        "The market definition IS the thesis. TAM is the ground INTERFACILITY "
        "slice only — the interfacility cut of A0426/A0428 (BLS), A0427/A0429 "
        "(ALS), A0433 (ALS2), A0434 (SCT) + A0425 mileage — and it excludes "
        "911/scene, air, and NEMT. Reading a whole-ambulance (~$21-22B, "
        "ILLUSTRATIVE) or NEMT (~$18B, ILLUSTRATIVE) number as the prize is the "
        "single biggest sizing error here; the ground-IFT TAM is "
        f"~${_TAM_CENTRAL:.1f}B (ILLUSTRATIVE, ${_TAM_LOW:.0f}-{_TAM_HIGH:.0f}B).",
        "The fee schedule is a floor, not the deal. An IFT operator lives on the "
        "health-system CONTRACT layered on top: per-transport rates, an "
        "availability/subsidy retainer that de-risks the deadhead problem, and "
        "exclusivity / first-call with the transfer center. Underwrite the "
        "contract, not the HCPCS code.",
        "Insource-vs-outsource is the whole ballgame per market. A system that "
        "runs its own fleet (Cleveland Clinic CCT, Mayo/Allina EMS, Children's "
        "peds teams) is a closed door — count only the discharge/return residual; "
        "a system that outsources with an exclusive is a moat you can buy. Map "
        "every anchor system's posture.",
        "Payer mix and acuity beat volume. IFT over-indexes on spend versus "
        "volume because it concentrates the high-RVU lines — SCT (A0434, RVU "
        "3.25) is definitionally interfacility and pays ~3.25× a BLS run (GOV, 42 "
        "CFR 414 Subpart H) — plus long loaded mileage. An interfacility book "
        "skewed to SCT/CCT + commercial is worth multiples of a 911-scene BLS book.",
        "Density is the durable moat. Ground IFT is a unit-hour-utilization "
        "business: labor is ~69-70% of cost (GOV, CMS GADCS) and mean cost/"
        "transport is ~$2,673 all-in (GOV, GADCS), so profit is made by chaining "
        "loads and killing deadhead. An incumbent with many hospital + post-acute "
        "nodes in one metro underbids a single-contract entrant structurally.",
        "Two compliance overhangs define the risk. RSNAT prior authorization "
        "(nationwide since 2021) already gutted the repetitive scheduled-dialysis "
        "model, and FCA/OIG enforcement on medically-unnecessary non-emergent "
        "runs is relentless — a target still fat on scheduled dialysis is a red "
        "flag, not a growth story.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Trigger at a FACILITY — a transfer-center request (up-transfer to "
            "higher level of care) or a discharge order (bed-clearing to post-acute)",
            "Level-of-service determination (BLS / ALS / ALS2 / SCT) + "
            "medical-necessity and Physician Certification Statement (PCS) docs",
            "Dispatch of the appropriate crew (2 EMT-Basic for BLS up to RN/RRT + "
            "critical-care paramedic for SCT) from a posted, often on-campus, unit",
            "Loaded transport facility-to-facility + A0425 ground loaded mileage",
            "ePCR run report; origin/destination modifier fixes the claim as "
            "interfacility (both endpoints in {H,N,E,G,J,D,I})",
            "Claim to Medicare AFS / Medicaid / commercial, then the ~20% patient "
            "balance; collect against the payer mix",
            "For repetitive non-emergent schedules: RSNAT prior authorization "
            "before the run to avoid prepayment review",
        ],
        sites_of_care=[
            "Hospital → hospital up-transfer (community ED → tertiary/quaternary "
            "hub for STEMI/stroke/trauma/complex surgery) — the ALS2/SCT margin core",
            "Hospital → post-acute discharge (SNF / IRF / LTCH / hospice) by "
            "stretcher — the BLS/ALS volume backbone",
            "SNF / post-acute → hospital non-emergent return, and facility-origin "
            "dialysis legs (N→G SNF-to-dialysis)",
            "Hospital → airport / helipad handoff (H→I) for an air leg the ground "
            "operator hands off",
            "Neonatal / pediatric specialty transport — almost entirely insourced "
            "by children's/academic systems (a moat, not an addressable contract)",
            "Bariatric interfacility — a capital + crew niche billed as BLS/ALS/SCT "
            "with add-ons",
        ],
        money_flow=(
            "Medicare pays under the Ambulance Fee Schedule (AFS, 42 CFR 414 "
            "Subpart H): payment = base rate × level-of-service RVU × geographic "
            "adjustment (the GAF applies to 70% of the base), PLUS A0425 loaded "
            "mileage paid per statute mile. RVU multiples are fixed regulatory "
            "constants (GOV) with BLS-non-emergency = 1.00 the anchor, up to "
            "ALS2 = 2.75 and SCT = 3.25 — so an SCT run pays ~3.25× a BLS run and "
            "IFT revenue-per-transport structurally beats a 911-scene BLS mix. The "
            "single national conversion factor updates each year by the Ambulance "
            "Inflation Factor (AIF = CPI-U less a productivity adjustment; CY2025 "
            "AIF = 2.4%, GOV), and temporary rural/urban/super-rural add-ons "
            "(+2%/+3%/+22.6%, extended through 12/31/2027, GOV) prop up rural legs. "
            "But the fee schedule does not cover the cost of standing up a truck: "
            "industry data put mean all-payer reimbursement near ~$1,147/transport "
            "against a much higher cost basis (INDUSTRY, AAA/EMS1). The gap is "
            "closed by the FACILITY CONTRACT — per-transport rates at or above AFS "
            "allowed, an availability/subsidy retainer so dedicated trucks post at "
            "the campus regardless of volume, and exclusivity with the transfer "
            "center. Ground ambulance is CARVED OUT of the federal No Surprises "
            "Act, so out-of-network balance-billing of commercial IFT is still "
            "federally legal (leverage and collection/reputational risk both)."),
        key_players=(
            "Four archetypes, and IFT is won market-by-market, not nationally. "
            "(1) HOSPITAL-BASED / INSOURCED — the pivotal one, because the IFT "
            "origin IS the hospital: Cleveland Clinic Critical Care Transport, "
            "MetroHealth Metro Life Flight, Allina Health EMS (Twin Cities; "
            "~34,000 interfacility requests in 2024), and Mayo Clinic Ambulance "
            "(Rochester) prove a big system can run a profitable owned fleet and "
            "keep the high-RVU legs. (2) MUNICIPAL / FIRE / THIRD-SERVICE — owns "
            "911 but variably sheds low-acuity IFT to protect unit-hours "
            "(Sedgwick County EMS, Louisville Metro EMS, Fairfax County Fire). "
            "(3) REGIONAL PRIVATE — the roll-up sweet spot living on hospital IFT "
            "contracts: Superior Air-Ground (Chicagoland/NW-Indiana), AmeriPro "
            "Health (Midwest consolidator), Midwest Medical Transport (Omaha), "
            "Ryan Brothers (Madison), Priority Ambulance's Lifecare/Frontier "
            "brands. (4) NATIONAL — Global Medical Response / AMR (KKR; the "
            "nation's largest, >7,000 ground vehicles, BLS/ALS/CCT), Acadian "
            "(employee-owned ESOP), Priority Ambulance. The acquirable pool is the "
            "regional privates and the outsourced discharge/interfacility books — "
            "insourced captive fleets and municipal 911 are not for sale."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Medicare FFS ambulance spend, 2023 (the GOV anchor)",
                    f"${_FFS_ANCHOR:.1f}B",
                    "GOV · MedPAC Payment Basics (Ambulance), Oct 2024 · ~1% of "
                    "FFS spend; ~13% of FFS beneficiaries used ambulance"),
            Segment("→ Medicare FFS GROUND ambulance (~85-88% of ambulance $)",
                    _rng_b(_FFS_GROUND),
                    "ILLUSTRATIVE · air is ~1-2% of transports but higher $/trip; "
                    "ground is the residual"),
            Segment("→ Medicare FFS GROUND IFT slice (~30-40% of ground $)",
                    _rng_b(_FFS_IFT),
                    "ILLUSTRATIVE · IFT over-indexes on spend — concentrates "
                    "ALS2/SCT + long mileage; the figure most directly anchored to GOV"),
            Segment("US GROUND IFT TAM, all-payer (ex-NEMT, ex-air)",
                    f"${_TAM_CENTRAL:.1f}B central (${_TAM_LOW:.0f}-{_TAM_HIGH:.0f}B)",
                    "ILLUSTRATIVE · ~5× all-payer gross-up of the Medicare-FFS "
                    "ground-IFT slice; commercial pays ~2-4× Medicare"),
            Segment("Volume cross-check",
                    "~4-5M ground IFT transports/yr × ~$1,200-1,400/leg",
                    "ILLUSTRATIVE · interfacility ~15-20% of ~25-30M US ground "
                    "transports × blended all-payer net revenue — reconciles top-down"),
            Segment("Context: US all-payer ground ambulance market",
                    "~$18-22B",
                    "ILLUSTRATIVE · Grand View / IBISWorld · IFT is a SLICE WITHIN "
                    "ground, never sized top-down off the whole"),
            Segment(f"SAM — {_N_METROS}-metro target operator footprint (bottom-up)",
                    f"${_SAM_C:,.1f}M central (${_SAM_LO:,.0f}-{_SAM_HI:,.0f}M)",
                    "SOURCED structure × ILLUSTRATIVE levers · ift_geo hospital + "
                    "post-acute build × f_IFT/s(m)/r_IFT in ift_analytics.sam_formula"),
            Segment("Footprint STATES' share of national demand",
                    f"{_FP_HOSP_SHARE:.1f}% of US hospitals · {_FP_SNF_SHARE:.1f}% of SNF beds",
                    f"SOURCED · {_FP_STATE_HOSP:,}/{_FP_HOSP_NAT:,} hospitals, "
                    f"{_FP_STATE_SNFB:,}/{_FP_SNFB_NAT:,} SNF beds in our CMS rolls"),
        ],
        growth_drivers=[
            "VOLUME (primary) — aging + ED-boarding + hub-and-spoke regionalization "
            "of stroke/STEMI/trauma pushes more (and higher-acuity) transfers "
            "~+2-4%/yr (drivers GOV/ACADEMIC, magnitude ILLUSTRATIVE)",
            "PRICE — AIF annual update (CY2025 2.4%, GOV) + temporary add-ons + "
            "facility-contract escalators + OON commercial leverage ~+2-4%/yr "
            "(ILLUSTRATIVE; AIF is productivity-lagged so real price is thinner)",
            "CONSOLIDATION — health-system share-of-wallet capture + PE roll-up of "
            "fragmented regional privates (inorganic; a platform multiplier, not "
            "organic market growth) (ILLUSTRATIVE)",
            "Post-acute discharge density — the SNF/IRF/LTCH destination inventory "
            "is the countable BLS/ALS discharge demand (SOURCED, our rolls)",
            "Regulatory drag — RSNAT prior-auth deflated scheduled dialysis; FCA "
            "enforcement removes non-compliant supply (GOV)",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Medicare / MA": 0.52,
            "Commercial": 0.28,
            "Medicaid": 0.12,
            "Self-pay / other": 0.08,
        },
        rate_mechanics=[
            "AFS base rate = level-of-service RVU × single national conversion "
            "factor × geographic adjustment; the GAF adjusts 70% of the base "
            "(labor portion), the other 30% is unadjusted (GOV, 42 CFR 414 Subpart H).",
            "RVU multiples (GOV, fixed constants): BLS-non-emerg 1.00 (anchor), "
            "BLS-emerg 1.60, ALS1-non-emerg 1.20, ALS1-emerg 1.90, ALS2 2.75, "
            "SCT/A0434 3.25 — SCT is the highest ground line and definitionally "
            "interfacility (42 CFR 414.605).",
            "Annual update = Ambulance Inflation Factor (CPI-U less a "
            "multifactor-productivity adjustment); CY2025 AIF = 2.4% (GOV) — a "
            "productivity-lagged update that chronically under-runs wage inflation.",
            "Temporary add-ons: +2% urban / +3% rural / +22.6% super-rural on base "
            "AND mileage, keyed to ZIP of pickup — extended through 12/31/2027 "
            "(CAA 2026); rural loaded miles 1-17 paid at 1.5× (GOV). Never made "
            "permanent — a recurring cliff.",
            "A0425 ground loaded mileage is paid separately, per statute mile; "
            "long-mileage rural/super-rural legs (WY, western NE/KS) carry "
            "outsized per-trip economics.",
            "Origin/destination modifier (origin letter + destination letter) is "
            "the interfacility fingerprint — IFT = both endpoints are FACILITIES "
            "(H hospital, N SNF, E residential facility, G/J dialysis, D dx site, "
            "I transfer site); origin S (scene) or R (residence) is 911/NEMT, not IFT.",
            "RSNAT prior authorization — repetitive scheduled non-emergent BLS "
            "(A0428) + ALS1 (A0426), nationwide since 2021; first 3 round trips "
            "exempt, then MAC affirmation up to 40 round trips/60 days or "
            "prepayment review (GOV).",
            "The economics that clear are the FACILITY CONTRACT on top of AFS: "
            "per-transport rates, availability/subsidy retainers (unit-hour "
            "guarantees that de-risk deadhead), exclusivity, and CPI/step "
            "escalators — a price lever independent of the fee schedule.",
            "Medicare Part B pays 80% of allowed after the annual deductible "
            "($240 in 2024, GOV); the 20% patient coinsurance is a real "
            "collection/bad-debt line.",
            "No Surprises Act CARVE-OUT — ground ambulance is excluded from "
            "federal OON balance-billing limits, so commercial OON balance-billing "
            "is still legal where state law allows (GOV/INDUSTRY).",
        ],
        reimbursement_risk=(
            "The fee schedule under-reimburses the cost of a truck (industry "
            "data put average under-reimbursement well north of $2,000/transport "
            "versus cost; mean all-payer reimbursement ~$1,147, INDUSTRY "
            "AAA/EMS1), so margin depends on the contract layer and on payer mix, "
            "not the AFS allowed amount. Three specific risks dominate. First, the "
            "temporary add-ons (2/3/22.6%) lapse 1/1/2028 absent re-extension and "
            "the productivity-adjusted AIF lags labor — a single non-extension or "
            "Medicaid rate freeze compresses margin directly. Second, FCA/OIG "
            "exposure on scheduled non-emergent (dialysis) transport — treble "
            "damages, Corporate Integrity Agreements, exclusion — with RSNAT "
            "prior-auth having already collapsed that volume nationally (it cut "
            "RSNAT utilization 63% and spend 72% among ESRD/pressure-ulcer "
            "beneficiaries, saving Medicare ~$650M over 4 years, GOV). Third, a "
            "possible extension of No Surprises Act protection (federal GAPB "
            "recommendations, or state rate-setting) that would compress the "
            "commercial/OON leverage. GADCS cost reporting is quietly assembling "
            "MedPAC's evidence base for a future AFS rebasing — a raise or a "
            "reset, still open."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("EMTALA — appropriate interfacility transfer (§1867 SSA, "
                 "42 USC 1395dd)",
                 "The legal ENGINE of IFT: a sending hospital that cannot "
                 "stabilize must effect an appropriate transfer with qualified "
                 "personnel/equipment, and a capable receiving hospital must "
                 "ACCEPT — mandating a clinically-capable transport partner "
                 "(drives SCT/CCT demand) and creating joint liability.",
                 "https://www.acep.org/patient-care/policy-statements/appropriate-interfacility-patient-transfer/"),
            Rule("Medicare Ambulance Fee Schedule (42 CFR 414 Subpart H)",
                 "Base rate × RVU × GAF + mileage; the RVU constants, conversion "
                 "factor, AIF, rural add-ons, and the SCT definition (414.605) — "
                 "the price of the largest single payer.",
                 "https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-B/part-414/subpart-H"),
            Rule("RSNAT prior authorization (repetitive scheduled non-emergent "
                 "ambulance transport)",
                 "Nationwide since 2021; the compliance overhang on the recurring "
                 "non-emergent (dialysis) book — it permanently deflated that "
                 "model and is a diligence red flag for any target that leans on it.",
                 "https://www.cms.gov/data-research/monitoring-programs/medicare-fee-service-compliance-programs/prior-authorization-and-pre-claim-review-initiatives/prior-authorization-repetitive-scheduled-non-emergent-ambulance-transport-rsnat"),
            Rule("No Surprises Act — ground-ambulance carve-out + GAPB committee",
                 "Ground ambulance is excluded from federal OON balance-billing "
                 "protection; the federal GAPB advisory committee (report Aug 2024) "
                 "recommended banning OON ground balance-billing and capping "
                 "patient cost-share — federal action stalled, states are moving.",
                 "https://www.cms.gov/files/document/report-advisory-committee-ground-ambulance-and-patient-billing.pdf"),
            Rule("State EMS licensure + CON/COPCN + medical director",
                 "Entry requires a state EMS license, Medicare supplier "
                 "enrollment, a physician medical director, and often a "
                 "Certificate of Need / Public Convenience & Necessity — a "
                 "barrier-to-entry moat that varies enormously across the 11 "
                 "footprint states.",
                 None),
            Rule("OIG / False Claims Act enforcement (non-emergent transport)",
                 "Medically-unnecessary scheduled non-emergent (dialysis) "
                 "transport is the #1 ambulance enforcement theme — real "
                 "settlements (Medical Transport LLC $9M + CIA; Mauran dialysis "
                 "~$28M billed) with treble damages, CIAs, and exclusion.",
                 "https://oig.hhs.gov/reports-and-publications/all-reports-and-publications/"),
            Rule("Ground Ambulance Data Collection System (GADCS, BBA 2018 §50203)",
                 "Mandatory cost/revenue survey for CMS-selected orgs; "
                 "non-reporting = a 10% AFS payment cut. Feeds MedPAC "
                 "payment-adequacy work — the evidentiary basis for a future AFS "
                 "rebasing.",
                 "https://www.cms.gov/medicare/payment/fee-schedules/ambulance/medicare-ground-ambulance-data-collection-system"),
        ],
        policy_watch=[
            "Add-on expiration 1/1/2028 — the recurring rural/urban/super-rural "
            "extender cliff (currently good through 12/31/2027)",
            "Federal GAPB action or state rate-setting closing the NSA "
            "ground-ambulance surprise-billing gap (compresses OON leverage)",
            "GADCS-documented under-reimbursement → a possible AFS rate rebasing "
            "(raise vs reset is the open question)",
            "RSNAT enforcement / expansion and continued FCA scrutiny of "
            "non-emergent runs",
            "Medicaid ground-ambulance rate adequacy across the footprint states "
            "(state-set, frequently below cost)",
            "MedPAC mandated ground-ambulance report and any move on the "
            "structural payment model",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "Extreme fragmentation: 10,500+ ground-ambulance organizations bill "
            "Medicare annually (GOV, CMS GADCS) and there are >20,000 EMS agencies "
            "overall (INDUSTRY). 'Market share' is really a portfolio of "
            "individual hospital IFT contracts and municipal franchises, so "
            "structure is set metro-by-metro. IFT is decided on local density and "
            "the anchor-system relationship, so a national flag does NOT translate "
            "into IFT dominance in a given market — the insourced-fleet systems "
            "and dense regional privates routinely out-compete the nationals on "
            "their home turf."),
        hhi_or_share=(
            "No meaningful national concentration — the relevant unit is the "
            "single hospital transfer-center contract or the county franchise. "
            "The per-market moat (density + first-call + workflow integration) "
            "matters far more than national share; the SOURCED per-metro node "
            "density that underwrites that moat is on /ift-markets."),
        consolidation=(
            "PE chased ambulances hard, but the national leverage roll-up got "
            "caught by labor inflation. KKR bought AMR's parent Envision for "
            "~$9.9B in 2018; Envision filed Chapter 11 in May 2023, and GMR itself "
            "was cut to CCC+ by S&P (Apr 2023) before KKR refinanced >$4B of GMR "
            "debt in 2024 (maturities pushed to Oct 2028, a Moody's upgrade to B3 "
            "stable). The durable value is REGIONAL DENSITY + hospital contracts, "
            "not national scale — Priority Ambulance (Enhanced Healthcare "
            "Partners) and AmeriPro Health (which acquired Priority Medical "
            "Transport in 2025) are the active regional consolidators, and "
            "Acadian's employee-owned ESOP is a viable non-PE alternative."),
        pe_activity=(
            "The thesis has shifted from national roll-up to buying DENSITY within "
            "a metro. Fragmentation (10,500+ Medicare-billing orgs) leaves ample "
            "runway, but the QoE now centers on the facility-contract book "
            "(per-transport rates, availability retainers, exclusivity, and "
            "remaining term), the LOS/payer mix (SCT/CCT + commercial vs 911-BLS), "
            "unit-hour utilization/deadhead, and RSNAT/FCA exposure on any "
            "scheduled non-emergent revenue. The winning platform stacks "
            "consolidation on top of organic price×volume — and avoids "
            "over-levering a low-cash-conversion, labor-heavy business (the GMR "
            "caution)."),
        notable_players=[
            "Global Medical Response / AMR (KKR)", "Acadian Ambulance (ESOP)",
            "Priority Ambulance (EHP) — Lifecare / Frontier",
            "Superior Air-Ground Ambulance", "AmeriPro Health",
            "Midwest Medical Transport (MMT)", "Ryan Brothers Ambulance",
            "Allina Health EMS (insourced)", "Mayo Clinic Ambulance (insourced)",
            "Cleveland Clinic Critical Care Transport (insourced)",
            "Children's Mercy / Children's peds CCT (insourced)",
            "Municipal fire-based & county EMS",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Unit-hour utilization (UHU)", "the density lever",
                "Billed transports per staffed ambulance-hour — the true "
                "efficiency metric. An incumbent with many clustered nodes chains "
                "loads and raises UHU; a single-contract entrant runs half-empty."),
            Kpi("Deadhead miles (empty return leg)", "the silent margin killer",
                "Scheduled discharge IFT has high empty-return miles; local "
                "density + on-campus posting dilute fixed crew cost across more "
                "billed legs — where a good IFT operator separates from a bad one."),
            Kpi("Mean cost per transport (all-in)", "~$2,673 (GOV, GADCS)",
                "$1,778 private-for-profit vs $3,127 governmental (GOV, CMS GADCS "
                "Yr1-2); the fee schedule alone does not cover it — the contract does."),
            Kpi("Crew labor share of cost", "~69-70% (GOV)",
                "The binding constraint (CMS GADCS / MedPAC). Paramedic/EMT/nurse "
                "wage inflation and shortage cap unit-hour capacity and squeeze "
                "margin faster than the AIF replaces it."),
            Kpi("Blended net revenue / IFT transport", "~$1,200-1,400 (ILLUSTRATIVE)",
                "IFT skews ALS/SCT + longer loaded mileage; rural/super-rural legs "
                "carry a higher figure via mileage + the +22.6% add-on."),
            Kpi("LOS & payer mix (BLS/ALS/ALS2/SCT × payer)", "the value swing",
                "A book skewed to SCT/CCT (RVU 2.75/3.25) and commercial pays "
                "multiples of a 911-scene BLS book — ask for the mix, not just "
                "transport count."),
            Kpi("Scheduled non-emergent (RSNAT-exposed) share", "the franchise test",
                "How much revenue rides on repetitive dialysis (prior-auth + FCA "
                "exposure) versus clean interfacility discharge/SCT."),
        ],
        margin_profile=(
            "Ground IFT is a labor-heavy, density-driven fixed-cost business. "
            "Because labor is ~69-70% of cost (GOV) and mean cost/transport is "
            "~$2,673 all-in (GOV), margin is made by raising unit-hour utilization "
            "and killing deadhead — which is a function of local node density and "
            "on-campus posting, not clinical differentiation. Layer the facility "
            "contract on top (per-transport rates + availability retainer + "
            "escalators) and the payer/acuity mix (SCT/CCT + commercial vs "
            "911-BLS), and the P&L is decided. Scale spreads dispatch, medical "
            "direction, and fleet overhead across more census, but the AIF is "
            "productivity-adjusted and chronically under-runs paramedic wage "
            "inflation — so 'CPI-linked' reimbursement quietly loses to labor "
            "every year unless the contract escalators and mix carry it."),
    ),
    risks=[
        Risk("Reimbursement / policy cliff", "High",
             "Temporary add-ons lapse 1/1/2028 absent re-extension; the "
             "productivity-adjusted AIF lags cost; Medicaid is below-cost. A "
             "single non-extension or rate freeze compresses margin directly."),
        Risk("FCA / OIG exposure on scheduled non-emergent (dialysis) transport",
             "High",
             "Treble damages, CIAs, exclusion; RSNAT prior-auth already collapsed "
             "that volume nationally. A target leaning on repetitive dialysis "
             "revenue is a red flag."),
        Risk("Crew labor cost + availability", "High",
             "~69-72% of cost; paramedic/EMT (and CCT nurse) wage inflation and "
             "shortage cap unit-hour capacity and squeeze margin faster than the "
             "AIF replaces it."),
        Risk("Insourcing / anchor-contract loss", "Medium",
             "A health system bringing IFT in-house or re-bidding the exclusive "
             "contract is the single biggest revenue-concentration risk — the "
             "insource-vs-outsource swing."),
        Risk("No Surprises Act extension to ground ambulance", "Medium",
             "Federal GAPB action or state rate-setting that compresses the "
             "commercial/OON balance-billing leverage."),
        Risk("Deadhead / low unit-hour utilization", "Medium",
             "Scheduled discharge IFT has high empty-return miles; without a "
             "subsidy/retainer contract and local density, low UHU destroys margin."),
        Risk("CON / licensure change", "Low",
             "Mostly protective; a loosening could invite entrants but is "
             "slow-moving and varies by state."),
        Risk("Fuel / vehicle / maintenance", "Low",
             "Real but a small cost share and largely pass-through / "
             "contract-escalated."),
    ],
    diligence_questions=[
        "What share of revenue is scheduled non-emergent (dialysis / "
        "RSNAT-exposed) versus clean interfacility discharge / SCT? (RSNAT + FCA "
        "exposure.)",
        "Show the facility-contract book: per-transport rates by LOS, "
        "availability/subsidy retainers, exclusivity clauses, escalators, and "
        "remaining term/renewal for each anchor system.",
        "Which anchor systems INSOURCE their IFT fleet vs outsource, and what is "
        "the concentration in the top 1-3 contracts?",
        "What is the LOS and payer mix (BLS/ALS/ALS2/SCT × Medicare/Medicaid/"
        "commercial/self-pay) and the revenue-per-transport trend?",
        "What is unit-hour utilization and the deadhead-mile profile, and how is "
        "low-utilization scheduled work subsidized?",
        "Any open OIG/DOJ inquiry, CIA, prepayment review, or RSNAT denial "
        "history? Medical-necessity / PCS documentation audit results?",
        "GADCS selection status and reporting compliance (the 10% penalty "
        "exposure)?",
        "Exposure to the add-on expiration (1/1/2028) and to state "
        "surprise-billing / rate-setting laws in the footprint states?",
        "Medical-director coverage, state licensure/CON status per operating "
        "jurisdiction, and transfer-center/CAD/ePCR integration depth (the "
        "switching-cost moat)?",
        "Crew wage trajectory and staffing-vacancy rate versus the local labor "
        "market (the binding cost constraint)?",
    ],
    insider_lens=[
        "The fee schedule is a floor, not the deal. An IFT operator lives or dies "
        "on the facility contract — per-transport rate + availability subsidy + "
        "exclusivity — not the AFS allowed amount. Underwrite the CONTRACT, not "
        "the code.",
        "Payer mix beats price. An interfacility book skewed to SCT/CCT and "
        "commercial pays multiples of a 911-scene BLS book. Ask for the LOS and "
        "payer mix, not just the transport count.",
        "RSNAT prior-auth is a franchise test. It wiped out the easy repetitive-"
        "dialysis money; survivors run clean interfacility discharge/SCT. Anyone "
        "still fat on scheduled non-emergent dialysis is exposed to prior-auth or "
        "to the FCA.",
        "The add-ons are structurally temporary. Pricing a deal off the "
        "2/3/22.6% add-ons as if permanent is a rookie error — they are a 2-year "
        "political renewal (now through 2027), not a rate.",
        "Insource-vs-outsource is the whole ballgame per market. A system that "
        "insources its fleet is a closed door; a system that outsources with an "
        "exclusive is a moat you can buy. Map every anchor system's posture — "
        "that is exactly what /ift-markets does.",
        "Deadhead is the silent margin killer. Scheduled discharge IFT has high "
        "empty-return miles; unit-hour utilization and post co-location (low "
        "deadhead via local density) separate a good IFT operator from a bad one.",
        "The AIF is productivity-adjusted, so it chronically under-runs paramedic "
        "wage inflation — 'CPI-linked' reimbursement quietly loses to labor every "
        "year unless the mix and the contract escalators carry it.",
        "GADCS is a slow fuse. Mandatory cost reporting is assembling MedPAC's "
        "case for rate reform; whether that means a raise (operators are "
        "under-reimbursed) or a rebasing is the open question to underwrite.",
    ],
    connections=[
        Connection(
            "Size it — the ground-IFT TAM/SAM build + the 20-metro footprint "
            "deep-dive",
            "/ift-markets", "sizing"),
        Connection(
            "Geographic deep-dive — the target-operator footprint, market by "
            "market (anchors, insource-vs-outsource, moat)",
            "/ift-markets", "page"),
        Connection(
            "Clinical demand engine — acute-transfer cases → codes → destination "
            "→ national volume → growth (the IFT volume driver)",
            "/ift-clinical", "deep-dive"),
        Connection(
            "Deal history — EMS + NEMT + air-medical realized corpus (the three "
            "transport modalities)",
            "/deal-search?sector=ems", "deals"),
        Connection(
            "Screen transport targets in this vertical",
            "/target-screener?vertical=ems", "screener"),
        # ── Outbound market reports (adjacencies + the exclusions) ──
        Connection("EMS — the 911/scene ground market IFT is carved out of",
                   "/market/ems", "page"),
        Connection("Air Medical — the EXCLUDED air modality (No Surprises Act "
                   "balance-billing rationale)", "/market/air_medical", "page"),
        Connection("NEMT — the EXCLUDED Medicaid wheelchair/livery benefit",
                   "/market/nemt", "page"),
        Connection("SNF — the largest discharge destination (BLS discharge legs)",
                   "/market/snf", "page"),
        Connection("IRF — inpatient-rehab discharge destination",
                   "/market/irf", "page"),
        Connection("LTCH — long-term acute-care discharge destination (highest "
                   "per-trip)", "/market/ltch", "page"),
        Connection("Hospice — end-of-life discharge destination",
                   "/market/hospice", "page"),
        Connection("Dialysis — the recurring facility-origin round-trip generator",
                   "/market/dialysis", "page"),
        Connection("Hospitals — the IFT ORIGIN (transfer centers + the discharge "
                   "queue)", "/market/hospitals", "page"),
        # ── Real connector datasets in the estate ──
        Connection("CMS Part B physician/supplier — ambulance HCPCS A0426-A0436 "
                   "utilization & spend (the ground-IFT TAM spine)",
                   "/connector-estate?dataset=cms_open_data_physician_supplier_procedure_summary",
                   "connector"),
        Connection("HHS hospital capacity — inpatient/ICU occupancy (the "
                   "throughput / transfer-demand signal)",
                   "/connector-estate?dataset=healthdata_gov_hospital_capacity_facility",
                   "connector"),
        Connection("NPI Registry — ambulance suppliers & EMS agencies "
                   "(taxonomy 341600000X)",
                   "/connector-estate?dataset=npi_provider", "connector"),
        Connection("CMS Provider of Services — the ambulance supplier universe",
                   "/connector-estate?dataset=cms_open_data_pos_qies", "connector"),
        Connection("BLS QCEW — NAICS 621910 ambulance employment & wages "
                   "(labor ~70% of cost)",
                   "/connector-estate?dataset=bls_qcew_industry_area", "connector"),
        Connection("Medicaid — NEMT benefit coverage (the EXCLUDED, "
                   "federally-mandated benefit)",
                   "/connector-estate?dataset=medicaid_data_benefits_covered_nonemergency_medical_transportation",
                   "connector"),
        Connection("OIG LEIE — excluded entities (non-emergent-transport FCA "
                   "screen)",
                   "/connector-estate?dataset=oig_leie_exclusions", "connector"),
    ],
    sources=[
        Source("MedPAC — Payment Basics: Ambulance Services Payment System "
               "(Oct 2024) — $4.0B FFS 2023, ~13% beneficiary use", "GOV",
               "https://www.medpac.gov/wp-content/uploads/2024/10/MedPAC_Payment_Basics_25_ambulance_FINAL_SEC.pdf"),
        Source("MedPAC — Mandated report: payment for ground ambulance services "
               "(Mar 2025)", "GOV",
               "https://www.medpac.gov/wp-content/uploads/2024/08/Ambulance-MedPAC-03.25sec.pdf"),
        Source("42 CFR Part 414 Subpart H — Fee Schedule for Ambulance Services "
               "(RVU table 414.610; SCT definition 414.605)", "GOV",
               "https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-B/part-414/subpart-H"),
        Source("CMS Ambulance Fee Schedule & Public Use Files (exact conversion "
               "factor + national base rates)", "GOV",
               "https://www.cms.gov/medicare/payment/fee-schedules/ambulance"),
        Source("CMS — RSNAT prior authorization (repetitive scheduled "
               "non-emergent ambulance transport)", "GOV",
               "https://www.cms.gov/data-research/monitoring-programs/medicare-fee-service-compliance-programs/prior-authorization-and-pre-claim-review-initiatives/prior-authorization-repetitive-scheduled-non-emergent-ambulance-transport-rsnat"),
        Source("CMS — Ground Ambulance Data Collection System (GADCS): mean cost "
               "$2,673, labor ~69-70%, 10,500+ orgs", "GOV",
               "https://www.cms.gov/medicare/payment/fee-schedules/ambulance/medicare-ground-ambulance-data-collection-system"),
        Source("CMS — Origin & Destination codes for ambulance claims "
               "(the interfacility modifier fingerprint)", "GOV",
               "https://www.cms.gov/files/document/origin-and-destination-codes-specific-ambulance-service-claims-and-emergency-triage-treat-and.pdf"),
        Source("HHS-OIG — Utilization of Medicare Ambulance Transports 2002-2011 "
               "(OEI-09-12-00350: +69% transports, dialysis +269%) + non-emergent "
               "transport enforcement", "GOV",
               "https://oig.hhs.gov/oei/reports/oei-09-12-00350.asp"),
        Source("CMS — Advisory Committee on Ground Ambulance and Patient Billing "
               "(GAPB) report to the Secretaries (Aug 2024)", "GOV",
               "https://www.cms.gov/files/document/report-advisory-committee-ground-ambulance-and-patient-billing.pdf"),
        Source("Canellas et al. — Cost of ED boarding via time-driven "
               "activity-based costing, Annals of Emergency Medicine (May 2024)",
               "ACADEMIC",
               "https://www.annemergmed.com/article/S0196-0644(24)00221-X/fulltext"),
        Source("American Hospital Association — report on discharge delays "
               "(LOS +19% overall, +24% for post-acute discharges, 2019-2022)",
               "INDUSTRY",
               "https://www.aha.org/press-releases/2022-12-06-new-aha-report-hospital-length-stay-increased-19-2019-2022"),
        Source("AAA / EMS1 Trend Report — gap between EMS expenses and "
               "reimbursement (~$1,147 mean/transport)", "INDUSTRY",
               "https://www.ems1.com/ems-trend-report/quantifying-the-gap-between-expenses-and-revenue-for-ems-services"),
        Source("IBISWorld / Grand View — US Ambulance Services market "
               "(~$21-22B; ground ~60-70%) — context cross-check only", "INDUSTRY",
               "https://www.grandviewresearch.com/industry-analysis/us-ambulance-services-market-report"),
        Source("PE Desk — ift_analytics (ground_tam / sam_formula, HCRIS "
               "occupancy, transport-deal corpus) + ift_geo (20-metro footprint "
               "structure)", "INTERNAL", "/ift-markets"),
    ],
    live_figures=_ift.live_figures(),
    trends=(
        "Ground IFT reimbursement sits on a productivity-lagged Medicare fee "
        "schedule (CY2025 AIF 2.4%, GOV) propped up by temporary rural/urban "
        "add-ons that Congress must re-extend every couple of years — now good "
        "only through 12/31/2027. The economics that actually clear are NOT the "
        "fee schedule but the facility contract on top of it: per-transport "
        "rates, availability retainers, and exclusivity with the anchor systems' "
        "transfer centers. Three forces move the market. Volume is the primary "
        "engine — an aging population, an ED-boarding crisis, and the "
        "regionalization of stroke/STEMI/trauma into hub-and-spoke networks push "
        "more (and higher-acuity, better-paying SCT/CCT) interfacility "
        "transports; our HCRIS panel shows national inpatient occupancy up 3.4pp "
        "to 65.5% in FY2022 (SOURCED), the throughput signal behind transfer "
        "demand. Price is a thin, policy-dependent tailwind. Consolidation — "
        "health systems concentrating IFT with a preferred or insourced vendor, "
        "and PE rolling up regional privates — is where a platform captures "
        "share, but the national leverage roll-up (GMR/AMR) got caught by labor "
        "inflation, so the durable value is regional density + hospital "
        "contracts. The dominant regulatory shifts are the nationwide RSNAT "
        "prior-auth (which permanently deflated the scheduled-dialysis model), "
        "relentless FCA enforcement on medically-unnecessary non-emergent runs, "
        "the stalled federal push to end ground-ambulance surprise billing, and "
        "GADCS cost reporting quietly building the case for a future AFS "
        "redesign."),
    growth_levers=[
        GrowthLever(
            "PRICE — fee-schedule + contract escalators",
            "AIF annual update (CY2025 2.4%, GOV) + temporary add-ons "
            "(2/3/22.6%, a floor with cliff risk) + facility-contract escalators "
            "+ commercial/OON leverage. Caveat: the productivity-adjusted AIF "
            "chronically lags labor, so real price is thinner than headline.",
            "~+2-4%/yr", "ILLUSTRATIVE"),
        GrowthLever(
            "VOLUME — demographics + throughput (the primary organic engine)",
            "Aging drives interfacility transfers + post-acute discharges; the "
            "ED-boarding crisis and hub-and-spoke regionalization of "
            "stroke/STEMI/trauma concentrate high-acuity SCT/CCT volume. Our "
            "HCRIS occupancy (62.1%→65.5%, +3.4pp FY2020-2022, SOURCED) is the "
            "throughput proxy.",
            "~+2-4%/yr (primary)", "ILLUSTRATIVE"),
        GrowthLever(
            "CONSOLIDATION — the inorganic multiplier",
            "Health-system integration pulling IFT to a preferred/insourced "
            "vendor (share-of-wallet capture) + PE roll-up of fragmented regional "
            "privates. Accretive to a PLATFORM via M&A + contract capture, NOT "
            "organic market growth — model it as the roll-up multiplier stacked "
            "on organic price×volume.",
            "platform multiplier", "ILLUSTRATIVE"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Interfacility transfer + post-acute discharge demand from "
               "hospital throughput",
        analysis=(
            "A ground-IFT operator's volume equals the count of patients who must "
            "MOVE between facilities, and that is driven by hospital throughput. "
            "High inpatient occupancy → ED boarding → capacity load-balancing "
            "transfers out AND accelerated discharges to post-acute (SNF/IRF/"
            "LTCH/home). Regionalization concentrates the high-acuity (SCT/CCT) "
            "share into hub-and-spoke networks anchored on the tertiary systems "
            "in each footprint. The evidence: ~1.5% of Medicare inpatients (and "
            "~3.5% all-payer, ~1.5M admissions/yr) are transferred between acute "
            "hospitals, with condition-specific rates far higher (up to ~44% of "
            "acute MI) — ACADEMIC; hospital LOS rose +24% for post-acute "
            "discharges 2019→2022 (INDUSTRY, AHA), a placement bottleneck a "
            "reliable discharge-transport partner directly relieves; and boarding "
            "nearly doubles the daily cost of care (~$1,856 vs ~$993/day for an "
            "acute-stroke boarder, ACADEMIC). Our own HCRIS panel puts national "
            "inpatient occupancy at 65.5% in FY2022 (+3.4pp from FY2020, "
            "SOURCED) — the throughput engine of the demand. The value framing to "
            "the hospital is bed-days recovered: a faster, reliable IFT partner "
            "compresses discharge LOS and unlocks admission capacity, a number "
            "that dwarfs the ambulance line-item."),
        basis="GOV"),
    cost_drivers=[
        CostDriver(
            "Crew labor (paramedics, EMTs, CCT nurses/RRTs + dispatch)",
            "~69-72% of cost",
            "The binding constraint (GOV, CMS GADCS puts the ground labor portion "
            "at ~70%). Wage inflation + the paramedic shortage cap unit-hour "
            "capacity and squeeze margin faster than the AIF replaces it.",
            "GOV"),
        CostDriver(
            "Vehicle, fuel & maintenance",
            "~10-15% of cost",
            "Ambulance capital, depreciation, upfit, fuel, and onboard medical "
            "equipment — capital-intensive and inflation-exposed, but largely "
            "pass-through / contract-escalated (INDUSTRY/trade benchmark).",
            "ILLUSTRATIVE"),
        CostDriver(
            "Billing / RCM (multi-payer claims + medical-necessity docs)",
            "~3-6% of cost",
            "Complex multi-payer claims, PCS/medical-necessity documentation, "
            "prior-auth admin, denials/appeals — a margin LEVER for a strong "
            "operator (clean docs + payer-mix optimization).",
            "ILLUSTRATIVE"),
        CostDriver(
            "Dispatch / communications / CAD",
            "~2-4% of cost",
            "Dispatch centers, CAD, and transfer-center + ePCR integration — "
            "rising with the digital-connectivity investment that is also the moat.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Insurance (auto + professional liability)",
            "~2-4% of cost",
            "Rising in litigious markets; EMTALA-adjacent liability on a "
            "life-safety service.",
            "ILLUSTRATIVE"),
    ],
    cms_trend=CmsTrend(
        takeaway=(_CMS_TAKEAWAY or
                  "National inpatient occupancy — the interfacility "
                  "transfer-demand engine — runs in the mid-60s% per CMS HCRIS "
                  "(GOV), elevated versus the pre-COVID low-60s; a trended "
                  "line-level ambulance-utilization series is network-gated "
                  "offline and cited from MedPAC / the fee schedule instead."),
        chart_kind="bars"),
    state_breakdown=(
        (_STATE_NOTE or
         "IFT carries no vendored ambulance/NEMT facility roll, so a per-state "
         "facility map is honestly omitted; the demand geography is hospital "
         "occupancy (SOURCED, HCRIS) and the SOURCED per-metro origin/destination "
         "structure on /ift-markets.")
        + f" The target-operator footprint is {_N_METROS} metros across "
        f"{_N_REGIONS} regions ({_FP_METRO_HOSP:,} metro hospitals; the footprint "
        f"STATES span {_FP_HOSP_SHARE:.1f}% of US hospitals and {_FP_SNF_SHARE:.1f}% "
        "of SNF beds, SOURCED). The bottom-up SAM built from that structure is "
        f"~${_SAM_C:,.1f}M central (${_SAM_LO:,.0f}-{_SAM_HI:,.0f}M), ~{_SAM_SERV:,.0f} "
        f"serviceable of ~{_SAM_DEMAND:,.0f} demand missions — market by market on "
        "/ift-markets."),
)


# ── Registration ─────────────────────────────────────────────────────────────
# ``interfacility_transport`` is a canonical subsector (see CANONICAL_SUBSECTORS
# in ``__init__.py``, added at the task-#16 integration step), so ``validate()``
# accepts the slug and this registers the full dossier straight away:
#   * report_for('interfacility_transport') returns the full dossier;
#   * /market/interfacility_transport renders the dossier, not the scaffold;
#   * the /market index lists it under "Other services";
#   * autoload_errors() stays [] — register() never raises.
register(REPORT)
