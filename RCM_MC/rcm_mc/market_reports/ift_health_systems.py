"""Hospital-system customer deep dives — the anchor IFT demand generators in
MMT's legacy-core footprint (NE + western IA), as sourced data.

Each system profile answers the questions a diligence team asks of an IFT
target's customer base: how big is the system (beds, CCNs), what makes it
generate transfers (trauma level, quaternary services, hub-spoke structure,
transfer center), does it OWN transport (competitive carve-out) or outsource
(addressable), and what near-term catalysts change its transfer volume.

Basis contract (no ILLUSTRATIVE):
  * SYSTEM  — the system's own public pages / press releases.
  * NEWS    — independent press.
  * CCN     — CMS certification number, via public cost-report directories.
  * GOV     — a government dataset or agency statement.

Research pull 2026-07-10; every profile carries source URLs. Facilities whose
figures conflict across sources carry the conflict inline rather than a
blended number. Design contract: frozen dataclasses, degrade — never raise.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class Facility:
    name: str
    city: str
    state: str
    beds: str                  # as published; conflicts shown, not blended
    ccn: str = ""              # CMS certification number ("" = not found)
    note: str = ""


@dataclass(frozen=True)
class SystemProfile:
    key: str
    name: str
    hq: str
    role: str                  # one-line: what it is in the transfer network
    facilities: Tuple[Facility, ...]
    transfer_center: str       # the system's own transfer-coordination story
    ems_posture: str           # owns transport / outsources / hybrid — cited
    catalysts: Tuple[str, ...] # near-term events that move transfer volume
    sources: Tuple[str, ...]   # URLs
    ift_read: str              # what this means for an outsourced IFT partner


SYSTEMS: Tuple[SystemProfile, ...] = (
    SystemProfile(
        "nebraska_medicine",
        "Nebraska Medicine / UNMC",
        "Omaha, NE",
        "The state's academic quaternary hub — the only ACS-verified Level I "
        "trauma center in Nebraska treating both adults and children, with "
        "nationally ranked solid-organ and stem-cell transplant programs.",
        (Facility("Nebraska Medical Center", "Omaha", "NE", "718", "280013",
                  "809 licensed beds system-wide with Bellevue."),
         Facility("Bellevue Medical Center", "Bellevue", "NE", "91", "280132",
                  "Purchased outright by Nebraska Medicine in 2016 for "
                  "$130M.")),
        "Runs a dedicated Transfer Center inside its 'Capacity Optimization "
        "Hub' — 'connects you with the appropriate Nebraska Medicine "
        "physician, coordinates patient admissions, and streamlines bed "
        "assignments' (system provider page). Nursing staff coordinate "
        "requests from referring facilities with a physician-of-the-day.",
        "No owned ground-ambulance or air program found (recorded as "
        "not-found, not absence). Every inbound quaternary transfer and "
        "outbound repatriation is carried by someone else — the classic "
        "outsourcer profile.",
        ("Project Health: $2.19B replacement hospital (550+ beds), NU "
         "Regents approved second design phase Oct 2025 — a multi-year "
         "capacity step-up at the top of the state's transfer pyramid.",
         "Operates outpatient services co-located at Great Plains Health "
         "(North Platte) — a live 280-mile referral pipeline from western "
         "NE."),
        ("https://www.nebraskamed.com/about-us/fast-facts",
         "https://www.nebraskamed.com/for-providers/patient-transfers",
         "https://nebraskaexaminer.com/2025/10/03/2-19-billion-project-"
         "health-takes-key-leap-forward-with-nu-vote/"),
        "Highest-acuity inbound magnet in the footprint; transplant + "
        "Level I status pulls long-haul CCT/SCT legs from the entire "
        "state. No captive fleet = fully addressable."),
    SystemProfile(
        "chi_health",
        "CHI Health (CommonSpirit — Midwest Division)",
        "Omaha, NE",
        "The state's largest hospital system (14+ hospitals NE/western IA) "
        "— the densest hub-spoke transfer web in the footprint.",
        (Facility("Creighton University Medical Center – Bergan Mercy",
                  "Omaha", "NE", "396", "280060", "Level I trauma."),
         Facility("CHI Health Immanuel", "Omaha", "NE", "352", "280081"),
         Facility("CHI Health Lakeside", "Omaha", "NE", "109", "280130"),
         Facility("CHI Health Midlands", "Papillion", "NE", "131", "280105"),
         Facility("CHI Health Mercy", "Council Bluffs", "IA", "194",
                  "160028", "L&D closure announced 2026-07-10."),
         Facility("CHI Health St. Elizabeth", "Lincoln", "NE", "260", "",
                  "Region's only dedicated burn trauma unit."),
         Facility("CHI Health St. Francis", "Grand Island", "NE",
                  "159 (some sources 130)", "280023", "Level III."),
         Facility("CHI Health Good Samaritan", "Kearney", "NE", "236",
                  "280009", "Region's only Level II trauma center.")),
        "Launched its 24/7 system Transfer Center in 2018 for its "
        "14-hospital system + critical-access referrers; at DHHS request it "
        "expanded to coordinate ALL Nebraska hospitals' COVID transfers "
        "(Apr 2020). Transfer Center RNs can accept STEMI, trauma and "
        "stroke transfers directly 'to expedite transportation "
        "arrangements' (system page).",
        "Hybrid: Good Samaritan (Kearney) directly operates a 911 ground "
        "service (city of Kearney + Buffalo County FD#1 since 1988) AND "
        "the AirCare helicopter (Bell 429, flown by Apollo MedFlight). No "
        "CHI-owned ground IFT found in Omaha/Lincoln — the metro transfer "
        "book is outsourced.",
        ("Mercy Council Bluffs L&D closure (announced 2026-07-10; "
         "deliveries end ~Sep 2026) — OB volume re-routes across the "
         "river to Omaha: new recurring maternal transfer legs.",
         "CommonSpirit FY2025 operating loss $225M (improved from $875M "
         "FY2024) — system-level margin pressure favors asset-light "
         "outsourcing over fleet ownership.",
         "Went out-of-network with Aetna in NE/western IA (Dec 2024) — "
         "payer friction that can shift volumes between systems."),
        ("https://www.chihealth.com/services/transfer-center",
         "https://www.chihealth.com/services/emergency-medicine/good-"
         "samaritan-emergency-department/aircare-ambulance-service",
         "https://www.wowt.com/2026/07/10/chi-health-ending-labor-delivery-"
         "care-council-bluffs-hospital/",
         "https://www.commonspirit.org/news-articles/commonspirit-health-"
         "releases-fy2025-year-end-results"),
        "The single largest account surface in the footprint: 8 anchor "
        "hospitals, a system transfer center that books transport, and a "
        "statewide spoke network. Kearney is the one market where CHI "
        "self-operates ground."),
    SystemProfile(
        "methodist",
        "Methodist Health System",
        "Omaha, NE",
        "Omaha's women's/oncology-weighted system — regional draw across "
        "southwestern IA + southeastern NE.",
        (Facility("Methodist Hospital", "Omaha", "NE", "423", "280040"),
         Facility("Methodist Women's Hospital", "Elkhorn", "NE", "137", "",
                  "Delivers more babies than any regional hospital; "
                  "~6,000 births/yr system-wide; high-acuity NICU. Appears "
                  "to bill under the Methodist Hospital CCN."),
         Facility("Methodist Fremont Health", "Fremont", "NE",
                  "75 (55 acute + 20 behavioral)", "280077",
                  "Only hospital in Dodge County; affiliated 2018 via "
                  "50-year lease."),
         Facility("Methodist Jennie Edmundson", "Council Bluffs", "IA",
                  "236", "160047")),
        "Runs a Patient Transfer Center — '(402) 354-XFER' for the three "
        "NE hospitals, '(844) JENNIE1' for Jennie Edmundson (system "
        "provider page).",
        "No owned ambulance operation found in Omaha/Council Bluffs. "
        "Fremont's chamber listing includes EMS among hospital services — "
        "the historic hospital-run Fremont ambulance; current ownership "
        "unconfirmed (flagged).",
        ("Jennie Edmundson partnering on a 96-bed behavioral-health "
         "hospital in Council Bluffs — behavioral health is a "
         "secure-transfer-heavy service line (new IFT demand).",
         "NICU concentration at Women's Hospital pulls neonatal/maternal "
         "transfers from the whole region."),
        ("https://bestcare.org/provider-and-employee-resources/patient-"
         "transfer-center",
         "https://bestcare.org/locations/methodist-womens-hospital",
         "https://theindependent.com/news/state-regional/jennie-edmundson-"
         "partners-to-build-96-bed-behavioral-health-hospital-in-council-"
         "bluffs/article_1031d69c-4c22-541e-8b52-a22afc87d510.html"),
        "Fully addressable metro account with a formal transfer center; "
        "behavioral-health expansion adds a differentiated secure-"
        "transport line."),
    SystemProfile(
        "childrens",
        "Children's Nebraska",
        "Omaha, NE",
        "The state's only Level I pediatric trauma center and only Level IV "
        "regional NICU — the pediatric transfer apex.",
        (Facility("Children's Nebraska (Hubbard Center)", "Omaha", "NE",
                  "~250 post-Hubbard (from 140)", "283301",
                  "Licensed-bed figures vary by source; use the cost "
                  "report for diligence-grade numbers."),),
        "Pediatric referrals route through its own transport/transfer "
        "coordination.",
        "OWNS its transport: a CAMTS-accredited neonatal/pediatric "
        "critical-care team with 'dedicated ambulance, helicopter or plane "
        "transport' — 'a fleet of ground ambulances, a EC 145-C2 "
        "helicopter and a PC 12 fixed-wing aircraft' (system provider "
        "page). Holds its own air-transport NPI (1831044759).",
        ("Hubbard Center capacity step-up (2021) consolidated pediatric "
         "acuity in Omaha — more inbound peds transfers, but carried "
         "in-house.",),
        ("https://www.childrensnebraska.org/providers/specialties/"
         "transport-critical-care",),
        "A CARVE-OUT, not an account: pediatric/neonatal IFT in the "
        "region is largely internalized. Size the addressable market "
        "net of Children's own missions."),
    SystemProfile(
        "bryan",
        "Bryan Health",
        "Lincoln, NE",
        "Lincoln's locally-owned hub system, expanding across central NE "
        "by affiliation — cardiac-weighted with a large rural outreach "
        "web.",
        (Facility("Bryan Medical Center (East + West)", "Lincoln", "NE",
                  "664", "280003 / 280005",
                  "Level II trauma, Level III NICU, Bryan Heart."),
         Facility("Kearney Regional Medical Center", "Kearney", "NE", "93",
                  "280134", "Joined Bryan Health Jan 2022; Level III."),
         Facility("Grand Island Regional Medical Center", "Grand Island",
                  "NE", "67", "280139", "Opened 2020; Bryan JV partner."),
         Facility("Crete Area Medical Center", "Crete", "NE", "15 (CAH)",
                  "", "Bryan-owned CAH; StarCare air base."),
         Facility("Merrick Medical Center", "Central City", "NE",
                  "CAH (new 2022)", "")),
        "No single published transfer center number; the Bryan Heart "
        "outreach-clinic network across rural NE/northern KS is the "
        "referral engine (outreach cardiology is a strong predictor of "
        "inbound STEMI/cardiac IFT).",
        "Outsources air: StarCare has long been operated by Air Methods "
        "(equipment, pilots, and now medical staffing). No Bryan-owned "
        "ground ambulance found — ground IFT is outsourced.",
        ("Pender Community Hospital affiliation (Jun 2025) — the "
         "affiliation web keeps widening (also: Heartland Health "
         "Alliance management agreements).",
         "Medicare Advantage JV with Sanford Health Plan (plan year 2026, "
         "20 counties around Lincoln).",
         "Bryan Elkhorn outpatient campus (2025) — a beachhead into the "
         "Omaha metro."),
        ("https://www.bryanhealth.com/locations/hospitals/bryan-medical-"
         "center/",
         "https://www.bryanhealth.com/about-bryan-health/news/2021/kearney-"
         "regional-medical-center-joins-bryan-health/",
         "https://www.pchne.org/pch-announces-affiliation-with-bryan-"
         "health/"),
        "A two-hub account (Lincoln + Kearney/GI affiliates) whose "
        "growing affiliate ring converts formerly-independent transfer "
        "decisions into system-directed ones — contract at the system "
        "level and the spokes follow."),
    SystemProfile(
        "madonna",
        "Madonna Rehabilitation Hospitals",
        "Lincoln + Omaha, NE",
        "The post-acute magnet: LTACH + IRF campuses that receive complex "
        "(vent, TBI/SCI, stroke) patients from every acute system above.",
        (Facility("Madonna Lincoln (LTACH + rehab)", "Lincoln", "NE",
                  "historically 319 (193 LTACH/subacute/rehab — dated AHA "
                  "case study; verify in cost report)", "282000"),
         Facility("Madonna Omaha campus (IRF)", "Omaha", "NE", "110",
                  "283026", "Opened Oct 2016; adult + pediatric.")),
        "Receives on referral from acute-care discharge planners; "
        "clinical/academic affiliation with UNMC since 2014.",
        "No owned transport found — inbound legs are arranged by the "
        "sending hospital or Madonna case management; outsourced.",
        ("Every LTACH/IRF admission is BY DEFINITION an interfacility "
         "transport, and complex patients often need ALS/CCT-level "
         "crews — structural, recurring, schedulable volume.",),
        ("https://madonna.org/complex-medical",
         "https://www.madonna.org/about-us/history-of-madonna-"
         "rehabilitation-hospitals"),
        "The destination side of the demand equation: ~430 combined "
        "post-acute beds whose entire census arrives by IFT."),
    SystemProfile(
        "great_plains",
        "Great Plains Health",
        "North Platte, NE",
        "The independent western-NE regional referral center — a 34-county "
        "catchment (~136,000 lives, ~67,832 sq mi) that both receives from "
        "far-west CAHs and sends tertiary cases ~280 mi east.",
        (Facility("Great Plains Health", "North Platte", "NE", "116", "",
                  "Level III trauma; heart & vascular, cancer, ortho."),),
        "No published transfer center; hosts LifeNet air ambulance "
        "(Air Methods) on campus and Nebraska Medicine outpatient "
        "services (the eastbound referral pipeline).",
        "No owned ground ambulance found; LifeNet (air) is a tenant, not "
        "a subsidiary. Note: AmeriPro EMS of Nebraska + Priority Medical "
        "Transport share a North Platte address — the contested market.",
        ("Exited ALL Medicare Advantage networks effective Jan 1 2025 — "
         "payer-mix reshuffle for the western referral corridor.",
         "Remains independent (Community Hospital Corporation support "
         "relationship, not ownership) — its transfer flows are not yet "
         "captive to any system's preferred carrier."),
        ("https://www.gphealth.org/about-us/",
         "https://www.gphealth.org/services/emergency-services/lifenet-"
         "air-ambulance/",
         "https://chc.com/hospitals-and-clients/locations/great-plains-"
         "health/"),
        "The long-haul corridor account: super-rural mileage economics "
        "(22.6% Medicare add-on) and a head-to-head AmeriPro contest."),
    SystemProfile(
        "independents",
        "Regional independents (Mary Lanning · Columbus Community · "
        "statewide CAH base)",
        "Hastings / Columbus, NE",
        "The independent mid-size + critical-access layer that feeds the "
        "hubs — and the layer consolidating fastest.",
        (Facility("Mary Lanning Healthcare", "Hastings", "NE",
                  "161–163 (sources conflict)", "280032",
                  "Independent; interim CEO publicly focused on staying "
                  "independent amid financial stabilization."),
         Facility("Columbus Community Hospital", "Columbus", "NE",
                  "50 acute (+15 outpatient; sources vary 47–50)", "",
                  "Community-owned; MMT's 1987 founding site."),),
        "No formal transfer centers; transfer decisions sit with ED "
        "physicians + on-call hubs. 19 Nebraska CAHs formed the 'Nebraska "
        "High Value Network' clinically-integrated network — a possible "
        "future group-contracting counterparty for transport.",
        "Columbus/Hastings municipal + volunteer squads handle 911; "
        "hospital-arranged IFT is outsourced. Statewide: Nebraska has "
        "61–62 licensed CAHs (DHHS roster/map), each capped at 25 beds — "
        "structural transfer-out dependence.",
        ("More than half of Nebraska hospitals operated in the red last "
         "year (Nebraska Examiner / NHA); at least five rural NE "
         "hospitals at closure risk (CHQPR) — every service cut or REH "
         "conversion converts local admissions into transfers.",
         "Nebraska's first REH conversion: Warren Memorial (Friend, NE), "
         "Jan 2024; Garden County (Oshkosh) announced Dec 2025 — REHs "
         "keep no inpatient beds, so every admission becomes an IFT.",),
        ("https://healthcarecomps.com/hospitals/ne/280032/",
         "https://www.columbushosp.org/patients-visitors/about-us",
         "https://dhhs.ne.gov/licensure/Documents/Hospital%20Roster.pdf",
         "https://nebraskaexaminer.com/2024/03/11/as-half-of-rural-"
         "hospitals-lose-money-many-are-cutting-services/"),
        "The spoke layer: individually small, collectively the volume "
        "engine — and financial distress is mechanically increasing its "
        "transfer-out rate."),
)


# Statewide context the pages cite once.
STATEWIDE = {
    "ne_hospitals": ("92 member hospitals (Nebraska Hospital Association); "
                     "61–62 licensed critical-access hospitals (NE DHHS "
                     "roster / Feb 2024 CAH map)"),
    "transfer_center_stats": (
        "The only public statewide transfer-volume series: Nebraska's "
        "COVID-era statewide transfer center confirmed 146 of 234 "
        "requested transfers (Sep 2021) and 113 of 168 (Oct 2021) — "
        "demand exceeded placement capacity (Omaha World-Herald / "
        "Journal Star, Nov 2021)."),
    "maternity": ("51.6% of Nebraska counties are maternity-care deserts "
                  "vs 32.6% nationally (March of Dimes 2023 via Nebraska "
                  "Medical Association)."),
}


def systems() -> Tuple[SystemProfile, ...]:
    return SYSTEMS


def system_by_key(key: str) -> Optional[SystemProfile]:
    for s in SYSTEMS:
        if s.key == key:
            return s
    return None


def ccn_registry() -> List[Tuple[str, str]]:
    """(facility, CCN) for every facility with a confirmed CCN."""
    out: List[Tuple[str, str]] = []
    for s in SYSTEMS:
        for f in s.facilities:
            if f.ccn:
                out.append((f.name, f.ccn))
    return out
