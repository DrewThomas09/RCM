"""IFT geographic deep-dive — the target-operator FOOTPRINT registry plus the
SOURCED per-metro market structure computed from our vendored CMS estate.

The Interfacility Transport (IFT) TAM is *US ground interfacility ambulance
only* (BLS/ALS/CCT/SCT + ground mileage — HCPCS A0426/A0428/A0427/A0429/A0433/
A0434/A0425), excluding NEMT and air. The national TAM is sized top-down in
:mod:`ift_analytics`; **this module supplies the bottom-up SAM spine** — the real
origins (hospitals = IFT origins) and destinations (SNF/IRF/LTCH/hospice/home-
health/dialysis = discharge + recurring-round-trip demand) in each of the target
operator's actual metros, computed offline from files that ship.

What is SOURCED (computed here, zero new data, reproducible):

  * per-metro hospital count + the named facilities (the anchor SYSTEMS are
    inferable from ``facility_name``) — from ``hospital_coords.csv``;
  * per-metro HCRIS beds + inpatient-days + a metro-specific occupancy, joined
    by CCN from the vendored HCRIS panel (``rcm_mc/data/hcris``) — the discharge
    engine sizing;
  * per-metro post-acute DESTINATION inventory (SNF facilities + certified beds,
    IRF, LTCH + beds, hospice, home-health, dialysis + stations) — the ground-IFT
    discharge + recurring-round-trip demand, from the ``*_providers.csv`` rolls;
  * a per-metro node-density read (the load-chaining / unit-hour-utilization moat)
    and a discharge-base building block (beds × discharges/bed/yr).

What is a LABELED assumption (basis stated, never presented as SOURCED):

  * discharges/bed/yr = occ × 365 / ALOS = 0.657 × 365 / 4.5 ≈ 53.3 — occ is the
    SOURCED national HCRIS FY2022 figure, ALOS 4.5 is GOV (AHA/HCUP); the product
    is ILLUSTRATIVE-with-basis. The metro-specific occupancy is *also* computed
    SOURCED and exposed so a caller can refine the national factor per market.

What is PUBLIC-WEB knowledge (named honestly, labeled, never fabricated): the
anchor health systems, the incumbent/consolidator IFT operators, and the
insource-vs-outsource read per metro — drawn from public/company sources in the
research briefs. **No contract exclusivities or per-transport rates are asserted.**

Two honest data caveats travel with the affected records: Nebraska Medicine/UNMC
(Omaha's academic quaternary hub) and Ascension Via Christi (Wichita's dominant
tertiary system) are ABSENT from the geocoded ``hospital_coords.csv`` rolls — they
are named from public knowledge with the gap flagged, and their absence depresses
the metro hospital/bed counts (a documented undercount, not a fabrication).

Design contract (mirrors ``ift_analytics``): pure, no runtime network, cached, and
every function **degrades — never raises** — returning typed records with a
``source_label`` so the report/page renders an honest label instead of crashing.
"""
from __future__ import annotations

import functools
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# ── Labeled sizing assumptions (basis stated) ────────────────────────────────
# Occupancy is SOURCED (national HCRIS FY2022: 188.65M patient-days / 287.25M
# bed-days-available = 0.657); ALOS 4.5 is GOV (AHA/HCUP national); the product
# — discharges per staffed bed per year — is ILLUSTRATIVE-with-basis.
OCC_NATIONAL = 0.657
ALOS_DAYS = 4.5
DISCHARGES_PER_BED_YEAR = round(OCC_NATIONAL * 365.0 / ALOS_DAYS, 1)   # ≈ 53.3

# SNF recurring-return-leg parameters (used by the report's PAC demand read; the
# dollarised SAM applies these in ift_analytics.sam_formula). Occupancy GOV
# magnitude (NIC/CMS ~0.77); the per-occupied-bed annual ground-IFT return-leg
# rate is ILLUSTRATIVE.
SNF_OCC = 0.77

# The 11 footprint states (every target state has real hospitals in our rolls).
FOOTPRINT_STATES: Tuple[str, ...] = (
    "NE", "OH", "WI", "IA", "KS", "IN", "KY", "MO", "MN", "VA", "WY")

_STRUCTURE_LABEL = (
    "SOURCED · CMS hospital_coords + HCRIS (beds/patient-days) + "
    "snf/irf/ltch/hospice/home_health/dialysis provider rolls, city+state "
    "filtered to the metro; anchor systems & operators PUBLIC-WEB (labeled)")


# ── The target-operator footprint registry (the MARKETS structure, as data) ──
@dataclass(frozen=True)
class MetroDef:
    """A static registry entry for one target metro.

    ``states``/``cities`` drive the SOURCED CSV filter. ``anchor_systems`` and
    ``named_operators`` are PUBLIC-WEB knowledge (named honestly). ``insource_class``
    is the coarse insource-vs-outsource archetype that ``ift_analytics.sam_formula``
    maps to a realistically-serviceable share s(m). ``rural`` flags the long-leg /
    super-rural mileage markets that carry a higher revenue-per-transport."""
    name: str
    region: str                     # region key (e.g. "nebraska")
    region_label: str               # human label (e.g. "Nebraska")
    states: Tuple[str, ...]         # postal abbrs used for the CSV filter
    cities: Tuple[str, ...]         # uppercase city names used for the filter
    profile: str                    # density/geography archetype
    insource_class: str             # drives s(m) in sam_formula
    rural: bool
    anchor_systems: Tuple[str, ...]
    named_operators: Tuple[str, ...]
    insource_read: str
    moat_note: str
    data_caveats: Tuple[str, ...] = ()


# Region labels for the roll-up.
REGION_LABELS: Dict[str, str] = {
    "nebraska": "Nebraska",
    "ohio": "Ohio",
    "kansas_missouri": "Kansas / Missouri",
    "upper_midwest": "Upper Midwest (WI/MN/IA)",
    "indiana_kentucky": "Indiana / Kentucky",
    "virginia_wyoming": "Virginia / Wyoming",
}


def _m(name, region, states, cities, profile, insource_class, rural,
       anchors, operators, insource_read, moat_note, caveats=()):
    return MetroDef(
        name=name, region=region, region_label=REGION_LABELS[region],
        states=tuple(states), cities=tuple(c.upper() for c in cities),
        profile=profile, insource_class=insource_class, rural=rural,
        anchor_systems=tuple(anchors), named_operators=tuple(operators),
        insource_read=insource_read, moat_note=moat_note,
        data_caveats=tuple(caveats))


MARKETS: Tuple[MetroDef, ...] = (
    # ── Nebraska ─────────────────────────────────────────────────────────────
    _m("Omaha", "nebraska", ["NE", "IA"],
       ["Omaha", "Bellevue", "Papillion", "La Vista", "Gretna", "Council Bluffs"],
       "dense-urban", "insourced-top-outsourced-bottom", False,
       ["Nebraska Medicine / UNMC (academic Level I / transplant quaternary hub)",
        "CHI Health (CommonSpirit) — Bergan Mercy/CUMC, Lakeside, Midlands",
        "Nebraska Methodist Health System", "Children's Nebraska (peds quaternary)"],
       ["Midwest Medical Transport (MMT, Omaha HQ — reference incumbent)",
        "GMR / AMR via legacy Rural/Metro (non-emergency IFT)",
        "Omaha Fire Department (municipal 911, insourced)"],
       "911 municipal (Omaha Fire); adult hospital IFT/CCT OUTSOURCED to privates "
       "(MMT-led); peds/neonatal CCT insourced at Children's. CHI's statewide "
       "intra-system transfer lanes are the captive, contractable prize.",
       "First-call/share-of-wallet with CHI + Methodist + Nebraska Medicine "
       "transfer centers; highest metro density in-state (best UHU, lowest "
       "deadhead); CHI Omaha↔GI↔Kearney↔Lincoln intra-system lanes.",
       ["Nebraska Medicine/UNMC (CCN 280048) ABSENT from geocoded rolls — named "
        "from public knowledge; its absence undercounts Omaha hospital beds."]),
    _m("Lincoln", "nebraska", ["NE"], ["Lincoln"],
       "mid-size-urban", "outsourced-two-horse", False,
       ["Bryan Health (Bryan Medical Center, ~664 beds, CAH network)",
        "CHI Health — St. Elizabeth, Nebraska Heart",
        "Madonna Rehabilitation Hospitals (national IRF/LTCH magnet)"],
       ["AmeriPro Health (Lancaster County)", "Midwest Medical Transport (MMT)",
        "Lincoln Fire & Rescue (municipal 911)"],
       "911 municipal; hospital IFT OUTSOURCED to AmeriPro/MMT. Bryan's ~30+ CAH "
       "network funnels transfers inbound; Madonna is an acute→rehab IFT magnet.",
       "Holding Bryan's transfer-center first-call captures BOTH the inbound "
       "CAH-network funnel AND the Madonna acute→rehab lane — compounding, "
       "high-switching-cost. A two-horse race (AmeriPro vs MMT)."),
    _m("North Platte", "nebraska", ["NE"], ["North Platte"],
       "rural-long-leg", "rural-contract-gated", True,
       ["Great Plains Health (sole west-central NE regional hub; 'LifeNet' air)"],
       ["Priority Medical Transport (est. North Platte 2015; acquired by AmeriPro)",
        "Midwest Medical Transport (MMT)"],
       "Ground IFT OUTSOURCED to privates (AmeriPro/Priority, MMT); air branded by "
       "GPH. Zero local IRF/LTCH → all rehab/LTAC placements transported OUT.",
       "Geography is the moat — long legs + thin volume mean only an operator with "
       "local posts + the GPH relationship runs it economically. AmeriPro's "
       "Priority acquisition is a direct incumbency-capture play."),
    _m("Columbus (NE)", "nebraska", ["NE"], ["Columbus"],
       "rural-spoke", "rural-contract-gated", True,
       ["Columbus Community Hospital (independent community, single acute node)"],
       ["AmeriPro Health (Platte County)", "Midwest Medical Transport (MMT)"],
       "Pure OUTBOUND spoke — tertiary cases sent to Omaha (~90 mi) / Lincoln "
       "(~75 mi); a CHI Schuyler CAH nearby pulls toward CHI. Single-contract market.",
       "LOW structural moat — one independent hospital, outbound-dominant. The prize "
       "is first-call + backhauling the Columbus→Omaha/Lincoln lane against corridor "
       "volume; highly exposed to whichever consolidator locks the hospital."),
    _m("Grand Island / Kearney", "nebraska", ["NE"],
       ["Grand Island", "Kearney", "Hastings"],
       "rural-cluster", "rural-contract-gated", True,
       ["CHI Health Good Samaritan (Kearney) + St. Francis (Grand Island) — "
        "CHI regional hubs on the captive statewide network",
        "Kearney Regional, Grand Island Regional (for-profit entrants)",
        "Mary Lanning Healthcare (Hastings, independent)"],
       ["AmeriPro Health (Buffalo/Dawson/Adams counties)",
        "Midwest Medical Transport (MMT)"],
       "Ground IFT OUTSOURCED; CHI facilities steer CHI-preferred vendors while "
       "for-profits/independents contract per-relationship — fragmented contracting.",
       "The CHI intra-system lanes (Good Sam + St. Francis) are the captive prize; "
       "three mid-size cities ~40-50 mi apart on I-80 are backhaul-friendly. "
       "AmeriPro's corridor roll-up is the central competitive threat."),
    # ── Ohio ─────────────────────────────────────────────────────────────────
    _m("Cleveland", "ohio", ["OH"],
       ["Cleveland", "Beachwood", "Independence", "Parma", "Euclid", "Mayfield Heights"],
       "dense-urban", "insourced-top-outsourced-bottom", False,
       ["Cleveland Clinic (quaternary magnet; own Critical Care Transport)",
        "University Hospitals (UH Ground CCT + AirMed via PHI)",
        "MetroHealth (Level I; Metro Life Flight)"],
       ["Physicians Ambulance (NE-Ohio hospital-partnered discharge/skilled)",
        "regional privates", "municipal fire-based EMS (911)"],
       "INSOURCED-TOP / OUTSOURCED-BOTTOM: Clinic/UH/Metro each own high-acuity "
       "CCT+air (a hard ceiling); the winnable SAM is routine BLS/ALS discharge + "
       "SNF/dialysis back-transfer.",
       "Three competing quaternary systems make this the densest transfer market "
       "and the strongest insource-vs-outsource battleground; moat on the routine "
       "book is contract + transfer-center workflow lock-in, not clinical."),
    _m("Cincinnati", "ohio", ["OH"], ["Cincinnati", "West Chester", "Blue Ash"],
       "bi-state-urban", "insourced-top-outsourced-bottom", False,
       ["UC Health (Level I / academic quaternary)", "TriHealth",
        "Bon Secours Mercy Health", "The Christ Hospital",
        "Cincinnati Children's (peds quaternary magnet; insourced peds/ECMO)"],
       ["Cincinnati Medical Transport", "regional privates",
        "municipal fire-based EMS (911)"],
       "Peds specialty transport insourced at Children's; adult routine BLS/ALS "
       "discharge is the contestable slice. Bi-state OH-KY dual licensure is a "
       "barrier-to-entry moat.",
       "Densest post-acute landscape in the footprint (72 SNFs) → the model "
       "discharge-transport + dialysis-round-trip market; low deadhead, high UHU; "
       "dual-state licensure protects incumbents."),
    _m("Columbus (OH)", "ohio", ["OH"],
       ["Columbus", "Dublin", "Westerville", "Marysville"],
       "dense-urban", "mixed-confirmed-outsource", False,
       ["OhioHealth (Riverside Methodist, Grant)", "OSU Wexner (academic quaternary)",
        "Mount Carmel / Trinity Health", "Nationwide Children's (peds quaternary)"],
       ["Superior Air-Ground (Mount Carmel 'Home Network', embedded coordinators)",
        "Ultra EMS", "Ohio Ambulance Solutions"],
       "CONFIRMED OUTSOURCE at Mount Carmel (Superior embedded per campus); "
       "OhioHealth/OSU sourcing unconfirmed — the largest unclaimed prize.",
       "The Mount Carmel–Superior relationship is a textbook workflow-integration "
       "moat (embedded scheduling coordinators = default first-call, high switching "
       "costs).",
       ["Home-health count (288) is statewide HQ-address clustering, not local "
        "service density — directional only."]),
    _m("Dayton", "ohio", ["OH"],
       ["Dayton", "Kettering", "Miamisburg", "Centerville"],
       "mid-size-urban", "two-anchor-contestable", False,
       ["Premier Health (Miami Valley Hospital, Level I trauma magnet)",
        "Kettering Health", "Dayton Children's (peds hub)"],
       ["Superior Air-Ground (Dayton station)", "regional privates",
        "fire-based EMS (911)"],
       "Two-anchor concentration — winning EITHER Premier or Kettering's BLS/ALS "
       "discharge book captures a large metro share; longest rural feeder legs of "
       "the four OH metros (Darke/Preble/Champaign) add deadhead + some air interplay.",
       "First-call status with one system is decisive; switching costs high once "
       "integrated into the transfer-center workflow."),
    # ── Kansas / Missouri ────────────────────────────────────────────────────
    _m("Kansas City (bi-state)", "kansas_missouri", ["KS", "MO"],
       ["Kansas City", "Overland Park", "Lees Summit", "Lee's Summit",
        "Independence", "Olathe", "Shawnee", "Leawood"],
       "bi-state-urban", "bi-state-outsourced", False,
       ["The University of Kansas Health System (academic Level I)",
        "Saint Luke's Health System", "HCA Midwest (Research/Overland Park)",
        "University Health (ex-Truman)", "Children's Mercy (insourced peds CCT)"],
       ["AMR / GMR KC Metro (dual KS+MO-licensed; adult IFT/CCT leader)",
        "Front Line EMS (regional private)", "KCFD + Johnson County MED-ACT (911)"],
       "Predominantly OUTSOURCED for adult IFT (AMR/GMR-led); ONE walled-off "
       "insource niche (Children's Mercy peds/neonatal CCT). HCA's national GMR "
       "relationship pre-commits its volume.",
       "Bi-state dual-licensure is a structural barrier; densest node cluster in the "
       "footprint (22 hospitals + 83 post-acute) → best deadhead/UHU economics — the "
       "market where the density moat pays most."),
    _m("Wichita", "kansas_missouri", ["KS"], ["Wichita"],
       "mid-size-urban", "public-utility-mixed", False,
       ["Ascension Via Christi (St. Francis Level I + St. Joseph — tertiary hubs)",
        "Wesley Healthcare (HCA)"],
       ["Sedgwick County EMS (public-utility 911 + IFT)",
        "AMR / GMR (won Wesley/HCA interfacility March 2022)"],
       "PUBLIC-UTILITY base (county EMS carries Via Christi + residual IFT) partially "
       "converted to system-directed private: Wesley/HCA moved ~77% of county IFT "
       "(~4,873/2020) to AMR in 2022 — the cleanest insource-vs-outsource proof point.",
       "Whoever holds Via Christi first-call + the county residual holds the volume, "
       "but the Wesley flip proves the moat is only as durable as ownership intent.",
       ["Ascension Via Christi St. Francis + St. Joseph (Wichita's dominant tertiary "
        "hubs) ABSENT from geocoded rolls; Wichita IRF/LTCH under-captured — the "
        "metro hospital/bed counts here are an undercount."]),
    # ── Upper Midwest (WI/MN/IA) ─────────────────────────────────────────────
    _m("Madison", "upper_midwest", ["WI"], ["Madison"],
       "academic-referral", "outsourced-fragmented", False,
       ["UW Health (academic quaternary; UW Med Flight)", "SSM Health / Dean",
        "UnityPoint Health-Meriter"],
       ["Ryan Brothers Ambulance (dominant private; IFT to 100-mi radius)",
        "Madison Fire Dept (municipal 911)"],
       "PRIVATE-ANCHORED / OUTSOURCED — the systems rely on Ryan Brothers + regional "
       "privates for routine hospital-to-hospital/discharge work.",
       "Incumbent moat = Ryan Brothers' 60-yr first-call relationships + critical-care "
       "capability + 100-mi coverage density; the acquirable asset is the regional "
       "private, not a system fleet."),
    _m("Milwaukee", "upper_midwest", ["WI"],
       ["Milwaukee", "Wauwatosa", "West Allis"],
       "dense-urban", "outsourced-fragmented", False,
       ["Advocate Aurora (Aurora St. Luke's, cardiac/quaternary)",
        "Froedtert & MCW (academic Level I)", "Ascension Wisconsin",
        "Children's Wisconsin"],
       ["Bell Ambulance (IFT-specialized)", "Curtis Ambulance (since 1858)",
        "Paratech Ambulance (Midwest Medical)", "fire-based 911"],
       "The clearest OUTSOURCED / private-dominant IFT market in the region — systems "
       "contract IFT out to the private pool; no single private is clearly first-call "
       "system-wide.",
       "Moat = local density + first-call with Aurora/Froedtert/Ascension transfer "
       "centers; densest compact-urban market (highest UHU / lowest deadhead) → the "
       "region's prime roll-up target, but the most contested."),
    _m("Twin Cities", "upper_midwest", ["MN"],
       ["Minneapolis", "Saint Paul", "St Paul", "St. Paul", "Edina", "Maplewood"],
       "dense-urban", "insourced-heavy", False,
       ["M Health Fairview (academic)", "Allina Health (Abbott Northwestern; owns EMS)",
        "HealthPartners (Regions Level I)", "Hennepin Healthcare (HCMC)",
        "North Memorial Health (owns ground + air)"],
       ["Allina Health EMS (hospital-owned; ~34,000 interfacility requests/2024)",
        "M Health Fairview EMS", "North Memorial Health (owned fleet)"],
       "STRONGLY INSOURCED — Allina/North Memorial/M Health run their own large IFT "
       "fleets and even sell CCT to non-system facilities; serviceable share is the "
       "SNF/post-acute discharge RESIDUAL, not the captive tertiary transfer stream.",
       "The moat belongs to the INCUMBENT SYSTEMS (deep transfer-center/CAD "
       "integration, co-located posts). Displacing captive volume needs a system to "
       "strategically outsource what it built to own — low-probability. WATCH: Allina→"
       "Sutter change of control (reported 2026)."),
    _m("Rochester (MN)", "upper_midwest", ["MN"], ["Rochester"],
       "academic-referral", "insourced-heavy", False,
       ["Mayo Clinic (national quaternary referral magnet; ~1,157 beds)",
        "Olmsted Medical Center (community counterweight)"],
       ["Mayo Clinic Ambulance (ex-Gold Cross; ~70 units; sole 911 ALS + Mayo IFT)"],
       "FULLY INSOURCED / CAPTIVE — Mayo owns the fleet, the transfer center, the 911 "
       "designation and the referral network. Independent opportunity = non-Mayo "
       "community discharges (small) + subcontracted overflow only.",
       "Essentially impenetrable in Mayo's captive stream (switching cost is infinite "
       "when transport is the same enterprise); long-leg/rural IFT geography with air "
       "interplay. A proof point of the insource archetype, not an acquisition target."),
    _m("Des Moines", "upper_midwest", ["IA"],
       ["Des Moines", "West Des Moines", "Clive"],
       "mid-size-urban", "mixed-insource-residual", False,
       ["UnityPoint Health-Iowa Methodist", "MercyOne Des Moines (own critical-care "
        "ambulance)", "Broadlawns (safety-net)"],
       ["MercyOne Des Moines Ambulance (hospital-based, MICU-capable)",
        "Midwest Ambulance Service of Iowa (private non-emergent/IFT)",
        "Des Moines Fire (911)"],
       "PARTIALLY INSOURCED — the two anchors tilt to insourcing their own critical-"
       "care legs; the private (Midwest Ambulance) picks up the non-emergent SNF-"
       "discharge/overflow residual.",
       "For the system critical-care stream the moat is system-owned; the contestable "
       "layer is the non-emergent SNF-discharge/repatriation pool + central-Iowa "
       "mileage legs."),
    # ── Indiana / Kentucky ───────────────────────────────────────────────────
    _m("Crown Point / NW Indiana", "indiana_kentucky", ["IN"],
       ["Crown Point", "Merrillville", "Gary", "Munster", "Hammond", "Valparaiso"],
       "spoke-cross-state", "outsourced-incumbent", False,
       ["Franciscan Health (runs own CCT elsewhere in IN — insource signal)",
        "Community Healthcare / Powers Health", "Methodist Hospitals (safety-net)",
        "Northwest Health (CHS)"],
       ["Superior Air-Ground Ambulance of Indiana (dominant regional private; "
        "911 + IFT + CCT + Chicago-corridor air)", "Preferred One Ambulance",
        "Elite Ambulance", "municipal fire-based 911"],
       "FRAGMENTED / OUTSOURCE-LEANING with one strong regional incumbent (Superior) "
       "and one likely partial-insourcer (Franciscan). Highest-acuity leaks OUT to "
       "Chicago academic centers (long cross-state CCT legs).",
       "Superior's 911 franchises + CCT depth + Chicago air/ground density is a hard-"
       "to-displace local-density moat; the contestable wedge is the Chicago-bound "
       "tertiary CCT/SCT legs + any system that chooses to outsource."),
    _m("Louisville", "indiana_kentucky", ["KY"], ["Louisville"],
       "dense-urban", "outsourced-incumbent", False,
       ["Norton Healthcare (largest transfer generator, ~1,479 beds; peds magnet)",
        "UofL Health (academic Level I / transplant)", "Baptist Health"],
       ["AMR / GMR (embedded 'preferred provider' with UofL — 8 co-branded units, "
        "9 facilities, embedded coordinators)", "Yellow Ambulance (Procarent)",
        "Louisville Metro EMS (911)"],
       "UofL clearly OUTSOURCED to AMR (co-branded, workflow-integrated); Norton and "
       "Baptist sourcing UNCONFIRMED — the decisive variable. High-acuity is RETAINED "
       "in-metro (UofL trauma/transplant, Norton peds) → dense repeat-route book.",
       "The AMR–UofL deal is a textbook contract moat (co-branding + embedded "
       "coordinators + 9-site workflow = high switching cost); Norton + Baptist are "
       "the prizes — win one and you win the market. Compact county = high UHU.",
       ["Hospice shows only 1 by city-attribution (CCNs file under suburb addresses "
        "— an undercount; use state-level context)."]),
    # ── Virginia / Wyoming ───────────────────────────────────────────────────
    _m("Northern Virginia", "virginia_wyoming", ["VA"],
       ["Lorton", "Fairfax", "Alexandria", "Arlington", "Falls Church",
        "Woodbridge", "Reston"],
       "dense-urban", "outsourced-incumbent", False,
       ["Inova (dominant integrated system; only Level I trauma center)",
        "HCA (Reston, Dominion)", "Sentara Northern Virginia", "Novant Prince William",
        "Virginia Hospital Center (Mayo-affiliated)"],
       ["Lifecare Medical Transports (Priority Ambulance brand; BLS/ALS/SCT/CCT)",
        "AMR / GMR Washington DC (Kaiser Permanente ~500k members; NICU/PICU/bariatric)",
        "Fairfax County Fire & Rescue + Arlington + Alexandria (fire-based 911)"],
       "Predominantly OUTSOURCED — Inova/HCA/Sentara/Novant contract regional privates "
       "for interfacility BLS/ALS/CCT; highest-acuity/neonatal via contracted teams. "
       "Two fortress incumbents (Lifecare, AMR).",
       "Prize = first-call + transfer-center/CAD/ePCR integration with INOVA (the hub "
       "every spoke feeds) + compact-geography density; BUT displacement is HARD "
       "(Lifecare 30-yr tenure, AMR's Kaiser book). Realistic play = share-of-wallet "
       "at one system or a niche acuity lane.",
       ["Zero LTCH in NoVA in our data (all 4 VA LTCHs are Hampton Roads/Richmond) — "
        "the highest-per-trip LTCH-IFT lane is thin/out-of-region."]),
    _m("Cheyenne / Casper (WY)", "virginia_wyoming", ["WY"],
       ["Cheyenne", "Casper", "Gillette", "Laramie"],
       "frontier-long-leg", "rural-contract-gated", True,
       ["Cheyenne Regional Medical Center (SE-WY referral hub)",
        "Banner Wyoming Medical Center (Casper, central hub)",
        "Campbell County Health (Gillette)", "Ivinson Memorial (Laramie)"],
       ["Frontier Ambulance (Priority brand; Fremont County 5-yr 911+IFT contract)",
        "Cheyenne + Casper municipal city EMS (AMR as backup)",
        "CRMC-UCHealth LifeLine + Banner-MedTrans (air, EXCLUDED from TAM)"],
       "Ground IFT outsourced-to-municipal/county/private and CAPPED ABOVE by system-"
       "partnered AIR (200-300+ mi legs to Denver/SLC/Billings are air-captured, "
       "out of the ground TAM). Ground SAM = short-leg/lower-acuity/discharge/"
       "weather-backup volume, gated behind exclusive contracts.",
       "The EXCLUSIVE county or hospital contract is the entire moat; density is "
       "INVERTED (long legs are the barrier AND the moat). Win by locking a county/"
       "hospital 911+IFT contract (Frontier/Fremont template) + being the ground "
       "complement to the air programs.",
       ["Zero LTCH statewide in WY; thinnest post-acute base in the footprint — "
        "rehab/LTAC placements route out of state."]),
)


def markets_by_region() -> Dict[str, List[MetroDef]]:
    """``{region_key: [MetroDef, ...]}`` preserving registry order."""
    out: Dict[str, List[MetroDef]] = {}
    for md in MARKETS:
        out.setdefault(md.region, []).append(md)
    return out


def metro_def(name: str) -> Optional[MetroDef]:
    """The :class:`MetroDef` whose ``name`` matches (case-insensitive), or None."""
    key = (name or "").strip().lower()
    for md in MARKETS:
        if md.name.lower() == key:
            return md
    return None


# ── Computed per-metro structure (SOURCED) ───────────────────────────────────
@dataclass
class MetroStructure:
    """The SOURCED market structure for one target metro, plus the registry read.

    Origins = hospitals (IFT origins); destinations = the post-acute rolls (the
    discharge + recurring-round-trip demand). ``discharge_base`` is the labeled
    building block ``hcris_beds × 53.3`` that ``ift_analytics.sam_formula`` turns
    into dollars."""
    available: bool
    name: str = ""
    region: str = ""
    region_label: str = ""
    states: List[str] = field(default_factory=list)
    profile: str = ""
    rural: bool = False
    insource_class: str = ""
    # origins
    n_hospitals: int = 0
    hospital_names: List[str] = field(default_factory=list)
    hcris_beds: float = 0.0
    hcris_patient_days: float = 0.0
    hcris_bed_days_available: float = 0.0
    n_hospitals_with_hcris: int = 0
    metro_occupancy: Optional[float] = None
    # destinations
    n_snf: int = 0
    snf_beds: int = 0
    n_irf: int = 0
    n_ltch: int = 0
    ltch_beds: int = 0
    n_hospice: int = 0
    n_home_health: int = 0
    n_dialysis: int = 0
    dialysis_stations: int = 0
    # density
    n_postacute_destinations: int = 0   # SNF + IRF + LTCH (load-chaining nodes)
    n_nodes: int = 0                    # hospitals + post-acute destinations
    density_tier: str = ""
    density_note: str = ""
    # SAM building block (labeled)
    discharge_base: float = 0.0         # hcris_beds × DISCHARGES_PER_BED_YEAR
    discharge_base_basis: str = ""
    # registry read (PUBLIC-WEB)
    anchor_systems: List[str] = field(default_factory=list)
    named_operators: List[str] = field(default_factory=list)
    insource_read: str = ""
    moat_note: str = ""
    data_caveats: List[str] = field(default_factory=list)
    source_label: str = ""


@functools.lru_cache(maxsize=1)
def _beds_by_ccn() -> Dict[str, Tuple[Optional[float], Optional[float], Optional[float]]]:
    """``{ccn_zfill6: (beds, patient_days, bed_days_available)}`` from the latest
    HCRIS row per CCN. Returns ``{}`` on any failure so callers degrade to a
    beds-unavailable structure rather than raising."""
    try:
        import pandas as pd
        from ..data import hcris
        df = hcris._get_latest_per_ccn()
        if df is None or df.empty:
            return {}
        out: Dict[str, Tuple[Optional[float], Optional[float], Optional[float]]] = {}
        beds = pd.to_numeric(df.get("beds"), errors="coerce")
        pdays = pd.to_numeric(df.get("total_patient_days"), errors="coerce")
        bda = pd.to_numeric(df.get("bed_days_available"), errors="coerce")
        ccns = df.get("ccn")
        for i in range(len(df)):
            ccn = str(ccns.iloc[i]).strip().zfill(6)
            if not ccn:
                continue
            b = beds.iloc[i]
            p = pdays.iloc[i]
            d = bda.iloc[i]
            out[ccn] = (
                float(b) if pd.notna(b) else None,
                float(p) if pd.notna(p) else None,
                float(d) if pd.notna(d) else None)
        return out
    except Exception:  # noqa: BLE001 — degrade, never raise
        return {}


def _filter(records, states: Tuple[str, ...], cities: Tuple[str, ...],
            city_attr: str = "city", state_attr: str = "state"):
    """Records whose (state, uppercased-city) fall inside the metro's sets."""
    st = set(states)
    cs = set(cities)
    out = []
    for r in records:
        rs = (getattr(r, state_attr, "") or "").strip().upper()
        rc = (getattr(r, city_attr, "") or "").strip().upper()
        if rs in st and rc in cs:
            out.append(r)
    return out


def _density_read(n_nodes: int, n_postacute: int, rural: bool) -> Tuple[str, str]:
    """A node-density tier + prose read (the load-chaining / UHU moat).

    Density is the ground-IFT moat: more clustered origin+destination nodes →
    higher achievable unit-hour utilization, lower deadhead. Rural markets flip
    the logic to long-leg mileage economics."""
    if rural:
        return ("thin/long-leg",
                f"Thin node cluster ({n_nodes} origin+destination nodes) over a "
                "wide rural geography — the logic flips from unit-hour utilization "
                "to long-leg mileage economics (super-rural add-ons, air interplay).")
    if n_nodes >= 90:
        tier = "very-dense"
    elif n_nodes >= 55:
        tier = "dense"
    elif n_nodes >= 30:
        tier = "moderate"
    else:
        tier = "thin"
    return (tier,
            f"{tier.capitalize()} node cluster ({n_nodes} origin+destination nodes; "
            f"{n_postacute} post-acute destinations) — the more nodes clustered, the "
            "higher achievable unit-hour utilization and the deeper the density moat "
            "(load-chaining, low deadhead).")


@functools.lru_cache(maxsize=64)
def metro_structure(name: str) -> MetroStructure:
    """The SOURCED structure for one metro (by :class:`MetroDef` name).

    Filters ``hospital_coords`` + the six post-acute rolls to the metro's
    city+state sets, joins HCRIS beds/patient-days by CCN, and reads the registry.
    Degrades to ``available=False`` if the metro is unknown or the CSVs are
    unreadable — never raises."""
    md = metro_def(name)
    if md is None:
        return MetroStructure(available=False, name=str(name),
                              source_label=_STRUCTURE_LABEL,
                              density_note="Unknown metro — not in the footprint registry.")
    try:
        from ..data.hospital_coords import load_hospital_coords
        from ..data.snf import load_snf_providers
        from ..data.irf import load_irf_providers
        from ..data.ltch import load_ltch_providers
        from ..data.hospice import load_hospice_providers
        from ..data.home_health import load_home_health_providers
        from ..data.dialysis import load_dialysis_providers

        hosp = _filter(load_hospital_coords().values(), md.states, md.cities)
        beds_map = _beds_by_ccn()
        hcris_beds = hcris_pd = hcris_bda = 0.0
        n_with_hcris = 0
        for h in hosp:
            row = beds_map.get(str(h.ccn).strip().zfill(6))
            if not row:
                continue
            b, p, d = row
            if b and b > 0:
                hcris_beds += b
                n_with_hcris += 1
            if p and p > 0:
                hcris_pd += p
            if d and d > 0:
                hcris_bda += d
        hospital_names = sorted(h.facility_name for h in hosp if h.facility_name)

        snf = _filter(load_snf_providers().values(), md.states, md.cities,
                      city_attr="city")
        snf_beds = sum(int(s.certified_beds or 0) for s in snf)
        irf = _filter(load_irf_providers().values(), md.states, md.cities)
        ltch = _filter(load_ltch_providers().values(), md.states, md.cities)
        ltch_beds = sum(int(l.total_beds or 0) for l in ltch)
        hospice = _filter(load_hospice_providers().values(), md.states, md.cities)
        # home_health rolls carry no county but do carry city+state.
        hh = _filter(load_home_health_providers().values(), md.states, md.cities)
        dia = _filter(load_dialysis_providers().values(), md.states, md.cities)
        dia_stations = 0
        for d in dia:
            try:
                dia_stations += int(getattr(d, "dialysis_stations", 0) or 0)
            except (TypeError, ValueError):
                continue

        n_postacute = len(snf) + len(irf) + len(ltch)
        n_nodes = len(hosp) + n_postacute
        tier, dnote = _density_read(n_nodes, n_postacute, md.rural)
        occ = (hcris_pd / hcris_bda) if hcris_bda > 0 else None
        discharge_base = hcris_beds * DISCHARGES_PER_BED_YEAR

        caveats = list(md.data_caveats)
        n_no_hcris = len(hosp) - n_with_hcris
        if n_no_hcris > 0:
            caveats.append(
                f"{n_no_hcris} of {len(hosp)} geocoded hospitals carry no HCRIS bed "
                "row (federal/VA, children's, psych or specialty file no 2552-10) — "
                "the HCRIS bed sum is a conservative floor.")

        return MetroStructure(
            available=True, name=md.name, region=md.region,
            region_label=md.region_label, states=list(md.states),
            profile=md.profile, rural=md.rural, insource_class=md.insource_class,
            n_hospitals=len(hosp), hospital_names=hospital_names,
            hcris_beds=hcris_beds, hcris_patient_days=hcris_pd,
            hcris_bed_days_available=hcris_bda, n_hospitals_with_hcris=n_with_hcris,
            metro_occupancy=occ,
            n_snf=len(snf), snf_beds=snf_beds, n_irf=len(irf),
            n_ltch=len(ltch), ltch_beds=ltch_beds, n_hospice=len(hospice),
            n_home_health=len(hh), n_dialysis=len(dia),
            dialysis_stations=dia_stations,
            n_postacute_destinations=n_postacute, n_nodes=n_nodes,
            density_tier=tier, density_note=dnote,
            discharge_base=discharge_base,
            discharge_base_basis=(
                f"ILLUSTRATIVE-with-basis · HCRIS beds ({hcris_beds:,.0f}, SOURCED) "
                f"× {DISCHARGES_PER_BED_YEAR} discharges/bed/yr "
                f"(= occ {OCC_NATIONAL:.3f} SOURCED-national × 365 / ALOS "
                f"{ALOS_DAYS} GOV)"),
            anchor_systems=list(md.anchor_systems),
            named_operators=list(md.named_operators),
            insource_read=md.insource_read, moat_note=md.moat_note,
            data_caveats=caveats, source_label=_STRUCTURE_LABEL)
    except Exception:  # noqa: BLE001
        return MetroStructure(
            available=False, name=md.name, region=md.region,
            region_label=md.region_label, source_label=_STRUCTURE_LABEL,
            density_note="Per-metro structure computation failed offline.")


def all_metros() -> List[MetroStructure]:
    """Every footprint metro's SOURCED structure, in registry order (available
    ones only). Degrade-safe — skips any metro that fails to compute."""
    out: List[MetroStructure] = []
    for md in MARKETS:
        s = metro_structure(md.name)
        if s.available:
            out.append(s)
    return out


# ── Footprint roll-up (SOURCED) ──────────────────────────────────────────────
@dataclass
class FootprintRollup:
    available: bool
    n_metros: int = 0
    n_regions: int = 0
    # origins
    n_hospitals: int = 0
    hcris_beds: float = 0.0
    n_hospitals_with_hcris: int = 0
    # destinations
    n_snf: int = 0
    snf_beds: int = 0
    n_irf: int = 0
    n_ltch: int = 0
    ltch_beds: int = 0
    n_hospice: int = 0
    n_home_health: int = 0
    n_dialysis: int = 0
    # national context (share-of-national)
    n_hospitals_national: int = 0
    n_snf_national: int = 0
    snf_beds_national: int = 0
    hospitals_national_share: Optional[float] = None
    snf_beds_national_share: Optional[float] = None
    footprint_state_hospitals: int = 0
    footprint_state_snf_beds: int = 0
    # per-region roll (values mix a region_label str with numeric aggregates)
    by_region: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    source_label: str = ""
    note: str = ""


@functools.lru_cache(maxsize=1)
def footprint_rollup() -> FootprintRollup:
    """The national roll-up of the target-operator footprint — the target METROS
    summed, plus share-of-national context (all-hospitals, all-SNF-beds) and the
    footprint-STATE totals (the wider demand pool the metros sit inside). SOURCED,
    offline, degrade-safe."""
    metros = all_metros()
    if not metros:
        return FootprintRollup(available=False, source_label=_STRUCTURE_LABEL,
                               note="No metro structure computed offline.")
    try:
        from ..data.hospital_coords import load_hospital_coords
        from ..data.snf import load_snf_providers

        by_region: Dict[str, Dict[str, Any]] = {}
        agg = dict(n_hospitals=0, hcris_beds=0.0, n_hospitals_with_hcris=0,
                   n_snf=0, snf_beds=0, n_irf=0, n_ltch=0, ltch_beds=0,
                   n_hospice=0, n_home_health=0, n_dialysis=0)
        for s in metros:
            agg["n_hospitals"] += s.n_hospitals
            agg["hcris_beds"] += s.hcris_beds
            agg["n_hospitals_with_hcris"] += s.n_hospitals_with_hcris
            agg["n_snf"] += s.n_snf
            agg["snf_beds"] += s.snf_beds
            agg["n_irf"] += s.n_irf
            agg["n_ltch"] += s.n_ltch
            agg["ltch_beds"] += s.ltch_beds
            agg["n_hospice"] += s.n_hospice
            agg["n_home_health"] += s.n_home_health
            agg["n_dialysis"] += s.n_dialysis
            r = by_region.setdefault(
                s.region, dict(region_label=s.region_label, n_metros=0,
                               n_hospitals=0, hcris_beds=0.0, n_snf=0, snf_beds=0,
                               n_postacute=0))
            r["n_metros"] += 1
            r["n_hospitals"] += s.n_hospitals
            r["hcris_beds"] += s.hcris_beds
            r["n_snf"] += s.n_snf
            r["snf_beds"] += s.snf_beds
            r["n_postacute"] += s.n_postacute_destinations

        # National + footprint-state context.
        all_h = list(load_hospital_coords().values())
        n_h_nat = len(all_h)
        fp_state_h = sum(1 for h in all_h if (h.state or "").upper() in FOOTPRINT_STATES)
        all_snf = list(load_snf_providers().values())
        n_snf_nat = len(all_snf)
        snf_beds_nat = sum(int(s.certified_beds or 0) for s in all_snf)
        fp_snf_beds = sum(int(s.certified_beds or 0) for s in all_snf
                          if (s.state or "").upper() in FOOTPRINT_STATES)

        return FootprintRollup(
            available=True, n_metros=len(metros), n_regions=len(by_region),
            n_hospitals=int(agg["n_hospitals"]), hcris_beds=float(agg["hcris_beds"]),
            n_hospitals_with_hcris=int(agg["n_hospitals_with_hcris"]),
            n_snf=int(agg["n_snf"]), snf_beds=int(agg["snf_beds"]),
            n_irf=int(agg["n_irf"]), n_ltch=int(agg["n_ltch"]),
            ltch_beds=int(agg["ltch_beds"]), n_hospice=int(agg["n_hospice"]),
            n_home_health=int(agg["n_home_health"]), n_dialysis=int(agg["n_dialysis"]),
            n_hospitals_national=n_h_nat, n_snf_national=n_snf_nat,
            snf_beds_national=snf_beds_nat,
            hospitals_national_share=(fp_state_h / n_h_nat) if n_h_nat else None,
            snf_beds_national_share=(fp_snf_beds / snf_beds_nat) if snf_beds_nat else None,
            footprint_state_hospitals=fp_state_h,
            footprint_state_snf_beds=fp_snf_beds,
            by_region=by_region, source_label=_STRUCTURE_LABEL,
            note=("The target-operator footprint summed across the "
                  f"{len(metros)} metros; the share-of-national context uses the "
                  "footprint-STATE totals (the wider demand pool the metros sit "
                  "inside) against the full national rolls. Anchor systems & "
                  "operators are PUBLIC-WEB; counts SOURCED."))
    except Exception:  # noqa: BLE001
        return FootprintRollup(available=False, source_label=_STRUCTURE_LABEL,
                               note="Footprint roll-up computation failed offline.")


# ── The SAM building-blocks helper (imported by the report / page) ───────────
@dataclass
class SamBuildingBlock:
    """One metro's structural inputs to the SAM formula (no assumptions applied)."""
    name: str
    region: str
    region_label: str
    rural: bool
    insource_class: str
    hcris_beds: float
    discharge_base: float           # beds × 53.3 (labeled)
    snf_beds: int
    n_snf: int
    n_irf: int
    n_ltch: int
    n_postacute_destinations: int
    density_tier: str


@dataclass
class FootprintSamInputs:
    available: bool
    blocks: List[SamBuildingBlock] = field(default_factory=list)
    total_hcris_beds: float = 0.0
    total_discharge_base: float = 0.0
    total_snf_beds: int = 0
    source_label: str = ""
    assumptions_note: str = ""


def footprint_sam_building_blocks() -> FootprintSamInputs:
    """The per-metro SAM building blocks the report/page (and
    ``ift_analytics.sam_formula``) consume.

    Returns the SOURCED structural inputs only — the discharge base
    (``beds × 53.3``) and post-acute destination inventory per metro — leaving
    the dollarising assumptions (f_IFT, s(m), r_IFT, λ_return) to
    ``ift_analytics.sam_formula`` so every ILLUSTRATIVE lever lives in one place.
    Degrade-safe."""
    metros = all_metros()
    if not metros:
        return FootprintSamInputs(
            available=False, source_label=_STRUCTURE_LABEL,
            assumptions_note="No metro structure computed offline.")
    blocks = [
        SamBuildingBlock(
            name=s.name, region=s.region, region_label=s.region_label,
            rural=s.rural, insource_class=s.insource_class,
            hcris_beds=s.hcris_beds, discharge_base=s.discharge_base,
            snf_beds=s.snf_beds, n_snf=s.n_snf, n_irf=s.n_irf, n_ltch=s.n_ltch,
            n_postacute_destinations=s.n_postacute_destinations,
            density_tier=s.density_tier)
        for s in metros]
    return FootprintSamInputs(
        available=True, blocks=blocks,
        total_hcris_beds=sum(b.hcris_beds for b in blocks),
        total_discharge_base=sum(b.discharge_base for b in blocks),
        total_snf_beds=sum(b.snf_beds for b in blocks),
        source_label=_STRUCTURE_LABEL,
        assumptions_note=(
            "Structural building blocks only (SOURCED): discharge base = HCRIS beds "
            f"× {DISCHARGES_PER_BED_YEAR} discharges/bed/yr, plus post-acute "
            "destination inventory. The ILLUSTRATIVE SAM levers (f_IFT ground-IFT "
            "fraction of discharges, s(m) serviceable share, r_IFT $/transport, "
            "λ_return SNF recurring legs) are applied by ift_analytics.sam_formula."))
