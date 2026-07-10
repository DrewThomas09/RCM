"""NE/IA ambulance-supplier landscape from the NPPES registry — the
"find them in claims data" foundation, computed from a vendored first-party
pull rather than asserted.

Data: ``reference/nppes_ambulance_orgs_ne_ia_20260710.csv`` — 751 unique
organizational NPIs (CMS NPPES sweep, taxonomy 'Ambulance', NPI-2, states
NE + IA, pulled 2026-07-10). Each row: npi, org_name, city, state,
search_state, primary_taxonomy, category (private | hospital-owned |
municipal-fire-volunteer | air, keyword-classified).

Caveats that travel with every read: NPPES matches mailing OR practice
address, so a search state includes some out-of-state-practice orgs; small
squads often hold 2–3 NPIs; classification is keyword-based (documented
here) and a handful of records will straddle categories. Counts from this
module are SOURCED (from the vendored registry pull); the curated profiles
carry their own bases.

Also here: the exact CMS claims-data recipe (dataset UUIDs + filter grammar)
to rank these suppliers by Medicare volume/payments — documented as a
connector spec because data.cms.gov is egress-blocked from this environment.

Degrade — never raise.
"""
from __future__ import annotations

import csv
import functools
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

_CSV = os.path.join(os.path.dirname(__file__), "reference",
                    "nppes_ambulance_orgs_ne_ia_20260710.csv")

PULL_DATE = "2026-07-10"

CATEGORY_LABELS: Dict[str, str] = {
    "private": "Private / commercial operators",
    "hospital-owned": "Hospital-owned services",
    "municipal-fire-volunteer": "Municipal / fire / volunteer squads",
    "air": "Air medical",
}


@dataclass(frozen=True)
class NpiOrg:
    npi: str
    org_name: str
    city: str
    state: str
    search_state: str
    primary_taxonomy: str
    category: str


@functools.lru_cache(maxsize=1)
def registry() -> Tuple[NpiOrg, ...]:
    """The vendored NPPES pull. Empty tuple (never an exception) if the
    reference CSV is missing."""
    try:
        with open(_CSV, newline="", encoding="utf-8") as fh:
            return tuple(NpiOrg(**row) for row in csv.DictReader(fh))
    except Exception:
        return ()


def counts_by_category(search_state: Optional[str] = None) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for r in registry():
        if search_state and r.search_state != search_state:
            continue
        out[r.category] = out.get(r.category, 0) + 1
    return out


def orgs(category: Optional[str] = None,
         search_state: Optional[str] = None) -> List[NpiOrg]:
    return [r for r in registry()
            if (category is None or r.category == category)
            and (search_state is None or r.search_state == search_state)]


# ── Curated competitor set (cross-checked against the registry + web) ───────
@dataclass(frozen=True)
class CompetitorProfile:
    name: str
    npis: Tuple[str, ...]
    base: str
    archetype: str        # national-platform | pe-backed-regional |
                          # local-private | hospital-owned | municipal-911 |
                          # air
    read: str             # the competitive read, cited in-line
    source_url: str


COMPETITORS: Tuple[CompetitorProfile, ...] = (
    CompetitorProfile(
        "American Medical Response (GMR)", ("1336315225",),
        "Omaha, NE (9340 G Ct)", "national-platform",
        "Omaha operation descends from Rural/Metro (absorbed by AMR 2015) "
        "— non-emergency interfacility services across greater Omaha / "
        "Council Bluffs; historically described as one of the largest "
        "private services in the state (~35 vehicles, ~90 employees — "
        "dated figure, treat as historical). No Omaha or Lincoln 911 "
        "contract found: both cities run fire-based 911, so AMR competes "
        "in the same outsourced-IFT lane as MMT. Parent GMR (KKR) cut its "
        "IPO valuation target to $3.3B in May 2026 after a $5.4B 2025 "
        "refinancing — a leveraged platform, not a hungry local "
        "consolidator.",
        "https://www.airmethods.com/"),
    CompetitorProfile(
        "AmeriPro Health (incl. Priority Medical Transport)",
        ("1295542520", "1891166799"),
        "North Platte, NE (2600 W Front St — both entities)",
        "pe-backed-regional",
        "THE head-on PE-backed challenger: Atlanta-based, Whistler "
        "Capital-backed AmeriPro acquired North Platte's Priority Medical "
        "Transport (founded 2015 by Trent & Trev Kleinow) in Feb 2025 — "
        "'expands its suite of patient-centric 911, interfacility medical "
        "transportation, and critical care transport services across "
        "Nebraska' (press release). Stated NE counties: Lincoln, Red "
        "Willow, Buffalo, Dawson, Adams, Dodge & Platte — i.e., Kearney, "
        "Hastings, Fremont, and MMT's home county of Platte (Columbus). "
        "Both large NE private IFT platforms are now PE-owned (Harbour "
        "Point vs Whistler).",
        "https://www.prnewswire.com/news-releases/ameripro-health-"
        "acquires-priority-medical-transport-and-expands-midwest-presence-"
        "302372373.html"),
    CompetitorProfile(
        "Omaha private locals (American / Eastern / Pioneer / Papio / "
        "Heartland EMS / 9 Line)",
        ("1558331405", "1699722298", "1104699545", "1477436988",
         "1295665461", "1285324947", "1104923473", "1962955187"),
        "Omaha metro + Fremont", "local-private",
        "The subscale local layer: American Ambulance Service (est. 1938), "
        "Eastern Ambulance (Omaha + Hastings), the co-located Pioneer / "
        "Pioneer Metro / American Ambulance LLC cluster (4420 Izard St), "
        "Papio Ambulance (Papillion/Sarpy), Heartland EMS (Fremont), "
        "9 Line Medical Solutions. Individually small; collectively they "
        "cap pricing on low-acuity BLS legs but cannot serve system-wide "
        "contracts.",
        "https://npiregistry.cms.hhs.gov/"),
    CompetitorProfile(
        "Siouxland Paramedics", ("1063495810",),
        "Sioux City, IA", "municipal-911",
        "Nonprofit sole 911 provider for Sioux City / North Sioux City / "
        "western Plymouth County (10,000+ patients/yr). MMT stations in "
        "Sioux City as the IFT overlay to Siouxland's 911 base.",
        "https://www.sioux-city.org/government/departments-a-f/fire-"
        "rescue/divisions/emergency-medical-services"),
    CompetitorProfile(
        "Fire-based 911 (Omaha FD · Lincoln F&R · Sarpy departments · "
        "Council Bluffs FD)",
        ("1083798912", "1477588101", "1154584639", "1154329340",
         "1790701985", "1366428716"),
        "Metro cores", "municipal-911",
        "Omaha FD runs 18 ALS ambulances as the city's primary 911 "
        "transport; Lincoln Fire & Rescue runs city EMS under a published "
        "rate schedule + EMS Oversight Authority; Papillion FD absorbed "
        "La Vista's department in 2014; Council Bluffs FD runs 11,000+ "
        "incidents/yr (80%+ EMS). Fire-based 911 monopolies leave the "
        "scheduled-IFT lane to privates — the structural opening MMT's "
        "'let the fire departments do the 911' model occupies (Columbus "
        "Telegram interview with the founders).",
        "https://www.omaha-fire.org/our-services/emergency-medical-"
        "services"),
    CompetitorProfile(
        "Hospital-owned (Children's Nebraska · CHI Good Samaritan · "
        "Regional West · rural IA hospital squads)",
        ("1831044759", "1336184019", "1639101199"),
        "Omaha / Kearney / Scottsbluff / rural IA", "hospital-owned",
        "The captive layer: Children's Nebraska runs a CAMTS-accredited "
        "peds/neonatal fleet (ground + EC145 + PC-12); CHI Good Samaritan "
        "operates Kearney's 911 ground + AirCare helicopter; Regional West "
        "runs Panhandle EMS. Iowa contrast: 40+ hospital-owned ambulance "
        "NPIs (the dominant rural-IA model) vs ~5 in Nebraska — Iowa "
        "expansion means displacing hospital self-operation, Nebraska "
        "means winning outsourcers.",
        "https://www.childrensnebraska.org/providers/specialties/"
        "transport-critical-care"),
    CompetitorProfile(
        "Air medical (LifeNet/Air Methods · Med-Trans · EagleMed · "
        "Guardian · Apollo MedFlight)",
        ("1730418666", "1184025009", "1972017523", "1063158947",
         "1194963918", "1467700500", "1578102547"),
        "Statewide (21 NE/IA base NPIs for Rocky Mountain Holdings alone)",
        "air",
        "Adjacent, not substitute: air carries the time-critical long-leg "
        "slice (LifeNet of the Heartland: 9 NE + 12 IA base NPIs, incl. "
        "bases at Nebraska Medical Center and Great Plains Health; "
        "fixed-wing returning to Omaha Jul 2026). Ground CCT wins "
        "whenever weather, cost, or acuity permits — air density is a "
        "complement to, and a ceiling on, the longest legs.",
        "https://www.airmethods.com/air-medical/program/lifenet-of-the-"
        "heartland/"),
)


# ── The claims-data recipe (documented connector spec) ───────────────────────
CLAIMS_RECIPE = {
    "dataset": "Medicare Physician & Other Practitioners — by Provider "
               "and Service (data.cms.gov)",
    "uuids": {
        "2020": "c957b49e-1323-49e7-8678-c09da387551d",
        "2021": "31dc2c47-f297-4948-bfb4-075e1bec3a02",
        "2022": "e650987d-01b7-4f09-b75e-b0b075afbf98",
        "2023": "92396110-2aed-4d63-a6a2-5d6207d46a29",
    },
    "companion_by_provider": "8889d81e-2ee7-448f-8713-f071038289b5",
    "companion_by_geo": "6fea9d79-0129-4e4c-b1b8-23cd86a4f435",
    "endpoint": "https://data.cms.gov/data-api/v1/dataset/{uuid}/data",
    "hcpcs": ("A0425", "A0426", "A0427", "A0428", "A0429", "A0430",
              "A0431", "A0432", "A0433", "A0434"),
    "filter_example": ("?filter[Rndrng_Prvdr_State_Abrvtn]=NE"
                       "&filter[c][condition][path]=HCPCS_Cd"
                       "&filter[c][condition][operator]=IN"
                       "&filter[c][condition][value][]=A0428&size=5000"),
    "note": ("Egress to data.cms.gov is policy-blocked from this "
             "environment (proxy CONNECT 403, verified 2026-07-10) — the "
             "pull runs from an unblocked network via the repo's existing "
             "connectors/cms_open_data slice; join rndrng_npi against the "
             "vendored NPPES registry to rank NE/IA ambulance suppliers "
             "by Medicare services + payments."),
}


def summary() -> Dict[str, object]:
    """Headline landscape read used by the pages."""
    reg = registry()
    ne = counts_by_category("NE")
    ia = counts_by_category("IA")
    return {
        "available": bool(reg),
        "pull_date": PULL_DATE,
        "total_orgs": len(reg),
        "ne": ne, "ia": ia,
        "read": (
            "Nebraska's supply base is overwhelmingly municipal/volunteer "
            f"({ne.get('municipal-fire-volunteer', 0)} of "
            f"{sum(ne.values()) or 1} captured NE org NPIs) with a thin "
            f"private layer ({ne.get('private', 0)}) — while Iowa runs a "
            f"hospital-owned model ({ia.get('hospital-owned', 0)} hospital "
            "ambulance NPIs vs ~5 in NE). A shrinking volunteer base "
            "(80%+ of NE agencies all-volunteer, per the state EMS "
            "assessment) plus hub-and-spoke consolidation is the "
            "structural opening for contracted IFT."),
        "source_label": ("SOURCED · CMS NPPES registry sweep (taxonomy "
                         "'Ambulance', NPI-2, NE+IA), vendored "
                         f"{PULL_DATE}; classification keyword-based"),
    }
