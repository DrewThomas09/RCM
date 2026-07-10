"""IFT structural-growth evidence registry — every trend the growth story
leans on, each with its published figure, source, and (where captured) the
verbatim quote.

This extends the ``ift_demand_evidence`` contract to the GROWTH side: hospital
consolidation, service-line specialization/regionalization, rural closures and
REH conversions, transfer-volume trend studies, disease-burden trajectories,
demographics, EMS supply contraction, and payment-policy factors. The pages'
growth levers must read from here — an uncited growth rate is a bug.

Basis labels (same four as the demand registry — NO 'illustrative'):
  * GOV       — published government statistic / regulation / agency report.
  * SOURCED   — a real dataset or registry (AHA survey, Kaufman Hall series,
                Chartis analysis, NPPES, Sheps Center).
  * ACADEMIC  — peer-reviewed study (journal + year; PubMed-verified quotes
                are marked verbatim).
  * DERIVED   — computed by an explicit equation from the above.

Provenance tiers travel with each entry: quotes marked ``verbatim=True`` were
read in fetched full text (PubMed/PMC); the rest were captured from
search-result excerpts of the cited page and should be re-verified from an
unblocked network before external circulation (tracked in ``needs_reverify``).

Research pull 2026-07-10. Degrade — never raise.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class GrowthEvidence:
    key: str
    theme: str           # consolidation | specialization | closures-reh |
                         # transfer-trend | disease-burden | demographics |
                         # ems-supply | payment
    figure: str
    value: str
    basis: str           # GOV | SOURCED | ACADEMIC | DERIVED
    source: str
    quote: str
    url: str
    verbatim: bool = False       # True = quote read in fetched full text
    needs_reverify: bool = False # captured from a search excerpt
    equation: str = ""


_E = GrowthEvidence

_EVIDENCE: Tuple[GrowthEvidence, ...] = (
    # ── The headline transfer-volume trend ──────────────────────────────────
    _E("ift_ed_trend",
       "transfer-trend",
       "ED visits arriving via interfacility EMS transfer — national trend",
       "~1.3M/yr; +15% (2017–19) and +35% (2020–22) vs 2014–16 baseline",
       "ACADEMIC",
       "Peters GA et al., 'Interfacility transfers to the emergency "
       "department via emergency medical services in the United States', "
       "Am J Emerg Med 2026;106:24-29",
       "There were 11,802,738 (1.0%) ED visits that arrived via IFT, "
       "yielding an annual mean of 1.3 M per year… the proportion of IFT "
       "among ED visits increased by 15% during 2017-2019 and by 35% during "
       "2020-2022 relative to the baseline period during 2014-2016.",
       "https://doi.org/10.1016/j.ajem.2026.04.025", verbatim=True),
    _E("neds_transfers",
       "transfer-trend",
       "Adult ED-to-ED interfacility transfers (all-payer, NEDS)",
       "9,867,701 over 2018–2022 (~1.97M/yr); critical-procedure transfers "
       "rising (OR 1.09/yr)",
       "ACADEMIC",
       "Nikolla DA et al., 'Emergency Department Interfacility Transfers "
       "Requiring Critical Procedures are Increasing', J Emerg Med 2025",
       "During the study period, an estimated 9867701 (95% CI "
       "9475559-10259843) adult patients were transferred from US EDs… "
       "Among those transferred, 655442 (6.6%) had at least 1 critical "
       "procedure. Time in years was associated with any critical "
       "procedure, with an odds ratio of 1.09 (95% CI 1.07-1.11).",
       "https://doi.org/10.1016/j.jemermed.2025.12.020", verbatim=True),
    _E("rural_transfer_multiplier",
       "transfer-trend",
       "Rural vs urban ED transfer rate (Medicare; similar for CAHs)",
       "6.2% rural vs 2.0% urban — a >3x multiplier",
       "ACADEMIC",
       "Greenwood-Ericksen et al., JAMA Network Open 2021",
       "Rural ED visits were associated with more transfer (6.2% vs 2.0%) "
       "and fewer hospitalizations (24.7% vs 39.2%)… All findings were "
       "similar for CAHs.",
       "https://doi.org/10.1001/jamanetworkopen.2021.34980", verbatim=True),
    _E("rural_ed_growth",
       "transfer-trend",
       "Rural ED visit volume growth 2005→2016",
       "16.7M → 28.4M visits (+50%+ per-capita, 36.5 → 64.5 per 100)",
       "ACADEMIC",
       "Greenwood-Ericksen & Kocher, JAMA Network Open 2019",
       "rural ED visit estimates increased from 16.7 million to 28.4 "
       "million… Rural ED visit rates increased by more than 50%, from "
       "36.5 to 64.5 visits per 100 persons.",
       "https://doi.org/10.1001/jamanetworkopen.2019.1919", verbatim=True),
    _E("iowa_sepsis_transfer",
       "transfer-trend",
       "Share of rural sepsis patients transferred between hospitals (Iowa "
       "statewide claims 2005–2014)",
       "59% of 18,246 patients",
       "ACADEMIC",
       "Mohr NM et al., J Crit Care 2016 (Iowa)",
       "A total of 18,246 patients were included, of which 59% were "
       "transferred between hospitals… Transfer was associated with "
       "additional costs of $6897.",
       "https://doi.org/10.1016/j.jcrc.2016.07.016", verbatim=True),
    _E("seizure_transfer_trend",
       "transfer-trend",
       "Seizure-related ED transfers rising; nonmetro hospitals transfer "
       "out at 2.2x odds",
       "1 in 19 seizure ED visits transferred by 2018 (1 in 5 for status "
       "epilepticus)",
       "ACADEMIC",
       "Acton EK et al., Neurology 2022 (NEDS 2007–2018)",
       "the rate of transfer increased significantly over time… By 2018, "
       "approximately 1 in 19 seizure-related and 1 in 5 status epilepticus "
       "ED visits resulted in interfacility transfers… transferring "
       "hospitals were more likely to be nonmetropolitan (aOR 2.2).",
       "https://doi.org/10.1212/WNL.0000000000201319", verbatim=True),
    # ── Consolidation ────────────────────────────────────────────────────────
    _E("system_affiliation_series",
       "consolidation",
       "Share of US community hospitals that are system-affiliated",
       "53% (2005) → 56% (2010) → 67% (2022) → 70% (FY2024: 3,567 of 5,121)",
       "SOURCED",
       "AHA Fast Facts 2026 (2024 Annual Survey); MedPAC Mar 2020 ch.15; "
       "KFF consolidation analyses",
       "Two thirds (67%) of hospitals nationwide were affiliated with "
       "health systems in 2022, up from 56% in 2010.",
       "https://www.aha.org/system/files/media/file/2026/02/Fast-Facts-on-"
       "US-Hospitals-2026.pdf", needs_reverify=True),
    _E("metro_concentration",
       "consolidation",
       "Metro areas whose entire inpatient market is held by 1–2 systems",
       "47% of US metros (2024); concentration rose in 80% of metros "
       "2015–2024",
       "SOURCED",
       "KFF, 2024 hospital-market concentration analysis",
       "In 2024, 47% of U.S. metropolitan areas had their entire inpatient "
       "hospital market under the control of just one or two health "
       "systems.",
       "https://www.kff.org/health-costs/one-or-two-health-systems-"
       "controlled-the-entire-market-for-inpatient-hospital-care-in-nearly-"
       "half-of-metropolitan-areas/", needs_reverify=True),
    _E("ma_series",
       "consolidation",
       "Hospital M&A announced transactions by year (Kaufman Hall)",
       "2015:112 · 2016:102 · 2017:115 · 2018:90 · 2019:92 · 2020:79 · "
       "2021:49 · 2022:53 · 2023:65 · 2024:72 · 2025:46 (distress share "
       "43.5% in 2025 — an all-time high)",
       "SOURCED",
       "Kaufman Hall annual hospital M&A reviews (2015–2025)",
       "distressed M&A activity reached an all-time high in 2025, with "
       "43.5% of all transactions involving a distressed party.",
       "https://www.kaufmanhall.com/insights/research-report/hospital-and-"
       "health-system-2025-ma-review-uncertainty-transitions-continue",
       needs_reverify=True),
    _E("footprint_consolidation",
       "consolidation",
       "Footprint consolidation events (NE/IA, 2018–2025)",
       "Methodist–Fremont (2018, 50-yr lease) · Bryan–Kearney Regional "
       "(Jan 2022) · Bryan–Pender affiliation (Jun 2025) · "
       "UnityPoint–MercyOne Siouxland (Sep 2025, 464 licensed beds)",
       "SOURCED",
       "System press releases + Kearney Hub / Becker's / KTIV coverage",
       "UnityPoint Health completed its acquisition of Sioux City, "
       "Iowa-based MercyOne Siouxland Medical Center on Sept. 1 [2025].",
       "https://www.unitypoint.org/news-and-articles/press-releases/"
       "unitypoint-health-acquires-mercyone-siouxland-medical-center",
       needs_reverify=True),
    # ── Specialization / regionalization ─────────────────────────────────────
    _E("rural_ob_closures",
       "specialization",
       "Rural hospitals that stopped offering obstetrics, 2011–2024",
       "331 (~27% of the nation's rural OB units); Iowa lost the most of "
       "any state (22 facilities)",
       "SOURCED",
       "Chartis, '2025/2026 Rural Health State of the State'",
       "Between 2011 and 2024, 331 rural hospitals stopped offering OB "
       "services… Iowa saw the largest decline in state-level rural OB "
       "units, losing care at 22 facilities.",
       "https://www.chartis.com/insights/2025-rural-health-state-state",
       needs_reverify=True),
    _E("ob_loss_effect",
       "specialization",
       "Effect of losing hospital OB services (rural counties, 2004–2014)",
       "179 rural counties lost OB; births at hospitals WITHOUT OB units "
       "rose +3.06pp in the year after loss",
       "ACADEMIC",
       "Kozhimannil KB et al., JAMA 2018",
       "Between 2004 and 2014, 179 rural counties lost hospital-based "
       "obstetric services… significant increases in… births in a hospital "
       "without an obstetric unit (3.06 percentage points…) and preterm "
       "births (0.67 percentage points…) in the year after loss of "
       "services.",
       "https://doi.org/10.1001/jama.2018.1830", verbatim=True),
    _E("ne_ob_deserts",
       "specialization",
       "Nebraska maternity-care deserts + service cuts",
       "51.6% of NE counties are maternity-care deserts (vs 32.6% US); "
       "20% of NE hospitals eliminated services incl. L&D 2022–2024",
       "SOURCED",
       "March of Dimes 2023 (via Nebraska Medical Association); Nebraska "
       "Rural Health Association",
       "Between 2022 and 2024, 20 percent of Nebraska hospitals were "
       "forced to eliminate services including labor and delivery units.",
       "https://nebraskaruralhealth.org/looming-crisis-in-rural-health-"
       "care/", needs_reverify=True),
    _E("stroke_transfer_share",
       "specialization",
       "Ischemic stroke admissions transferred between hospitals",
       "5.7% of 312,367 admissions; senders median 88 beds / 24% rural, "
       "receivers median 371 beds / 2% rural",
       "ACADEMIC",
       "Man S et al., J Stroke Cerebrovasc Dis 2020",
       "Among 312,367 ischemic stroke admissions, 5.7% underwent "
       "inter-hospital transfer.",
       "https://doi.org/10.1016/j.jstrokecerebrovasdis.2020.105331",
       verbatim=True),
    _E("stroke_registry_scale",
       "specialization",
       "Stroke transfers in the GWTG registry, 2016–2021",
       "776,556 patients transferred out of 1,333 sites",
       "ACADEMIC",
       "Turner et al., Stroke 2026",
       "776,556 patients transferred out of 1333 sites.",
       "https://doi.org/10.1161/STROKEAHA.125.054333", verbatim=True),
    _E("secondary_overtriage",
       "specialization",
       "Secondary overtriage (transfers discharged from receiving ED) — "
       "facial-fracture transfers, NTDB 2007–2015",
       "171,618 transferred patients; ED-discharge-on-arrival share up "
       "151%",
       "ACADEMIC",
       "Wasicek PJ et al., Plast Reconstr Surg 2022",
       "there was a decline in operative intervention (29.5 to 22.1 "
       "percent…) and a 151 percent increase in the proportion discharged "
       "from the emergency department upon transfer arrival… reflecting "
       "increasing rates of secondary overtriage.",
       "https://doi.org/10.1097/PRS.0000000000009039", verbatim=True),
    # ── Closures + REH ───────────────────────────────────────────────────────
    _E("rural_closures",
       "closures-reh",
       "Rural hospital closures since 2005 (Sheps Center)",
       "194 since 2005 (151 after 2010); NE: 2 (latest MercyOne Oakland "
       "2021); IA: Blessing Health Keokuk 2022 (first in 22 years)",
       "SOURCED",
       "UNC Sheps Center rural hospital closures tracker",
       "194 facilities have closed since 2005, with 151 occurring after "
       "2010.",
       "https://www.shepscenter.unc.edu/programs-projects/rural-health/"
       "rural-hospital-closures/", needs_reverify=True),
    _E("closure_at_risk",
       "closures-reh",
       "Rural hospitals at risk of closure",
       "432 at risk (Chartis 2025); 417 (2026 update); 46% of rural "
       "hospitals in the red",
       "SOURCED",
       "Chartis rural health analyses 2025/2026",
       "46% of rural hospitals in the red, 432 at risk to close.",
       "https://www.fiercehealthcare.com/providers/46-rural-hospitals-red-"
       "432-vulnerable-closure-report-finds", needs_reverify=True),
    _E("reh_conversions",
       "closures-reh",
       "Rural Emergency Hospital conversions (no inpatient beds — every "
       "admission becomes a transfer)",
       "40–50 conversions since Jan 2023; nearly half in KS/TX/NE/OK; "
       "NE: Warren Memorial (Friend) Jan 2024, Garden County (Oshkosh) "
       "announced Dec 2025",
       "ACADEMIC",
       "J Rural Health 2026 (REH adaptation study; counts corroborated by "
       "KFF Health News / NCSL / Becker's)",
       "The Rural Emergency Hospital (REH) designation… allows small rural "
       "hospitals to discontinue inpatient services in exchange for a 5% "
       "Medicare reimbursement increase and a $3.2 M annual facility "
       "subsidy… Since its implementation, over 40 hospitals have "
       "converted to REH status… REHs must… limit average patient stays "
       "to under 24 hours… and must establish transfer agreements with "
       "Medicare-certified level I or level II trauma centers.",
       "https://doi.org/10.1111/jrh.70112", verbatim=True),
    _E("closure_transport_times",
       "closures-reh",
       "Effect of rural closures on EMS transport times (NEMSIS 2010–16)",
       "+2.6 min mean transport time; +7.2 min total activation time",
       "ACADEMIC",
       "Miller KEM et al., Health Services Research 2020",
       "Closures increased mean EMS transport times by 2.6 minutes (P = "
       ".09) and total activation time by 7.2 minutes (P = .02).",
       "https://doi.org/10.1111/1475-6773.13254", verbatim=True),
    # ── Disease burden (the clinical demand engine's growth) ────────────────
    _E("heart_failure_growth",
       "disease-burden",
       "US heart-failure prevalence trajectory",
       "6.7M (now) → 8.7M (2030) → 10.3M (2040) → 11.4M (2050)",
       "ACADEMIC",
       "HFSA 'HF STATS 2024', J Cardiac Failure",
       "Approximately 6.7 million Americans over 20 years of age have "
       "heart failure…expected to rise to 8.7 million in 2030, 10.3 "
       "million in 2040, and 11.4 million by 2050.",
       "https://hfsa.org/hf-stats-2024", needs_reverify=True),
    _E("stroke_incidence",
       "disease-burden",
       "US stroke incidence",
       ">795,000/yr (610,000 first events)",
       "GOV",
       "AHA 2024 Statistics Update / CDC Stroke Facts",
       "Every year, more than 795,000 people in the United States have a "
       "stroke.",
       "https://www.cdc.gov/stroke/data-research/facts-stats/",
       needs_reverify=True),
    _E("esrd_prevalence",
       "disease-burden",
       "US ESRD prevalence (dialysis = recurring scheduled transport)",
       ">808,000 living with ESRD; ~68% on dialysis; prevalence rising "
       "~20,000 cases/yr pre-2020",
       "GOV",
       "NIDDK Kidney Disease Statistics (USRDS-based), Oct 2025; USRDS "
       "2024 ADR",
       "More than 808,000 people in the United States are living with "
       "ESRD, with 68% on dialysis and 32% with a kidney transplant.",
       "https://www.niddk.nih.gov/health-information/health-statistics/"
       "kidney-disease", needs_reverify=True),
    _E("sepsis_burden",
       "disease-burden",
       "US sepsis hospitalizations",
       "≥1.7M adult hospitalizations/yr; inpatient stays +40% 2016→2021",
       "GOV",
       "CDC Sepsis program (HCUP-derived trend)",
       "Sepsis contributes to at least 1.7 million adult hospitalizations "
       "and at least 350,000 deaths annually.",
       "https://www.cdc.gov/sepsis/", needs_reverify=True),
    # ── Demographics ─────────────────────────────────────────────────────────
    _E("us_seniors",
       "demographics",
       "US 65+ population trajectory",
       "61.2M (2024) → 71.6M (2030) → ~78M (2035)",
       "GOV",
       "Census Bureau estimates + 2023 National Population Projections",
       "by 2030… more 65-and-older residents than children.",
       "https://www.census.gov/data/tables/2023/demo/popproj/2023-summary-"
       "tables.html", needs_reverify=True),
    _E("sarpy_growth",
       "demographics",
       "Fastest-growing footprint county (Sarpy, NE)",
       "159,732 (2010) → ~204,828 (2024) = +28% — by far the largest "
       "percentage gain among Nebraska counties (2010–2020: ~+20%)",
       "GOV",
       "Census Bureau county estimates (CO-EST2024) via Journal Star "
       "Nebraska demographics coverage",
       "Sarpy County grew ~20% between 2010 and 2020 — by far the largest "
       "percentage gain among Nebraska counties.",
       "https://www.census.gov/programs-surveys/popest.html",
       needs_reverify=True),
    _E("ne_brfss",
       "demographics",
       "Nebraska adult chronic-disease prevalence (state-level, BRFSS)",
       "Diabetes 10.8% (2024; 9.9% 2020); Obesity 37.8% (2024; +3.5pp "
       "over 5 yrs)",
       "SOURCED",
       "CDC BRFSS via PopHIVE (Yale SPH; DOI 10.5281/zenodo.17345935), "
       "pulled 2026-07-10",
       "BRFSS is a self-reported telephone survey; estimates carry "
       "confidence intervals.",
       "https://www.pophive.org/", verbatim=True),
    # ── EMS supply contraction (the outsourcing forcing function) ───────────
    _E("ne_volunteer_base",
       "ems-supply",
       "Nebraska EMS volunteer dependence",
       "80%+ of NE EMS agencies rely entirely on volunteers (237,000+ "
       "calls in 2023); only 31% of volunteer agencies say they have "
       "enough staff; 28% expect to be unable to operate within 5 years",
       "GOV",
       "Nebraska DHHS 2023–24 Statewide EMS Assessment (+ 1011now "
       "coverage, Sep 2025)",
       "Volunteerism and low-cost labor are Nebraska's primary and "
       "largest EMS subsidies, but these subsidies are disappearing, with "
       "volunteerism across Nebraska waning and not likely to return.",
       "https://dhhs.ne.gov/OEHS%20Program%20Documents/NE%20Statewide%20"
       "EMS%20Assessment%20v2024.pdf", needs_reverify=True),
    _E("ne_agency_excess",
       "ems-supply",
       "Nebraska EMS agency fragmentation",
       "State assessment: possible EXCESS of licensed transporting "
       "agencies exacerbating shortages; 16 air medical services "
       "supplement ground",
       "GOV",
       "Nebraska DHHS 2023–24 Statewide EMS Assessment",
       "Nebraska may have an excess of licensed EMS transporting "
       "agencies, which may be exacerbating shortages and creating "
       "inefficiencies.",
       "https://dhhs.ne.gov/OEHS%20Program%20Documents/NE%20Statewide%20"
       "EMS%20Assessment%20v2024.pdf", needs_reverify=True),
    _E("nppes_universe",
       "ems-supply",
       "NE/IA ambulance-organization universe (vendored NPPES pull)",
       "751 unique org NPIs captured (NE 400: 82% municipal/fire/"
       "volunteer, 58 private, 5 hospital-owned, 9 air · IA 351: 62% "
       "municipal, 70 private, 40 hospital-owned, 22 air)",
       "SOURCED",
       "CMS NPPES registry sweep, taxonomy 'Ambulance', NPI-2, pulled "
       "2026-07-10 (vendored: market_reports/reference/"
       "nppes_ambulance_orgs_ne_ia_20260710.csv)",
       "",
       "https://npiregistry.cms.hhs.gov/"),
    # ── Payment ──────────────────────────────────────────────────────────────
    _E("aif_2026",
       "payment",
       "Medicare Ambulance Inflation Factor",
       "CY2026: +2.0% (CY2025: +2.4% per industry summaries — verify "
       "against CMS/AAA before circulation)",
       "GOV",
       "CMS Ambulance Fee Schedule PUF / industry summaries",
       "For 2026, the AIF is 2.0%, a step down from the 2.4% applied in "
       "2025.",
       "https://www.cms.gov/medicare/payment/fee-schedules/ambulance/"
       "ambulance-fee-schedule-public-use-files", needs_reverify=True),
    _E("addons_extended",
       "payment",
       "Temporary Medicare ambulance add-ons extended through 2027",
       "+2% urban, +3% rural, +22.6% super-rural (CAA 2026 §6203, "
       "through Dec 31 2027)",
       "GOV",
       "Consolidated Appropriations Act 2026, §6203 (industry summary)",
       "the temporary statutory add-on payments… have been extended "
       "through December 31, 2027… 2% urban, 3% rural, and 22.6% "
       "super-rural.",
       "https://www.cms.gov/medicare/payment/fee-schedules/ambulance",
       needs_reverify=True),
    _E("gadcs",
       "payment",
       "Ground Ambulance Data Collection System (cost transparency)",
       "Collected from ~half of the 10,500+ ground organizations billing "
       "Medicare; MedPAC rate-adequacy verdict expected June 2026",
       "GOV",
       "MedPAC ambulance assessment, Dec 2025; CMS GADCS Year 1–2 cohort "
       "report",
       "since 2023, representative samples of organizations billing "
       "Traditional Medicare… have reported cost, revenue, utilization… "
       "Now collected from roughly half of the more than 10,500 ground "
       "ambulance organizations billing Medicare annually.",
       "https://www.medpac.gov/wp-content/uploads/2025/12/Tab-M-Ambulance-"
       "Dec-2025.pdf", needs_reverify=True),
    _E("gapb_risk",
       "payment",
       "Ground-ambulance balance-billing policy risk (GAPB committee)",
       "Advisory committee recommends banning OON balance billing and "
       "capping patient cost-share at lesser of $100 or 10% — covering "
       "IFT; no federal legislation enacted as of mid-2026",
       "GOV",
       "CMS GAPB Advisory Committee report (Mar 2024, transmitted Aug "
       "2024)",
       "ban out-of-network balance billing for ground ambulance services "
       "and cap patient cost-sharing at the lesser of $100 or 10% of the "
       "bill.",
       "https://www.cms.gov/files/document/report-advisory-committee-"
       "ground-ambulance-and-patient-billing.pdf", needs_reverify=True),
    _E("et3_end",
       "payment",
       "ET3 model cancelled — transport-based payment persists",
       "CMS ended ET3 Dec 31 2023, two years early, on low participation",
       "GOV",
       "CMS Innovation Center ET3 FAQ",
       "the CMS Innovation Center made the decision to end the Model "
       "ahead of schedule on December 31, 2023.",
       "https://www.cms.gov/priorities/innovation/innovation-models/et3/"
       "faq", needs_reverify=True),
)


EVIDENCE: Dict[str, GrowthEvidence] = {e.key: e for e in _EVIDENCE}

THEMES: Tuple[Tuple[str, str], ...] = (
    ("transfer-trend", "Transfer volume is growing — measured, not assumed"),
    ("consolidation", "Hospital-system consolidation over time"),
    ("specialization", "Service-line specialization & regionalization"),
    ("closures-reh", "Rural closures & REH conversions"),
    ("disease-burden", "Chronic-disease burden trajectories"),
    ("demographics", "Population & aging"),
    ("ems-supply", "EMS supply contraction (the outsourcing forcing function)"),
    ("payment", "Payment policy — tailwinds & watch items"),
)


def evidence(key: str) -> Optional[GrowthEvidence]:
    return EVIDENCE.get(key)


def by_theme(theme: str) -> List[GrowthEvidence]:
    return [e for e in _EVIDENCE if e.theme == theme]


def all_evidence() -> Tuple[GrowthEvidence, ...]:
    return _EVIDENCE


def reverify_queue() -> List[GrowthEvidence]:
    """Entries whose quotes came from search excerpts — the re-verification
    worklist for an unblocked network."""
    return [e for e in _EVIDENCE if e.needs_reverify]
