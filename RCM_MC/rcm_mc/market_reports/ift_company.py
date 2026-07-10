"""MMT (Midwest Medical Transport Company, LLC / "MMT Ambulance") — the
company dossier, as data.

Why this module exists: the prior /ift-mmt surface modeled MMT as a 7-CBSA,
22-county Nebraska+Iowa operator. Primary-source research (NPPES registry
pulls + press/deal records, 2026-07-10) shows that is only the LEGACY CORE —
MMT is a multi-state IFT platform: company materials claim **13 states,
2,800+ team members, 500+ vehicles**, and the NPPES registry carries **24
active organizational NPIs** across NE/IA/SD/MO/OH/IN/WI/CO/RI/NC/VA. This
module is the single source of truth for who MMT actually is: every record
carries an honesty basis and its source (URL + verbatim quote where the
quote was actually seen).

Honesty bases used here (suite contract — no ILLUSTRATIVE anywhere):
  * NPPES     — first-party CMS NPI registry data (pulled 2026-07-10).
  * PRESS     — a company / sponsor / advisor press release or filing.
  * NEWS      — independent press (World-Herald, Journal Star, trade).
  * COURT     — a public docket (Justia / CourtListener / NLRB).
  * ESTIMATE  — a third-party revenue/headcount estimate, named, with the
                conflict between estimators shown, never blended.

Design contract: frozen dataclasses, pure functions, degrade — never raise.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


# ── Source registry ──────────────────────────────────────────────────────────
@dataclass(frozen=True)
class CompanySource:
    key: str
    basis: str            # NPPES | PRESS | NEWS | COURT | ESTIMATE
    label: str            # publisher, title, year
    url: str
    quote: str = ""       # verbatim, only where actually observed


_SOURCES: Tuple[CompanySource, ...] = (
    CompanySource(
        "nppes_pull",
        "NPPES",
        "CMS NPPES NPI Registry — org-NPI sweep for 'Midwest Medical "
        "Transport' + Platte County Ambulance (pulled 2026-07-10)",
        "https://npiregistry.cms.hhs.gov/"),
    CompanySource(
        "hpc_2022",
        "PRESS",
        "Businesswire / Harbour Point Capital, 'Harbour Point Capital "
        "Completes Investment in Midwest Medical Transport', Jan 25 2022",
        "https://www.businesswire.com/news/home/20220125006174/en/",
        "advanced life support and basic life support inter-facility "
        "transports (IFT) and specialty transports to large and mid-sized "
        "health systems, critical access hospitals and long-term care "
        "facilities"),
    CompanySource(
        "lincoln_intl",
        "PRESS",
        "Lincoln International (sell-side advisor) transaction notice, 2022",
        "https://www.lincolninternational.com/transactions/panorama-point-"
        "partners-dixon-midland-and-orix-have-sold-midwest-medical-transport-"
        "to-harbour-point-capital/",
        "one of the largest, independently owned providers of private ground "
        "ambulance services with operations currently in seven states and "
        "nearly 1,000 employees"),
    CompanySource(
        "about_us",
        "PRESS",
        "mmtamb.com — About Us / Careers (company self-report, 2026)",
        "https://mmtamb.com/about-us/",
        "For over 35 years, MMT has partnered with some of the largest and "
        "most prestigious health systems across the country"),
    CompanySource(
        "ciatto_2023",
        "PRESS",
        "Businesswire, 'MMT Ambulance Appoints Chris Ciatto as New CEO', "
        "Apr 5 2023",
        "https://www.businesswire.com/news/home/20230405005703/en/"),
    CompanySource(
        "sale_2015",
        "NEWS",
        "Lincoln Journal Star, 'Private equity firm buys Nebraska ambulance "
        "company', Feb 2015",
        "https://journalstar.com/business/local/private-equity-firm-buys-"
        "nebraska-ambulance-company/article_f17387c0-ec6f-5872-b159-"
        "3c99a212dd03.html"),
    CompanySource(
        "founding",
        "NEWS",
        "Columbus Telegram / Omaha World-Herald retrospectives on the 2015 "
        "sale (founding story)",
        "https://omaha.com/news/nation-world/business/midwest-medical-"
        "transport-ready-to-take-flight-with-new-owners/article_b6fa47d3-"
        "9c50-5bee-85e2-528815926374.html",
        "with one ambulance, doing a few transfers a week out of the "
        "Columbus Hospital"),
    CompanySource(
        "not911",
        "PRESS",
        "MMT / Siouxland Chamber directory (company positioning)",
        "https://directory.siouxlandchamber.com/list/member/midwest-medical-"
        "transport-company-6143",
        "Midwest Medical Transport is not a 911 service—it provides "
        "inter-facility medical transportation, taking patients from "
        "hospital to hospital, nursing home to hospital, and vice versa."),
    CompanySource(
        "medair",
        "NEWS",
        "Omaha World-Herald, 'Air ambulance team adds Hastings-based "
        "helicopter' (Midwest MedAir)",
        "https://omaha.com/news/air-ambulance-team-adds-hastings-based-"
        "helicopter/article_0038cb3a-8f7d-52fc-9a70-7003fec324b2.html",
        "responded to 30,000 ambulance calls and more than 400 emergency "
        "helicopter calls last year"),
    CompanySource(
        "meysenburg",
        "COURT",
        "Meysenburg v. Midwest Medical Transport Company, LLC, "
        "No. 4:2024-cv-03107 (D. Neb., filed Jun 11 2024) — FLSA",
        "https://dockets.justia.com/docket/nebraska/nedce/"
        "4:2024cv03107/103544"),
    CompanySource(
        "wroblewski",
        "COURT",
        "Wroblewski v. Midwest Medical Transport Company LLC, "
        "No. 2:23-cv-00877 (E.D. Wis., filed Jul 3 2023) — FLSA",
        "https://www.courtlistener.com/docket/67552669/wroblewski-v-midwest-"
        "medical-transport-company-llc/"),
    CompanySource(
        "reust",
        "COURT",
        "Reust v. Midwest Medical Transport Company, LLC, "
        "No. 1:20-cv-01548 (N.D. Ohio, filed Jul 14 2020) — FLSA",
        "https://dockets.justia.com/docket/ohio/ohndce/"
        "1:2020cv01548/267528"),
    CompanySource(
        "nlrb",
        "COURT",
        "NLRB Case 14-CA-251082, Midwest Medical Transport Company, LLC "
        "(Wichita, KS; filed Nov 4 2019; closed)",
        "https://www.nlrb.gov/case/14-CA-251082"),
    CompanySource(
        "growjo",
        "ESTIMATE",
        "Growjo revenue/headcount estimate (third-party, unaudited)",
        "https://growjo.com/company/Midwest_Medical_Transport"),
    CompanySource(
        "zoominfo",
        "ESTIMATE",
        "ZoomInfo revenue/headcount estimate (third-party, unaudited)",
        "https://www.zoominfo.com/c/midwest-medical-transport-inc/58362004"),
    CompanySource(
        "leadiq",
        "ESTIMATE",
        "LeadIQ revenue/headcount estimate (third-party, unaudited, "
        "as of Jun 2026)",
        "https://leadiq.com/c/midwest-medical-transport-company---midwest-"
        "medair/5a1d990c2300005e0087a7c8"),
)

SOURCES: Dict[str, CompanySource] = {s.key: s for s in _SOURCES}


# ── NPI-verified location estate ─────────────────────────────────────────────
@dataclass(frozen=True)
class MmtNpiLocation:
    npi: str
    name: str              # NPPES org name / DBA
    address: str
    city: str
    state: str
    note: str = ""
    enumerated: str = ""   # YYYY-MM-DD where captured
    legacy_core: bool = False   # the pre-2022 NE/IA/SD footprint


_L = MmtNpiLocation

# All taxonomy 341600000X (Ambulance) unless noted; NPPES pull 2026-07-10.
MMT_NPI_LOCATIONS: Tuple[MmtNpiLocation, ...] = (
    _L("1871991125", "Midwest Medical Transport Co LLC (flagship)",
       "2155 33rd Ave", "Columbus", "NE",
       "Historic HQ; taxonomies incl. Air (3416A0800X) + Land (3416L0300X); "
       "secondary practice location 3729 Corporate Dr, Columbus OH; "
       "authorized official Jeff Shullaw (GM).", "2014-12-18", True),
    _L("1689665143", "Platte County Ambulance Company DBA Midwest Medical "
       "Transport Co", "2155 33rd Ave", "Columbus", "NE",
       "Predecessor legal entity (founded 1987); NE Medicaid ID on file.",
       "2005-11-03", True),
    _L("1356115562", "Midwest Medical Transport Co LLC",
       "13326 B St", "Omaha", "NE",
       "Omaha corporate; authorized official Chris Ciatto (CEO).",
       "2023-11-08", True),
    _L("1740645332", "Midwest Medical Transport Co LLC (subpart)",
       "2110 23rd Ave Ste A", "Council Bluffs", "IA",
       "NE + IA Medicaid IDs; authorized official Tim Hoffman "
       "(Finance Director).", "2015-12-23", True),
    _L("1588115893", "MMT Co LLC — Sioux City, IA (subpart)",
       "1015 Court St", "Sioux City", "IA", "IA license 2001400.",
       "2016-10-21", True),
    _L("1073296893", "MMT Co LLC DBA Southeast Iowa Ambulance",
       "4780 NE 3rd St", "Des Moines", "IA",
       "authorized official Chris Ciatto (CEO).", "2023-08-09", True),
    _L("1235681354", "MMT Co LLC DBA Fraser Transportation Services",
       "4780 NE 3rd St", "Des Moines", "IA", "", "", True),
    _L("1346792371", "MMT Co LLC DBA Southeast Iowa Ambulance",
       "2155 33rd Ave", "Columbus", "NE", "", "", True),
    _L("1760832695", "MMT Co LLC", "59706 Airport Rd", "Atlantic", "IA",
       "", "", True),
    _L("1982069134", "MMT Co LLC", "705 E Division St", "Audubon", "IA",
       "Historic MedAir helicopter base.", "", True),
    _L("1538612320", "MMT Co LLC", "118 N Runger Ave", "Sheldon", "IA",
       "", "", True),
    _L("1003266339", "MMT Co LLC", "1812 4th St SW", "Mason City", "IA",
       "", "", True),
    _L("1932650272", "MMT Co LLC — Albia, IA", "521 I Ave W", "Albia", "IA",
       "", "", True),
    _L("1205387545", "MMT Co LLC — Aberdeen, SD",
       "2919 Industrial Ave", "Aberdeen", "SD", "", "2016-10", True),
    _L("1134670219", "MMT Co LLC — Huron, SD",
       "1199 Dakota Ave N", "Huron", "SD", "", "", True),
    _L("1235998626", "MMT Co LLC", "3198 Mercier St", "Kansas City", "MO",
       "authorized official Brian Lohrding (CFO).", "2024-03-18", False),
    _L("1548034754", "MMT Co LLC", "3729 Corporate Dr", "Columbus", "OH",
       "", "", False),
    _L("1477490381", "MMT Co LLC", "320 Transfer Dr", "Indianapolis", "IN",
       "", "", False),
    _L("1548047152", "MMT Co LLC", "9401 W Brown Deer Rd", "Milwaukee", "WI",
       "", "", False),
    _L("1629831102", "MMT Co LLC", "3515 N Prospect St",
       "Colorado Springs", "CO", "", "", False),
    _L("1992579338", "MMT Co LLC", "290 Armistice Blvd", "Pawtucket", "RI",
       "Consistent with reported acquisition of Med Tech Ambulance Service "
       "of Rhode Island + Access Ambulance (company social post).", "",
       False),
    _L("1053162420", "MMT Co LLC", "1144 N Road St", "Elizabeth City", "NC",
       "", "", False),
    _L("1922872134", "Midwest Medical Transport LLC",
       "5792 Arrowhead Dr", "Virginia Beach", "VA",
       "Near-identical 800-number to MMT's; same-org link unconfirmed — "
       "flagged, not asserted.", "", False),
)

# Cities with an MMT station named by company/web sources but no separate
# NPI record captured (subparts often bill under a parent NPI). PUBLIC-WEB.
MMT_WEB_STATIONS: Tuple[Tuple[str, str], ...] = (
    ("Lincoln", "NE"), ("Fremont", "NE"), ("Bellevue", "NE"),
    ("Grand Island", "NE"), ("Kearney", "NE"), ("Lexington", "NE"),
    ("Hastings", "NE"), ("North Platte", "NE"), ("Iowa City", "IA"),
    ("Tea", "SD"), ("Cincinnati", "OH"),
)


# ── Ownership / control timeline ─────────────────────────────────────────────
@dataclass(frozen=True)
class OwnershipEvent:
    year: str
    event: str
    detail: str
    source_key: str


OWNERSHIP_TIMELINE: Tuple[OwnershipEvent, ...] = (
    OwnershipEvent(
        "1987",
        "Founded in Columbus, NE",
        "Kim and Jill Wolfe start Platte County Ambulance Company — 'with "
        "one ambulance, doing a few transfers a week out of the Columbus "
        "Hospital'.",
        "founding"),
    OwnershipEvent(
        "2015",
        "First institutional ownership",
        "Panorama Point Partners (Omaha), with Dixon Midland Company and "
        "ORIX Private Equity Solutions, acquires MMT from the founders. At "
        "acquisition: a one-state operation, 350+ employees, 13 ground "
        "ambulance locations, two helicopter bases (North Platte, "
        "Hastings). Longtime GM Jeff Shullaw becomes CEO.",
        "sale_2015"),
    OwnershipEvent(
        "2022",
        "Harbour Point Capital recapitalization (current sponsor)",
        "Harbour Point Capital (healthcare-services PE), with co-investor "
        "Headway Capital Partners, buys MMT from Panorama Point / Dixon "
        "Midland / ORIX; Lincoln International advised the sellers. Deal-"
        "time framing: ~7 states, ~1,000 employees, 200,000+ missions/yr. "
        "HPC pairs with Kevin Ketzel (ex-president, Agiliti Health).",
        "hpc_2022"),
    OwnershipEvent(
        "2023",
        "CEO appointment + expansion wave",
        "Chris Ciatto (ex-Phoenix Physical Therapy CEO; Optum, Aramark) "
        "appointed CEO (Apr 2023). New NPIs enumerated: Des Moines "
        "(Aug 2023), Omaha (Nov 2023), Kansas City MO (Mar 2024). Company "
        "materials move from '10 states' (2022) to '13 states'.",
        "ciatto_2023"),
    OwnershipEvent(
        "2025–26",
        "Continued eastward expansion; leadership shift",
        "Cincinnati hiring/expansion per company job postings; Kevin "
        "Ketzel now listed as CEO & Chairman on the company leadership "
        "page — an apparent unannounced transition from Ciatto (flagged, "
        "needs management confirmation).",
        "about_us"),
)


# ── Litigation registry ──────────────────────────────────────────────────────
@dataclass(frozen=True)
class LitigationRecord:
    case: str
    court: str
    filed: str
    nature: str
    status: str
    source_key: str


LITIGATION: Tuple[LitigationRecord, ...] = (
    LitigationRecord(
        "Meysenburg v. Midwest Medical Transport Company, LLC",
        "U.S. District Court, D. Neb. (4:2024-cv-03107)", "2024-06-11",
        "FLSA wage & hour", "Outcome not public without PACER",
        "meysenburg"),
    LitigationRecord(
        "Wroblewski v. Midwest Medical Transport Company LLC",
        "U.S. District Court, E.D. Wis. (2:23-cv-00877)", "2023-07-03",
        "FLSA wage & hour (jury demand)",
        "Outcome not public without PACER", "wroblewski"),
    LitigationRecord(
        "Reust v. Midwest Medical Transport Company, LLC",
        "U.S. District Court, N.D. Ohio (1:20-cv-01548)", "2020-07-14",
        "FLSA wage & hour", "Outcome not public without PACER", "reust"),
    LitigationRecord(
        "NLRB Case 14-CA-251082 (Wichita, KS)",
        "NLRB Region 14 (St. Louis)", "2019-11-04",
        "Unfair labor practice charge", "Closed", "nlrb"),
)

LITIGATION_READ = (
    "Three separate FLSA wage-and-hour suits across three districts "
    "(OH 2020, WI 2023, NE 2024) is the classic multi-state EMS-rollup "
    "pattern — crew comp practices (shift pay, meal breaks, OT) diverging "
    "from federal wage rules as footprint scales. A diligence workstream, "
    "not a headline risk: outcomes are sealed without PACER. No negligence "
    "/ malpractice or contract-dispute cases surfaced in public search — "
    "recorded as not-found, not as absence."
)


# ── Scale + estimates ────────────────────────────────────────────────────────
@dataclass(frozen=True)
class ScaleClaim:
    metric: str
    value: str
    as_of: str
    basis: str
    source_key: str


SCALE_CLAIMS: Tuple[ScaleClaim, ...] = (
    ScaleClaim("States of operation", "13", "2026 (company site)",
               "PRESS", "about_us"),
    ScaleClaim("Team members", "2,800+", "2026 (company site)",
               "PRESS", "about_us"),
    ScaleClaim("Fleet", "500+ vehicles (ambulances, helicopters, "
               "para-transit vans)", "2026 (company site)", "PRESS",
               "about_us"),
    ScaleClaim("Missions / year", "200,000+", "Jan 2022 (deal release, "
               "then 10 states)", "PRESS", "hpc_2022"),
    ScaleClaim("Employees at 2022 deal", "~1,000 (7 states)",
               "Jan 2022 (sell-side advisor)", "PRESS", "lincoln_intl"),
    ScaleClaim("Active org NPIs", "24 (NE 4 · IA 9 · SD 2 · MO 1 · OH 2 · "
               "IN 1 · WI 1 · CO 1 · RI 1 · NC 1 · VA 1)",
               "2026-07-10 (NPPES pull)", "NPPES", "nppes_pull"),
)

# Third-party revenue estimates conflict MATERIALLY — shown side by side,
# never blended, never presented as company figures.
REVENUE_ESTIMATES: Tuple[ScaleClaim, ...] = (
    ScaleClaim("Revenue (est.)", "$296.4M · 784 employees", "2026",
               "ESTIMATE", "growjo"),
    ScaleClaim("Revenue (est.)", "$293.6M · 1,000–5,000 employees", "2026",
               "ESTIMATE", "zoominfo"),
    ScaleClaim("Revenue (est.)", "$100M–$250M · ~700 employees",
               "Jun 2026", "ESTIMATE", "leadiq"),
)

REVENUE_ESTIMATE_READ = (
    "The three estimators disagree by ~3x on both revenue and headcount — "
    "and all disagree with the company's own 2,800+ headcount claim. "
    "Treat every third-party revenue figure as unusable for underwriting; "
    "the only load-bearing scale facts are the NPPES estate, the deal-time "
    "press figures, and the company's own claims, each labelled."
)


# ── Positioning ──────────────────────────────────────────────────────────────
POSITIONING = (
    "IFT specialist, explicitly NOT a 911 service — 'it provides "
    "inter-facility medical transportation, taking patients from hospital "
    "to hospital, nursing home to hospital, and vice versa.' Flagship "
    "service is ALS/BLS interfacility transport, plus specialty/critical-"
    "care transport and wheelchair/para-transit; historically air "
    "ambulance via Midwest MedAir (current MedAir status unconfirmed "
    "post-2022)."
)


def npi_states() -> List[str]:
    """Distinct states in the NPPES estate, legacy core first."""
    seen: List[str] = []
    for loc in MMT_NPI_LOCATIONS:
        if loc.state not in seen:
            seen.append(loc.state)
    return seen


def legacy_core_locations() -> List[MmtNpiLocation]:
    return [l for l in MMT_NPI_LOCATIONS if l.legacy_core]


def expansion_locations() -> List[MmtNpiLocation]:
    return [l for l in MMT_NPI_LOCATIONS if not l.legacy_core]


def source_for(key: str) -> Optional[CompanySource]:
    return SOURCES.get(key)
