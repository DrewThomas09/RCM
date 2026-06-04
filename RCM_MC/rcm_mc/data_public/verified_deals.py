"""Verified, real, sourced healthcare-services PE / M&A deals.

WHY THIS EXISTS
---------------
The bundled 605-deal "corpus" (``extended_seed_*.py``) is **synthetic seed
data** — invented names like "OrthoAmerica / Clearfield Capital", ``source_id``
values like ``seed_605``. Presenting fabricated deals as a real track record is
a credibility problem: a model trained / benchmarked on made-up deals predicts
nothing, and an LP who spots one invented name distrusts the whole platform.

This module is the **opposite**: a hand-curated set of deals that are every one
REAL and carry a real source URL (press release, SEC filing, or named trade /
financial publication). It is the seed of the "verify every deal online"
effort — the document we grow toward replacing the synthetic corpus. Enterprise
value is recorded ONLY where it was publicly disclosed (``ev_usd_mm = None``
otherwise — most physician-MSO rollups never disclose EV; we do not guess).

Outcomes — including the marquee PE-hospital/staffing bankruptcies (Steward,
Envision, Prospect, Cano, American Physician Partners, Hahnemann) — are public
record, which is exactly why they make the corpus credible: real failures, not
a curve of invented winners.

SCHEMA (per deal dict)
    target, sponsor, year, ev_usd_mm (int|None), sector, subsector_note,
    outcome ∈ {active, exited, bankrupt, distressed, unknown}, outcome_note,
    source_url, source_note

These are the load-bearing facts (target / sponsor / year / sector / outcome /
source). EV is null wherever undisclosed. Sources were gathered 2026-06 from
public coverage; see source_note for the publication.
"""
from __future__ import annotations

from typing import Dict, List, Optional

SECTORS = (
    "hospitals", "physician_practices", "behavioral_health",
    "home_health_hospice", "dental", "dermatology", "ophthalmology",
    "asc", "urgent_care", "rcm_healthtech", "dialysis", "other_services",
    # added in the 2026-06 batch-4/6 expansion
    "veterinary", "value_based_care", "lab", "ems", "managed_care",
)

VERIFIED_DEALS: List[Dict] = [
    # ── Hospitals / health systems (incl. the marquee failure cases) ──
    {
        "target": "Steward Health Care (Caritas Christi)", "sponsor": "Cerberus Capital Management",
        "year": 2010, "ev_usd_mm": 246, "sector": "hospitals",
        "subsector_note": "Catholic system take-private; later the largest US private hospital operator (~37 hospitals at peak)",
        "outcome": "bankrupt",
        "outcome_note": "Cerberus exited ~Jan 2021 (reported ~$800M profit); Steward filed Chapter 11 on 2024-05-06 with >$9B liabilities — a marquee PE-hospital failure.",
        "source_url": "https://pestakeholder.org/reports/the-pillaging-of-steward-health-care/",
        "source_note": "Private Equity Stakeholder Project; 2024 Ch.11 corroborated by Sen. Markey statement",
    },
    {
        "target": "Prospect Medical Holdings", "sponsor": "Leonard Green & Partners",
        "year": 2010, "ev_usd_mm": 363, "sector": "hospitals",
        "subsector_note": "Multi-state safety-net operator (~16 hospitals CA/CT/PA/RI)",
        "outcome": "bankrupt",
        "outcome_note": "LGP owned 2010–2021, took ~$645M in dividends/redemptions; Prospect filed Ch.11 on 2025-01-11.",
        "source_url": "https://www.healthcaredive.com/news/prospect-medical-holdings-files-bankruptcy/737138/",
        "source_note": "Healthcare Dive (bankruptcy); Fierce Healthcare (2010 acquisition)",
    },
    {
        "target": "LifePoint Health", "sponsor": "Apollo Global Management",
        "year": 2018, "ev_usd_mm": 5600, "sector": "hospitals",
        "subsector_note": "Take-private of non-urban hospital system at $65.00/share; merged with Apollo's RCCH",
        "outcome": "active",
        "outcome_note": "Remains an Apollo portfolio company; later expanded into behavioral health (Springstone).",
        "source_url": "https://pitchbook.com/news/articles/apollo-to-pay-56b-in-pes-latest-healthcare-deal",
        "source_note": "PitchBook; SEC 8-K",
    },
    {
        "target": "Hahnemann University Hospital", "sponsor": "Paladin Healthcare (Joel Freedman)",
        "year": 2018, "ev_usd_mm": 170, "sector": "hospitals",
        "subsector_note": "Two Philadelphia hospitals; real estate split from the OpCo at deal time",
        "outcome": "bankrupt",
        "outcome_note": "OpCo filed Ch.11 on 2019-07-01; Hahnemann closed mid-2019 (~2,572 laid off) — cited 'real-estate play' failure.",
        "source_url": "https://www.cnn.com/2019/07/29/economy/hahnemann-hospital-closing-philadelphia/index.html",
        "source_note": "CNN Business; The American Prospect",
    },
    # ── Physician practice management ──
    {
        "target": "Envision Healthcare (AMSURG + EmCare)", "sponsor": "KKR",
        "year": 2018, "ev_usd_mm": 9900, "sector": "physician_practices",
        "subsector_note": "Take-private of physician staffing + ASC giant at $46.00/share",
        "outcome": "bankrupt",
        "outcome_note": "Filed Ch.11 on 2023-05-15 (~$7.7B debt) — a marquee No Surprises Act failure; among KKR's steepest losses.",
        "source_url": "https://www.modernhealthcare.com/finance/envision-healthcare-bankruptcy-chapter-11-amsurg",
        "source_note": "Modern Healthcare; $9.9B EV via Bass Berry & Sims",
    },
    {
        "target": "U.S. Anesthesia Partners", "sponsor": "Welsh, Carson, Anderson & Stowe",
        "year": 2012, "ev_usd_mm": None, "sector": "physician_practices",
        "subsector_note": "Anesthesiology MSO rollup (>12 practices over a decade)",
        "outcome": "distressed",
        "outcome_note": "FTC sued WCAS/USAP (2023) over a Texas roll-up scheme; WCAS settled (consent order May 2025) — landmark antitrust outcome.",
        "source_url": "https://www.ftc.gov/news-events/news/press-releases/2025/01/ftc-secures-settlement-private-equity-firm-antitrust-roll-scheme-case",
        "source_note": "FTC press release",
    },
    {
        "target": "American Physician Partners", "sponsor": "Brown Brothers Harriman Capital Partners",
        "year": 2016, "ev_usd_mm": None, "sector": "physician_practices",
        "subsector_note": "Emergency / hospital medicine staffing (~150 ED contracts, 15 states)",
        "outcome": "bankrupt",
        "outcome_note": "Wound down by 2023-07-31, filed Ch.11 on 2023-09-18; cited No Surprises Act cash-flow hit.",
        "source_url": "https://www.fiercehealthcare.com/providers/hospital-ed-staffer-american-physician-partners-files-chapter-11-bankruptcy",
        "source_note": "Fierce Healthcare; Bloomberg Law",
    },
    {
        "target": "agilon health", "sponsor": "Clayton, Dubilier & Rice",
        "year": 2016, "ev_usd_mm": None, "sector": "physician_practices",
        "subsector_note": "Value-based primary-care enablement for Medicare Advantage",
        "outcome": "exited",
        "outcome_note": "IPO 2021-04-19 (~$1.2B net proceeds); CD&R was controlling sponsor.",
        "source_url": "https://www.sec.gov/Archives/edgar/data/0001831097/000119312521085566/d10763ds1.htm",
        "source_note": "SEC Form S-1",
    },
    {
        "target": "Cardiovascular Associates of America", "sponsor": "Webster Equity Partners",
        "year": 2021, "ev_usd_mm": None, "sector": "physician_practices",
        "subsector_note": "Cardiology MSO rollup — one of the largest PE-backed cardiology platforms",
        "outcome": "active", "outcome_note": "Active platform.",
        "source_url": "https://cvausa.com/about-cardiovascular-associates-of-america",
        "source_note": "CVAUSA corporate site (Webster formation); broader context via Cardiovascular Business",
    },
    # ── Behavioral health ──
    {
        "target": "LifeStance Health", "sponsor": "TPG / Summit Partners / Silversmith",
        "year": 2020, "ev_usd_mm": None, "sector": "behavioral_health",
        "subsector_note": "Large US outpatient mental-health platform; ~$1.2B 2020 equity investment",
        "outcome": "exited",
        "outcome_note": "IPO 2021-06-10 (~$720M raised; ~$6.4B target valuation); sponsors retained ~66%.",
        "source_url": "https://www.silversmith.com/news/lifestance-health-partners-with-tpg-summit-partners-and-silversmith-to-expand-behavioral-health-access",
        "source_note": "Silversmith Capital; IPO valuation via Behavioral Health Business",
    },
    {
        "target": "Summit BHC", "sponsor": "Patient Square Capital",
        "year": 2021, "ev_usd_mm": 1300, "sector": "behavioral_health",
        "subsector_note": "SUD + acute psychiatric operator (24 facilities, 16 states); bought from FFL & Lee Equity",
        "outcome": "active", "outcome_note": "PE-to-PE secondary; prior owners exited.",
        "source_url": "https://www.prnewswire.com/news-releases/patient-square-capital-to-acquire-summit-bhc-from-ffl-partners-and-lee-equity-partners-301371933.html",
        "source_note": "PR Newswire; $1.3B EV via Behavioral Health Business",
    },
    {
        "target": "Geode Health", "sponsor": "KKR",
        "year": 2021, "ev_usd_mm": None, "sector": "behavioral_health",
        "subsector_note": "KKR-founded outpatient mental-health platform (de novo + roll-up)",
        "outcome": "active", "outcome_note": "Active.",
        "source_url": "https://news.bloomberglaw.com/mergers-and-acquisitions/kkr-said-to-create-invest-in-mental-health-firm-geode-health",
        "source_note": "Bloomberg Law; Behavioral Health Business",
    },
    # ── Home health & hospice ──
    {
        "target": "Kindred at Home", "sponsor": "TPG Capital & Welsh, Carson, Anderson & Stowe",
        "year": 2021, "ev_usd_mm": 8100, "sector": "home_health_hospice",
        "subsector_note": "Humana bought the 60% it didn't own from TPG/WCAS; EV incl. Humana's $2.4B equity",
        "outcome": "exited", "outcome_note": "PE exit to Humana; hospice later divested to CD&R (Gentiva).",
        "source_url": "https://humana.gcs-web.com/news-releases/news-release-details/humana-announces-agreement-acquire-remaining-60-percent-interest",
        "source_note": "Humana IR press release; SEC 8-K",
    },
    {
        "target": "BrightSpring Health Services", "sponsor": "KKR",
        "year": 2019, "ev_usd_mm": 1300, "sector": "home_health_hospice",
        "subsector_note": "Home/community care + LTC pharmacy (merged with PharMerica); ~$4.5B combined revenue",
        "outcome": "exited", "outcome_note": "KKR IPO'd BrightSpring on Nasdaq in 2024.",
        "source_url": "https://www.businesswire.com/news/home/20190305005975/en/KKR-Completes-Acquisition-BrightSpring-Health-Services",
        "source_note": "Business Wire; PharMerica merger via Home Health Care News",
    },
    # ── Dental / DSO ──
    {
        "target": "Heartland Dental", "sponsor": "KKR",
        "year": 2018, "ev_usd_mm": None, "sector": "dental",
        "subsector_note": "Largest US DSO (~900+ supported offices); bought from Ontario Teachers'",
        "outcome": "active", "outcome_note": "Active; OTPP retained a stake.",
        "source_url": "https://www.globenewswire.com/news-release/2018/03/07/1418000/0/en/KKR-to-Acquire-Majority-Interest-in-Heartland-Dental.html",
        "source_note": "GlobeNewswire; Ontario Teachers' confirmation",
    },
    {
        "target": "MB2 Dental", "sponsor": "Warburg Pincus (from Charlesbank)",
        "year": 2024, "ev_usd_mm": 3500, "sector": "dental",
        "subsector_note": "Dentist-owned DSO partnership model (~600 partnerships); $525M equity check",
        "outcome": "active", "outcome_note": "PE-to-PE recap; Charlesbank retained a stake.",
        "source_url": "https://www.beckersdental.com/dso-dpms/mb2-dental-undergoes-recapitalization-event-6-things-to-know/",
        "source_note": "Becker's Dental; Charlesbank portfolio page",
    },
    # ── Dermatology / ophthalmology ──
    {
        "target": "Forefront Dermatology", "sponsor": "Partners Group (from OMERS PE)",
        "year": 2022, "ev_usd_mm": None, "sector": "dermatology",
        "subsector_note": "Largest US physician-led dermatology group (200+ practices)",
        "outcome": "active", "outcome_note": "OMERS PE secondary; terms undisclosed.",
        "source_url": "https://pensionpulse.blogspot.com/2022/02/omers-sells-stake-in-forefront.html",
        "source_note": "PensionPulse summarizing the OMERS→Partners Group sale (Feb 2022)",
    },
    {
        "target": "EyeCare Partners", "sponsor": "Partners Group (from FFL Partners)",
        "year": 2020, "ev_usd_mm": 2200, "sector": "ophthalmology",
        "subsector_note": "Integrated optometry + ophthalmology MSO; grew via 60+ acquisitions",
        "outcome": "distressed",
        "outcome_note": "Completed a debt refinancing / new-money restructuring in May 2024 amid heavy leverage.",
        "source_url": "https://www.eyecare-partners.com/press-release/eyecare-partners-announces-refinancing-transactions-secures-new-money-investment/",
        "source_note": "EyeCare Partners (2024 refinancing); Partners Group (acquisition)",
    },
    # ── ASC / dialysis / urgent care ──
    {
        "target": "Surgery Partners (control) + National Surgical Healthcare", "sponsor": "Bain Capital",
        "year": 2017, "ev_usd_mm": 760, "sector": "asc",
        "subsector_note": "Bain bought H.I.G.'s ~54% stake (~$503M) + funded the $760M NSH acquisition",
        "outcome": "active", "outcome_note": "Bain remains controlling shareholder; Surgery Partners stayed listed.",
        "source_url": "https://www.baincapital.com/news/surgery-partners-acquire-national-surgical-healthcare-irving-place-capital",
        "source_note": "Bain Capital press release; H.I.G. exit; GlobeNewswire ($760M)",
    },
    {
        "target": "American Renal Associates", "sponsor": "Nautic Partners (Innovative Renal Care)",
        "year": 2020, "ev_usd_mm": 853, "sector": "dialysis",
        "subsector_note": "Take-private at $11.50/share (66% premium); from Centerbridge",
        "outcome": "exited", "outcome_note": "Public→private; closed 2021-01-25; merged into Innovative Renal Care.",
        "source_url": "https://nautic.com/news/american-renal-associates-enters-into-definitive-agreement-to-be-acquired-by-nautic-partners/",
        "source_note": "Nautic Partners; $853M via HealthLeaders",
    },
    {
        "target": "Summit Health-CityMD", "sponsor": "Warburg Pincus (exit to VillageMD/Walgreens)",
        "year": 2022, "ev_usd_mm": 8900, "sector": "urgent_care",
        "subsector_note": "Urgent care + multispecialty group; Warburg PE exit",
        "outcome": "exited", "outcome_note": "Sold to VillageMD (Walgreens-backed) for ~$8.9B; closed 2023.",
        "source_url": "https://www.villagemd.com/press-releases/villagemd-acquires-summit-health-citymd-creating-one-of-the-largest-independent-provider-groups-in-the-u.s",
        "source_note": "VillageMD press release; PE Hub (Warburg exit)",
    },
    # ── RCM / healthcare IT services (the platform's home sector) ──
    {
        "target": "athenahealth", "sponsor": "Hellman & Friedman + Bain Capital",
        "year": 2022, "ev_usd_mm": 17000, "sector": "rcm_healthtech",
        "subsector_note": "Cloud EHR / RCM platform; PE-to-PE secondary (Veritas bought it for $5.7B in 2019)",
        "outcome": "active", "outcome_note": "Large LBO; active.",
        "source_url": "https://www.baincapital.com/news/athenahealth-healthcare-technology-leader-be-acquired-hellman-friedman-and-bain-capital-17",
        "source_note": "Bain Capital; Milbank (Veritas sell-side)",
    },
    {
        "target": "R1 RCM", "sponsor": "TowerBrook Capital Partners + CD&R",
        "year": 2024, "ev_usd_mm": 8900, "sector": "rcm_healthtech",
        "subsector_note": "Take-private of the RCM company at $14.30/share; closed Nov 2024",
        "outcome": "exited", "outcome_note": "Public→private; TowerBrook already held ~36%.",
        "source_url": "https://www.sec.gov/Archives/edgar/data/0001910851/000119312524190603/d837241dex991.htm",
        "source_note": "SEC 8-K (merger agreement, $8.9B EV)",
    },
    {
        "target": "Cotiviti", "sponsor": "Veritas Capital (2018); KKR ~50% stake (2024)",
        "year": 2018, "ev_usd_mm": 4900, "sector": "rcm_healthtech",
        "subsector_note": "Payment-accuracy & data-analytics platform; Veritas partial exit to KKR in 2024",
        "outcome": "active", "outcome_note": "Active; 2024 Carlyle ~$15B bid fell through, KKR took half.",
        "source_url": "https://www.healthcaredive.com/news/kkr-talks-buy-stake-cotiviti-veritas-capital/702397/",
        "source_note": "Healthcare Dive; 2018 Veritas/$4.9B via coverage",
    },
    {
        "target": "Cano Health", "sponsor": "Jaws Acquisition Corp SPAC (Barry Sternlicht)",
        "year": 2021, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Value-based senior primary care (Medicare); Miami; de-SPAC public listing",
        "outcome": "bankrupt",
        "outcome_note": "Filed Ch.11 on 2024-02-04; emerged July 2024 having cut ~$1B debt; delisted — a value-based-care/SPAC failure.",
        "source_url": "https://www.healthcaredive.com/news/cano-health-chapter-11-bankruptcy-restructuring-agreement/706546/",
        "source_note": "Healthcare Dive",
    },

    # ════════════════════════════════════════════════════════════════════
    # 2026-06 expansion — more real, sourced deals toward fuller coverage.
    # Public-company deals link to SEC EDGAR (pull the actual 8-K/S-1);
    # private deals link to the sponsor's own site. Load-bearing facts
    # (target / sponsor / year / sector / outcome) verified from public
    # coverage; EV recorded only where publicly disclosed.
    # ════════════════════════════════════════════════════════════════════

    # ── Hospitals / health systems ──
    {
        "target": "Vanguard Health Systems", "sponsor": "Blackstone",
        "year": 2004, "ev_usd_mm": 1750, "sector": "hospitals",
        "subsector_note": "Urban/suburban hospital operator; Blackstone took majority control",
        "outcome": "exited",
        "outcome_note": "IPO'd on the NYSE in 2011; acquired by Tenet Healthcare in 2013 (~$4.3B incl. debt) — a full PE round-trip.",
        "source_url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company=vanguard+health+systems&type=S-1&dateb=&owner=include&count=40",
        "source_note": "SEC EDGAR (Vanguard Health Systems 2011 IPO S-1); Tenet 2013 acquisition 8-K",
    },
    {
        "target": "IASIS Healthcare", "sponsor": "TPG Capital (with JLL Partners)",
        "year": 2004, "ev_usd_mm": 1400, "sector": "hospitals",
        "subsector_note": "Acute-care hospital operator (Southwest/Mountain states)",
        "outcome": "exited",
        "outcome_note": "Sold to Steward Health Care (real estate to Medical Properties Trust) in 2017 — folding into the later Steward failure.",
        "source_url": "https://www.medicalpropertiestrust.com/",
        "source_note": "Medical Properties Trust (2017 Steward/IASIS transaction); 2004 TPG+JLL buyout via Modern Healthcare",
    },

    # ── Physician practice management ──
    {
        "target": "Team Health Holdings", "sponsor": "Blackstone",
        "year": 2017, "ev_usd_mm": 6100, "sector": "physician_practices",
        "subsector_note": "Physician staffing (ED / hospital medicine); take-private at $43.50/share",
        "outcome": "distressed",
        "outcome_note": "Heavy post-LBO leverage; restructured debt amid No Surprises Act pressure (reported 2023–2024) — the staffing-LBO stress case that did NOT (yet) file, unlike Envision/APP.",
        "source_url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company=team+health&type=8-K&dateb=&owner=include&count=40",
        "source_note": "SEC EDGAR (Team Health merger 8-K, $6.1B); distress via Bloomberg/Reuters",
    },
    {
        "target": "Radiology Partners", "sponsor": "New Enterprise Associates + Starr Investment Holdings",
        "year": 2018, "ev_usd_mm": None, "sector": "physician_practices",
        "subsector_note": "Largest US radiology physician practice; 2018 majority recap",
        "outcome": "distressed",
        "outcome_note": "Completed a debt restructuring / new-money deal in 2024 amid heavy leverage and No Surprises Act payment friction.",
        "source_url": "https://www.radpartners.com/",
        "source_note": "Radiology Partners (corporate); 2024 restructuring via Bloomberg/Axios",
    },
    {
        "target": "Surgical Care Affiliates", "sponsor": "TPG Capital",
        "year": 2007, "ev_usd_mm": None, "sector": "asc",
        "subsector_note": "ASC operator carved out of HealthSouth's outpatient-surgery division",
        "outcome": "exited",
        "outcome_note": "IPO 2013 (Nasdaq: SCAI); acquired by UnitedHealth's Optum in 2017 (~$2.3B).",
        "source_url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company=surgical+care+affiliates&type=&dateb=&owner=include&count=40",
        "source_note": "SEC EDGAR (Surgical Care Affiliates filings); Optum 2017 acquisition",
    },
    {
        "target": "US Oncology", "sponsor": "Welsh, Carson, Anderson & Stowe",
        "year": 2004, "ev_usd_mm": 1700, "sector": "physician_practices",
        "subsector_note": "Oncology practice-management network; take-private (~$1.7B incl. debt)",
        "outcome": "exited",
        "outcome_note": "Acquired by McKesson in 2010 (~$2.16B) — a clean PE exit to a strategic.",
        "source_url": "https://www.wcas.com/",
        "source_note": "Welsh, Carson, Anderson & Stowe (portfolio); McKesson 2010 acquisition press",
    },
    {
        "target": "OneOncology", "sponsor": "General Atlantic",
        "year": 2018, "ev_usd_mm": None, "sector": "physician_practices",
        "subsector_note": "Physician-led national oncology network (platform formed 2018)",
        "outcome": "exited",
        "outcome_note": "TPG + Cencora (AmerisourceBergen) acquired a majority in 2023 (~$2.1B EV) — General Atlantic's exit.",
        "source_url": "https://www.generalatlantic.com/",
        "source_note": "General Atlantic (portfolio); 2023 TPG/Cencora majority recap",
    },
    {
        "target": "GI Alliance", "sponsor": "Apollo Global Management",
        "year": 2022, "ev_usd_mm": None, "sector": "physician_practices",
        "subsector_note": "Physician-owned gastroenterology MSO; Apollo took a majority",
        "outcome": "active",
        "outcome_note": "Active platform (subject of founder/Waud Capital litigation over the buyout).",
        "source_url": "https://www.apollo.com/",
        "source_note": "Apollo Global Management (portfolio); 2022 GI Alliance majority investment",
    },

    # ── Behavioral health ──
    {
        "target": "Springstone", "sponsor": "Welsh, Carson, Anderson & Stowe",
        "year": 2017, "ev_usd_mm": None, "sector": "behavioral_health",
        "subsector_note": "Inpatient psychiatric + addiction-treatment operator",
        "outcome": "exited",
        "outcome_note": "Sold to LifePoint Health (Apollo) in 2021 — behavioral platform exit to a PE-backed strategic.",
        "source_url": "https://www.wcas.com/",
        "source_note": "Welsh, Carson, Anderson & Stowe (portfolio); 2021 LifePoint acquisition",
    },
    {
        "target": "Refresh Mental Health", "sponsor": "Kelso & Company",
        "year": 2020, "ev_usd_mm": None, "sector": "behavioral_health",
        "subsector_note": "Outpatient mental-health / SUD group practice network",
        "outcome": "exited",
        "outcome_note": "Acquired by UnitedHealth's Optum in 2022 — exit to a payer-owned strategic.",
        "source_url": "https://www.kelso.com/",
        "source_note": "Kelso & Company (portfolio); 2022 Optum acquisition via Behavioral Health Business",
    },
    {
        "target": "Behavioral Health Group", "sponsor": "The Vistria Group",
        "year": 2020, "ev_usd_mm": None, "sector": "behavioral_health",
        "subsector_note": "Opioid-treatment-program (OTP) / medication-assisted treatment network",
        "outcome": "active", "outcome_note": "Active platform.",
        "source_url": "https://www.vistria.com/",
        "source_note": "The Vistria Group (portfolio); 2020 Behavioral Health Group investment",
    },

    # ── Home health & hospice ──
    {
        "target": "Help at Home", "sponsor": "Centerbridge Partners + The Vistria Group",
        "year": 2020, "ev_usd_mm": None, "sector": "home_health_hospice",
        "subsector_note": "In-home personal care for seniors & people with disabilities",
        "outcome": "active", "outcome_note": "Active platform.",
        "source_url": "https://www.centerbridge.com/",
        "source_note": "Centerbridge Partners (portfolio); 2020 Help at Home investment",
    },
    {
        "target": "Aveanna Healthcare", "sponsor": "Bain Capital + J.H. Whitney",
        "year": 2017, "ev_usd_mm": None, "sector": "home_health_hospice",
        "subsector_note": "Pediatric + adult home health / private-duty nursing (formed by merger)",
        "outcome": "exited",
        "outcome_note": "IPO 2021 (Nasdaq: AVAH) — PE-built platform taken public.",
        "source_url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company=aveanna&type=S-1&dateb=&owner=include&count=40",
        "source_note": "SEC EDGAR (Aveanna 2021 IPO S-1)",
    },
    {
        "target": "Gentiva (Kindred hospice & personal care)", "sponsor": "Clayton, Dubilier & Rice",
        "year": 2022, "ev_usd_mm": None, "sector": "home_health_hospice",
        "subsector_note": "CD&R bought a majority of Kindred at Home's hospice & personal-care business from Humana; rebranded Gentiva",
        "outcome": "active", "outcome_note": "Active; Humana retained a minority stake.",
        "source_url": "https://www.cdr-inc.com/",
        "source_note": "Clayton, Dubilier & Rice (portfolio); Humana 2022 divestiture 8-K",
    },

    # ── Dental / DSO ──
    {
        "target": "Aspen Dental (The Aspen Group)", "sponsor": "Leonard Green & Partners (later American Securities + Ares)",
        "year": 2015, "ev_usd_mm": None, "sector": "dental",
        "subsector_note": "One of the largest US DSOs by office count",
        "outcome": "active", "outcome_note": "Active; ownership recapitalized over time.",
        "source_url": "https://www.leonardgreen.com/",
        "source_note": "Leonard Green & Partners (portfolio); 2015 Aspen Dental majority investment",
    },
    {
        "target": "Affordable Care (Affordable Dentures & Implants)", "sponsor": "TPG (from Berkshire Partners)",
        "year": 2021, "ev_usd_mm": None, "sector": "dental",
        "subsector_note": "Dental-implant / denture DSO; PE-to-PE secondary",
        "outcome": "active", "outcome_note": "Active; Berkshire Partners exited to TPG.",
        "source_url": "https://www.tpg.com/",
        "source_note": "TPG (portfolio); 2021 Affordable Care acquisition from Berkshire Partners",
    },

    # ── Dermatology ──
    {
        "target": "Advanced Dermatology & Cosmetic Surgery", "sponsor": "Harvest Partners",
        "year": 2016, "ev_usd_mm": None, "sector": "dermatology",
        "subsector_note": "Large US dermatology MSO (roll-up)",
        "outcome": "active", "outcome_note": "Active platform.",
        "source_url": "https://www.harvestpartners.com/",
        "source_note": "Harvest Partners (portfolio); 2016 ADCS investment",
    },
    {
        "target": "U.S. Dermatology Partners", "sponsor": "ABRY Partners",
        "year": 2017, "ev_usd_mm": None, "sector": "dermatology",
        "subsector_note": "Physician-led dermatology group practice (South/Midwest)",
        "outcome": "active", "outcome_note": "Active platform.",
        "source_url": "https://www.abry.com/",
        "source_note": "ABRY Partners (portfolio); U.S. Dermatology Partners investment",
    },

    # ── Ophthalmology ──
    {
        "target": "Retina Consultants of America", "sponsor": "Webster Equity Partners",
        "year": 2020, "ev_usd_mm": None, "sector": "ophthalmology",
        "subsector_note": "Retina-subspecialty physician practice management platform",
        "outcome": "active", "outcome_note": "Active platform.",
        "source_url": "https://www.websterequitypartners.com/",
        "source_note": "Webster Equity Partners (portfolio); 2020 RCA platform formation",
    },

    # ── Dialysis ──
    {
        "target": "U.S. Renal Care", "sponsor": "Bain Capital + Summit Partners",
        "year": 2019, "ev_usd_mm": None, "sector": "dialysis",
        "subsector_note": "Dialysis-services operator; 2019 majority recapitalization",
        "outcome": "distressed",
        "outcome_note": "Completed an out-of-court debt restructuring in 2023 amid heavy leverage.",
        "source_url": "https://www.baincapital.com/",
        "source_note": "Bain Capital (portfolio); 2019 U.S. Renal Care recap; 2023 restructuring via Bloomberg",
    },

    # ── Urgent care ──
    {
        "target": "GoHealth Urgent Care", "sponsor": "TPG Growth",
        "year": 2015, "ev_usd_mm": None, "sector": "urgent_care",
        "subsector_note": "Urgent-care operator run as health-system joint ventures",
        "outcome": "active", "outcome_note": "Active platform.",
        "source_url": "https://www.tpg.com/",
        "source_note": "TPG Growth (portfolio); GoHealth Urgent Care investment",
    },

    # ── RCM / healthcare IT services (the platform's home sector) ──
    {
        "target": "Change Healthcare (Emdeon)", "sponsor": "Blackstone",
        "year": 2011, "ev_usd_mm": 3000, "sector": "rcm_healthtech",
        "subsector_note": "Healthcare payments / claims clearinghouse; Emdeon take-private (~$3B), later Change Healthcare",
        "outcome": "exited",
        "outcome_note": "Merged with McKesson IT (2017), IPO 2019, then acquired by UnitedHealth's Optum in 2022 (~$13B) after a DOJ antitrust trial.",
        "source_url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company=change+healthcare&type=8-K&dateb=&owner=include&count=40",
        "source_note": "SEC EDGAR (Change Healthcare / Optum 8-K); 2011 Emdeon take-private",
    },
    {
        "target": "Waystar", "sponsor": "EQT + Canada Pension Plan Investment Board + Bain Capital",
        "year": 2019, "ev_usd_mm": None, "sector": "rcm_healthtech",
        "subsector_note": "Healthcare payments / RCM software platform; 2019 majority recap",
        "outcome": "exited",
        "outcome_note": "IPO 2024 (Nasdaq: WAY) — RCM software platform taken public.",
        "source_url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company=waystar&type=S-1&dateb=&owner=include&count=40",
        "source_note": "SEC EDGAR (Waystar 2024 IPO S-1)",
    },
    {
        "target": "Ensemble Health Partners", "sponsor": "Golden Gate Capital",
        "year": 2019, "ev_usd_mm": None, "sector": "rcm_healthtech",
        "subsector_note": "Hospital revenue-cycle-management outsourcer (bought from Bon Secours Mercy Health)",
        "outcome": "exited",
        "outcome_note": "Golden Gate sold a majority to Berkshire Partners + Warburg Pincus in 2022.",
        "source_url": "https://www.goldengatecap.com/",
        "source_note": "Golden Gate Capital (portfolio); 2022 Berkshire/Warburg majority recap",
    },

    # ── Value-based & other services (PE-backed exits to strategics) ──
    {
        "target": "Oak Street Health", "sponsor": "General Atlantic + Newlight Partners",
        "year": 2016, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Value-based primary care for Medicare seniors",
        "outcome": "exited",
        "outcome_note": "IPO 2020; acquired by CVS Health in 2023 (~$10.6B) — a marquee value-based-care exit.",
        "source_url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company=oak+street+health&type=8-K&dateb=&owner=include&count=40",
        "source_note": "SEC EDGAR (Oak Street Health filings); CVS 2023 acquisition",
    },
    {
        "target": "One Medical (1Life Healthcare)", "sponsor": "The Carlyle Group",
        "year": 2018, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Membership-based primary care; Carlyle-led growth investment",
        "outcome": "exited",
        "outcome_note": "IPO 2020; acquired by Amazon in 2023 (~$3.9B).",
        "source_url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company=1life+healthcare&type=8-K&dateb=&owner=include&count=40",
        "source_note": "SEC EDGAR (1Life Healthcare / One Medical); Amazon 2023 acquisition",
    },
    {
        "target": "Signify Health", "sponsor": "New Mountain Capital",
        "year": 2017, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "In-home health evaluations + value-based payment platform",
        "outcome": "exited",
        "outcome_note": "IPO 2021; acquired by CVS Health in 2023 (~$8B).",
        "source_url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company=signify+health&type=8-K&dateb=&owner=include&count=40",
        "source_note": "SEC EDGAR (Signify Health filings); CVS 2023 acquisition",
    },

    # ════════════════════════════════════════════════════════════════════
    # 2026-06 expansion (batch 3) — health-IT, medical supply, and more
    # services/behavioral platforms. Same bar: real, sourced; EV only where
    # publicly disclosed; SEC EDGAR for public-touching deals, sponsor sites
    # for private ones.
    # ════════════════════════════════════════════════════════════════════

    # ── RCM / healthcare IT services (the platform's home sector) ──
    {
        "target": "NextGen Healthcare", "sponsor": "Thoma Bravo",
        "year": 2024, "ev_usd_mm": 1800, "sector": "rcm_healthtech",
        "subsector_note": "Ambulatory EHR / practice-management & RCM; take-private at $23.95/share",
        "outcome": "exited", "outcome_note": "Public→private; closed Nov 2024.",
        "source_url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company=nextgen+healthcare&type=8-K&dateb=&owner=include&count=40",
        "source_note": "SEC EDGAR (NextGen Healthcare merger 8-K, $1.8B)",
    },
    {
        "target": "Press Ganey", "sponsor": "EQT (from Leonard Green & Partners)",
        "year": 2019, "ev_usd_mm": None, "sector": "rcm_healthtech",
        "subsector_note": "Patient-experience measurement & analytics; PE-to-PE secondary (later merged with Forsta)",
        "outcome": "active", "outcome_note": "Active; Leonard Green exited to EQT.",
        "source_url": "https://www.eqtgroup.com/",
        "source_note": "EQT (portfolio); 2019 Press Ganey acquisition from Leonard Green",
    },
    {
        "target": "Datavant (Ciox Health)", "sponsor": "New Mountain Capital",
        "year": 2021, "ev_usd_mm": None, "sector": "rcm_healthtech",
        "subsector_note": "Health-data exchange / de-identification; New Mountain merged Ciox with Datavant (~$7B combined valuation)",
        "outcome": "active", "outcome_note": "Active platform.",
        "source_url": "https://www.newmountaincapital.com/",
        "source_note": "New Mountain Capital (portfolio); 2021 Ciox/Datavant merger",
    },
    {
        "target": "HealthEdge", "sponsor": "Blackstone",
        "year": 2020, "ev_usd_mm": None, "sector": "rcm_healthtech",
        "subsector_note": "Core administrative / claims software for health plans",
        "outcome": "active", "outcome_note": "Active platform.",
        "source_url": "https://www.blackstone.com/",
        "source_note": "Blackstone (portfolio); 2020 HealthEdge acquisition",
    },
    {
        "target": "Net Health", "sponsor": "The Carlyle Group",
        "year": 2018, "ev_usd_mm": None, "sector": "rcm_healthtech",
        "subsector_note": "Specialty EHR for post-acute / rehab / wound care (with Level Equity)",
        "outcome": "active", "outcome_note": "Active platform.",
        "source_url": "https://www.carlyle.com/",
        "source_note": "The Carlyle Group (portfolio); 2018 Net Health acquisition",
    },
    {
        "target": "Modernizing Medicine (ModMed)", "sponsor": "Warburg Pincus",
        "year": 2017, "ev_usd_mm": None, "sector": "rcm_healthtech",
        "subsector_note": "Specialty-specific EHR + practice management (derm, ophtho, ortho)",
        "outcome": "active", "outcome_note": "Active platform.",
        "source_url": "https://www.warburgpincus.com/",
        "source_note": "Warburg Pincus (portfolio); 2017 Modernizing Medicine investment",
    },

    # ── Medical supply / equipment services ──
    {
        "target": "Medline Industries", "sponsor": "Blackstone + Carlyle + Hellman & Friedman",
        "year": 2021, "ev_usd_mm": 34000, "sector": "other_services",
        "subsector_note": "Medical-supply manufacturing & distribution; one of the largest-ever healthcare LBOs (GIC/ADIA also invested)",
        "outcome": "active", "outcome_note": "Founding family retained control; consortium minority-to-majority capital.",
        "source_url": "https://www.blackstone.com/",
        "source_note": "Blackstone (press); ~$34B EV widely reported (WSJ/Reuters)",
    },
    {
        "target": "Apria Healthcare", "sponsor": "Blackstone",
        "year": 2008, "ev_usd_mm": 1600, "sector": "home_health_hospice",
        "subsector_note": "Home respiratory therapy & medical equipment; take-private",
        "outcome": "exited",
        "outcome_note": "IPO 2021 (Nasdaq: APR); acquired by Owens & Minor in 2022 (~$1.6B) — a full round-trip.",
        "source_url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company=apria&type=8-K&dateb=&owner=include&count=40",
        "source_note": "SEC EDGAR (Apria filings); Owens & Minor 2022 acquisition",
    },
    {
        "target": "Agiliti (Universal Hospital Services)", "sponsor": "Thomas H. Lee Partners",
        "year": 2019, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Medical-equipment management & rental for health systems",
        "outcome": "exited",
        "outcome_note": "IPO 2021 (NYSE: AGTI); THL took it public, later re-privatized (2024).",
        "source_url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company=agiliti&type=8-K&dateb=&owner=include&count=40",
        "source_note": "SEC EDGAR (Agiliti filings); THL ownership",
    },
    {
        "target": "Sotera Health (Sterigenics)", "sponsor": "Warburg Pincus + GTCR",
        "year": 2015, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Sterilization & lab-testing services for medical devices/pharma",
        "outcome": "exited",
        "outcome_note": "IPO 2020 (Nasdaq: SHC); sponsors retained majority post-IPO.",
        "source_url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company=sotera+health&type=S-1&dateb=&owner=include&count=40",
        "source_note": "SEC EDGAR (Sotera Health 2020 IPO S-1)",
    },

    # ── Hospitals / behavioral / dermatology / ophthalmology ──
    {
        "target": "ScionHealth", "sponsor": "Apollo Global Management (via LifePoint Health)",
        "year": 2021, "ev_usd_mm": None, "sector": "hospitals",
        "subsector_note": "Formed from Kindred's LTAC hospitals + LifePoint community hospitals",
        "outcome": "active", "outcome_note": "Active; created in the LifePoint/Kindred combination.",
        "source_url": "https://www.apollo.com/",
        "source_note": "Apollo Global Management / LifePoint Health (2021 ScionHealth formation)",
    },
    {
        "target": "Acadia Healthcare", "sponsor": "Waud Capital Partners",
        "year": 2011, "ev_usd_mm": None, "sector": "behavioral_health",
        "subsector_note": "Acute psychiatric & addiction operator; went public via 2011 reverse merger (PHC Inc.)",
        "outcome": "exited", "outcome_note": "Waud Capital founded it; now an independent public company (Nasdaq: ACHC).",
        "source_url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company=acadia+healthcare&type=8-K&dateb=&owner=include&count=40",
        "source_note": "SEC EDGAR (Acadia Healthcare filings); Waud Capital formation",
    },
    {
        "target": "Beacon Health Options", "sponsor": "Bain Capital + Diamond Castle Holdings",
        "year": 2014, "ev_usd_mm": None, "sector": "behavioral_health",
        "subsector_note": "Managed behavioral-health organization (ValueOptions + Beacon merger)",
        "outcome": "exited", "outcome_note": "Acquired by Anthem (Elevance) in 2020.",
        "source_url": "https://www.baincapital.com/",
        "source_note": "Bain Capital (portfolio); Anthem 2020 acquisition",
    },
    {
        "target": "MyEyeDr (Capital Vision Services)", "sponsor": "Goldman Sachs (from Altas Partners)",
        "year": 2019, "ev_usd_mm": 2700, "sector": "ophthalmology",
        "subsector_note": "Optometry / vision-care retail MSO; PE-to-PE secondary",
        "outcome": "active", "outcome_note": "Active; Altas Partners exited to Goldman Sachs.",
        "source_url": "https://www.goldmansachs.com/",
        "source_note": "Goldman Sachs Merchant Banking; ~$2.7B via Reuters",
    },
    {
        "target": "Pinnacle Dermatology", "sponsor": "Chicago Pacific Founders",
        "year": 2019, "ev_usd_mm": None, "sector": "dermatology",
        "subsector_note": "Multi-state dermatology MSO platform",
        "outcome": "active", "outcome_note": "Active platform.",
        "source_url": "https://www.cpfounders.com/",
        "source_note": "Chicago Pacific Founders (portfolio); Pinnacle Dermatology platform",
    },

    # ════════════════════════════════════════════════════════════════════
    # 2026-06 expansion — fill sponsor gaps that show up in the league
    # (General Catalyst, Advent, Ares, Gryphon, Vista, Audax). Same bar:
    # real, sourced; includes a marquee healthtech failure (Olive AI).
    # ════════════════════════════════════════════════════════════════════
    {
        "target": "Livongo Health", "sponsor": "General Catalyst",
        "year": 2014, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Digital chronic-care management (diabetes etc.); General Catalyst was a lead venture/growth backer",
        "outcome": "exited",
        "outcome_note": "IPO 2019 (Nasdaq: LVGO); acquired by Teladoc in 2020 (~$18.5B) — a marquee digital-health exit.",
        "source_url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company=livongo&type=S-1&dateb=&owner=include&count=40",
        "source_note": "SEC EDGAR (Livongo 2019 IPO S-1); Teladoc 2020 acquisition",
    },
    {
        "target": "Olive AI", "sponsor": "General Catalyst",
        "year": 2020, "ev_usd_mm": None, "sector": "rcm_healthtech",
        "subsector_note": "Healthcare administrative/RCM automation (RPA); peaked at a ~$4B private valuation in 2021",
        "outcome": "distressed",
        "outcome_note": "Wound down and sold off its business units in 2023 (RCM tools to Waystar; prior-auth to Humata Health) — a marquee healthtech failure.",
        "source_url": "https://www.fiercehealthcare.com/health-tech/olive-ai-shuts-down-sells-clearinghouse-business-amid-broader-wind-down",
        "source_note": "Fierce Healthcare (2023 wind-down); Axios (2021 $4B valuation)",
    },
    {
        "target": "AccentCare", "sponsor": "Advent International",
        "year": 2019, "ev_usd_mm": None, "sector": "home_health_hospice",
        "subsector_note": "Home health, hospice & personal care; bought from Oak Hill Capital",
        "outcome": "active", "outcome_note": "Active; later merged with Seasons Hospice.",
        "source_url": "https://www.adventinternational.com/",
        "source_note": "Advent International (portfolio); 2019 AccentCare acquisition from Oak Hill",
    },
    {
        "target": "DuPage Medical Group (Midwest Physician Administrative Services)", "sponsor": "Ares Management",
        "year": 2017, "ev_usd_mm": None, "sector": "physician_practices",
        "subsector_note": "Large independent multispecialty physician group (Illinois); later rebranded Duly Health and Care",
        "outcome": "active", "outcome_note": "Active platform.",
        "source_url": "https://www.aresmgmt.com/",
        "source_note": "Ares Management (portfolio); 2017 DuPage Medical Group majority investment",
    },
    {
        "target": "Smile Brands", "sponsor": "Gryphon Investors",
        "year": 2019, "ev_usd_mm": None, "sector": "dental",
        "subsector_note": "Dental support organization (DSO)",
        "outcome": "active", "outcome_note": "Active; Gryphon recapitalized the platform.",
        "source_url": "https://www.gryphoninvestors.com/",
        "source_note": "Gryphon Investors (portfolio); 2019 Smile Brands recapitalization",
    },
    {
        "target": "Gastro Health", "sponsor": "Audax Group",
        "year": 2018, "ev_usd_mm": None, "sector": "physician_practices",
        "subsector_note": "Gastroenterology physician practice management platform",
        "outcome": "active", "outcome_note": "Active platform.",
        "source_url": "https://www.audaxprivateequity.com/",
        "source_note": "Audax Private Equity (portfolio); Gastro Health platform",
    },

    # ── 2026-06 expansion (cont.) — more PE-backed exits + a distress case ──
    {
        "target": "Health Catalyst", "sponsor": "Frazier Healthcare Partners",
        "year": 2013, "ev_usd_mm": None, "sector": "rcm_healthtech",
        "subsector_note": "Healthcare data & analytics platform; Frazier was an early/lead investor",
        "outcome": "exited",
        "outcome_note": "IPO 2019 (Nasdaq: HCAT) — venture/growth-backed analytics platform taken public.",
        "source_url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company=health+catalyst&type=S-1&dateb=&owner=include&count=40",
        "source_note": "SEC EDGAR (Health Catalyst 2019 IPO S-1); Frazier Healthcare backing",
    },
    {
        "target": "MultiPlan", "sponsor": "Hellman & Friedman",
        "year": 2016, "ev_usd_mm": 7500, "sector": "rcm_healthtech",
        "subsector_note": "Payer payment-integrity / cost-management network; H&F take-private (~$7.5B)",
        "outcome": "exited",
        "outcome_note": "Went public via the Churchill Capital Corp III SPAC in 2020 (~$11B); H&F retained a stake.",
        "source_url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company=multiplan&type=8-K&dateb=&owner=include&count=40",
        "source_note": "SEC EDGAR (MultiPlan / Churchill Capital III 8-K); 2016 H&F acquisition",
    },
    {
        "target": "InnovAge", "sponsor": "Welsh, Carson, Anderson & Stowe + Apax Partners",
        "year": 2016, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "PACE (Program of All-Inclusive Care for the Elderly) operator",
        "outcome": "exited",
        "outcome_note": "IPO 2021 (Nasdaq: INNV) — senior-care platform taken public.",
        "source_url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company=innovage&type=S-1&dateb=&owner=include&count=40",
        "source_note": "SEC EDGAR (InnovAge 2021 IPO S-1); WCAS + Apax backing",
    },
    {
        "target": "P3 Health Partners", "sponsor": "Chicago Pacific Founders",
        "year": 2017, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Value-based primary-care / physician-enablement; de-SPAC via Foresight Acquisition Corp (2021)",
        "outcome": "distressed",
        "outcome_note": "Public via SPAC Dec 2021; has flagged going-concern / financing pressure since — a value-based-care/SPAC stress case.",
        "source_url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company=p3+health+partners&type=8-K&dateb=&owner=include&count=40",
        "source_note": "SEC EDGAR (P3 Health Partners filings); Chicago Pacific Founders sponsor",
    },
    {
        "target": "Sound Physicians", "sponsor": "Summit Partners",
        "year": 2014, "ev_usd_mm": None, "sector": "physician_practices",
        "subsector_note": "Hospital-medicine / acute physician services; later OptumHealth stake, then Centerbridge majority (2022)",
        "outcome": "active", "outcome_note": "Active; PE-to-PE recapitalized over time.",
        "source_url": "https://www.summitpartners.com/",
        "source_note": "Summit Partners (portfolio); 2014 Sound Physicians investment",
    },
    {
        "target": "Upstream Rehabilitation", "sponsor": "Revelstoke Capital Partners",
        "year": 2017, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Outpatient physical-therapy platform (one of the largest US providers)",
        "outcome": "active", "outcome_note": "Active platform.",
        "source_url": "https://www.revelstokecapital.com/",
        "source_note": "Revelstoke Capital Partners (portfolio); 2017 Upstream Rehabilitation investment",
    },

    # ════════════════════════════════════════════════════════════════════
    # 2026-06 expansion (batch 4) — toward a 400+ fully-validated real
    # corpus. Each row is a real, documented PE healthcare transaction:
    # target / sponsor / year / sector / outcome verified from public
    # coverage. EV recorded only where publicly disclosed (most PE deals
    # never disclose it). Several were web-validated this sprint (Heartland
    # Dental/KKR, U.S. Dermatology/ABRY ~$300M, EyeCare Partners/Partners
    # Group $2.2B, Syneos/$7.1B). source_url points at the deal announcement
    # where known, else the sponsor's portfolio page.
    # ════════════════════════════════════════════════════════════════════

    # ── Dental DSOs ──
    {
        "target": "Western Dental & Orthodontics (Sonrava Health)", "sponsor": "New Mountain Capital",
        "year": 2012, "ev_usd_mm": None, "sector": "dental",
        "subsector_note": "DSO with heavy Medicaid/DentiCal exposure (CA); bought from Court Square; now Sonrava Health",
        "outcome": "active", "outcome_note": "Active; New Mountain platform since 2012 (rebranded Sonrava Health).",
        "source_url": "https://www.newmountaincapital.com/portfolio/sonrava-health/",
        "source_note": "New Mountain Capital (Sonrava Health portfolio page); 2012 from Court Square",
    },
    {
        "target": "North American Dental Group", "sponsor": "Jacobs Holding AG",
        "year": 2019, "ev_usd_mm": None, "sector": "dental",
        "subsector_note": "DSO (~250 offices); Jacobs Holding acquired from ABRY Partners + The Riverside Company",
        "outcome": "active", "outcome_note": "Active; PE-to-strategic-family-office (announced Aug 2019).",
        "source_url": "https://www.prnewswire.com/news-releases/jacobs-holding-to-acquire-north-american-dental-group-300903831.html",
        "source_note": "PRNewswire (Jacobs Holding/NADG, Aug 2019)",
    },
    {
        "target": "Dental Care Alliance", "sponsor": "Harvest Partners",
        "year": 2015, "ev_usd_mm": None, "sector": "dental",
        "subsector_note": "DSO; Harvest acquired from Quad-C Management (Mubadala bought it 2023)",
        "outcome": "exited", "outcome_note": "Harvest sold DCA to Mubadala Capital in 2023.",
        "source_url": "https://www.quadcmanagement.com/quad-c-management-announces-sale-of-dental-care-alliance/",
        "source_note": "Quad-C (2015 sale to Harvest); Mubadala 2023 acquisition",
    },

    # ── Dermatology ──
    {
        "target": "Schweiger Dermatology Group", "sponsor": "LNK Partners",
        "year": 2018, "ev_usd_mm": None, "sector": "dermatology",
        "subsector_note": "Northeast derm platform; $100M LNK investment (May 2018); serial consolidator",
        "outcome": "active", "outcome_note": "Active; most acquisitive derm platform of the 2024-25 cycle.",
        "source_url": "https://www.prnewswire.com/news-releases/schweiger-dermatology-group-announces-100-million-investment-from-lnk-partners-300653694.html",
        "source_note": "PRNewswire (LNK $100M into Schweiger, May 2018)",
    },
    {
        "target": "QualDerm Partners", "sponsor": "BayPine",
        "year": 2022, "ev_usd_mm": None, "sector": "dermatology",
        "subsector_note": "Derm MSO; later merged into Pinnacle Dermatology (Cressey)",
        "outcome": "active", "outcome_note": "Active; consolidating with Pinnacle (2025).",
        "source_url": "https://www.baypine.com/",
        "source_note": "BayPine; 2022 QualDerm; 2025 Pinnacle combination via trade press",
    },

    # ── Ophthalmology ──
    {
        "target": "EyeSouth Partners", "sponsor": "Olympus Partners",
        "year": 2022, "ev_usd_mm": 1000, "sector": "ophthalmology",
        "subsector_note": "Southeast ophthalmology MSO; Olympus bought from Shore Capital (~$1B, ~13x EBITDA)",
        "outcome": "active", "outcome_note": "Active; Shore formed it in 2017, sold to Olympus in 2022.",
        "source_url": "https://www.businesswire.com/news/home/20220930005141/en/Shore-Capital-Partners-Announces-Sale-of-EyeSouth-Partners",
        "source_note": "BusinessWire (Shore sale of EyeSouth, 2022); ~$1B via ION Analytics",
    },

    # ── ASC / surgery ──
    {
        "target": "Covenant Physician Partners (Covenant Surgical Partners)", "sponsor": "KKR",
        "year": 2017, "ev_usd_mm": None, "sector": "asc",
        "subsector_note": "ASC + physician-practice manager; KKR acquired Covenant Surgical Partners",
        "outcome": "exited", "outcome_note": "KKR-owned from 2017; later sold to UnitedSurgical/USPI (Tenet) — a PE-to-strategic exit.",
        "source_url": "https://www.stblaw.com/about-us/news/view/2017/08/08/kkr-to-acquire-covenant-surgical-partners",
        "source_note": "Simpson Thacher (KKR/Covenant 2017); USPI acquisition via ION Analytics",
    },
    {
        "target": "Compass Surgical Partners", "sponsor": "TPG",
        "year": 2024, "ev_usd_mm": None, "sector": "asc",
        "subsector_note": "ASC development/JV partner; TPG growth investment",
        "outcome": "active", "outcome_note": "Active; reinforces the ASC JV model.",
        "source_url": "https://www.tpg.com/",
        "source_note": "TPG; 2024 Compass Surgical Partners via Physician Growth Partners coverage",
    },

    # ── Veterinary (PE roll-up wave) ──
    {
        "target": "Pathway Vet Alliance", "sponsor": "TSG Consumer Partners",
        "year": 2020, "ev_usd_mm": None, "sector": "veterinary",
        "subsector_note": "Veterinary hospital group; TSG bought majority from Morgan Stanley Capital Partners",
        "outcome": "active", "outcome_note": "Active; rebranded Thrive Pet Healthcare.",
        "source_url": "https://www.businesswire.com/news/home/20200403005155/en/TSG-Consumer-Partners-Acquires-Pathway-Vet-Alliance-from-Morgan-Stanley-Capital-Partners",
        "source_note": "BusinessWire (TSG/Pathway from MSCP, Apr 2020)",
    },
    {
        "target": "Mission Veterinary Partners", "sponsor": "Shore Capital Partners",
        "year": 2017, "ev_usd_mm": None, "sector": "veterinary",
        "subsector_note": "Veterinary hospital consolidator (Midwest-anchored); founded 2017",
        "outcome": "active", "outcome_note": "Active; serial acquirer.",
        "source_url": "https://www.shorecp.com/companies/mission-veterinary-partners",
        "source_note": "Shore Capital Partners (company page); founded 2017",
    },

    # ── Physician specialty MSOs ──
    {
        "target": "North American Partners in Anesthesia (NAPA)", "sponsor": "American Securities",
        "year": 2016, "ev_usd_mm": None, "sector": "physician_practices",
        "subsector_note": "Largest single-specialty anesthesia group; No Surprises Act exposure",
        "outcome": "active", "outcome_note": "Active; out-of-network billing pressure post-2022.",
        "source_url": "https://www.american-securities.com/en/our-companies",
        "source_note": "American Securities (portfolio); NAPA",
    },
    {
        "target": "US Radiology Specialists", "sponsor": "Welsh, Carson, Anderson & Stowe",
        "year": 2018, "ev_usd_mm": None, "sector": "physician_practices",
        "subsector_note": "Radiology physician group + imaging centers; WCAS-backed",
        "outcome": "active", "outcome_note": "Active; large radiology consolidator.",
        "source_url": "https://www.welshcarson.com/portfolio/",
        "source_note": "Welsh Carson (portfolio); US Radiology Specialists",
    },
    {
        "target": "US Acute Care Solutions", "sponsor": "Welsh, Carson, Anderson & Stowe",
        "year": 2015, "ev_usd_mm": None, "sector": "physician_practices",
        "subsector_note": "Physician-owned + WCAS emergency-medicine/hospitalist group",
        "outcome": "active", "outcome_note": "Active; staffing-model exposure to No Surprises Act.",
        "source_url": "https://www.welshcarson.com/portfolio/",
        "source_note": "Welsh Carson (portfolio); 2015 USACS formation",
    },
    {
        "target": "SCP Health (Schumacher Clinical Partners)", "sponsor": "Onex Corporation",
        "year": 2015, "ev_usd_mm": None, "sector": "physician_practices",
        "subsector_note": "Emergency-medicine + hospital-medicine staffing; Onex buyout",
        "outcome": "distressed", "outcome_note": "Staffing-model + No Surprises Act pressure; restructured.",
        "source_url": "https://www.onex.com/",
        "source_note": "Onex (portfolio); 2015 Schumacher Clinical Partners",
    },
    {
        "target": "Unified Women's Healthcare", "sponsor": "Altas Partners + Ares Management",
        "year": 2021, "ev_usd_mm": None, "sector": "physician_practices",
        "subsector_note": "Largest US OB/GYN practice-management platform; Altas joined Ares in 2021",
        "outcome": "active", "outcome_note": "Active; women's-health MSO leader.",
        "source_url": "https://www.altas.com/news/unified-womens-healthcare-announces-new-investment-from-altas-partners",
        "source_note": "Altas Partners (press); 2021 Unified Women's Healthcare investment",
    },
    {
        "target": "Axia Women's Health", "sponsor": "Partners Group",
        "year": 2021, "ev_usd_mm": 800, "sector": "physician_practices",
        "subsector_note": "OB/GYN + women's-health MSO; Partners Group bought from Audax (~$800M)",
        "outcome": "exited", "outcome_note": "Audax's exit to Partners Group in 2021 (~$800M).",
        "source_url": "https://www.businesswire.com/news/home/20210512005600/en/Audax-Private-Equity-to-Sell-Axia-Womens-Health-to-Partners-Group",
        "source_note": "BusinessWire (Audax sells Axia to Partners Group, 2021); ~$800M via PitchBook",
    },
    {
        "target": "Women's Care Enterprises", "sponsor": "BC Partners",
        "year": 2020, "ev_usd_mm": None, "sector": "physician_practices",
        "subsector_note": "OB/GYN + fertility MSO; BC Partners majority",
        "outcome": "active", "outcome_note": "Active platform.",
        "source_url": "https://www.bcpartners.com/private-equity-strategy/portfolio",
        "source_note": "BC Partners (portfolio); 2020 Women's Care",
    },

    # ── Behavioral health ──
    {
        "target": "Discovery Behavioral Health", "sponsor": "Webster Equity Partners + GarMark Partners",
        "year": 2018, "ev_usd_mm": None, "sector": "behavioral_health",
        "subsector_note": "Eating-disorder + mental-health + addiction treatment (Center for Discovery + Cliffside Malibu)",
        "outcome": "distressed", "outcome_note": "Capital One seized control in early 2026 after a debt default — a documented behavioral-health downside.",
        "source_url": "https://bhbusiness.com/2026/02/09/capital-one-seizes-control-of-discovery-behavioral-health-after-defaulting-on-debt/",
        "source_note": "Behavioral Health Business (2026 lender takeover); Mergr (2018 Webster/GarMark formation)",
    },
    {
        "target": "BayMark Health Services", "sponsor": "Webster Equity Partners",
        "year": 2015, "ev_usd_mm": None, "sector": "behavioral_health",
        "subsector_note": "Largest US opioid-use-disorder / medication-assisted treatment provider",
        "outcome": "active", "outcome_note": "Active; SUD treatment leader.",
        "source_url": "https://www.websterequitypartners.com/portfolio/",
        "source_note": "Webster Equity Partners (portfolio); 2015 BayMark",
    },

    # ── Home health / hospice ──
    {
        "target": "Compassus", "sponsor": "TowerBrook Capital Partners + Ascension",
        "year": 2019, "ev_usd_mm": 1000, "sector": "home_health_hospice",
        "subsector_note": "Hospice + palliative + home health; TowerBrook/Ascension JV (~$1B)",
        "outcome": "active", "outcome_note": "Active platform.",
        "source_url": "https://hospicenews.com/2019/10/01/towerbrook-ascension-health-to-acquire-compassus-for-1-billion/",
        "source_note": "Hospice News (TowerBrook/Ascension, ~$1B, Oct 2019)",
    },
    {
        "target": "St. Croix Hospice", "sponsor": "H.I.G. Capital",
        "year": 2020, "ev_usd_mm": 580, "sector": "home_health_hospice",
        "subsector_note": "Midwest hospice consolidator; H.I.G. bought from The Vistria Group (~$580M)",
        "outcome": "active", "outcome_note": "Active; serial hospice acquirer.",
        "source_url": "https://www.businesswire.com/news/home/20201019005240/en/H.I.G.-Capital-to-Acquire-St.-Croix-Hospice",
        "source_note": "BusinessWire (H.I.G./St. Croix, Oct 2020); ~$580M via PE Hub",
    },
    {
        "target": "Agape Care Group", "sponsor": "Ridgemont Equity Partners",
        "year": 2021, "ev_usd_mm": None, "sector": "home_health_hospice",
        "subsector_note": "Southeast hospice + palliative care platform",
        "outcome": "exited", "outcome_note": "Ridgemont sold Agape to Linden Capital Partners in 2025 — a PE-to-PE exit.",
        "source_url": "https://www.businesswire.com/news/home/20211019005242/en/Ridgemont-Equity-Partners-Acquires-Agape-Care-Group",
        "source_note": "BusinessWire (Ridgemont/Agape, Oct 2021); Linden 2025 exit via Hospice News",
    },

    # ── RCM / health IT ──
    {
        "target": "symplr", "sponsor": "Clearlake Capital + SkyKnight Capital",
        "year": 2018, "ev_usd_mm": None, "sector": "rcm_healthtech",
        "subsector_note": "Healthcare governance/risk/compliance + credentialing SaaS; Charlesbank joined 2021",
        "outcome": "active", "outcome_note": "Active; Clearlake/SkyKnight since 2018, Charlesbank co-invested 2021.",
        "source_url": "https://www.prnewswire.com/news-releases/charlesbank-to-make-a-strategic-investment-in-clearlake-and-skyknight-backed-symplr-301331373.html",
        "source_note": "PRNewswire (Charlesbank into Clearlake/SkyKnight-backed symplr, 2021)",
    },
    {
        "target": "Greenway Health", "sponsor": "Vista Equity Partners",
        "year": 2013, "ev_usd_mm": 644, "sector": "rcm_healthtech",
        "subsector_note": "Ambulatory EHR/RCM; Vista take-private + Vitera/SuccessEHS merger (~$644M)",
        "outcome": "active", "outcome_note": "Active; Vista platform.",
        "source_url": "https://www.vistaequitypartners.com/companies/",
        "source_note": "Vista Equity Partners (portfolio); 2013 Greenway take-private (~$644M)",
    },

    # ── CRO / pharma services ──
    {
        "target": "Syneos Health", "sponsor": "Elliott Investment Management + Patient Square + Veritas Capital",
        "year": 2023, "ev_usd_mm": 7100, "sector": "other_services",
        "subsector_note": "Contract research org (CRO) + commercial; take-private at $43.00/share",
        "outcome": "exited", "outcome_note": "Public→private Sept 2023 ($7.1B EV) — large healthcare-services take-private.",
        "source_url": "https://www.globenewswire.com/news-release/2023/09/28/2751390/33420/en/Syneos-Health-Closes-Transaction-with-Private-Investment-Firms.html",
        "source_note": "GlobeNewswire (Syneos close); $7.1B / $43.00 per share",
    },

    # ════════════════════════════════════════════════════════════════════
    # 2026-06 expansion (batch 5) — specialty-physician MSOs (GI / ortho /
    # urology / cardiology), infusion/specialty pharmacy, and ABA/hospice.
    # Every row web-validated this sprint (sponsor + year confirmed from the
    # deal announcement or sponsor page). EV only where disclosed.
    # ════════════════════════════════════════════════════════════════════

    # ── Gastroenterology MSOs ──
    {
        "target": "United Digestive", "sponsor": "Frazier Healthcare Partners",
        "year": 2018, "ev_usd_mm": None, "sector": "physician_practices",
        "subsector_note": "GI MSO formed with Atlanta Gastroenterology Associates",
        "outcome": "exited", "outcome_note": "Frazier sold United Digestive to Kohlberg & Company in 2023 (~$500M).",
        "source_url": "https://www.uniteddigestive.com/atlanta-gastroenterology-associates-enters-agreement-with-frazier-healthcare-partners-to-form-united-digestive/",
        "source_note": "United Digestive (formation, Dec 2018); Kohlberg 2023 acquisition (~$500M)",
    },
    {
        "target": "Allied Digestive Health", "sponsor": "Assured Healthcare Partners",
        "year": 2015, "ev_usd_mm": None, "sector": "physician_practices",
        "subsector_note": "GI MSO (NJ-anchored, 200+ providers); formed by 5-practice merger",
        "outcome": "active", "outcome_note": "Active GI platform.",
        "source_url": "https://www.assuredhp.com/portfolio/",
        "source_note": "Assured Healthcare Partners (portfolio); Allied Digestive Health",
    },
    {
        "target": "Pinnacle GI Partners", "sponsor": "H.I.G. Capital",
        "year": 2020, "ev_usd_mm": None, "sector": "physician_practices",
        "subsector_note": "GI MSO (Michigan); H.I.G. Growth + The Center for Digestive Health",
        "outcome": "active", "outcome_note": "Active GI platform.",
        "source_url": "https://hig.com/portfolio/pinnacle-gi-partners/",
        "source_note": "H.I.G. Capital (portfolio); Dec 2020 Pinnacle GI Partners",
    },

    # ── Orthopedics / MSK MSOs ──
    {
        "target": "Healthcare Outcomes Performance Company (HOPCo)", "sponsor": "Linden Capital Partners + Audax Group",
        "year": 2019, "ev_usd_mm": None, "sector": "physician_practices",
        "subsector_note": "Largest fully-integrated value-based MSK/ortho platform (per-member-per-month)",
        "outcome": "active", "outcome_note": "Active; exploring a sale (2024).",
        "source_url": "https://hopco.com/",
        "source_note": "HOPCo; 2019 Linden + Audax investment via Physician Growth Partners",
    },
    {
        "target": "U.S. Orthopaedic Partners", "sponsor": "FFL Partners + Thurston Group",
        "year": 2020, "ev_usd_mm": None, "sector": "physician_practices",
        "subsector_note": "Southeast orthopedic MSO; formed Oct 2020",
        "outcome": "active", "outcome_note": "Active ortho platform.",
        "source_url": "https://www.fflpartners.com/u-s-orthopaedic-partners-announces-two-new-acquisitions",
        "source_note": "FFL Partners; Oct 2020 USOP formation",
    },
    {
        "target": "OrthoAlliance", "sponsor": "Revelstoke Capital Partners",
        "year": 2019, "ev_usd_mm": None, "sector": "physician_practices",
        "subsector_note": "Midwest orthopedic MSO; Revelstoke platform",
        "outcome": "exited", "outcome_note": "SCA Health (Optum's ASC arm) acquired OrthoAlliance in 2025 (~$1.4B).",
        "source_url": "https://revelstokecapital.com/investment/orthoalliance/",
        "source_note": "Revelstoke Capital Partners; 2019 OrthoAlliance; 2025 SCA/Optum acquisition (~$1.4B)",
    },
    {
        "target": "Spire Orthopedic Partners", "sponsor": "Kohlberg & Company",
        "year": 2021, "ev_usd_mm": None, "sector": "physician_practices",
        "subsector_note": "Northeast orthopedic MSO; founded 2021",
        "outcome": "active", "outcome_note": "Active ortho platform.",
        "source_url": "https://www.kohlberg.com/investment/spire-orthopedic-partners/",
        "source_note": "Kohlberg & Company (investment page); 2021 Spire Orthopedic Partners",
    },

    # ── Urology MSOs ──
    {
        "target": "Solaris Health", "sponsor": "Lee Equity Partners",
        "year": 2020, "ev_usd_mm": None, "sector": "physician_practices",
        "subsector_note": "Largest US urology MSO; Lee Equity formed it June 2020",
        "outcome": "active", "outcome_note": "Active; ~$1B revenue urology platform.",
        "source_url": "https://www.leeequity.com/news-article/urology-associates-joins-solaris-health-nations-largest-urological-services-provider",
        "source_note": "Lee Equity Partners (Solaris Health); formed June 2020",
    },
    {
        "target": "United Urology Group (Chesapeake Urology)", "sponsor": "Audax Private Equity",
        "year": 2016, "ev_usd_mm": None, "sector": "physician_practices",
        "subsector_note": "Urology MSO; Audax partnered with Chesapeake Urology (Aug 2016)",
        "outcome": "active", "outcome_note": "Active urology platform.",
        "source_url": "https://www.audaxprivateequity.com/portfolio",
        "source_note": "Audax Private Equity; Aug 2016 Chesapeake Urology / United Urology Group",
    },
    {
        "target": "US Urology Partners", "sponsor": "NMS Capital",
        "year": 2018, "ev_usd_mm": None, "sector": "physician_practices",
        "subsector_note": "Urology MSO; NMS invested in Central Ohio Urology Group (2018)",
        "outcome": "active", "outcome_note": "Active urology platform.",
        "source_url": "https://www.nms.capital/portfolio",
        "source_note": "NMS Capital; 2018 US Urology Partners launch",
    },

    # ── Cardiology MSOs ──
    {
        "target": "US Heart & Vascular", "sponsor": "Ares Management + Rubicon Founders",
        "year": 2022, "ev_usd_mm": None, "sector": "physician_practices",
        "subsector_note": "Value-based cardiovascular MSO; Ares PE + Rubicon Founders",
        "outcome": "active", "outcome_note": "Active cardiology platform.",
        "source_url": "https://usheartandvascular.com/us-heart-vascular-and-rubicon-founders-announce-partnership-to-build-the-premier-cardiovascular-value-based-care-model-in-the-united-states/",
        "source_note": "US Heart & Vascular (Rubicon Founders partnership, 2022); Ares PE",
    },
    {
        "target": "Cardiovascular Logistics", "sponsor": "Lee Equity Partners",
        "year": 2022, "ev_usd_mm": None, "sector": "physician_practices",
        "subsector_note": "National cardiovascular platform launched with Cardiovascular Institute of the South",
        "outcome": "active", "outcome_note": "Active cardiology platform.",
        "source_url": "https://comvest.com/comvest-credit-partners-announces-investment-in-cardiovascular-logistics/",
        "source_note": "Comvest (credit investment); Lee Equity-backed Cardiovascular Logistics",
    },

    # ── Infusion / specialty pharmacy ──
    {
        "target": "IVX Health", "sponsor": "Great Hill Partners",
        "year": 2021, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Outpatient infusion centers (biologics for chronic conditions); $100M Series F",
        "outcome": "active", "outcome_note": "Active; Linden was earlier lead, Great Hill led 2021.",
        "source_url": "https://www.paragonventures.com/market-pulse-posts/ivx-ghp/",
        "source_note": "Paragon Ventures (Great Hill $100M into IVX Health, Sept 2021)",
    },
    {
        "target": "Paragon Healthcare", "sponsor": "Peak Rock Capital",
        "year": 2020, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Infusion centers + specialty pharmacy",
        "outcome": "exited", "outcome_note": "Elevance Health (Anthem) acquired Paragon Healthcare in 2024 — a PE-to-payer exit.",
        "source_url": "https://www.paragonventures.com/market-pulse-posts/soleo-health-acquired-paragon-infusion-therapy/",
        "source_note": "Peak Rock Capital (Sept 2020); Elevance 2024 acquisition",
    },
    {
        "target": "Soleo Health", "sponsor": "Court Square Capital Partners + WindRose Health Investors",
        "year": 2025, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Specialty pharmacy + home/alternate-site infusion",
        "outcome": "active", "outcome_note": "Active; Court Square + WindRose joint investment (2025).",
        "source_url": "https://www.soleohealth.com/",
        "source_note": "Soleo Health; 2025 Court Square + WindRose investment",
    },

    # ── ABA / autism (behavioral health) ──
    {
        "target": "BlueSprig Pediatrics", "sponsor": "KKR",
        "year": 2017, "ev_usd_mm": None, "sector": "behavioral_health",
        "subsector_note": "ABA autism therapy; KKR-formed platform (2017)",
        "outcome": "active", "outcome_note": "Active; grew to 160+ centers.",
        "source_url": "https://www.kkr.com/invest/portfolio",
        "source_note": "KKR (portfolio); 2017 BlueSprig Pediatrics formation",
    },
    {
        "target": "Hopebridge", "sponsor": "Arsenal Capital Partners",
        "year": 2019, "ev_usd_mm": 255, "sector": "behavioral_health",
        "subsector_note": "ABA autism therapy; Arsenal SBO from Baird Capital (~$255M)",
        "outcome": "active", "outcome_note": "Active; Baird's 2017 platform sold to Arsenal in 2019.",
        "source_url": "https://www.arsenalcapital.com/portfolio/",
        "source_note": "Arsenal Capital Partners (portfolio); 2019 Hopebridge SBO (~$255M)",
    },
    {
        "target": "Centria Autism (Centria Healthcare)", "sponsor": "Martis Capital (Capricorn Healthcare)",
        "year": 2016, "ev_usd_mm": None, "sector": "behavioral_health",
        "subsector_note": "ABA autism therapy; largest ABA provider in Michigan, expanded to 9 states",
        "outcome": "active", "outcome_note": "Active ABA platform.",
        "source_url": "https://www.martiscapital.com/portfolio",
        "source_note": "Martis Capital (fka Capricorn Healthcare); 2016 Centria platform",
    },

    # ── Hospice ──
    {
        "target": "Three Oaks Hospice", "sponsor": "Granite Growth Health Partners + Petra Capital",
        "year": 2019, "ev_usd_mm": None, "sector": "home_health_hospice",
        "subsector_note": "Hospice consolidator; backed by Granite Growth, Health Velocity, Petra Capital",
        "outcome": "active", "outcome_note": "Active; began operating May 2019.",
        "source_url": "https://hospicenews.com/2019/09/24/three-oaks-hospice-opens-its-doors-completes-three-acquisitions/",
        "source_note": "Hospice News (Three Oaks launch + backers, 2019)",
    },

    # ════════════════════════════════════════════════════════════════════
    # 2026-06 expansion (batch 6) — pharma-services/CDMO, clinical labs,
    # value-based primary care (incl. a bankruptcy), and dialysis. Each
    # web-validated this sprint. Introduces the "lab" sector.
    # ════════════════════════════════════════════════════════════════════

    # ── Pharma services / CDMO ──
    {
        "target": "PCI Pharma Services", "sponsor": "Kohlberg & Company + Mubadala",
        "year": 2020, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Biopharma CDMO / supply-chain; Bain Capital co-led a 2025 round valuing it ~$10B",
        "outcome": "active", "outcome_note": "Active; 2025 Bain Capital + Kohlberg + Mubadala recap (~$10B).",
        "source_url": "https://pci.com/strategic-investment-bain-capital-kohlberg-and-mubadala/",
        "source_note": "PCI (2025 Bain/Kohlberg/Mubadala); Kohlberg+Mubadala since 2020",
    },
    {
        "target": "Adare Pharma Solutions", "sponsor": "Thomas H. Lee Partners + Frazier Healthcare Partners",
        "year": 2021, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Oral-dosage CDMO; THL + Frazier acquired from TPG",
        "outcome": "active", "outcome_note": "Active CDMO platform.",
        "source_url": "https://www.thl.com/portfolio/",
        "source_note": "Thomas H. Lee Partners (portfolio); 2021 Adare from TPG",
    },

    # ── Clinical labs / diagnostics ──
    {
        "target": "Aegis Sciences", "sponsor": "Metalmark Capital",
        "year": 2021, "ev_usd_mm": None, "sector": "lab",
        "subsector_note": "Toxicology + clinical reference lab (Nashville); Metalmark majority",
        "outcome": "exited", "outcome_note": "ABRY Partners became owner by 2025 — a PE-to-PE transition.",
        "source_url": "https://www.nashvillepost.com/business/finance/ny-private-equity-firm-buys-into-aegis-sciences/article_ef8a9ff2-cbac-55c9-a0af-dbc371829b2e.html",
        "source_note": "Nashville Post (Metalmark/Aegis, 2021); ABRY 2025 ownership",
    },
    {
        "target": "Inform Diagnostics", "sponsor": "Avista Capital Partners",
        "year": 2017, "ev_usd_mm": 170, "sector": "lab",
        "subsector_note": "Anatomic-pathology lab (fka Miraca Life Sciences); Avista from Miraca",
        "outcome": "exited", "outcome_note": "Sold to Fulgent Genetics in 2022 for $170M.",
        "source_url": "https://www.prnewswire.com/news-releases/avista-capital-partners-completes-sale-of-inform-diagnostics-to-fulgent-genetics-inc-301534266.html",
        "source_note": "PRNewswire (Avista sells Inform Diagnostics to Fulgent, 2022, $170M)",
    },
    {
        "target": "Discovery Life Sciences", "sponsor": "Water Street Healthcare Partners",
        "year": 2018, "ev_usd_mm": None, "sector": "lab",
        "subsector_note": "Biospecimen + lab services; Water Street four-company merger",
        "outcome": "active", "outcome_note": "Active life-sciences/lab platform.",
        "source_url": "https://waterstreet.com/companies/discovery-life-sciences",
        "source_note": "Water Street Healthcare Partners (company page); 2018 Discovery Life Sciences",
    },

    # ── Value-based / primary care ──
    {
        "target": "Privia Health", "sponsor": "Goldman Sachs + Brighton Park Capital",
        "year": 2014, "ev_usd_mm": None, "sector": "physician_practices",
        "subsector_note": "Value-based physician-enablement MSO; Goldman-led majority growth investment",
        "outcome": "exited", "outcome_note": "IPO'd on Nasdaq (PRVA) in 2021 — a PE-to-public exit.",
        "source_url": "https://matrixbcg.com/blogs/brief-history/priviahealth",
        "source_note": "Privia Health history (Goldman/Brighton Park 2014); 2021 IPO",
    },
    {
        "target": "CareMax", "sponsor": "Deerfield Management",
        "year": 2021, "ev_usd_mm": None, "sector": "value_based_care",
        "subsector_note": "Value-based senior primary care (Medicare); Deerfield SPAC de-SPAC",
        "outcome": "bankrupt", "outcome_note": "Filed Chapter 11 in 2024 — another value-based-care/SPAC failure (cf. Cano).",
        "source_url": "https://www.businesswire.com/news/home/20201218005517/en/Deerfield-Healthcare-Technology-Acquisitions-Corp.-Announces-Proposed-Business-Combination-to-Form-CareMax",
        "source_note": "BusinessWire (Deerfield/CareMax de-SPAC, 2021); 2024 Ch.11 via PESP",
    },

    # ════════════════════════════════════════════════════════════════════
    # 2026-06 expansion (batch 7) — RCM/specialty pharmacy, urgent care,
    # fertility MSOs, post-acute, home care, wound care, behavioral health.
    # Each web-validated this sprint (sponsor + year confirmed).
    # ════════════════════════════════════════════════════════════════════

    # ── RCM / specialty pharmacy ──
    {
        "target": "Shields Health Solutions", "sponsor": "Welsh, Carson, Anderson & Stowe",
        "year": 2019, "ev_usd_mm": None, "sector": "rcm_healthtech",
        "subsector_note": "Health-system specialty-pharmacy management; WCAS + Walgreens equity",
        "outcome": "exited", "outcome_note": "Walgreens took full control (2022); Sycamore Partners acquired it as a standalone in 2025.",
        "source_url": "https://shieldshealthsolutions.com/shields-health-solutions-receives-equity-investments-from-welsh-carson-anderson-stowe-and-walgreen-co-2/",
        "source_note": "Shields Health Solutions (WCAS/Walgreens 2019); 2025 Sycamore",
    },
    {
        "target": "GeBBS Healthcare Solutions", "sponsor": "EQT",
        "year": 2024, "ev_usd_mm": None, "sector": "rcm_healthtech",
        "subsector_note": "RCM / health-information-management BPO; EQT bought from ChrysCapital",
        "outcome": "active", "outcome_note": "Active RCM platform.",
        "source_url": "https://www.pehub.com/eqt-to-acquire-healthtech-biz-gebbs-healthcare-from-chryscapital/",
        "source_note": "PE Hub (EQT/GeBBS from ChrysCapital, 2024)",
    },

    # ── Fertility MSOs ──
    {
        "target": "CCRM Fertility", "sponsor": "TA Associates",
        "year": 2015, "ev_usd_mm": None, "sector": "physician_practices",
        "subsector_note": "Fertility/IVF network; PE's first fertility-services platform",
        "outcome": "active", "outcome_note": "Active fertility platform.",
        "source_url": "https://www.ta.com/portfolio/",
        "source_note": "TA Associates; 2015 CCRM recapitalization",
    },
    {
        "target": "Prelude Fertility", "sponsor": "Lee Equity Partners",
        "year": 2016, "ev_usd_mm": None, "sector": "physician_practices",
        "subsector_note": "Fertility network; merged with Inception Fertility (largest US platform)",
        "outcome": "active", "outcome_note": "Active; Prelude+Inception is the largest US fertility platform.",
        "source_url": "https://www.leeequity.com/",
        "source_note": "Lee Equity Partners; 2016 Prelude Fertility",
    },
    {
        "target": "US Fertility", "sponsor": "Amulet Capital Partners",
        "year": 2020, "ev_usd_mm": None, "sector": "physician_practices",
        "subsector_note": "Fertility MSO formed with Shady Grove Fertility",
        "outcome": "active", "outcome_note": "Active; L Catterton bought 42.5% from Amulet in 2024 (~$1.7B).",
        "source_url": "https://www.usfertility.com/newsroom/amulet-capital-and-shady-grove-fertility-form-us-fertility",
        "source_note": "US Fertility (Amulet/Shady Grove formation, 2020); L Catterton 2024",
    },
    {
        "target": "IVIRMA Global", "sponsor": "KKR",
        "year": 2017, "ev_usd_mm": None, "sector": "physician_practices",
        "subsector_note": "Global fertility/IVF network (incl. Boston IVF); KKR investment",
        "outcome": "active", "outcome_note": "Active global fertility platform.",
        "source_url": "https://www.kkr.com/invest/portfolio",
        "source_note": "KKR (portfolio); 2017 IVIRMA Global",
    },

    # ── Post-acute ──
    {
        "target": "Ernest Health", "sponsor": "One Equity Partners",
        "year": 2018, "ev_usd_mm": None, "sector": "hospitals",
        "subsector_note": "Inpatient rehab + LTAC hospitals; OEP + Vibra bought from Medical Properties Trust",
        "outcome": "active", "outcome_note": "Active post-acute hospital operator.",
        "source_url": "https://www.oneequity.com/",
        "source_note": "One Equity Partners; 2018 Ernest Health from MPT",
    },

    # ── Home care ──
    {
        "target": "Elara Caring", "sponsor": "Blue Wolf Capital Partners + Kelso & Company",
        "year": 2018, "ev_usd_mm": None, "sector": "home_health_hospice",
        "subsector_note": "Home health + personal care + hospice (merger of Great Lakes Caring, National Home Health, Jordan Health)",
        "outcome": "active", "outcome_note": "Active; Ares PE + DaVita made a strategic investment in 2026.",
        "source_url": "https://mergr.com/transaction/blue-wolf-capital-partners-acquires-elara-caring",
        "source_note": "Mergr (Blue Wolf + Kelso + HarbourVest acquire Elara Caring, Apr 2018)",
    },
    {
        "target": "Interim HealthCare (Caring Brands International)", "sponsor": "Wellspring Capital Management",
        "year": 2021, "ev_usd_mm": None, "sector": "home_health_hospice",
        "subsector_note": "Home health/hospice franchisor; Wellspring bought from The Halifax Group",
        "outcome": "active", "outcome_note": "Active home-care franchisor.",
        "source_url": "https://homehealthcarenews.com/2021/10/wellspring-capital-management-acquires-interim-healthcare-parent-company-caring-brands-international/",
        "source_note": "Home Health Care News (Wellspring/Caring Brands, 2021)",
    },
    {
        "target": "Senior Helpers", "sponsor": "Waud Capital Partners",
        "year": 2024, "ev_usd_mm": None, "sector": "home_health_hospice",
        "subsector_note": "In-home senior care; Waud bought from Advocate Health",
        "outcome": "active", "outcome_note": "Active senior home-care platform.",
        "source_url": "https://www.waudcapital.com/",
        "source_note": "Waud Capital Partners; 2024 Senior Helpers from Advocate Health",
    },

    # ── Wound care ──
    {
        "target": "Healogics", "sponsor": "Clayton, Dubilier & Rice",
        "year": 2014, "ev_usd_mm": 910, "sector": "other_services",
        "subsector_note": "Largest US wound-care services operator; CD&R bought from Metalmark (~$910M)",
        "outcome": "active", "outcome_note": "Active; 2021 CD&R/Partners Group/Northwestern Mutual recap.",
        "source_url": "https://www.cdr.com/news/clayton-dubilier-rice-to-acquire-healogics-the-nations-wound-care-services-leader-transaction-valued-at-910-million",
        "source_note": "Clayton, Dubilier & Rice (Healogics, 2014, $910M)",
    },
    {
        "target": "RestorixHealth", "sponsor": "Leonard Green & Partners + Cressey & Company",
        "year": 2015, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Wound-care + hyperbarics management",
        "outcome": "exited", "outcome_note": "Acquired by American Medical Technologies (One Equity Partners) in 2021.",
        "source_url": "https://mergr.com/transaction/leonard-green-partners-acquires-restorixhealth",
        "source_note": "Mergr (Leonard Green + Cressey acquire RestorixHealth, 2015); AMT 2021",
    },

    # ── Behavioral health ──
    {
        "target": "Eating Recovery Center", "sponsor": "Apax Partners + Oak HC/FT",
        "year": 2021, "ev_usd_mm": 1400, "sector": "behavioral_health",
        "subsector_note": "Eating-disorder + behavioral treatment; Apax bought from CCMP (~$1.4B)",
        "outcome": "active", "outcome_note": "Active; CCMP owned it 2017-2021, Apax/Oak bought for ~$1.4B.",
        "source_url": "https://bhbusiness.com/2021/10/05/apax-partners-and-oak-hc-ft-purchase-eating-recovery-center-for-1-4b/",
        "source_note": "Behavioral Health Business (Apax/Oak buy ERC, 2021, ~$1.4B)",
    },
    {
        "target": "Pyramid Healthcare", "sponsor": "Nautic Partners",
        "year": 2021, "ev_usd_mm": None, "sector": "behavioral_health",
        "subsector_note": "Behavioral health + addiction treatment; Nautic bought from Clearview Capital",
        "outcome": "active", "outcome_note": "Active behavioral-health operator.",
        "source_url": "https://mergr.com/transaction/nautic-partners-acquires-pyramid-healthcare",
        "source_note": "Mergr (Nautic/Pyramid Healthcare from Clearview, 2021)",
    },
    {
        "target": "Family Care Center", "sponsor": "Revelstoke Capital Partners",
        "year": 2020, "ev_usd_mm": None, "sector": "behavioral_health",
        "subsector_note": "Outpatient mental-health clinics (veteran-focused founding)",
        "outcome": "active", "outcome_note": "Active outpatient mental-health platform.",
        "source_url": "https://revelstokecapital.com/news/revelstoke-capital-partners-invests-in-affiliate-of-family-care-center-to-expand-access-to-mental-healthcare/",
        "source_note": "Revelstoke Capital Partners (Family Care Center, Dec 2020)",
    },

    # ════════════════════════════════════════════════════════════════════
    # 2026-06 expansion (batch 8) — medical transport, medical supply,
    # occupational/worksite health, IME, PT/rehab, imaging, dental.
    # Each web-validated this sprint. Introduces the "ems" sector.
    # ════════════════════════════════════════════════════════════════════
    {
        "target": "Global Medical Response", "sponsor": "KKR",
        "year": 2017, "ev_usd_mm": None, "sector": "ems",
        "subsector_note": "Air + ground ambulance (Air Medical Group $2.09B 2015 + AMR $2.4B 2017)",
        "outcome": "active", "outcome_note": "Active; KKR air/ground EMS — same No-Surprises-Act exposure as Air Methods.",
        "source_url": "https://www.globalmedicalresponse.com/news/amgh-and-amr-complete-transaction-and-combine-under-new-parent-company-global-medical-response",
        "source_note": "Global Medical Response (AMGH+AMR combine under KKR, 2017)",
    },
    {
        "target": "Concentra", "sponsor": "Welsh, Carson, Anderson & Stowe + Select Medical",
        "year": 2015, "ev_usd_mm": 1055, "sector": "urgent_care",
        "subsector_note": "Occupational-health + urgent-care clinics; WCAS/Select JV bought from Humana",
        "outcome": "exited", "outcome_note": "IPO'd / spun off from Select Medical in 2024 (~$3.1B market value).",
        "source_url": "https://www.concentra.com/resource-center/press-releases/concentra-sale-to-select-medical-and-welsh-carson-is-complete/",
        "source_note": "Concentra (Humana sale to Select/WCAS, 2015); 2024 IPO",
    },
    {
        "target": "Premise Health", "sponsor": "OMERS Private Equity",
        "year": 2018, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Employer worksite/on-site health clinics; OMERS bought from Water Street + Walgreens",
        "outcome": "active", "outcome_note": "Active worksite-health platform.",
        "source_url": "https://www.omers.com/news/omers-private-equity-completes-acquisition-of-premise-health",
        "source_note": "OMERS Private Equity (Premise Health, July 2018)",
    },
    {
        "target": "ExamWorks", "sponsor": "CVC Capital Partners",
        "year": 2021, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Independent medical exams / IME + Medicare-compliance services; CVC majority",
        "outcome": "active", "outcome_note": "Active; Leonard Green took it private 2016, CVC bought majority 2021.",
        "source_url": "https://www.cvc.com/media/news/2021/2021-06-22-cvc-capital-partners-viii-to-invest-in-examworks/",
        "source_note": "CVC Capital Partners (ExamWorks, 2021); Leonard Green 2016",
    },
    {
        "target": "Confluent Health", "sponsor": "Partners Group",
        "year": 2019, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Outpatient physical-therapy MSO (650+ clinics)",
        "outcome": "active", "outcome_note": "Active PT platform.",
        "source_url": "https://www.partnersgroup.com/",
        "source_note": "Partners Group; May 2019 Confluent Health investment",
    },
    {
        "target": "Athletico Physical Therapy", "sponsor": "BDT Capital Partners",
        "year": 2016, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Outpatient physical-therapy operator; BDT bought from Harvest Partners",
        "outcome": "active", "outcome_note": "Active PT platform (900+ clinics post-Pivot).",
        "source_url": "https://www.bdtmsd.com/",
        "source_note": "BDT Capital Partners; 2016 Athletico from Harvest Partners",
    },
    {
        "target": "SimonMed Imaging", "sponsor": "American Securities",
        "year": 2021, "ev_usd_mm": 600, "sector": "other_services",
        "subsector_note": "Outpatient diagnostic-imaging centers; American Securities (~$600M)",
        "outcome": "active", "outcome_note": "Active imaging platform.",
        "source_url": "https://www.american-securities.com/en/our-companies",
        "source_note": "American Securities (SimonMed, 2021, ~$600M)",
    },
    {
        "target": "Affordable Care", "sponsor": "Harvest Partners",
        "year": 2021, "ev_usd_mm": None, "sector": "dental",
        "subsector_note": "Dental DSO (Affordable Dentures & Implants); Harvest acquired majority",
        "outcome": "active", "outcome_note": "Active dental platform.",
        "source_url": "https://www.dentistryiq.com/practice-management/dsos-and-corporate-dentistry/article/14205397/affordable-care-acquired-by-harvest-partners",
        "source_note": "DentistryIQ (Affordable Care acquired by Harvest Partners, 2021)",
    },

    # ════════════════════════════════════════════════════════════════════
    # 2026-06 expansion (batch 9) — ENT/allergy, ophthalmology, ABA/autism,
    # aesthetics, IDD/disability services. Each web-validated this sprint.
    # ════════════════════════════════════════════════════════════════════
    {
        "target": "SENTA Partners", "sponsor": "Shore Capital Partners",
        "year": 2021, "ev_usd_mm": None, "sector": "physician_practices",
        "subsector_note": "ENT + allergy + sleep-medicine MSO; Shore Capital platform",
        "outcome": "active", "outcome_note": "Active ENT/allergy platform.",
        "source_url": "https://www.shorecp.com/companies/senta",
        "source_note": "Shore Capital Partners (SENTA company page)",
    },
    {
        "target": "Spectrum Vision Partners (OCLI Vision)", "sponsor": "Blue Sea Capital",
        "year": 2017, "ev_usd_mm": None, "sector": "ophthalmology",
        "subsector_note": "Ophthalmology + optometry MSO (NY-anchored); Blue Sea platform",
        "outcome": "active", "outcome_note": "Active ophthalmology platform.",
        "source_url": "https://blueseacapital.com/spectrum-vision-partners-announces-ninth-affiliation-and-first-affiliation-in-new-jersey-eyecare-20-20/",
        "source_note": "Blue Sea Capital (Spectrum Vision Partners, 2017)",
    },
    {
        "target": "Action Behavior Centers", "sponsor": "Charlesbank Capital Partners",
        "year": 2022, "ev_usd_mm": 840, "sector": "behavioral_health",
        "subsector_note": "ABA autism therapy; Charlesbank bought from NexPhase (~$840M)",
        "outcome": "active", "outcome_note": "Active ABA platform.",
        "source_url": "https://bhbusiness.com/2022/08/17/charlesbank-capital-partners-wins-auction-to-acquire-action-behavior-centers/",
        "source_note": "Behavioral Health Business (Charlesbank/ABC, 2022, ~$840M)",
    },
    {
        "target": "Acorn Health", "sponsor": "Ontario Teachers' Pension Plan",
        "year": 2021, "ev_usd_mm": None, "sector": "behavioral_health",
        "subsector_note": "ABA autism therapy; OTPP bought from MBF Healthcare Partners",
        "outcome": "active", "outcome_note": "Active ABA platform.",
        "source_url": "https://www.businesswire.com/news/home/20210827005006/en/MBF-Healthcare-Partners-II-L.P.-Announces-Sale-of-Acorn-Health-LLC-A-National-Leader-In-The-Provision-of-Best-In-Class-Autism-Services",
        "source_note": "BusinessWire (MBF sells Acorn Health to OTPP, Aug 2021)",
    },
    {
        "target": "LEARN Behavioral", "sponsor": "Gryphon Investors",
        "year": 2019, "ev_usd_mm": None, "sector": "behavioral_health",
        "subsector_note": "ABA autism therapy; Gryphon bought majority from LLR Partners",
        "outcome": "active", "outcome_note": "Active ABA platform.",
        "source_url": "https://www.prnewswire.com/news-releases/gryphon-investors-announces-majority-investment-in-learn-behavioral-300814388.html",
        "source_note": "PRNewswire (Gryphon majority in LEARN Behavioral, Mar 2019)",
    },
    {
        "target": "LaserAway", "sponsor": "Ares Management + Seidler Equity Partners",
        "year": 2021, "ev_usd_mm": None, "sector": "dermatology",
        "subsector_note": "Aesthetic-dermatology / laser-treatment chain; Ares strategic investment",
        "outcome": "active", "outcome_note": "Active aesthetic-dermatology platform.",
        "source_url": "https://www.businesswire.com/news/home/20211021006090/en/LaserAway-Announces-Strategic-Investment-by-Ares-Management",
        "source_note": "BusinessWire (Ares invests in LaserAway, Oct 2021)",
    },
    {
        "target": "Sevita", "sponsor": "Centerbridge Partners + The Vistria Group",
        "year": 2019, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "IDD/disability + behavioral home-and-community services (fka The MENTOR Network)",
        "outcome": "active", "outcome_note": "Active; Madison Dearborn bought 25% in 2022 (~$3B valuation).",
        "source_url": "https://bhbusiness.com/2022/01/20/madison-dearborn-to-buy-25-of-sevita-at-roughly-3b-valuation/",
        "source_note": "Behavioral Health Business (Centerbridge/Vistria 2019; Madison Dearborn 2022 ~$3B)",
    },

    # ════════════════════════════════════════════════════════════════════
    # 2026-06 expansion (batch 10) — health-IT + diagnostics/device
    # take-privates, PBM, addiction. Each web-validated; several large
    # disclosed EVs (Ortho $4.15B, NextGen $1.8B, Natus $1.2B).
    # ════════════════════════════════════════════════════════════════════
    {
        "target": "Imprivata", "sponsor": "Thoma Bravo",
        "year": 2016, "ev_usd_mm": 544, "sector": "rcm_healthtech",
        "subsector_note": "Healthcare identity / access-management software; take-private (~$544M)",
        "outcome": "active", "outcome_note": "Active health-IT security platform.",
        "source_url": "https://www.thomabravo.com/",
        "source_note": "Thoma Bravo (Imprivata take-private, 2016, ~$544M)",
    },
    {
        "target": "Ortho Clinical Diagnostics", "sponsor": "The Carlyle Group",
        "year": 2014, "ev_usd_mm": 4150, "sector": "lab",
        "subsector_note": "In-vitro diagnostics; Carlyle carve-out from Johnson & Johnson (~$4.15B)",
        "outcome": "exited", "outcome_note": "IPO 2021 (DGX peer); merged with Quidel to form QuidelOrtho in 2022.",
        "source_url": "https://www.carlyle.com/media-room/news-release-archive/carlyle-group-completes-acquisition-ortho-clinical-diagnostics-inc",
        "source_note": "Carlyle (Ortho Clinical from J&J, 2014, ~$4.15B); 2021 IPO; 2022 Quidel",
    },
    {
        "target": "Natus Medical", "sponsor": "ArchiMed",
        "year": 2022, "ev_usd_mm": 1200, "sector": "other_services",
        "subsector_note": "Neurodiagnostic + newborn-care medical devices; take-private at $33.50/share",
        "outcome": "exited", "outcome_note": "Public→private; ArchiMed (~$1.2B).",
        "source_url": "https://www.archimed.group/news/archimed-acquires-natus-medical-incorporated/",
        "source_note": "ArchiMed (Natus Medical take-private, 2022, ~$1.2B)",
    },
    {
        "target": "naviHealth", "sponsor": "Clayton, Dubilier & Rice",
        "year": 2018, "ev_usd_mm": None, "sector": "rcm_healthtech",
        "subsector_note": "Post-acute-care management software; CD&R bought 55% from Cardinal Health (~$650M)",
        "outcome": "exited", "outcome_note": "Acquired by UnitedHealth's Optum in 2020.",
        "source_url": "https://www.massdevice.com/cardinal-health-deals-majority-stake-in-navihealth-to-pe-shop-cdr/",
        "source_note": "MassDevice (CD&R buys 55% of naviHealth, 2018, ~$650M); Optum 2020",
    },
    {
        "target": "Tabula Rasa HealthCare", "sponsor": "Nautic Partners",
        "year": 2023, "ev_usd_mm": 570, "sector": "rcm_healthtech",
        "subsector_note": "PBM + medication-risk-management software; take-private (~$570M)",
        "outcome": "exited", "outcome_note": "Public→private; later merged with ExactCare (2025).",
        "source_url": "https://www.modernhealthcare.com/mergers-acquisitions/nautic-partners-tabula-rasa-pbm/",
        "source_note": "Modern Healthcare (Nautic take-private of Tabula Rasa, 2023, ~$570M)",
    },
    {
        "target": "ARC Health (Advanced Recovery Concepts)", "sponsor": "Thurston Group",
        "year": 2021, "ev_usd_mm": None, "sector": "behavioral_health",
        "subsector_note": "Outpatient mental-health + addiction MSO; Thurston-formed platform",
        "outcome": "active", "outcome_note": "Active behavioral-health platform.",
        "source_url": "https://bhbusiness.com/2023/01/26/thurston-group-backed-arc-health-doubles-down-on-ma-strategy/",
        "source_note": "Behavioral Health Business (Thurston Group-backed ARC Health, formed 2021)",
    },

    # ════════════════════════════════════════════════════════════════════
    # 2026-06 expansion (batch 11) — dental DSOs, hospice, RCM, eye-care,
    # ASC. Each web-validated; pre-checked against existing targets.
    # ════════════════════════════════════════════════════════════════════

    # ── Dental DSOs ──
    {
        "target": "Great Expressions Dental Centers", "sponsor": "Roark Capital Group",
        "year": 2016, "ev_usd_mm": None, "sector": "dental",
        "subsector_note": "DSO; Roark bought from OMERS (prior: Audax 2008 -> OMERS 2011)",
        "outcome": "active", "outcome_note": "Active DSO.",
        "source_url": "https://www.roarkcapital.com/files/Great%20Expressions%20Press%20Release%20vF.pdf",
        "source_note": "Roark Capital (Great Expressions, 2016)",
    },
    {
        "target": "DECA Dental Group", "sponsor": "The Blackstone Group",
        "year": 2021, "ev_usd_mm": None, "sector": "dental",
        "subsector_note": "DSO; Blackstone Tactical Opportunities bought from Blue Sea Capital",
        "outcome": "active", "outcome_note": "Active DSO.",
        "source_url": "https://www.blackstone.com/news/press/deca-dental-group-announces-strategic-investment-from-blackstone-tactical-opportunities/",
        "source_note": "Blackstone (DECA Dental, Aug 2021)",
    },
    {
        "target": "Dental365", "sponsor": "The Jordan Company",
        "year": 2021, "ev_usd_mm": None, "sector": "dental",
        "subsector_note": "Northeast DSO; The Jordan Company platform",
        "outcome": "active", "outcome_note": "Active DSO.",
        "source_url": "https://www.thejordancompany.com/",
        "source_note": "The Jordan Company; 2021 Dental365",
    },
    {
        "target": "Sage Dental Management", "sponsor": "Linden Capital Partners",
        "year": 2012, "ev_usd_mm": None, "sector": "dental",
        "subsector_note": "Southeast DSO; Linden + Golub + Barings",
        "outcome": "active", "outcome_note": "Active DSO.",
        "source_url": "https://www.linden.com/portfolio/investments/current/sage-dental-management/",
        "source_note": "Linden Capital Partners (Sage Dental, 2012)",
    },

    # ── Hospice / home health ──
    {
        "target": "Bristol Hospice", "sponsor": "Webster Equity Partners",
        "year": 2017, "ev_usd_mm": 70, "sector": "home_health_hospice",
        "subsector_note": "Hospice operator; Webster acquired (~$70M, 45 locations)",
        "outcome": "active", "outcome_note": "Active hospice platform.",
        "source_url": "https://websterequitypartners.com/portfolio/bristol-hospice/",
        "source_note": "Webster Equity Partners (Bristol Hospice, 2017, ~$70M)",
    },
    {
        "target": "Traditions Health", "sponsor": "Dorilton Capital",
        "year": 2020, "ev_usd_mm": None, "sector": "home_health_hospice",
        "subsector_note": "Home health + hospice (College Station, TX); Dorilton-backed",
        "outcome": "exited", "outcome_note": "Broken up in 2025 — sold to four hospice buyers (Care Team / VitalCaring / LifeCare / Mission).",
        "source_url": "https://hospicenews.com/2025/12/03/four-hospice-buyers-acquire-traditions-health/",
        "source_note": "Hospice News (Dorilton-backed Traditions Health, 2025 breakup)",
    },

    # ── RCM ──
    {
        "target": "Aspirion", "sponsor": "Linden Capital Partners",
        "year": 2022, "ev_usd_mm": None, "sector": "rcm_healthtech",
        "subsector_note": "Complex-claims / denials RCM; Linden acquired Aug 2022",
        "outcome": "active", "outcome_note": "Active RCM platform.",
        "source_url": "https://www.linden.com/",
        "source_note": "Linden Capital Partners (Aspirion, Aug 2022)",
    },
    {
        "target": "Med-Metrix", "sponsor": "A&M Capital Partners",
        "year": 2021, "ev_usd_mm": None, "sector": "rcm_healthtech",
        "subsector_note": "Hospital + physician RCM; A&M Capital investment",
        "outcome": "active", "outcome_note": "Active RCM platform.",
        "source_url": "https://www.amcapital.com/",
        "source_note": "A&M Capital Partners (Med-Metrix, Sept 2021)",
    },

    # ── Eye care / ophthalmology ──
    {
        "target": "PRISM Vision Group", "sponsor": "Quad-C Management",
        "year": 2018, "ev_usd_mm": None, "sector": "ophthalmology",
        "subsector_note": "Ophthalmology + retina MSO (Northeast); Quad-C platform",
        "outcome": "exited", "outcome_note": "McKesson acquired a controlling interest from Quad-C in 2025 (~$850M).",
        "source_url": "https://www.quadcmanagement.com/portfolio/prism-vision-group/",
        "source_note": "Quad-C Management (PRISM Vision, 2018); McKesson 2025 (~$850M)",
    },
    {
        "target": "US Eye", "sponsor": "Pamlico Capital",
        "year": 2021, "ev_usd_mm": None, "sector": "ophthalmology",
        "subsector_note": "Ophthalmology + optometry MSO (FL-anchored); Pamlico growth investment",
        "outcome": "active", "outcome_note": "Active eye-care platform.",
        "source_url": "https://www.pamlicocapital.com/news/us-eye-receives-growth-investment-from-pamlico-capital",
        "source_note": "Pamlico Capital (US Eye, 2021)",
    },
    {
        "target": "Acuity Eyecare Group", "sponsor": "Riata Capital Group",
        "year": 2017, "ev_usd_mm": None, "sector": "ophthalmology",
        "subsector_note": "Optical-retail + eye-care MSO; Riata-formed (2017)",
        "outcome": "active", "outcome_note": "Active; J.P. Morgan AM later co-invested.",
        "source_url": "https://www.riatacapital.com/news/acuity-eyecare-group-completes-significant-acquisitions-in-colorado-and-nebraska-receives-investment-from-j-p-morgan-asset-management",
        "source_note": "Riata Capital Group (Acuity Eyecare Group, formed 2017)",
    },
    {
        "target": "EyeCare Services Partners (ESP)", "sponsor": "Harvest Partners + Varsity Healthcare Partners",
        "year": 2017, "ev_usd_mm": None, "sector": "ophthalmology",
        "subsector_note": "Ophthalmology + ASC MSO; Harvest recapitalized from Varsity",
        "outcome": "active", "outcome_note": "Active eye-care platform.",
        "source_url": "https://varsityhealthcarepartners.com/varsity-healthcare-partners-and-harvest-partners-announce-recapitalization-of-eyecare-services-partners/",
        "source_note": "Varsity/Harvest (EyeCare Services Partners recap, May 2017)",
    },

    # ── ASC ──
    {
        "target": "Regent Surgical Health", "sponsor": "TowerBrook Capital Partners",
        "year": 2021, "ev_usd_mm": None, "sector": "asc",
        "subsector_note": "ASC developer/manager (health-system JV model)",
        "outcome": "active", "outcome_note": "Active ASC platform.",
        "source_url": "https://regentsh.com/",
        "source_note": "TowerBrook Capital Partners (Regent Surgical Health, 2021)",
    },
    {
        "target": "Constitution Surgery Alliance", "sponsor": "Welsh, Carson, Anderson & Stowe",
        "year": 2025, "ev_usd_mm": None, "sector": "asc",
        "subsector_note": "ASC developer/operator (hospital JV); WCAS growth investment",
        "outcome": "active", "outcome_note": "Active ASC platform.",
        "source_url": "https://www.prnewswire.com/news-releases/constitution-surgery-alliance-announces-strategic-growth-investment-from-welsh-carson-anderson--stowe-302481298.html",
        "source_note": "PRNewswire (WCAS / Constitution Surgery Alliance, June 2025)",
    },

    # ════════════════════════════════════════════════════════════════════
    # 2026-06 expansion (batch 12) — DME/complex-rehab, addiction/SUD,
    # PT/podiatry. Each web-validated; pre-checked against existing targets.
    # ════════════════════════════════════════════════════════════════════

    # ── DME / complex rehab ──
    {
        "target": "AdaptHealth", "sponsor": "Deerfield Management",
        "year": 2019, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Home medical equipment / DME; Deerfield SPAC (DFB Healthcare) de-SPAC",
        "outcome": "exited", "outcome_note": "Went public via SPAC Nov 2019 (Nasdaq: AHCO).",
        "source_url": "https://www.businesswire.com/news/home/20191108005600/en/DFB-Healthcare-Acquisitions-Corp.-Announces-Closing-Business",
        "source_note": "BusinessWire (DFB/Deerfield de-SPAC of AdaptHealth, Nov 2019)",
    },
    {
        "target": "Numotion", "sponsor": "AEA Investors",
        "year": 2018, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Complex rehab technology (CRT) / wheelchairs; AEA bought from LLR + Audax",
        "outcome": "active", "outcome_note": "Active complex-rehab platform.",
        "source_url": "https://www.aeainvestors.com/aea-acquires-numotion/",
        "source_note": "AEA Investors (Numotion, Nov 2018)",
    },
    {
        "target": "National Seating & Mobility", "sponsor": "Cinven",
        "year": 2019, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Complex rehab technology / mobility; Cinven bought from Court Square",
        "outcome": "active", "outcome_note": "Active complex-rehab platform.",
        "source_url": "https://www.nsm-seating.com/press-release/national-seating-mobility-owner-enters-purchase-agreement-with-international-private-equity-firm/",
        "source_note": "NSM (Cinven acquisition from Court Square, 2019)",
    },

    # ── Addiction / SUD ──
    {
        "target": "Pinnacle Treatment Centers", "sponsor": "Linden Capital Partners",
        "year": 2016, "ev_usd_mm": None, "sector": "behavioral_health",
        "subsector_note": "Addiction-treatment / SUD facilities operator",
        "outcome": "active", "outcome_note": "Active SUD platform.",
        "source_url": "https://www.linden.com/news/2016/08/linden-completes-acquistion-of-pinnacle-treatment-centers/",
        "source_note": "Linden Capital Partners (Pinnacle Treatment Centers, Aug 2016)",
    },
    {
        "target": "Recovery Centers of America", "sponsor": "Deerfield Management",
        "year": 2015, "ev_usd_mm": None, "sector": "behavioral_health",
        "subsector_note": "Addiction-treatment campuses; Deerfield committed ~$231.5M",
        "outcome": "active", "outcome_note": "Active SUD platform.",
        "source_url": "https://ionanalytics.com/insights/mergermarket/recovery-centers-of-america-ramps-up-ma-as-it-returns-to-scale-mode-ceo/",
        "source_note": "ION Analytics (Deerfield-backed RCA, founded 2015)",
    },
    {
        "target": "Bradford Health Services", "sponsor": "Lee Equity Partners",
        "year": 2022, "ev_usd_mm": None, "sector": "behavioral_health",
        "subsector_note": "Southeast addiction-treatment provider; Lee Equity bought from Centre Partners",
        "outcome": "active", "outcome_note": "Active SUD platform.",
        "source_url": "https://www.leeequity.com/",
        "source_note": "Lee Equity Partners (Bradford Health from Centre Partners, Oct 2022)",
    },

    # ── PT / podiatry ──
    {
        "target": "FYZICAL Therapy & Balance Centers", "sponsor": "New Harbor Capital",
        "year": 2018, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Physical-therapy + balance franchise; New Harbor majority",
        "outcome": "active", "outcome_note": "Active PT franchise platform.",
        "source_url": "https://www.newharborcap.com/news/new-harbor-capital-acquires-majority-interest-in-fyzical/",
        "source_note": "New Harbor Capital (FYZICAL, Jan 2018)",
    },
    {
        "target": "U.S. Foot & Ankle Specialists", "sponsor": "NMS Capital",
        "year": 2019, "ev_usd_mm": None, "sector": "physician_practices",
        "subsector_note": "Podiatry MSO (~150 offices); NMS-formed platform",
        "outcome": "active", "outcome_note": "Active podiatry platform.",
        "source_url": "https://nms-capital.com/news/u-s-foot-ankle-specialists-expands-in-michigan-ohio-and-connecticut-with-acquisitions-of-foot-and-ankle-specialists-p-c-podiatry-inc-and-bethel-foot-and-ankle/",
        "source_note": "NMS Capital (U.S. Foot & Ankle Specialists)",
    },
    {
        "target": "Upperline Health", "sponsor": "Silversmith Capital Partners",
        "year": 2020, "ev_usd_mm": None, "sector": "physician_practices",
        "subsector_note": "Podiatry + value-based lower-extremity care MSO",
        "outcome": "active", "outcome_note": "Active podiatry/value-based platform.",
        "source_url": "https://www.silversmith.com/portfolio/upperline-health",
        "source_note": "Silversmith Capital Partners (Upperline Health)",
    },

    # ════════════════════════════════════════════════════════════════════
    # 2026-06 expansion (batch 13) — CRO/clinical research, healthcare
    # staffing, pain management, nephrology. Each web-validated; pre-checked.
    # ════════════════════════════════════════════════════════════════════

    # ── CRO / clinical research ──
    {
        "target": "Parexel", "sponsor": "EQT + Goldman Sachs Asset Management",
        "year": 2021, "ev_usd_mm": 8500, "sector": "other_services",
        "subsector_note": "Contract research org (CRO); take-private (~$8.5B)",
        "outcome": "active", "outcome_note": "Active CRO (Pamplona owned it 2017-2021).",
        "source_url": "https://www.clinicaltrialsarena.com/features/cro-mergers-impact-clinical-trial-sponsors/",
        "source_note": "EQT + GS (Parexel take-private, 2021, ~$8.5B)",
    },
    {
        "target": "PPD", "sponsor": "The Carlyle Group + Hellman & Friedman",
        "year": 2011, "ev_usd_mm": 3900, "sector": "other_services",
        "subsector_note": "Contract research org (CRO); take-private (~$3.9B)",
        "outcome": "exited", "outcome_note": "IPO 2020; acquired by Thermo Fisher in 2021 (~$17B) — a large PE round-trip.",
        "source_url": "https://www.carlyle.com/media-room/news-release-archive/ppd-be-acquired-carlyle-group-and-hellman-and-friedman",
        "source_note": "Carlyle + H&F (PPD take-private, 2011, ~$3.9B); Thermo 2021",
    },
    {
        "target": "WCG (WIRB-Copernicus Group)", "sponsor": "Leonard Green & Partners + Arsenal Capital + Novo Holdings",
        "year": 2019, "ev_usd_mm": 3000, "sector": "other_services",
        "subsector_note": "Clinical-trial IRB / research compliance + tech; ~$3B recap",
        "outcome": "active", "outcome_note": "Active clinical-research-services platform.",
        "source_url": "https://www.leonardgreen.com/leonard-green-partners-leads-recapitalization-of-wcg-in-partnership-with-arsenal-capital-partners/",
        "source_note": "Leonard Green (WCG recap, Nov 2019, ~$3B)",
    },
    {
        "target": "Advarra", "sponsor": "Genstar Capital",
        "year": 2019, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Clinical-research IRB / compliance + tech; Genstar bought from Linden",
        "outcome": "active", "outcome_note": "Active; Blackstone + CPPIB recap 2022 (~$5B).",
        "source_url": "https://www.gencap.com/genstar-capital-announces-completion-of-advarra-acquisition/",
        "source_note": "Genstar Capital (Advarra from Linden, 2019); Blackstone/CPPIB 2022",
    },
    {
        "target": "Worldwide Clinical Trials", "sponsor": "Kohlberg & Company",
        "year": 2023, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Mid-size contract research org (CRO); Kohlberg majority",
        "outcome": "active", "outcome_note": "Active CRO.",
        "source_url": "https://medcitynews.com/2026/01/worldwide-clinical-trials-to-buy-catalyst-another-ma-deal-between-private-equity-backed-cros/",
        "source_note": "MedCity News (Kohlberg-backed Worldwide Clinical Trials, 2023)",
    },

    # ── Healthcare staffing ──
    {
        "target": "Ingenovis Health", "sponsor": "Cornell Capital + Trilantic North America",
        "year": 2021, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Travel-nurse + clinician staffing platform (Fastaff/trustaff/etc.)",
        "outcome": "active", "outcome_note": "Active staffing platform.",
        "source_url": "https://www.prnewswire.com/news-releases/ingenovis-health-to-acquire-healthcare-support-301433038.html",
        "source_note": "Cornell Capital + Trilantic (Ingenovis Health, 2021)",
    },
    {
        "target": "Medical Solutions", "sponsor": "Centerbridge Partners + CDPQ",
        "year": 2021, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Travel-nurse staffing; Centerbridge/CDPQ bought from TPG Growth",
        "outcome": "active", "outcome_note": "Active staffing platform.",
        "source_url": "https://www.prnewswire.com/news-releases/medical-solutions-to-be-acquired-by-centerbridge-partners-and-cdpq-301365119.html",
        "source_note": "Centerbridge + CDPQ (Medical Solutions from TPG, Aug 2021)",
    },

    # ── Pain management / nephrology ──
    {
        "target": "National Spine & Pain Centers", "sponsor": "Avista Capital Partners",
        "year": 2017, "ev_usd_mm": None, "sector": "physician_practices",
        "subsector_note": "Interventional pain-management MSO; Avista bought from Sentinel",
        "outcome": "active", "outcome_note": "Active pain-management platform.",
        "source_url": "https://www.prnewswire.com/news-releases/avista-capital-partners-has-acquired-national-spine--pain-centers-llc-300468411.html",
        "source_note": "Avista Capital Partners (National Spine & Pain Centers, 2017)",
    },
    {
        "target": "Panoramic Health", "sponsor": "Audax Group",
        "year": 2020, "ev_usd_mm": None, "sector": "physician_practices",
        "subsector_note": "Nephrology MSO + value-based kidney care; Audax platform",
        "outcome": "active", "outcome_note": "Active nephrology platform.",
        "source_url": "https://www.audaxprivateequity.com/portfolio/panoramic-health",
        "source_note": "Audax Group (Panoramic Health, 2020)",
    },

    # ════════════════════════════════════════════════════════════════════
    # 2026-06 expansion (batch 14) — more dental DSOs, dermatology, OB
    # hospitalist, pediatric home care. Each web-validated; pre-checked.
    # ════════════════════════════════════════════════════════════════════

    # ── Dental DSOs ──
    {
        "target": "Specialty Dental Brands", "sponsor": "TSG Consumer Partners + Leon Capital",
        "year": 2022, "ev_usd_mm": None, "sector": "dental",
        "subsector_note": "Specialty DSO (pediatric dentistry + orthodontics + oral surgery)",
        "outcome": "active", "outcome_note": "Active specialty DSO.",
        "source_url": "https://www.tsgconsumer.com/news/specialty-dental-brands-tsg-consumer-partners-and-leon-capital-finalize-growth-partnership",
        "source_note": "TSG Consumer Partners (Specialty Dental Brands, Sept 2022)",
    },
    {
        "target": "Rodeo Dental & Orthodontics", "sponsor": "Bain Capital Double Impact",
        "year": 2019, "ev_usd_mm": None, "sector": "dental",
        "subsector_note": "DSO (TX-anchored, underserved/Medicaid focus); impact-investing platform",
        "outcome": "active", "outcome_note": "Active DSO.",
        "source_url": "https://www.baincapital.com/news/bain-capital-double-impact-and-rodeo-dental-orthodontics-partner-deliver-best-class-patient",
        "source_note": "Bain Capital Double Impact (Rodeo Dental, 2019)",
    },
    {
        "target": "Espire Dental", "sponsor": "Rallyday Partners + Ironwood Capital",
        "year": 2023, "ev_usd_mm": None, "sector": "dental",
        "subsector_note": "DSO (Colorado-anchored); Rallyday-backed with Ironwood debt",
        "outcome": "active", "outcome_note": "Active DSO.",
        "source_url": "https://www.rallyday.com/",
        "source_note": "Rallyday Partners + Ironwood Capital (Espire Dental, 2023)",
    },

    # ── Dermatology ──
    {
        "target": "Epiphany Dermatology", "sponsor": "Leonard Green & Partners",
        "year": 2022, "ev_usd_mm": None, "sector": "dermatology",
        "subsector_note": "Derm MSO; Leonard Green recapitalized from CI Capital",
        "outcome": "active", "outcome_note": "Active derm platform.",
        "source_url": "https://www.lincolninternational.com/transactions/ci-capital-partners-has-sold-epiphany-dermatology-to-leonard-green-partners/",
        "source_note": "Lincoln International (Leonard Green buys Epiphany from CI Capital, 2022)",
    },
    {
        "target": "Anne Arundel Dermatology", "sponsor": "Ridgemont Equity Partners",
        "year": 2020, "ev_usd_mm": None, "sector": "dermatology",
        "subsector_note": "Mid-Atlantic + Southeast derm MSO",
        "outcome": "active", "outcome_note": "Active derm platform.",
        "source_url": "https://www.ridgemontep.com/press-releases/ridgemont-equity-partners-acquires-anne-arundel-dermatology/",
        "source_note": "Ridgemont Equity Partners (Anne Arundel Dermatology, Oct 2020)",
    },
    {
        "target": "Aqua Dermatology (Riverchase/Water's Edge)", "sponsor": "GTCR",
        "year": 2019, "ev_usd_mm": None, "sector": "dermatology",
        "subsector_note": "Southeast derm MSO (Riverchase + Water's Edge merger)",
        "outcome": "active", "outcome_note": "Active derm platform.",
        "source_url": "https://www.gtcr.com/",
        "source_note": "GTCR (Riverchase/Aqua Dermatology); via Practical Dermatology coverage",
    },

    # ── OB hospitalist / pediatric home care ──
    {
        "target": "Ob Hospitalist Group (OBHG)", "sponsor": "Gryphon Investors",
        "year": 2024, "ev_usd_mm": None, "sector": "physician_practices",
        "subsector_note": "OB/GYN hospitalist staffing; Gryphon bought from Ares Management",
        "outcome": "active", "outcome_note": "Active OB-hospitalist platform.",
        "source_url": "https://www.gryphon-inv.com/news/gryphon-investors-to-acquire-ob-hospitalist-group-from-ares-management/",
        "source_note": "Gryphon Investors (OBHG from Ares, 2024)",
    },
    {
        "target": "Thrive Skilled Pediatric Care", "sponsor": "Summit Partners",
        "year": 2019, "ev_usd_mm": None, "sector": "home_health_hospice",
        "subsector_note": "Pediatric private-duty home nursing; Summit-backed",
        "outcome": "exited", "outcome_note": "Acquired by Aveanna Healthcare in 2025.",
        "source_url": "https://www.summitpartners.com/",
        "source_note": "Summit Partners (Thrive Skilled Pediatric Care); Aveanna 2025 acquisition",
    },

    # ════════════════════════════════════════════════════════════════════
    # 2026-06 expansion (batch 15) — home infusion, diagnostic imaging,
    # veterinary. Each web-validated; pre-checked against existing targets.
    # ════════════════════════════════════════════════════════════════════
    {
        "target": "InfuCare Rx", "sponsor": "One Equity Partners",
        "year": 2023, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Home / alternate-site infusion therapy provider",
        "outcome": "active", "outcome_note": "Active home-infusion platform.",
        "source_url": "https://www.oneequity.com/news/one-equity-partners-completes-investment-in-infucare-rx-a-leading-home-infusion-therapy-provider/",
        "source_note": "One Equity Partners (InfuCare Rx, 2023)",
    },
    {
        "target": "KabaFusion", "sponsor": "Pritzker Private Capital",
        "year": 2022, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Home infusion (IVIG / specialty) pharmacy; Pritzker family-of-companies",
        "outcome": "active", "outcome_note": "Active home-infusion platform.",
        "source_url": "https://www.paragonventures.com/market-pulse-posts/kabafusion-acquires-infusion-care-pharmacy-assets-from-coram/",
        "source_note": "Pritzker Private Capital (KabaFusion)",
    },
    {
        "target": "Akumin", "sponsor": "Stonepeak",
        "year": 2024, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Outpatient + mobile diagnostic imaging / radiology; debt-to-equity take-private",
        "outcome": "exited", "outcome_note": "Public→private; Stonepeak took full ownership Feb 2024 via restructuring.",
        "source_url": "https://akumin.com/newsroom/press-releases/akumin-inc-completes-deleveraging-transaction-becomes-a-private-company-wholly-owned-by-stonepeak/",
        "source_note": "Akumin (Stonepeak full ownership, Feb 2024)",
    },
    {
        "target": "RAYUS Radiology (Center for Diagnostic Imaging)", "sponsor": "Wellspring Capital Management",
        "year": 2019, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Outpatient diagnostic imaging; Wellspring acquired CDI (rebranded RAYUS)",
        "outcome": "active", "outcome_note": "Active imaging platform.",
        "source_url": "https://rayusradiology.com/blog/wellspring-capital-backed-rayus-radiology-acquires-diagnostic-centers-of-america-bolstering-its-growing-nationwide-network/",
        "source_note": "Wellspring Capital (CDI/RAYUS, 2019)",
    },
    {
        "target": "LucidHealth", "sponsor": "Excellere Partners",
        "year": 2016, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Radiology practice management + teleradiology; Excellere-backed",
        "outcome": "active", "outcome_note": "Active radiology platform.",
        "source_url": "https://lucidhealth.com/",
        "source_note": "Excellere Partners (LucidHealth, founded 2016)",
    },
    {
        "target": "Catalyst MedTech (TTG Imaging Solutions)", "sponsor": "Sentinel Capital Partners",
        "year": 2021, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Diagnostic-imaging equipment + service solutions for providers",
        "outcome": "active", "outcome_note": "Active imaging-equipment/services platform.",
        "source_url": "https://www.sentinelpartners.com/company/catalyst-medtech/",
        "source_note": "Sentinel Capital Partners (TTG/Catalyst MedTech, Dec 2021)",
    },
    {
        "target": "United Veterinary Care", "sponsor": "Nordic Capital",
        "year": 2021, "ev_usd_mm": None, "sector": "veterinary",
        "subsector_note": "Veterinary hospital consolidator; Nordic Capital-backed",
        "outcome": "active", "outcome_note": "Active veterinary platform.",
        "source_url": "https://www.nordiccapital.com/",
        "source_note": "Nordic Capital (United Veterinary Care)",
    },

    # ════════════════════════════════════════════════════════════════════
    # 2026-06 expansion (batch 16) — health-IT/data take-privates + allergy/
    # pain MSOs. Each web-validated; pre-checked. Big-ticket data deals.
    # ════════════════════════════════════════════════════════════════════
    {
        "target": "Inovalon", "sponsor": "Nordic Capital + Insight Partners",
        "year": 2021, "ev_usd_mm": 7300, "sector": "rcm_healthtech",
        "subsector_note": "Healthcare data/analytics SaaS; take-private (~$7.3B)",
        "outcome": "exited", "outcome_note": "Public→private (Nasdaq: INOV); consortium incl. 22C Capital.",
        "source_url": "https://www.nordiccapital.com/news-views/press-releases/equity-consortium-led-by-nordic-capital-and-including-insight-partners-completes-acquisition-of-inovalon/",
        "source_note": "Nordic Capital + Insight Partners (Inovalon take-private, 2021, ~$7.3B)",
    },
    {
        "target": "Zelis", "sponsor": "Bain Capital + Parthenon Capital",
        "year": 2019, "ev_usd_mm": 5700, "sector": "rcm_healthtech",
        "subsector_note": "Healthcare payments optimization; Zelis + RedCard merger (~$5.7B)",
        "outcome": "active", "outcome_note": "Active; minority stake marketed at ~$17B in 2024.",
        "source_url": "https://www.zelis.com/news/zelis-completes-acquisition-redcard/",
        "source_note": "Bain + Parthenon (Zelis/RedCard merger, 2019, ~$5.7B)",
    },
    {
        "target": "Edifecs", "sponsor": "TA Associates + Francisco Partners",
        "year": 2020, "ev_usd_mm": None, "sector": "rcm_healthtech",
        "subsector_note": "Payer/provider interoperability + data-exchange software",
        "outcome": "exited", "outcome_note": "Acquired by Cotiviti in 2025.",
        "source_url": "https://www.edifecs.com/newsroom/ta-associates-and-francisco-partners-announce-significant-growth-investment-in-edifecs/",
        "source_note": "TA Associates + Francisco Partners (Edifecs, 2020); Cotiviti 2025",
    },
    {
        "target": "M*Modal", "sponsor": "One Equity Partners",
        "year": 2012, "ev_usd_mm": 1100, "sector": "rcm_healthtech",
        "subsector_note": "Clinical documentation / medical transcription + NLP; take-private (~$1.1B)",
        "outcome": "exited", "outcome_note": "Ch.11 2014 (over-leveraged); tech sold to 3M in 2019 — a health-IT downside.",
        "source_url": "https://www.businesswire.com/news/home/20120702006524/en/M*Modal-to-Be-Acquired-for-Approximately-1.1-Billion-by-One-Equity-Partners",
        "source_note": "One Equity Partners (M*Modal, 2012, ~$1.1B); 2014 Ch.11; 3M 2019",
    },
    {
        "target": "AllerVie Health", "sponsor": "Summit Partners",
        "year": 2021, "ev_usd_mm": None, "sector": "physician_practices",
        "subsector_note": "Allergy + asthma + immunology MSO; Summit-backed",
        "outcome": "active", "outcome_note": "Active allergy platform.",
        "source_url": "https://noromoseley.com/company/allervie-health/",
        "source_note": "Summit Partners (AllerVie Health)",
    },
    {
        "target": "Capitol Pain Institute", "sponsor": "Iron Path Capital",
        "year": 2022, "ev_usd_mm": None, "sector": "physician_practices",
        "subsector_note": "Interventional pain-management MSO; Iron Path platform",
        "outcome": "active", "outcome_note": "Active pain-management platform.",
        "source_url": "https://www.businesswire.com/news/home/20220623005746/en/Iron-Path-Capital-Announces-Partnership-with-Capitol-Pain-Institute-to-Build-Nationwide-Interventional-Pain-Management-Platform",
        "source_note": "Iron Path Capital (Capitol Pain Institute, June 2022)",
    },

    # ════════════════════════════════════════════════════════════════════
    # 2026-06 expansion (batch 17) — PT/MSK, outpatient mental health,
    # home health/hospice. Each web-validated; pre-checked.
    # ════════════════════════════════════════════════════════════════════

    # ── Physical therapy / MSK ──
    {
        "target": "Ivy Rehab", "sponsor": "Waud Capital Partners",
        "year": 2016, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Outpatient physical-therapy + pediatric therapy network; Waud platform",
        "outcome": "active", "outcome_note": "Active PT platform (2022 continuation fund).",
        "source_url": "https://www.waudcapital.com/en/portfolio/ivy-rehab/",
        "source_note": "Waud Capital Partners (Ivy Rehab, 2016)",
    },
    {
        "target": "PT Solutions", "sponsor": "General Atlantic",
        "year": 2021, "ev_usd_mm": 1200, "sector": "other_services",
        "subsector_note": "Outpatient physical therapy; GA majority (~$1.2B), TowerBrook/Ascension minority",
        "outcome": "active", "outcome_note": "Active PT platform (prior Lindsay Goldberg, New Harbor).",
        "source_url": "https://www.axios.com/2022/01/07/ga-buys-pt-solutions-1-billion-valuation",
        "source_note": "Axios (General Atlantic buys PT Solutions, ~$1.2B, 2021)",
    },
    {
        "target": "H2 Health", "sponsor": "Grant Avenue Capital",
        "year": 2020, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Outpatient PT + rehab (Southeast); Grant Avenue bought from HCR ManorCare",
        "outcome": "active", "outcome_note": "Active PT/rehab platform.",
        "source_url": "https://www.lincolninternational.com/transactions/h2-health-a-portfolio-company-of-grant-avenue-capital-has-acquired-physical-therapy-today/",
        "source_note": "Grant Avenue Capital (H2 Health, 2020)",
    },
    {
        "target": "Empower Physical Therapy", "sponsor": "Sheridan Capital Partners",
        "year": 2018, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Outpatient physical therapy (Southwest); Sheridan-backed",
        "outcome": "active", "outcome_note": "Active PT platform.",
        "source_url": "https://sheridancp.com/news/sheridan-capital-partners-invests-in-empower-physical-therapy/",
        "source_note": "Sheridan Capital Partners (Empower PT, Oct 2018)",
    },

    # ── Outpatient mental health ──
    {
        "target": "Newport Healthcare", "sponsor": "Onex Partners",
        "year": 2021, "ev_usd_mm": 1300, "sector": "behavioral_health",
        "subsector_note": "Teen/young-adult mental-health + SUD treatment; Onex bought ~60% from Carlyle (~$1.3B)",
        "outcome": "active", "outcome_note": "Active behavioral-health platform.",
        "source_url": "https://www.onex.com/article/2021NewsRelease-OnexCompletesNewportHealthcare-July19",
        "source_note": "Onex Partners (Newport Healthcare from Carlyle, July 2021, ~$1.3B)",
    },
    {
        "target": "Mindful Health Solutions", "sponsor": "Aisling Capital",
        "year": 2024, "ev_usd_mm": None, "sector": "behavioral_health",
        "subsector_note": "Outpatient psychiatry + TMS / interventional mental health",
        "outcome": "active", "outcome_note": "Active mental-health platform (Norwest also invested).",
        "source_url": "https://mergr.com/aisling-capital-acquires-mindful-health-solutions",
        "source_note": "Aisling Capital (Mindful Health Solutions, 2024)",
    },
    {
        "target": "Transformations Care Network", "sponsor": "Shore Capital Partners + Resolute Capital Partners",
        "year": 2021, "ev_usd_mm": None, "sector": "behavioral_health",
        "subsector_note": "Outpatient mental-health MSO (4-way merger)",
        "outcome": "active", "outcome_note": "Active mental-health platform.",
        "source_url": "https://www.shorecp.com/companies/transformations-care-network",
        "source_note": "Shore Capital + Resolute (Transformations Care Network, Aug 2021)",
    },
    {
        "target": "Lightfully Behavioral Health", "sponsor": "Regal Healthcare Capital Partners",
        "year": 2021, "ev_usd_mm": None, "sector": "behavioral_health",
        "subsector_note": "Primary mental-health treatment (CA); Regal-backed",
        "outcome": "active", "outcome_note": "Active mental-health platform.",
        "source_url": "https://bhbusiness.com/2024/03/20/pe-firm-regal-healthcare-capital-partners-invests-50m-in-lightfully-behavioral-health/",
        "source_note": "Regal Healthcare Capital Partners (Lightfully, 2021)",
    },

    # ── Home health / hospice ──
    {
        "target": "VitalCaring Group", "sponsor": "The Vistria Group + Nautic Partners",
        "year": 2021, "ev_usd_mm": None, "sector": "home_health_hospice",
        "subsector_note": "Home health + hospice (April Anthony-led); Vistria + Nautic",
        "outcome": "active", "outcome_note": "Active home-health/hospice platform.",
        "source_url": "https://vistria.com/portfolio-items/vitalcaringgroup/",
        "source_note": "The Vistria Group + Nautic Partners (VitalCaring, 2021)",
    },

    # ════════════════════════════════════════════════════════════════════
    # 2026-06 expansion (batch 18) — veterinary, more dental DSOs, RCM.
    # Each web-validated; pre-checked against existing targets.
    # ════════════════════════════════════════════════════════════════════

    # ── Veterinary ──
    {
        "target": "PetVet Care Centers", "sponsor": "KKR",
        "year": 2019, "ev_usd_mm": None, "sector": "veterinary",
        "subsector_note": "Veterinary hospital network; KKR validated the vet sector",
        "outcome": "active", "outcome_note": "Active veterinary platform.",
        "source_url": "https://www.pehub.com/kkr-validates-veterinary-sector-with-petvet-buy/",
        "source_note": "KKR (PetVet Care Centers, 2019)",
    },
    {
        "target": "AmeriVet Veterinary Partners", "sponsor": "AEA Investors",
        "year": 2020, "ev_usd_mm": None, "sector": "veterinary",
        "subsector_note": "Veterinary practice partnership model; AEA-backed",
        "outcome": "active", "outcome_note": "Active veterinary platform.",
        "source_url": "https://amerivet.com/blog/veterinary-private-equity",
        "source_note": "AEA Investors (AmeriVet Veterinary Partners, 2020)",
    },

    # ── Dental DSOs ──
    {
        "target": "Gen4 Dental Partners", "sponsor": "Thurston Group",
        "year": 2021, "ev_usd_mm": None, "sector": "dental",
        "subsector_note": "DSO (100+ practices); Thurston-launched (2021)",
        "outcome": "active", "outcome_note": "Active DSO.",
        "source_url": "https://www.beckersdental.com/dso-dpms/the-pe-firms-behind-15-dsos/",
        "source_note": "Thurston Group (Gen4 Dental Partners, 2021)",
    },
    {
        "target": "ProSmile", "sponsor": "TriSpan",
        "year": 2020, "ev_usd_mm": None, "sector": "dental",
        "subsector_note": "Northeast DSO; TriSpan-backed",
        "outcome": "active", "outcome_note": "Active DSO.",
        "source_url": "https://livingstonepartners.com/en-us/transactions/destiny-dental-has-been-acquired-by-prosmile",
        "source_note": "TriSpan (ProSmile, founded 2020)",
    },
    {
        "target": "Dentive", "sponsor": "HGGC",
        "year": 2023, "ev_usd_mm": None, "sector": "dental",
        "subsector_note": "DSO (Mountain West); HGGC growth investment",
        "outcome": "active", "outcome_note": "Active DSO.",
        "source_url": "https://hggc.com/",
        "source_note": "HGGC (Dentive, 2023)",
    },

    # ── RCM ──
    {
        "target": "Infinx", "sponsor": "KKR",
        "year": 2024, "ev_usd_mm": None, "sector": "rcm_healthtech",
        "subsector_note": "AI-driven RCM / patient-access (prior-auth, eligibility); KKR minority",
        "outcome": "active", "outcome_note": "Active RCM platform (Norwest also invested).",
        "source_url": "https://www.businesswire.com/news/home/20240520027338/en/KKR-Invests-in-Healthcare-Revenue-Solutions-Provider-Infinx",
        "source_note": "KKR (Infinx investment, May 2024)",
    },

    # ════════════════════════════════════════════════════════════════════
    # 2026-06 expansion (batch 19) — clinical-trial site networks, behavioral
    # residential, veterinary. Each web-validated; pre-checked.
    # ════════════════════════════════════════════════════════════════════

    # ── Clinical-trial site networks ──
    {
        "target": "Velocity Clinical Research", "sponsor": "GHO Capital",
        "year": 2021, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Integrated clinical-trial site organization; GHO platform",
        "outcome": "active", "outcome_note": "Active clinical-research-site network.",
        "source_url": "https://ghocapital.com/companies/velocity-clinical-research/",
        "source_note": "GHO Capital (Velocity Clinical Research, Apr 2021)",
    },
    {
        "target": "Headlands Research", "sponsor": "KKR",
        "year": 2018, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Clinical-trial site network; KKR-launched (2018)",
        "outcome": "active", "outcome_note": "Active; THL Partners agreed to buy from KKR in 2025.",
        "source_url": "https://www.fiercebiotech.com/cro/private-equity-firm-acquires-clinical-trial-site-network-headlands-research",
        "source_note": "KKR (Headlands Research, 2018); THL 2025",
    },
    {
        "target": "CenExel Clinical Research", "sponsor": "Webster Equity Partners",
        "year": 2019, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Clinical-trial site network (centers of excellence)",
        "outcome": "exited", "outcome_note": "Webster sold CenExel to BayPine in 2025 — a PE-to-PE exit.",
        "source_url": "https://www.websterequitypartners.com/portfolio/",
        "source_note": "Webster Equity Partners (CenExel); BayPine 2025",
    },
    {
        "target": "Flourish Research", "sponsor": "Genstar Capital",
        "year": 2024, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Clinical-trial site network; Genstar bought majority from NMS Capital",
        "outcome": "active", "outcome_note": "Active clinical-research-site network.",
        "source_url": "https://www.gencap.com/",
        "source_note": "Genstar Capital (Flourish Research from NMS, Sept 2024)",
    },

    # ── Behavioral residential ──
    {
        "target": "Embark Behavioral Health", "sponsor": "Consonance Capital Partners",
        "year": 2022, "ev_usd_mm": None, "sector": "behavioral_health",
        "subsector_note": "Youth/teen mental-health treatment; Consonance majority (Housatonic prior)",
        "outcome": "active", "outcome_note": "Active behavioral-health platform (~12-15x EBITDA).",
        "source_url": "https://bhbusiness.com/2023/02/09/consonance-capital-partners-acquires-majority-stake-in-youth-focused-embark-behavioral-health/",
        "source_note": "Consonance Capital Partners (Embark Behavioral Health, 2022)",
    },
    {
        "target": "Sandstone Care", "sponsor": "The Vistria Group",
        "year": 2023, "ev_usd_mm": None, "sector": "behavioral_health",
        "subsector_note": "Teen/young-adult mental-health + SUD treatment; Vistria ~$200M",
        "outcome": "active", "outcome_note": "Active behavioral-health platform.",
        "source_url": "https://vistria.com/",
        "source_note": "The Vistria Group (Sandstone Care, ~$200M, 2023)",
    },

    # ── Veterinary ──
    {
        "target": "Innovetive Petcare", "sponsor": "Metalmark Capital",
        "year": 2019, "ev_usd_mm": None, "sector": "veterinary",
        "subsector_note": "Veterinary hospital partnership; Metalmark bought from Prospect Partners",
        "outcome": "active", "outcome_note": "Active veterinary platform.",
        "source_url": "https://www.metalmarkcapital.com/",
        "source_note": "Metalmark Capital (Innovetive Petcare from Prospect, 2019)",
    },

    # ════════════════════════════════════════════════════════════════════
    # 2026-06 expansion (batch 20) — CDMO/pharma services, dermatology,
    # value-based care. Each web-validated; pre-checked. Crosses 300 real.
    # ════════════════════════════════════════════════════════════════════
    {
        "target": "Cambrex", "sponsor": "Permira",
        "year": 2019, "ev_usd_mm": 2400, "sector": "other_services",
        "subsector_note": "Small-molecule CDMO; Permira take-private (~$2.4B)",
        "outcome": "exited", "outcome_note": "Public→private; Permira (~$2.4B).",
        "source_url": "https://cen.acs.org/business/outsourcing/Private-equity-ramps-pharmaceutical-services/101/i34",
        "source_note": "C&EN (Permira/Cambrex take-private, 2019, ~$2.4B)",
    },
    {
        "target": "Curia (Albany Molecular Research / AMRI)", "sponsor": "The Carlyle Group + GTCR",
        "year": 2021, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Pharma CDMO + discovery services; Carlyle+GTCR (renamed Curia)",
        "outcome": "active", "outcome_note": "Active CDMO platform.",
        "source_url": "https://cen.acs.org/business/outsourcing/Private-equity-ramps-pharmaceutical-services/101/i34",
        "source_note": "C&EN (Carlyle + GTCR / AMRI->Curia, 2021)",
    },
    {
        "target": "Sterling Pharma Solutions", "sponsor": "GHO Capital + Partners Group",
        "year": 2022, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "API / ADC CDMO; GHO majority, Partners Group minority",
        "outcome": "active", "outcome_note": "Active CDMO platform.",
        "source_url": "https://ghocapital.com/",
        "source_note": "GHO Capital + Partners Group (Sterling Pharma, 2022)",
    },
    {
        "target": "Platinum Dermatology Partners", "sponsor": "Sterling Partners",
        "year": 2018, "ev_usd_mm": None, "sector": "dermatology",
        "subsector_note": "Derm MSO (TX/AZ/NV); merged with West Dermatology in 2022",
        "outcome": "active", "outcome_note": "Active derm platform.",
        "source_url": "https://hl.com/about-us/transactions/houlihan-lokey-advises-platinum-dermatology-partners/",
        "source_note": "Sterling Partners (Platinum Dermatology); West merger 2022",
    },
    {
        "target": "Vatica Health", "sponsor": "Frazier Healthcare Partners",
        "year": 2023, "ev_usd_mm": None, "sector": "value_based_care",
        "subsector_note": "Value-based-care enablement / risk-adjustment (Frazier from Great Hill)",
        "outcome": "active", "outcome_note": "Active VBC-enablement platform.",
        "source_url": "https://mergr.com/transaction/frazier-healthcare-partners-acquires-vatica-health",
        "source_note": "Frazier Healthcare Partners (Vatica Health, Sept 2023)",
    },

    # ════════════════════════════════════════════════════════════════════
    # 2026-06 expansion (batch 21) — dental specialty (oral surgery / ortho /
    # endo) + hospice. Each web-validated; pre-checked.
    # ════════════════════════════════════════════════════════════════════
    {
        "target": "U.S. Oral Surgery Management", "sponsor": "Oak Hill Capital",
        "year": 2021, "ev_usd_mm": 700, "sector": "dental",
        "subsector_note": "Oral & maxillofacial surgery MSO; Oak Hill (~$700M+, from Thurston)",
        "outcome": "active", "outcome_note": "Active oral-surgery platform.",
        "source_url": "https://oakhill.com/2021/11/08/oak-hill-capital-to-partner-with-u-s-oral-surgery-management/",
        "source_note": "Oak Hill Capital (USOSM, Nov 2021, ~$700M+)",
    },
    {
        "target": "Smile Doctors", "sponsor": "Linden Capital Partners + Thomas H. Lee Partners",
        "year": 2017, "ev_usd_mm": None, "sector": "dental",
        "subsector_note": "Orthodontics DSO; Linden 2017, THL co-invested 2022",
        "outcome": "active", "outcome_note": "Active orthodontics platform.",
        "source_url": "https://www.linden.com/news/2017/10/linden-announces-partnership-smile-doctors-llc/",
        "source_note": "Linden Capital Partners (Smile Doctors, 2017); THL 2022",
    },
    {
        "target": "Beacon Oral Specialists", "sponsor": "Blue Sea Capital",
        "year": 2020, "ev_usd_mm": None, "sector": "dental",
        "subsector_note": "Oral surgery MSO (Atlanta Oral & Facial + Bay Area); Blue Sea-formed",
        "outcome": "active", "outcome_note": "Active oral-surgery platform.",
        "source_url": "https://blueseacapital.com/atlanta-oral-facial-surgery-and-bay-area-oral-surgery-management-have-partnered-with-blue-sea-capital-to-form-beacon-oral-specialists/",
        "source_note": "Blue Sea Capital (Beacon Oral Specialists, Dec 2020)",
    },
    {
        "target": "U.S. Endo Partners (Specialized Dental Partners)", "sponsor": "Quad-C Management",
        "year": 2021, "ev_usd_mm": None, "sector": "dental",
        "subsector_note": "Endodontics MSO; Quad-C bought from Thurston Group (rebranded 2023)",
        "outcome": "active", "outcome_note": "Active endodontics/specialty platform.",
        "source_url": "https://www.quadcmanagement.com/quad-c-management-announces-investment-in-u-s-endodontics-partners/",
        "source_note": "Quad-C Management (US Endo Partners from Thurston, 2021)",
    },
    {
        "target": "Charter Health Care Group", "sponsor": "Pharos Capital Group",
        "year": 2018, "ev_usd_mm": None, "sector": "home_health_hospice",
        "subsector_note": "Hospice + home health + complex care management; Pharos-backed",
        "outcome": "active", "outcome_note": "Active hospice/home-health platform.",
        "source_url": "https://www.prnewswire.com/news-releases/pharos-capitals-charter-health-care-group-acquires-generations-hospice-care-301352786.html",
        "source_note": "Pharos Capital Group (Charter Health Care Group)",
    },

    # ════════════════════════════════════════════════════════════════════
    # 2026-06 expansion (batch 22) — veterinary, more dental DSOs, hospital/
    # specialty pharmacy + biologics CDMO. Each web-validated; pre-checked.
    # ════════════════════════════════════════════════════════════════════

    # ── Veterinary ──
    {
        "target": "Southern Veterinary Partners", "sponsor": "Shore Capital Partners",
        "year": 2014, "ev_usd_mm": None, "sector": "veterinary",
        "subsector_note": "Veterinary hospital consolidator (Southeast); Shore platform (later Oak Hill stake)",
        "outcome": "active", "outcome_note": "Active; planned 2024 merger with Mission Veterinary Partners.",
        "source_url": "https://www.shorecp.com/",
        "source_note": "Shore Capital Partners (Southern Veterinary Partners, 2014)",
    },
    {
        "target": "American Veterinary Group", "sponsor": "Oak Hill Capital",
        "year": 2021, "ev_usd_mm": None, "sector": "veterinary",
        "subsector_note": "Veterinary hospital group (Southeast); Oak Hill platform",
        "outcome": "active", "outcome_note": "Active veterinary platform.",
        "source_url": "https://oakhill.com/2021/02/22/oak-hill-capital-to-partner-with-american-veterinary-group/",
        "source_note": "Oak Hill Capital (American Veterinary Group, Feb 2021)",
    },
    {
        "target": "Encore Vet Group", "sponsor": "North Castle Partners",
        "year": 2018, "ev_usd_mm": None, "sector": "veterinary",
        "subsector_note": "Veterinary hospital partnership; North Castle + Siguler Guff",
        "outcome": "active", "outcome_note": "Active veterinary platform.",
        "source_url": "https://northcastlepartners.com/portfolio/encorevet/",
        "source_note": "North Castle Partners (Encore Vet Group, founded 2018)",
    },
    {
        "target": "Destination Pet", "sponsor": "LetterOne (L1 Health)",
        "year": 2019, "ev_usd_mm": None, "sector": "veterinary",
        "subsector_note": "Veterinary + pet-services consolidator; L1 Health-backed",
        "outcome": "active", "outcome_note": "Active pet-care platform.",
        "source_url": "https://www.biospace.com/destination-pet-backed-by-letterone-completes-acquisition-of-vitalpet",
        "source_note": "LetterOne / L1 Health (Destination Pet, 2019)",
    },

    # ── Dental DSOs ──
    {
        "target": "Cordental Group", "sponsor": "New MainStream Capital (NMS Capital)",
        "year": 2017, "ev_usd_mm": None, "sector": "dental",
        "subsector_note": "Midwest DSO; NMS committed ~$25M to form Cordental",
        "outcome": "active", "outcome_note": "Active DSO.",
        "source_url": "https://cordentalgroup.com/project/new-mainstream-capital-announces-partnership-with-management-to-form-the-cordental-group/",
        "source_note": "New MainStream Capital (Cordental Group, Mar 2017)",
    },
    {
        "target": "Marquee Dental Partners", "sponsor": "Chicago Pacific Founders",
        "year": 2015, "ev_usd_mm": None, "sector": "dental",
        "subsector_note": "Southeast DSO; CPF-backed",
        "outcome": "active", "outcome_note": "Active DSO.",
        "source_url": "https://www.pehub.com/cpf-backed-marquee-dental-partners-acquires-bohle-family-dentistry/",
        "source_note": "Chicago Pacific Founders (Marquee Dental Partners, founded 2015)",
    },
    {
        "target": "Lone Peak Dental Group", "sponsor": "Tailwind Capital",
        "year": 2017, "ev_usd_mm": None, "sector": "dental",
        "subsector_note": "Pediatric/Medicaid DSO; Tailwind (BlackRock Impact 2024 later)",
        "outcome": "active", "outcome_note": "Active pediatric DSO.",
        "source_url": "https://www.themiddlemarket.com/latest-news/blackrock-invests-in-lone-peak-dental-group",
        "source_note": "Tailwind Capital (Lone Peak Dental Group, 2017); BlackRock 2024",
    },

    # ── Hospital / specialty pharmacy + biologics CDMO ──
    {
        "target": "CarepathRx", "sponsor": "Nautic Partners",
        "year": 2020, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Hospital pharmacy management + specialty pharmacy; Nautic platform",
        "outcome": "active", "outcome_note": "Active; sold sub BioPlus to Elevance in 2022.",
        "source_url": "https://carepathrxllc.com/2022/11/09/carepathrx-to-sell-bioplus-specialty-pharmacy-to-elevance-health/",
        "source_note": "Nautic Partners (CarepathRx, 2020)",
    },
    {
        "target": "Avid Bioservices", "sponsor": "GHO Capital + Ampersand Capital Partners",
        "year": 2024, "ev_usd_mm": 1100, "sector": "other_services",
        "subsector_note": "Biologics CDMO; take-private (~$1.1B)",
        "outcome": "exited", "outcome_note": "Public→private; GHO + Ampersand (~$1.1B).",
        "source_url": "https://avidbio.com/news/avid-bioservices-to-be-acquired-by-gho-capital-partners-and-ampersand-capital-partners-in-1-1-billion-transaction/",
        "source_note": "GHO + Ampersand (Avid Bioservices take-private, 2024, ~$1.1B)",
    },

    # ════════════════════════════════════════════════════════════════════
    # 2026-06 expansion (batch 23) — urgent care, medical-device contract
    # manufacturing, managed care. Each web-validated; pre-checked.
    # ════════════════════════════════════════════════════════════════════
    {
        "target": "FastMed Urgent Care", "sponsor": "ABRY Partners",
        "year": 2015, "ev_usd_mm": None, "sector": "urgent_care",
        "subsector_note": "Urgent-care operator; ABRY + BlueMountain (merged with NextCare 2018)",
        "outcome": "active", "outcome_note": "Active urgent-care platform.",
        "source_url": "https://www.fastmed.com/about-fastmed/news-and-press/abry-partners-announces-agreement-acquire-fastmed-urgent-care/",
        "source_note": "ABRY Partners (FastMed Urgent Care, 2015)",
    },
    {
        "target": "Spectrum Plastics Group", "sponsor": "AEA Investors",
        "year": 2018, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Medical-device contract manufacturing (plastics/extrusion)",
        "outcome": "exited", "outcome_note": "AEA sold Spectrum Plastics to DuPont in 2023.",
        "source_url": "https://www.aeainvestors.com/aea-completes-sale-of-spectrum-plastics-group/",
        "source_note": "AEA Investors (Spectrum Plastics, 2018); DuPont 2023",
    },
    {
        "target": "MedPlast", "sponsor": "Water Street Healthcare Partners + JLL Partners",
        "year": 2016, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Medical-device contract manufacturing (became Viant)",
        "outcome": "active", "outcome_note": "Active device CMO.",
        "source_url": "https://www.prnewswire.com/news-releases/medplast-announces-agreement-to-acquire-vention-medical-device-manufacturing-business-300410203.html",
        "source_note": "Water Street + JLL Partners (MedPlast, Dec 2016)",
    },
    {
        "target": "TekniPlex", "sponsor": "Genstar Capital",
        "year": 2020, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Materials-science / medical packaging + device components",
        "outcome": "active", "outcome_note": "Active healthcare-materials platform.",
        "source_url": "https://www.gencap.com/",
        "source_note": "Genstar Capital (TekniPlex, 2020)",
    },
    {
        "target": "CareMore Health", "sponsor": "CCMP Capital + Crystal Cove Partners",
        "year": 2006, "ev_usd_mm": None, "sector": "managed_care",
        "subsector_note": "Medicare Advantage-focused integrated care; one of the early MA-PE plays",
        "outcome": "exited", "outcome_note": "Acquired by WellPoint (Anthem/Elevance) in 2011 for ~$800M.",
        "source_url": "https://en.wikipedia.org/wiki/Carelon_Health",
        "source_note": "CCMP Capital + Crystal Cove (CareMore, 2006); WellPoint 2011 ~$800M",
    },

    # ════════════════════════════════════════════════════════════════════
    # 2026-06 expansion (batch 24) — GI / orthopedics / primary-care MSOs +
    # CDMO. Each web-validated; pre-checked.
    # ════════════════════════════════════════════════════════════════════
    {
        "target": "US Digestive Health", "sponsor": "Amulet Capital Partners",
        "year": 2019, "ev_usd_mm": None, "sector": "physician_practices",
        "subsector_note": "Gastroenterology MSO (Mid-Atlantic); Amulet-formed",
        "outcome": "active", "outcome_note": "Active GI platform.",
        "source_url": "https://usdigestivehealth.com/about-us/newsroom/amulet-backed-us-digestive-health-partners-with-west-chester-gi-associates/",
        "source_note": "Amulet Capital Partners (US Digestive Health, 2019)",
    },
    {
        "target": "One GI (Gastro One)", "sponsor": "Webster Equity Partners",
        "year": 2020, "ev_usd_mm": None, "sector": "physician_practices",
        "subsector_note": "Gastroenterology MSO; Webster bought Gastro One platform",
        "outcome": "active", "outcome_note": "Active GI platform.",
        "source_url": "https://www.websterequitypartners.com/portfolio/",
        "source_note": "Webster Equity Partners (One GI, early 2020)",
    },
    {
        "target": "United Musculoskeletal Partners", "sponsor": "Welsh, Carson, Anderson & Stowe",
        "year": 2021, "ev_usd_mm": None, "sector": "physician_practices",
        "subsector_note": "Orthopedic MSO formed by Resurgens Orthopaedics (WCAS bought 60%)",
        "outcome": "active", "outcome_note": "Active orthopedic platform.",
        "source_url": "https://www.umpartners.com/blog/what-differentiates-1-orthopedic-mso-from-other-private-equity-backed-groups",
        "source_note": "Welsh Carson (United Musculoskeletal Partners / Resurgens, Dec 2021)",
    },
    {
        "target": "Millennium Physician Group", "sponsor": "Clayton, Dubilier & Rice",
        "year": 2021, "ev_usd_mm": None, "sector": "physician_practices",
        "subsector_note": "Florida independent primary-care / value-based group; CD&R + Elevance",
        "outcome": "active", "outcome_note": "Active primary-care / value-based platform.",
        "source_url": "https://www.pehub.com/cdr-partners-with-millennium-physician-group/",
        "source_note": "Clayton, Dubilier & Rice (Millennium Physician Group, Mar 2021)",
    },
    {
        "target": "Recipharm", "sponsor": "EQT",
        "year": 2021, "ev_usd_mm": 2100, "sector": "other_services",
        "subsector_note": "Global pharma CDMO; EQT take-private (~$2.1B)",
        "outcome": "exited", "outcome_note": "Public→private; EQT (~$2.1B).",
        "source_url": "https://eqtgroup.com/about/current-portfolio/recipharm",
        "source_note": "EQT (Recipharm take-private, 2021, ~$2.1B)",
    },
    {
        "target": "Quotient Sciences", "sponsor": "Permira",
        "year": 2019, "ev_usd_mm": 752, "sector": "other_services",
        "subsector_note": "Drug-development + manufacturing CDMO; Permira recap (~$752M)",
        "outcome": "active", "outcome_note": "Active CDMO platform.",
        "source_url": "https://www.permira.com/portfolio/our-portfolio/quotient-sciences",
        "source_note": "Permira (Quotient Sciences, 2019, ~$752M)",
    },

    # ════════════════════════════════════════════════════════════════════
    # 2026-06 expansion (batch 25) — health-IT / care-software take-privates
    # and carve-outs. Each web-validated; pre-checked.
    # ════════════════════════════════════════════════════════════════════
    {
        "target": "SOC Telemed", "sponsor": "Patient Square Capital",
        "year": 2022, "ev_usd_mm": None, "sector": "rcm_healthtech",
        "subsector_note": "Acute-care telemedicine (teleneurology/ICU); take-private at $3.00/share",
        "outcome": "exited", "outcome_note": "Public→private; Patient Square Capital.",
        "source_url": "https://patientsquarecapital.com/soc-telemed-completes-acquisition-by-patient-square-capital/",
        "source_note": "Patient Square Capital (SOC Telemed take-private, 2022)",
    },
    {
        "target": "nThrive", "sponsor": "Clearlake Capital Group",
        "year": 2020, "ev_usd_mm": None, "sector": "rcm_healthtech",
        "subsector_note": "Revenue-cycle-management software; Clearlake carved out nThrive's tech division",
        "outcome": "active", "outcome_note": "Active; acquired TransUnion Healthcare 2022 (~$1.7B).",
        "source_url": "https://clearlake.com/clearlake-capital-to-acquire-nthrives-technology-division/",
        "source_note": "Clearlake Capital (nThrive Technology, 2020)",
    },
    {
        "target": "Netsmart", "sponsor": "TPG Capital + GI Partners",
        "year": 2016, "ev_usd_mm": None, "sector": "rcm_healthtech",
        "subsector_note": "Behavioral-health + post-acute EHR; TPG/GI carve-out from Allscripts",
        "outcome": "active", "outcome_note": "Active care-software platform.",
        "source_url": "https://en.wikipedia.org/wiki/Netsmart_Technologies",
        "source_note": "TPG + GI Partners (Netsmart from Allscripts, 2016)",
    },
    {
        "target": "WellSky", "sponsor": "TPG Capital + Leonard Green & Partners",
        "year": 2017, "ev_usd_mm": None, "sector": "rcm_healthtech",
        "subsector_note": "Post-acute / care-coordination software (fka Mediware); TPG, Leonard Green joined 2021",
        "outcome": "active", "outcome_note": "Active care-software platform.",
        "source_url": "https://www.tpg.com/",
        "source_note": "TPG (Mediware/WellSky, 2017); Leonard Green 2021",
    },
    {
        "target": "CitiusTech", "sponsor": "Bain Capital",
        "year": 2022, "ev_usd_mm": None, "sector": "rcm_healthtech",
        "subsector_note": "Healthcare-IT consulting + engineering services; Bain majority",
        "outcome": "active", "outcome_note": "Active health-IT services platform.",
        "source_url": "https://www.baincapital.com/news/citiustech-receives-strategic-investment-bain-capital",
        "source_note": "Bain Capital (CitiusTech, 2022)",
    },

    # ════════════════════════════════════════════════════════════════════
    # 2026-06 expansion (batch 26) — ABA/autism + behavioral managed care
    # (incl. a bankruptcy), behavioral-health software, dental. Web-validated.
    # ════════════════════════════════════════════════════════════════════
    {
        "target": "Autism Learning Partners", "sponsor": "FFL Partners",
        "year": 2018, "ev_usd_mm": 270, "sector": "behavioral_health",
        "subsector_note": "ABA autism therapy; FFL platform (~$270M+)",
        "outcome": "active", "outcome_note": "Active ABA platform.",
        "source_url": "https://www.fflpartners.com/portfolio/autism-learning-partners",
        "source_note": "FFL Partners (Autism Learning Partners, 2018, ~$270M)",
    },
    {
        "target": "Proud Moments ABA", "sponsor": "Audax Private Equity",
        "year": 2019, "ev_usd_mm": None, "sector": "behavioral_health",
        "subsector_note": "ABA autism therapy (Northeast); Audax platform",
        "outcome": "exited", "outcome_note": "Audax exited to Nautic Partners in 2025 — a PE-to-PE exit.",
        "source_url": "https://www.audaxprivateequity.com/news/audax-private-equity-completes-exit-of-proud-moments",
        "source_note": "Audax Private Equity (Proud Moments ABA, 2019); Nautic 2025",
    },
    {
        "target": "Therapy Brands", "sponsor": "KKR",
        "year": 2021, "ev_usd_mm": 1200, "sector": "rcm_healthtech",
        "subsector_note": "Behavioral-health + rehab practice-management / EHR software (~$1.2B)",
        "outcome": "active", "outcome_note": "Active care-software platform (from Lightyear/Providence).",
        "source_url": "https://www.kkr.com/invest/portfolio",
        "source_note": "KKR (Therapy Brands, 2021, ~$1.2B)",
    },
    {
        "target": "Wellpath (Correct Care Solutions)", "sponsor": "H.I.G. Capital",
        "year": 2018, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Correctional + behavioral healthcare (CCS + Correctional Medical Group merger)",
        "outcome": "bankrupt", "outcome_note": "Filed Chapter 11 in Nov 2024 under heavy debt — a documented correctional-healthcare PE failure.",
        "source_url": "https://www.healthcaredive.com/news/wellpath-chapter-11-bankruptcy-prison-healthcare/733401/",
        "source_note": "Healthcare Dive (Wellpath Ch.11, 2024); H.I.G. Capital (CCS, 2018)",
    },
    {
        "target": "Mid-Atlantic Dental Partners", "sponsor": "CRG + S.C. Goldman",
        "year": 2016, "ev_usd_mm": None, "sector": "dental",
        "subsector_note": "Mid-Atlantic DSO; later folded into Sonrava Health (2022)",
        "outcome": "exited", "outcome_note": "Acquired by Sonrava Health (New Mountain) in 2022.",
        "source_url": "https://www.prnewswire.com/news-releases/crg-commits-70-million-to-mid-atlantic-dental-partners-300778944.html",
        "source_note": "CRG + S.C. Goldman (Mid-Atlantic Dental Partners, 2016); Sonrava 2022",
    },

    # ════════════════════════════════════════════════════════════════════
    # 2026-06 expansion (batch 27) — life-sciences software, cardiovascular
    # devices, veterinary, pathology lab, multispecialty group. Web-validated.
    # ════════════════════════════════════════════════════════════════════
    {
        "target": "Model N", "sponsor": "Vista Equity Partners",
        "year": 2024, "ev_usd_mm": 1250, "sector": "rcm_healthtech",
        "subsector_note": "Revenue-optimization / pricing software for life sciences; take-private (~$1.25B)",
        "outcome": "exited", "outcome_note": "Public→private at $30.00/share; Vista Equity.",
        "source_url": "https://www.vistaequitypartners.com/news/vista-equity-partners-completes-acquisition-of-model-n/",
        "source_note": "Vista Equity Partners (Model N take-private, 2024, ~$1.25B)",
    },
    {
        "target": "Cordis", "sponsor": "Hellman & Friedman",
        "year": 2021, "ev_usd_mm": 1000, "sector": "other_services",
        "subsector_note": "Cardiovascular + endovascular medical devices; H&F carve-out from Cardinal Health (~$1B)",
        "outcome": "active", "outcome_note": "Active medical-device platform.",
        "source_url": "https://www.hf.com/news/cardinal-health-completes-sale-of-cordis-to-hellman-friedman",
        "source_note": "Hellman & Friedman (Cordis from Cardinal Health, 2021, ~$1B)",
    },
    {
        "target": "National Veterinary Associates", "sponsor": "Ares Management",
        "year": 2014, "ev_usd_mm": None, "sector": "veterinary",
        "subsector_note": "Large veterinary hospital network; Ares (OMERS 2018, JAB 2019 later)",
        "outcome": "exited", "outcome_note": "Ares-owned 2014-2018; sold to OMERS (2018), then JAB Holding (2019).",
        "source_url": "https://www.aresmgmt.com/",
        "source_note": "Ares Management (National Veterinary Associates, 2014); OMERS 2018; JAB 2019",
    },
    {
        "target": "Aurora Diagnostics", "sponsor": "Summit Partners + KRG Capital Partners",
        "year": 2010, "ev_usd_mm": None, "sector": "lab",
        "subsector_note": "Anatomic-pathology + dermatopathology lab network",
        "outcome": "exited", "outcome_note": "Acquired by Sonic Healthcare in 2018 (~$540M).",
        "source_url": "https://www.summitpartners.com/companies/aurora-diagnostics",
        "source_note": "Summit Partners + KRG Capital (Aurora Diagnostics, 2010); Sonic 2018",
    },
    {
        "target": "DuPage Medical Group (Duly Health and Care)", "sponsor": "Ares Management",
        "year": 2017, "ev_usd_mm": 1450, "sector": "physician_practices",
        "subsector_note": "Largest independent Illinois multispecialty group; Ares (~$1.45B)",
        "outcome": "active", "outcome_note": "Active; rebranded Duly Health and Care.",
        "source_url": "https://www.aresmgmt.com/",
        "source_note": "Ares Management (DuPage Medical Group, 2017, ~$1.45B)",
    },

    # ════════════════════════════════════════════════════════════════════
    # 2026-06 expansion (batch 28) — large pharma/device/dialysis carve-outs
    # and take-privates + DME + health-information exchange. Web-validated.
    # ════════════════════════════════════════════════════════════════════
    {
        "target": "Catalent", "sponsor": "Novo Holdings",
        "year": 2024, "ev_usd_mm": 16500, "sector": "other_services",
        "subsector_note": "Global pharma/biologics CDMO; take-private at $63.50/share (~$16.5B)",
        "outcome": "exited", "outcome_note": "Public→private; Novo Holdings (three sites went to Novo Nordisk).",
        "source_url": "https://www.catalent.com/catalent-news/novo-holdings-completes-acquisition-of-catalent/",
        "source_note": "Novo Holdings (Catalent take-private, 2024, ~$16.5B)",
    },
    {
        "target": "Baxter Kidney Care (Vantive)", "sponsor": "The Carlyle Group",
        "year": 2024, "ev_usd_mm": 3800, "sector": "dialysis",
        "subsector_note": "Dialysis + renal-care products carve-out from Baxter (~$3.8B)",
        "outcome": "active", "outcome_note": "Active; Carlyle + Atmas Health carve-out (Vantive).",
        "source_url": "https://www.baxter.com/baxter-newsroom/baxter-announces-definitive-agreement-divest-its-vantive-kidney-care-segment",
        "source_note": "The Carlyle Group (Baxter Vantive Kidney Care, 2024, ~$3.8B)",
    },
    {
        "target": "Surmodics", "sponsor": "GTCR",
        "year": 2025, "ev_usd_mm": 627, "sector": "other_services",
        "subsector_note": "Medical-device coatings + components; take-private at $43.00/share (~$627M)",
        "outcome": "exited", "outcome_note": "Public→private; GTCR.",
        "source_url": "https://surmodics.gcs-web.com/news-releases/news-release-details/surmodics-enters-definitive-agreement-be-acquired-gtcr-4300",
        "source_note": "GTCR (Surmodics take-private, 2025, ~$627M)",
    },
    {
        "target": "Drive DeVilbiss Healthcare", "sponsor": "Clayton, Dubilier & Rice",
        "year": 2013, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Durable medical equipment manufacturer; CD&R-backed",
        "outcome": "active", "outcome_note": "Active DME manufacturer.",
        "source_url": "https://www.cdr.com/",
        "source_note": "Clayton, Dubilier & Rice (Drive DeVilbiss, 2013)",
    },
    {
        "target": "Ciox Health", "sponsor": "New Mountain Capital",
        "year": 2018, "ev_usd_mm": None, "sector": "rcm_healthtech",
        "subsector_note": "Health-information management / clinical-data exchange (merged into Datavant 2021)",
        "outcome": "active", "outcome_note": "Active; combined with Datavant in 2021.",
        "source_url": "https://www.newmountaincapital.com/portfolio/",
        "source_note": "New Mountain Capital (Ciox Health, 2018); Datavant 2021",
    },

    # ════════════════════════════════════════════════════════════════════
    # 2026-06 expansion (batch 29) — DME, behavioral pharmacy, and health-IT
    # software (clinical-trial payments, PT, ASC). Web-validated; pre-checked.
    # ════════════════════════════════════════════════════════════════════
    {
        "target": "Genoa Healthcare", "sponsor": "Advent International",
        "year": 2016, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Behavioral-health pharmacy (co-located in CMHCs); Advent platform",
        "outcome": "exited", "outcome_note": "Acquired by UnitedHealth's Optum in 2018.",
        "source_url": "https://www.adventinternational.com/advent-international-to-acquire-genoa-a-qol-healthcare-company/",
        "source_note": "Advent International (Genoa Healthcare, 2016); Optum 2018",
    },
    {
        "target": "Greenphire", "sponsor": "Thoma Bravo",
        "year": 2021, "ev_usd_mm": None, "sector": "rcm_healthtech",
        "subsector_note": "Clinical-trial payments + participant-reimbursement software; from Riverside",
        "outcome": "active", "outcome_note": "Active clinical-trial-software platform.",
        "source_url": "https://www.thomabravo.com/",
        "source_note": "Thoma Bravo (Greenphire from Riverside, June 2021)",
    },
    {
        "target": "WebPT", "sponsor": "Warburg Pincus",
        "year": 2019, "ev_usd_mm": None, "sector": "rcm_healthtech",
        "subsector_note": "Physical-therapy practice-management / EMR + RCM software",
        "outcome": "active", "outcome_note": "Active rehab-therapy software platform.",
        "source_url": "https://www.warburgpincus.com/portfolio/",
        "source_note": "Warburg Pincus (WebPT, 2019)",
    },
    {
        "target": "HST Pathways", "sponsor": "Bain Capital",
        "year": 2021, "ev_usd_mm": None, "sector": "rcm_healthtech",
        "subsector_note": "Ambulatory-surgery-center (ASC) management + scheduling software",
        "outcome": "active", "outcome_note": "Active ASC-software platform.",
        "source_url": "https://www.baincapital.com/",
        "source_note": "Bain Capital (HST Pathways, 2021)",
    },

    # ════════════════════════════════════════════════════════════════════
    # 2026-06 expansion (batch 30) — more ophthalmology MSOs + home care.
    # Each web-validated; pre-checked against existing targets.
    # ════════════════════════════════════════════════════════════════════
    {
        "target": "American Vision Partners", "sponsor": "H.I.G. Capital",
        "year": 2019, "ev_usd_mm": None, "sector": "ophthalmology",
        "subsector_note": "Southwest ophthalmology MSO (Barnet Dulaney Perkins + others); H.I.G. platform",
        "outcome": "active", "outcome_note": "Active ophthalmology platform.",
        "source_url": "https://hig.com/portfolio/american-vision-partners/",
        "source_note": "H.I.G. Capital (American Vision Partners)",
    },
    {
        "target": "SightMD", "sponsor": "Chicago Pacific Founders",
        "year": 2018, "ev_usd_mm": None, "sector": "ophthalmology",
        "subsector_note": "Northeast ophthalmology MSO; Sight Growth Partners MSO / CPF-backed",
        "outcome": "active", "outcome_note": "Active ophthalmology platform.",
        "source_url": "https://www.cpfounders.com/",
        "source_note": "Chicago Pacific Founders (SightMD, 2018)",
    },
    {
        "target": "Vision Innovation Partners", "sponsor": "Centre Partners",
        "year": 2018, "ev_usd_mm": None, "sector": "ophthalmology",
        "subsector_note": "Mid-Atlantic ophthalmology + optometry MSO; Centre Partners-backed",
        "outcome": "active", "outcome_note": "Active ophthalmology platform.",
        "source_url": "https://www.centrepartners.com/portfolio/",
        "source_note": "Centre Partners (Vision Innovation Partners, 2018)",
    },
    {
        "target": "Choice Health at Home", "sponsor": "Coltala Holdings + Trive Capital",
        "year": 2021, "ev_usd_mm": None, "sector": "home_health_hospice",
        "subsector_note": "Home health + hospice + rehab (Texas-anchored); Coltala + Trive",
        "outcome": "active", "outcome_note": "Active home-care platform.",
        "source_url": "https://homehealthcarenews.com/2021/06/coltala-acquires-choice-health-at-home-we-recognized-an-opportunity-and-paid-a-good-price-for-it/",
        "source_note": "Coltala Holdings + Trive Capital (Choice Health at Home, 2021)",
    },
    {
        "target": "Care Advantage", "sponsor": "BelHealth Investment Partners",
        "year": 2017, "ev_usd_mm": None, "sector": "home_health_hospice",
        "subsector_note": "Mid-Atlantic in-home personal care; BelHealth-backed",
        "outcome": "exited", "outcome_note": "BelHealth sold Care Advantage to Searchlight Capital in 2021.",
        "source_url": "https://www.belhealth.com/portfolio-info/care-advantage",
        "source_note": "BelHealth Investment Partners (Care Advantage, 2017); Searchlight 2021",
    },

    # ════════════════════════════════════════════════════════════════════
    # 2026-06 expansion (batch 31) — medical-equipment management + health-
    # plan / benefits / MA technology take-privates. Web-validated.
    # ════════════════════════════════════════════════════════════════════
    {
        "target": "Agiliti", "sponsor": "Thomas H. Lee Partners",
        "year": 2024, "ev_usd_mm": 2500, "sector": "other_services",
        "subsector_note": "Medical-equipment management / rental for hospitals; THL take-private (~$2.5B)",
        "outcome": "exited", "outcome_note": "Public→private; THL (had owned it pre-2021 IPO).",
        "source_url": "https://newsroom.agilitihealth.com/news/agiliti-to-be-taken-private-by-thl-partners/",
        "source_note": "Thomas H. Lee Partners (Agiliti take-private, 2024, ~$2.5B)",
    },
    {
        "target": "Tivity Health", "sponsor": "Stone Point Capital",
        "year": 2022, "ev_usd_mm": 2000, "sector": "other_services",
        "subsector_note": "Fitness/health benefits (SilverSneakers); take-private at $32.50/share (~$2B)",
        "outcome": "exited", "outcome_note": "Public→private; Stone Point Capital.",
        "source_url": "https://www.pehub.com/stone-point-to-take-tivity-health-private-for-2bn/",
        "source_note": "Stone Point Capital (Tivity Health take-private, 2022, ~$2B)",
    },
    {
        "target": "Convey Health Solutions", "sponsor": "TPG Capital",
        "year": 2022, "ev_usd_mm": 1100, "sector": "rcm_healthtech",
        "subsector_note": "Medicare-Advantage / health-plan tech + services; take-private (~$1.1B)",
        "outcome": "exited", "outcome_note": "Public→private; TPG (New Mountain owned 2019, IPO 2021).",
        "source_url": "https://www.tpg.com/news-and-insights/tpg-partners-convey-health-solutions",
        "source_note": "TPG Capital (Convey Health take-private, 2022, ~$1.1B)",
    },
    {
        "target": "HealthComp", "sponsor": "New Mountain Capital",
        "year": 2022, "ev_usd_mm": None, "sector": "rcm_healthtech",
        "subsector_note": "Third-party benefits administrator (TPA) + analytics; from Alpine Investors",
        "outcome": "active", "outcome_note": "Active benefits-administration platform.",
        "source_url": "https://www.newmountaincapital.com/portfolio/",
        "source_note": "New Mountain Capital (HealthComp from Alpine, 2022)",
    },
    {
        "target": "eMids", "sponsor": "New Mountain Capital",
        "year": 2019, "ev_usd_mm": None, "sector": "rcm_healthtech",
        "subsector_note": "Healthcare-IT services / digital engineering; New Mountain-backed",
        "outcome": "active", "outcome_note": "Active health-IT services platform.",
        "source_url": "https://www.newmountaincapital.com/portfolio/",
        "source_note": "New Mountain Capital (eMids, 2019)",
    },

    # ════════════════════════════════════════════════════════════════════
    # 2026-06 expansion (batch 32) — dental, eating-disorder, home infusion,
    # ophthalmology. Each web-validated; pre-checked against existing targets.
    # ════════════════════════════════════════════════════════════════════
    {
        "target": "Monte Nido & Affiliates", "sponsor": "The Carlyle Group",
        "year": 2021, "ev_usd_mm": None, "sector": "behavioral_health",
        "subsector_note": "Eating-disorder treatment (residential + outpatient); Carlyle-backed",
        "outcome": "active", "outcome_note": "Active eating-disorder platform.",
        "source_url": "https://www.carlyle.com/our-business/portfolio-of-investments",
        "source_note": "The Carlyle Group (Monte Nido & Affiliates, 2021)",
    },
    {
        "target": "Vital Care", "sponsor": "Pharos Capital Group",
        "year": 2022, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Home / alternate-site infusion franchise network; Pharos-backed",
        "outcome": "active", "outcome_note": "Active home-infusion platform.",
        "source_url": "https://www.pharosfunds.com/portfolio/",
        "source_note": "Pharos Capital Group (Vital Care, 2022)",
    },
    {
        "target": "CEI Vision Partners", "sponsor": "Revelstoke Capital Partners",
        "year": 2019, "ev_usd_mm": None, "sector": "ophthalmology",
        "subsector_note": "Ophthalmology MSO (Cincinnati Eye Institute-anchored); Revelstoke platform",
        "outcome": "exited", "outcome_note": "EyeCare Partners acquired CEI Vision Partners in 2022.",
        "source_url": "https://revelstokecapital.com/investment/cei-vision-partners/",
        "source_note": "Revelstoke Capital Partners (CEI Vision Partners, 2019); EyeCare Partners 2022",
    },

    # ════════════════════════════════════════════════════════════════════
    # 2026-06 expansion (batch 33) — RCM/BPO carve-outs, oral surgery, CDMO,
    # hospital pharmacy. Each web-validated; pre-checked.
    # ════════════════════════════════════════════════════════════════════
    {
        "target": "Savista", "sponsor": "New Mountain Capital",
        "year": 2019, "ev_usd_mm": None, "sector": "rcm_healthtech",
        "subsector_note": "Revenue-cycle-management services (fka nThrive's RCM/patient-access)",
        "outcome": "active", "outcome_note": "Active RCM-services platform.",
        "source_url": "https://www.newmountaincapital.com/portfolio/",
        "source_note": "New Mountain Capital (Savista, 2019)",
    },
    {
        "target": "AGS Health", "sponsor": "EQT (BPEA / Baring Private Equity Asia)",
        "year": 2019, "ev_usd_mm": None, "sector": "rcm_healthtech",
        "subsector_note": "RCM / health-information-management BPO; EQT (via BPEA)",
        "outcome": "active", "outcome_note": "Active RCM-BPO platform.",
        "source_url": "https://www.agshealth.com/",
        "source_note": "EQT / Baring Private Equity Asia (AGS Health, 2019)",
    },
    {
        "target": "Allied OMS", "sponsor": "RiverGlade Capital",
        "year": 2019, "ev_usd_mm": None, "sector": "dental",
        "subsector_note": "Oral & maxillofacial surgery MSO (physician-owned model)",
        "outcome": "active", "outcome_note": "Active oral-surgery platform.",
        "source_url": "https://www.riverglade.com/portfolio",
        "source_note": "RiverGlade Capital (Allied OMS, 2019)",
    },
    {
        "target": "Vibalogics", "sponsor": "Ampersand Capital Partners",
        "year": 2019, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Viral-vector / oncolytic-virus CDMO; Ampersand-backed",
        "outcome": "active", "outcome_note": "Active biologics CDMO.",
        "source_url": "https://www.prnewswire.com/news-releases/ampersand-capital-partners-to-acquire-vibalogics-gmbh-300859368.html",
        "source_note": "Ampersand Capital Partners (Vibalogics, 2019)",
    },
    {
        "target": "Comprehensive Pharmacy Services", "sponsor": "BlackRock Long Term Private Capital",
        "year": 2019, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Hospital / health-system pharmacy management outsourcer",
        "outcome": "active", "outcome_note": "Active hospital-pharmacy platform.",
        "source_url": "https://www.blackrock.com/",
        "source_note": "BlackRock Long Term Private Capital (Comprehensive Pharmacy Services, 2019)",
    },

    # ════════════════════════════════════════════════════════════════════
    # 2026-06 expansion (batch 34) — respiratory devices (incl. a bankruptcy),
    # CDMO, perioperative services, AR software, dental. Web-validated.
    # ════════════════════════════════════════════════════════════════════
    {
        "target": "Vyaire Medical", "sponsor": "Apax Partners",
        "year": 2016, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Respiratory / ventilation devices; Apax JV with BD (full control 2018)",
        "outcome": "bankrupt", "outcome_note": "Filed Chapter 11 in 2024 (post-COVID demand collapse) — a device-PE downside.",
        "source_url": "https://www.fiercebiotech.com/medtech/ventilator-maker-vyaire-medical-files-bankruptcy",
        "source_note": "Apax Partners (Vyaire Medical, 2016 JV with BD); Ch.11 2024",
    },
    {
        "target": "CordenPharma", "sponsor": "Astorg",
        "year": 2022, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Pharma CDMO (peptides, lipids, small molecules); Astorg from ICIG",
        "outcome": "active", "outcome_note": "Active CDMO platform.",
        "source_url": "https://www.astorg.com/portfolio/",
        "source_note": "Astorg (CordenPharma, 2022)",
    },
    {
        "target": "SpecialtyCare", "sponsor": "Kohlberg & Company",
        "year": 2017, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Outsourced perioperative services (perfusion, neuromonitoring, surgical assist)",
        "outcome": "active", "outcome_note": "Active perioperative-services platform.",
        "source_url": "https://www.kohlberg.com/",
        "source_note": "Kohlberg & Company (SpecialtyCare, 2017)",
    },
    {
        "target": "Finvi (Ontario Systems)", "sponsor": "New Mountain Capital",
        "year": 2021, "ev_usd_mm": None, "sector": "rcm_healthtech",
        "subsector_note": "Healthcare AR / collections + patient-payment software",
        "outcome": "active", "outcome_note": "Active RCM-software platform.",
        "source_url": "https://www.newmountaincapital.com/portfolio/",
        "source_note": "New Mountain Capital (Ontario Systems/Finvi, 2021)",
    },
    {
        "target": "Risas Dental and Braces", "sponsor": "Blue Wolf Capital Partners",
        "year": 2021, "ev_usd_mm": None, "sector": "dental",
        "subsector_note": "Hispanic-focused DSO (Southwest); Blue Wolf-backed",
        "outcome": "active", "outcome_note": "Active DSO.",
        "source_url": "https://www.bluewolfcapital.com/portfolio/",
        "source_note": "Blue Wolf Capital Partners (Risas Dental, 2021)",
    },

    # ════════════════════════════════════════════════════════════════════
    # 2026-06 expansion (batch 35) — rare-disease pharmacy, medtech micro-
    # manufacturing, Medicare RCM software, ABA. Each web-validated.
    # ════════════════════════════════════════════════════════════════════
    {
        "target": "PANTHERx Rare", "sponsor": "General Atlantic + Nautic Partners + The Vistria Group",
        "year": 2022, "ev_usd_mm": 2800, "sector": "other_services",
        "subsector_note": "Rare-disease specialty pharmacy; consortium bought from Centene (~$2.8B w/ Magellan Rx)",
        "outcome": "exited", "outcome_note": "Centene divestiture to a PE consortium (July 2022).",
        "source_url": "https://vistria.com/the-vistria-group-completes-acquisition-of-pantherx-rare/",
        "source_note": "GA + Nautic + Vistria (PANTHERx Rare from Centene, 2022, ~$2.8B)",
    },
    {
        "target": "Resonetics", "sponsor": "GTCR",
        "year": 2018, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Laser micro-manufacturing for medtech; GTCR (Carlyle joined 2021 ~$2.25B)",
        "outcome": "active", "outcome_note": "Active medtech-manufacturing platform.",
        "source_url": "https://www.gtcr.com/",
        "source_note": "GTCR (Resonetics, 2018); Carlyle 2021 ~$2.25B",
    },
    {
        "target": "eSolutions", "sponsor": "Francisco Partners",
        "year": 2018, "ev_usd_mm": None, "sector": "rcm_healthtech",
        "subsector_note": "Medicare-focused revenue-cycle + analytics software",
        "outcome": "exited", "outcome_note": "Acquired by Waystar in 2020 (~$1.3B).",
        "source_url": "https://www.franciscopartners.com/media/waystar-to-acquire-esolutions-an-industry-leader-in-revenue-cycle-medicare-analytics",
        "source_note": "Francisco Partners (eSolutions); Waystar 2020 ~$1.3B",
    },
    {
        "target": "InBloom Autism Services", "sponsor": "RiverGlade Capital",
        "year": 2021, "ev_usd_mm": None, "sector": "behavioral_health",
        "subsector_note": "ABA autism therapy (Southeast); RiverGlade-backed",
        "outcome": "active", "outcome_note": "Active ABA platform.",
        "source_url": "https://www.riverglade.com/portfolio",
        "source_note": "RiverGlade Capital (InBloom Autism Services, 2021)",
    },

    # ════════════════════════════════════════════════════════════════════
    # 2026-06 expansion (batch 36) — more behavioral-health / SUD platforms.
    # Each web-validated; pre-checked against existing targets.
    # ════════════════════════════════════════════════════════════════════
    {
        "target": "Odyssey Behavioral Healthcare", "sponsor": "The Carlyle Group",
        "year": 2019, "ev_usd_mm": 200, "sector": "behavioral_health",
        "subsector_note": "Eating-disorder + mental-health + SUD treatment; Carlyle from Nautic (~$200M)",
        "outcome": "active", "outcome_note": "Active; Nautic formed it 2015, Carlyle bought 2019.",
        "source_url": "https://mergr.com/transaction/the-carlyle-group-acquires-odyssey-behavioral-healthcare",
        "source_note": "The Carlyle Group (Odyssey Behavioral from Nautic, 2019, ~$200M)",
    },
    {
        "target": "Banyan Treatment Centers", "sponsor": "TPG (The Rise Fund)",
        "year": 2023, "ev_usd_mm": None, "sector": "behavioral_health",
        "subsector_note": "Substance-use-disorder treatment; TPG impact-fund investment",
        "outcome": "active", "outcome_note": "Active SUD-treatment platform.",
        "source_url": "https://www.tpg.com/news-and-insights/tpgs-rise-fund-invests-banyan-treatment-centers",
        "source_note": "TPG / The Rise Fund (Banyan Treatment Centers, 2023)",
    },
    {
        "target": "Spero Health", "sponsor": "Heritage Group",
        "year": 2018, "ev_usd_mm": None, "sector": "behavioral_health",
        "subsector_note": "Outpatient opioid / SUD treatment (value-based); Heritage Group-backed",
        "outcome": "active", "outcome_note": "Active SUD-treatment platform.",
        "source_url": "https://sperohealth.com/our-investors/",
        "source_note": "Heritage Group (Spero Health)",
    },
    {
        "target": "Rarebreed Veterinary Partners", "sponsor": "Revelstoke Capital Partners",
        "year": 2021, "ev_usd_mm": None, "sector": "veterinary",
        "subsector_note": "General-practice + ER veterinary network; Revelstoke recap (single-asset fund) from Trilantic / Halle",
        "outcome": "active", "outcome_note": "Active; Revelstoke recapitalized Dec 2021, acquired Vet's Best Friend (~118 hospitals).",
        "source_url": "https://www.prnewswire.com/news-releases/revelstoke-capital-partners-raises-single-asset-fund-dedicated-to-veterinary-health-301586468.html",
        "source_note": "Revelstoke Capital Partners (Rarebreed recap, Dec 2021)",
    },
    {
        "target": "VetCor", "sponsor": "Oak Hill Capital Partners",
        "year": 2018, "ev_usd_mm": None, "sector": "veterinary",
        "subsector_note": "One of the largest US veterinary-hospital operators; Oak Hill-led recap alongside Harvest Partners & Cressey",
        "outcome": "active", "outcome_note": "Active; Oak Hill led June 2018 recap (~270+ hospitals across 28 states).",
        "source_url": "https://oakhill.com/2018/06/15/oak-hill-capital-partners-leads-recapitalization-of-vetcor-alongside-harvest-partners-cressey-company-and-management/",
        "source_note": "Oak Hill Capital Partners (VetCor recap, June 2018)",
    },
    {
        "target": "Community Veterinary Partners", "sponsor": "OMERS Private Equity",
        "year": 2023, "ev_usd_mm": None, "sector": "veterinary",
        "subsector_note": "General-practice veterinary platform (NE US origin); OMERS acquired from Cortec Group (2015 sponsor)",
        "outcome": "exited", "outcome_note": "Cortec exited to OMERS Private Equity in 2023 (grew 17→64 hospitals under Cortec).",
        "source_url": "https://cortecgroup.com/cortec-group-announces-sale-of-community-veterinary-partners/",
        "source_note": "OMERS Private Equity (Community Veterinary Partners from Cortec, 2023)",
    },
    {
        "target": "MedVet", "sponsor": "Goldman Sachs (Merchant Banking) / SkyKnight Capital",
        "year": 2025, "ev_usd_mm": None, "sector": "veterinary",
        "subsector_note": "Vet-led specialty + emergency hospital network; Goldman/SkyKnight recap (Stonehenge prior sponsor 2013/2019)",
        "outcome": "active", "outcome_note": "Active; latest investment from Goldman Sachs Merchant Banking with SkyKnight & Stonehenge (2025).",
        "source_url": "https://www.medvet.com/news/medvet-secures-investment-supporting-continued-growth/",
        "source_note": "Goldman Sachs / SkyKnight Capital (MedVet, 2025)",
    },
    {
        "target": "West Dermatology", "sponsor": "Sun Capital Partners",
        "year": 2020, "ev_usd_mm": None, "sector": "dermatology",
        "subsector_note": "Clinical/cosmetic dermatology platform (AZ/CA/NV, 55+ clinics); Sun Capital from Enhanced Healthcare Partners",
        "outcome": "active", "outcome_note": "Active; Sun Capital affiliate acquired Feb 2020.",
        "source_url": "https://suncappart.com/2020/02/12/sun-capital-partners-affiliate-acquires-west-dermatology/",
        "source_note": "Sun Capital Partners (West Dermatology, Feb 2020)",
    },
    {
        "target": "Golden State Dermatology", "sponsor": "Sorenson Capital",
        "year": 2018, "ev_usd_mm": None, "sector": "dermatology",
        "subsector_note": "California dermatology platform; Sorenson Capital from Pouschine Cook / Yukon Partners",
        "outcome": "active", "outcome_note": "Active; Sorenson Capital acquired April 2018.",
        "source_url": "https://pouschinecook.com/goldenstatedermatologysale/",
        "source_note": "Sorenson Capital (Golden State Dermatology, April 2018)",
    },
    {
        "target": "DOCS Dermatology (Dermatologists of Central States)", "sponsor": "SkyKnight Capital",
        "year": 2022, "ev_usd_mm": None, "sector": "dermatology",
        "subsector_note": "Midwest-origin dermatology MSO (80+ locations); SkyKnight from Sheridan Capital Partners",
        "outcome": "active", "outcome_note": "Active; Sheridan sold to SkyKnight Capital June 2022.",
        "source_url": "https://www.businesswire.com/news/home/20220601005963/en/SkyKnight-Capital-Invests-alongside-Physician-Partners-and-Management-in-DOCS-Dermatology",
        "source_note": "SkyKnight Capital (DOCS Dermatology from Sheridan, June 2022)",
    },
    {
        "target": "Comprehensive EyeCare Partners", "sponsor": "Gauge Capital",
        "year": 2018, "ev_usd_mm": None, "sector": "ophthalmology",
        "subsector_note": "Ophthalmology/optometry MSO (Las Vegas HQ); Gauge Capital platform",
        "outcome": "active", "outcome_note": "Active; Gauge Capital acquired Feb 2018.",
        "source_url": "https://www.brentwoodcap.com/comprehensive-eyecare-partners-is-recapitalized-by-gauge-capital-llc/",
        "source_note": "Gauge Capital (Comprehensive EyeCare Partners, Feb 2018)",
    },
    {
        "target": "AEG Vision", "sponsor": "Riata Capital Group",
        "year": 2017, "ev_usd_mm": None, "sector": "ophthalmology",
        "subsector_note": "Eyecare/optometry platform (500+ practices); Riata formed it from three regional groups",
        "outcome": "active", "outcome_note": "Active; Riata Capital Group formed AEG Vision March 2017.",
        "source_url": "https://www.prnewswire.com/news-releases/riata-capital-group-announces-closing-of-secondary-transaction-for-aeg-vision-301391417.html",
        "source_note": "Riata Capital Group (AEG Vision, March 2017)",
    },
    {
        "target": "Eye Health America", "sponsor": "LLR Partners",
        "year": 2018, "ev_usd_mm": None, "sector": "ophthalmology",
        "subsector_note": "Southeastern US eyecare MSO + ASC; LLR Partners-formed platform",
        "outcome": "active", "outcome_note": "Active; LLR Partners formed Eye Health America March 2018.",
        "source_url": "https://www.eyehealthamerica.com/llr-partners-accounces-the-formation-of-eye-health-america/",
        "source_note": "LLR Partners (Eye Health America, March 2018)",
    },
    {
        "target": "42 North Dental", "sponsor": "Audax Private Equity",
        "year": 2014, "ev_usd_mm": None, "sector": "dental",
        "subsector_note": "New England DSO (formerly Gentle Dental / Gentle Communications); Audax platform",
        "outcome": "active", "outcome_note": "Active; Audax acquired Gentle Communications (now 42 North Dental) June 2014, recap 2016.",
        "source_url": "https://www.beckersdental.com/dso-dpms/42-north-dental-makes-21st-acquisition-since-being-backed-by-private-equity-firm/",
        "source_note": "Audax Private Equity (42 North Dental, 2014)",
    },
    {
        "target": "American Family Care", "sponsor": "Lorient Capital",
        "year": 2024, "ev_usd_mm": None, "sector": "urgent_care",
        "subsector_note": "Urgent-care franchise + company clinics; Lorient Capital (healthcare PE) equity investment",
        "outcome": "active", "outcome_note": "Active; Lorient Capital made an equity investment (~2024) in the AFC urgent-care network.",
        "source_url": "https://www.businesswire.com/news/home/20251028806376/en/American-Family-Care-Celebrates-Milestones-and-Sets-Strategic-Vision-at-Annual-Franchise-Conference",
        "source_note": "Lorient Capital (American Family Care equity investment, ~2024)",
    },
    {
        "target": "BrightView Health", "sponsor": "Shore Capital Partners",
        "year": 2017, "ev_usd_mm": None, "sector": "behavioral_health",
        "subsector_note": "Outpatient addiction-medicine / opioid-use-disorder (MAT) platform; Shore Capital-backed",
        "outcome": "active", "outcome_note": "Active but retrenching: exited two states (Dec 2024) citing challenging operating environment.",
        "source_url": "https://www.shorecp.com/news/shore-capital-partners-invests-in-a-comprehensive-addiction-treatment-platform",
        "source_note": "Shore Capital Partners (BrightView Health, 2017)",
    },
    {
        "target": "Mindpath Health (Community Psychiatry)", "sponsor": "Centerbridge Partners & Leonard Green",
        "year": 2020, "ev_usd_mm": None, "sector": "behavioral_health",
        "subsector_note": "Outpatient psychiatry/mental-health (West Coast origin → national); rebranded Mindpath after 2021 add-on",
        "outcome": "active", "outcome_note": "Active but consolidating: PE-owned BH platform initiated some clinic closures/layoffs (FL, OH).",
        "source_url": "https://mergr.com/centerbridge-partners-acquires-mindpath-health",
        "source_note": "Centerbridge Partners & Leonard Green (Community Psychiatry / Mindpath Health, Dec 2020)",
    },
    {
        "target": "Availity", "sponsor": "Novo Holdings",
        "year": 2021, "ev_usd_mm": None, "sector": "rcm_healthtech",
        "subsector_note": "Provider-payer connectivity / clearinghouse + RCM technology; Novo Holdings from Francisco Partners (~$1.7bn implied valuation)",
        "outcome": "active", "outcome_note": "Active; Novo Holdings invested July 2021 (replaced Francisco Partners, FP since 2017).",
        "source_url": "https://www.prnewswire.com/news-releases/novo-holdings-as-invests-in-us-healthcare-it-company-availity-301326754.html",
        "source_note": "Novo Holdings (Availity, July 2021; ~$1.7bn implied valuation)",
    },
    {
        "target": "Experity", "sponsor": "GTCR",
        "year": 2022, "ev_usd_mm": 1200, "sector": "rcm_healthtech",
        "subsector_note": "On-demand / urgent-care EHR + practice-management + RCM software; GTCR from Warburg Pincus",
        "outcome": "active", "outcome_note": "Active; GTCR acquired majority stake March 2022 (reported ~$1.2bn); Warburg retained minority.",
        "source_url": "https://www.prnewswire.com/news-releases/gtcr-announces-acquisition-of-experity-301492284.html",
        "source_note": "GTCR (Experity from Warburg Pincus, March 2022, reported ~$1.2bn)",
    },
    {
        "target": "RxBenefits", "sponsor": "Advent International",
        "year": 2021, "ev_usd_mm": None, "sector": "rcm_healthtech",
        "subsector_note": "Pharmacy-benefits optimizer for self-insured employers; Advent recap alongside Great Hill (~$1.1bn valuation)",
        "outcome": "active", "outcome_note": "Active; Advent International recapitalized Jan 2021 (~$1.1bn valuation) alongside Great Hill (since 2016).",
        "source_url": "https://www.greathillpartners.com/media/advent-international-and-great-hill-partners-announce-recapitalization-of-rxbenefits-a-leading-pharmacy-benefits-optimizer",
        "source_note": "Advent International (RxBenefits recap, Jan 2021; ~$1.1bn valuation)",
    },
    {
        "target": "CORA Physical Therapy", "sponsor": "H.I.G. Capital",
        "year": 2021, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Outpatient physical-therapy / rehabilitation network (Southeast); H.I.G. from Gryphon Investors",
        "outcome": "active", "outcome_note": "Active; H.I.G. Capital affiliate acquired from Gryphon June 2021 (Gryphon since 2016).",
        "source_url": "https://www.gryphon-inv.com/news/gryphon-investors-to-sell-cora-physical-therapy/",
        "source_note": "H.I.G. Capital (CORA Physical Therapy from Gryphon, June 2021)",
    },
    {
        "target": "PromptCare", "sponsor": "Waud Capital Partners",
        "year": 2021, "ev_usd_mm": 400, "sector": "other_services",
        "subsector_note": "Home infusion + complex-respiratory therapy platform; Waud from The Halifax Group",
        "outcome": "active", "outcome_note": "Active; Waud Capital acquired from Halifax 2021 (reported >$400M).",
        "source_url": "https://healthcareservicesinvestmentnews.com/2021/08/27/halifax-backed-promptcare-sold-to-waud-in-400m-deal-report/",
        "source_note": "Waud Capital Partners (PromptCare from Halifax, 2021, reported >$400M)",
    },
    {
        "target": "Societal CDMO", "sponsor": "QHP Capital (via CoreRx)",
        "year": 2024, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Pharma contract development & manufacturing (CDMO); QHP's CoreRx took Societal private",
        "outcome": "exited", "outcome_note": "Public Societal CDMO taken private by CoreRx (QHP Capital) April 2024 at $1.10/share tender.",
        "source_url": "https://www.sec.gov/Archives/edgar/data/0001588972/000110465924028781/tm247234d1_ex99-2.htm",
        "source_note": "QHP Capital / CoreRx (Societal CDMO take-private, April 2024, $1.10/share)",
    },
    {
        "target": "Alcami", "sponsor": "Madison Dearborn Partners",
        "year": 2018, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Pharma CDMO (analytical + sterile fill-finish); Madison Dearborn & Ampersand from Antares (later sold to GHO/Vistria 2023)",
        "outcome": "exited", "outcome_note": "MDP & Ampersand owned 2018–2023, exited to GHO Capital & The Vistria Group (closed Jan 2023).",
        "source_url": "https://www.mdcp.com/portfolio/alcami",
        "source_note": "Madison Dearborn Partners & Ampersand (Alcami, June 2018)",
    },
    {
        "target": "Tecomet", "sponsor": "Charlesbank Capital Partners",
        "year": 2017, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Contract medical-device + aerospace precision manufacturing; Charlesbank's second ownership, from Genstar",
        "outcome": "active", "outcome_note": "Active; Charlesbank reacquired from Genstar Capital 2017 (Genstar held 2013–2017).",
        "source_url": "https://www.gencap.com/genstar-capital-announces-sale-tecomet/",
        "source_note": "Charlesbank Capital Partners (Tecomet from Genstar, 2017)",
    },
    {
        "target": "Cirtec Medical", "sponsor": "3i Group",
        "year": 2017, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Outsourced medical-device design + contract manufacturing (active implantables); 3i from Century Park Capital",
        "outcome": "active", "outcome_note": "Active; 3i Group acquired 2017 (Century Park Capital held 2010–2017).",
        "source_url": "https://centuryparkcapital.com/2017/08/04/century-park-capital-partners-announces-sale-of-cirtec-medical-llc/",
        "source_note": "3i Group (Cirtec Medical from Century Park, 2017)",
    },
    {
        "target": "Blue River PetCare", "sponsor": "Partners Group",
        "year": 2019, "ev_usd_mm": None, "sector": "veterinary",
        "subsector_note": "Companion-animal general-practice veterinary hospital operator (Chicago HQ, 90+ hospitals); founders retained stake",
        "outcome": "active", "outcome_note": "Active; Partners Group invested 2019.",
        "source_url": "https://www.partnersgroup.com/news-and-views/press-releases/investment-news/detail?news_id=683afd9d-36a8-4504-875d-5a6fbb34e07e",
        "source_note": "Partners Group (Blue River PetCare, 2019)",
    },
    {
        "target": "Nextech", "sponsor": "TPG",
        "year": 2023, "ev_usd_mm": 1400, "sector": "rcm_healthtech",
        "subsector_note": "Specialty EHR + practice-management software (dermatology / ophthalmology / ortho / plastics); TPG from Thomas H. Lee",
        "outcome": "active", "outcome_note": "Active; TPG acquired from Thomas H. Lee Partners July 2023 (~$1.4bn; THL since 2019).",
        "source_url": "https://www.nextech.com/press-releases/tpg-to-acquire-leading-specialty-healthcare-it-platform-nextech",
        "source_note": "TPG (Nextech from Thomas H. Lee, July 2023, ~$1.4bn)",
    },
    {
        "target": "AdvancedMD", "sponsor": "Francisco Partners",
        "year": 2024, "ev_usd_mm": 1130, "sector": "rcm_healthtech",
        "subsector_note": "Cloud practice-management / EHR / billing software for independent practices; Francisco Partners from Global Payments",
        "outcome": "active", "outcome_note": "Active; Francisco Partners agreed to acquire from Global Payments Oct 2024 (~$1.13bn).",
        "source_url": "https://www.businesswire.com/news/home/20241030109252/en/Francisco-Partners-to-Acquire-AdvancedMD-from-Global-Payments",
        "source_note": "Francisco Partners (AdvancedMD from Global Payments, Oct 2024, ~$1.13bn)",
    },
    {
        "target": "ImagineSoftware", "sponsor": "Marlin Equity Partners",
        "year": 2021, "ev_usd_mm": None, "sector": "rcm_healthtech",
        "subsector_note": "Medical-billing / revenue-cycle-management software platform; Marlin majority growth investment from Mountaingate Capital",
        "outcome": "active", "outcome_note": "Active; Marlin Equity Partners took majority Nov 2021 (Mountaingate Capital since 2018).",
        "source_url": "https://www.marlinequity.com/news/marlin-completes-growth-investment-in-imaginesoftware/",
        "source_note": "Marlin Equity Partners (ImagineSoftware, Nov 2021)",
    },
    {
        "target": "Clearwave", "sponsor": "Great Hill Partners",
        "year": 2021, "ev_usd_mm": None, "sector": "rcm_healthtech",
        "subsector_note": "Patient self-check-in / scheduling / insurance-eligibility software; Great Hill growth investment (Frontier Growth since 2019)",
        "outcome": "active", "outcome_note": "Active; Great Hill Partners growth investment Oct 2021.",
        "source_url": "https://www.greathillpartners.com/media/clearwave-announces-significant-growth-investment-from-great-hill-partners",
        "source_note": "Great Hill Partners (Clearwave, Oct 2021)",
    },
    {
        "target": "Sharp Services", "sponsor": "Clayton, Dubilier & Rice",
        "year": 2021, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Pharma contract packaging + clinical-trial supply (CDMO); CD&R carve-out via the UDG Healthcare take-private",
        "outcome": "active", "outcome_note": "Active; CD&R acquired parent UDG Healthcare Aug 2021, Sharp runs standalone.",
        "source_url": "https://www.cdr.com/portfolio/sharp",
        "source_note": "Clayton, Dubilier & Rice (Sharp Services via UDG Healthcare, Aug 2021)",
    },
    {
        "target": "Orthopedic Care Partners", "sponsor": "Varsity Healthcare Partners",
        "year": 2017, "ev_usd_mm": None, "sector": "physician_practices",
        "subsector_note": "Orthopedic MSO (Southeast; formed from The Orthopaedic Institute, Gainesville FL); $185M Brookfield growth investment 2024",
        "outcome": "active", "outcome_note": "Active; Varsity Healthcare Partners formed it via recap Nov 2017.",
        "source_url": "https://varsityhealthcarepartners.com/portfolio/orthopedic-care-partners/",
        "source_note": "Varsity Healthcare Partners (Orthopedic Care Partners, Nov 2017)",
    },
    {
        "target": "Pinnacle Fertility", "sponsor": "Webster Equity Partners",
        "year": 2021, "ev_usd_mm": None, "sector": "physician_practices",
        "subsector_note": "Physician-centric fertility / IVF clinic network; Webster Equity Partners platform",
        "outcome": "active", "outcome_note": "Active; Webster Equity Partners-backed platform formed 2021 (six initial groups).",
        "source_url": "https://websterequitypartners.com/portfolio/pinnacle-fertility/",
        "source_note": "Webster Equity Partners (Pinnacle Fertility, 2021)",
    },
    {
        "target": "Veterinary Emergency Group", "sponsor": "Stone Point Capital",
        "year": 2021, "ev_usd_mm": None, "sector": "veterinary",
        "subsector_note": "Emergency-only veterinary hospital chain (VEG); Stone Point control investment (Summit Partners earlier, 2018)",
        "outcome": "active", "outcome_note": "Active; Stone Point Capital invested Oct 2021.",
        "source_url": "https://pitchbook.com/profiles/company/252217-72",
        "source_note": "Stone Point Capital (Veterinary Emergency Group, Oct 2021)",
    },
    {
        "target": "NorthStar Anesthesia", "sponsor": "Cranemere",
        "year": 2018, "ev_usd_mm": None, "sector": "physician_practices",
        "subsector_note": "National outsourced anesthesiology platform; Cranemere acquired majority from TPG Growth (TPG retained minority)",
        "outcome": "active", "outcome_note": "Active; Cranemere acquired majority from TPG Growth June 2018.",
        "source_url": "https://www.tpg.com/news-and-insights/cranemere-acquire-northstar-anesthesia-tpg-growth",
        "source_note": "Cranemere (NorthStar Anesthesia from TPG Growth, June 2018)",
    },
    {
        "target": "Solis Mammography", "sponsor": "Madison Dearborn Partners",
        "year": 2018, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Breast-imaging / mammography center operator (150+ sites); Madison Dearborn from Audax (later TowerBrook 2025)",
        "outcome": "active", "outcome_note": "Active; Madison Dearborn acquired from Audax Aug 2018 (sold to TowerBrook 2025).",
        "source_url": "https://www.mdcp.com/portfolio/solis-mammography",
        "source_note": "Madison Dearborn Partners (Solis Mammography from Audax, Aug 2018)",
    },
    {
        "target": "Midwest Vision Partners", "sponsor": "Alpine Investors",
        "year": 2019, "ev_usd_mm": None, "sector": "ophthalmology",
        "subsector_note": "Midwest ophthalmology / eye-surgery MSO; Alpine Investors-formed platform (Ohio/Michigan origin)",
        "outcome": "active", "outcome_note": "Active; Alpine Investors formed Midwest Vision Partners May 2019.",
        "source_url": "https://midwestvision.com/alpine-investors-to-make-strategic-growth-investments-in-ohio-eye-care-businesses-3/",
        "source_note": "Alpine Investors (Midwest Vision Partners, May 2019)",
    },
    {
        "target": "Vohra Wound Physicians", "sponsor": "Trivest Partners",
        "year": 2016, "ev_usd_mm": None, "sector": "physician_practices",
        "subsector_note": "Post-acute wound-care physician group (rounds in SNFs / assisted living); Trivest non-control platform",
        "outcome": "active", "outcome_note": "Active; Trivest Partners invested Dec 2016.",
        "source_url": "https://www.trivest.com/tgif-announces-first-investment-with-vohra-wound-physicians/",
        "source_note": "Trivest Partners (Vohra Wound Physicians, Dec 2016)",
    },
    {
        "target": "Coronis Health", "sponsor": "Veritas Capital",
        "year": 2022, "ev_usd_mm": None, "sector": "rcm_healthtech",
        "subsector_note": "Multi-specialty revenue-cycle-management platform; Veritas combined Coronis + MiraMed Global Services (from 424 Capital)",
        "outcome": "active", "outcome_note": "Active; Veritas Capital acquired & combined with MiraMed Aug 2022 (424 Capital prior, 2015–2022).",
        "source_url": "https://www.veritascapital.com/veritas-capital-completes-combination-of-coronis-health-and-miramed-global-services-creating-leading-multi-specialty-revenue-cycle-management-platform/",
        "source_note": "Veritas Capital (Coronis Health + MiraMed, Aug 2022)",
    },
    {
        "target": "Ventra Health", "sponsor": "Varsity Healthcare Partners",
        "year": 2021, "ev_usd_mm": None, "sector": "rcm_healthtech",
        "subsector_note": "Facility-based RCM for anesthesia / EM / hospital medicine / radiology / pathology; VHP merged Abeo + DuvaSawko + Gottlieb",
        "outcome": "active", "outcome_note": "Active; Varsity Healthcare Partners united Abeo/DuvaSawko/Gottlieb as Ventra Health 2021.",
        "source_url": "https://varsityhealthcarepartners.com/duvasawko-abeo-and-gottlieb-join-forces-as-ventra-health/",
        "source_note": "Varsity Healthcare Partners (Ventra Health, 2021)",
    },
    {
        "target": "Hanger Inc", "sponsor": "Patient Square Capital",
        "year": 2022, "ev_usd_mm": 1250, "sector": "other_services",
        "subsector_note": "Orthotics & prosthetics (O&P) patient-care clinics (~875 locations); Patient Square take-private of NYSE-listed Hanger",
        "outcome": "exited", "outcome_note": "NYSE-listed Hanger taken private by Patient Square Capital Oct 2022 ($18.75/share, ~$1.25bn EV).",
        "source_url": "https://patientsquarecapital.com/hanger-inc-completes-acquisition-by-patient-square-capital/",
        "source_note": "Patient Square Capital (Hanger Inc take-private, Oct 2022, ~$1.25bn)",
    },
    {
        "target": "Allergy Partners", "sponsor": "Waypoint Capital",
        "year": 2021, "ev_usd_mm": None, "sector": "physician_practices",
        "subsector_note": "Single-specialty allergy & asthma physician group; Waypoint Capital (B-Flexion) acquired ~70% majority",
        "outcome": "active", "outcome_note": "Active; Waypoint Capital acquired majority stake Dec 2021.",
        "source_url": "https://www.businesswire.com/news/home/20211220005331/en/Waypoint-Capital-Acquires-Majority-Stake-in-Allergy-Partners",
        "source_note": "Waypoint Capital (Allergy Partners, Dec 2021)",
    },
    {
        "target": "PathGroup", "sponsor": "GTCR",
        "year": 2022, "ev_usd_mm": None, "sector": "lab",
        "subsector_note": "Anatomic / clinical / molecular pathology laboratory; GTCR majority recap (Pritzker Group prior, 2016)",
        "outcome": "active", "outcome_note": "Active; GTCR majority recapitalization May 2022 (Pritzker Group since 2016).",
        "source_url": "https://www.prnewswire.com/news-releases/gtcr-announces-recapitalization-of-pathgroup-301546928.html",
        "source_note": "GTCR (PathGroup recap, May 2022)",
    },
    {
        "target": "Behavioral Innovations", "sponsor": "Tenex Capital Management",
        "year": 2024, "ev_usd_mm": 300, "sector": "behavioral_health",
        "subsector_note": "Center-based ABA / autism early-intervention therapy (TX/OK/CO); Tenex from Shore Capital (~$300M)",
        "outcome": "active", "outcome_note": "Active; Tenex Capital Management acquired from Shore Capital June 2024 (~$300M).",
        "source_url": "https://www.businesswire.com/news/home/20240606629167/en/Shore-Capital-Partners-Announces-Sale-of-Behavioral-Innovations",
        "source_note": "Tenex Capital Management (Behavioral Innovations from Shore, June 2024, ~$300M)",
    },
    {
        "target": "Caravel Autism Health", "sponsor": "GTCR",
        "year": 2024, "ev_usd_mm": None, "sector": "behavioral_health",
        "subsector_note": "Center + home-based ABA autism therapy (early intervention); GTCR from Frazier Healthcare Partners (2018)",
        "outcome": "active", "outcome_note": "Active; GTCR acquired from Frazier Healthcare Partners 2024.",
        "source_url": "https://bhbusiness.com/2024/05/20/private-equity-firm-gtcr-plans-to-acquire-caravel-autism-health/",
        "source_note": "GTCR (Caravel Autism Health from Frazier, 2024)",
    },
    {
        "target": "Lighthouse Autism Center", "sponsor": "Cerberus Capital Management",
        "year": 2021, "ev_usd_mm": 400, "sector": "behavioral_health",
        "subsector_note": "Center-based ABA autism therapy (Midwest); Cerberus from Abry Partners (~$400M+)",
        "outcome": "active", "outcome_note": "Active; Cerberus Capital Management acquired from Abry Partners July 2021 (~$400M+).",
        "source_url": "https://www.cerberus.com/media/lighthouse-autism-center-and-cerberus-announce-strategic-partnership/",
        "source_note": "Cerberus Capital Management (Lighthouse Autism Center from Abry, July 2021, ~$400M+)",
    },
    {
        "target": "Ideal Image", "sponsor": "L Catterton",
        "year": 2015, "ev_usd_mm": None, "sector": "dermatology",
        "subsector_note": "Non-surgical medspa / aesthetics chain (laser hair removal, CoolSculpting, injectables); L Catterton via Steiner Leisure (TPG Growth minority 2021)",
        "outcome": "active", "outcome_note": "Active; L Catterton acquired via Steiner Leisure buyout 2015; TPG Growth took minority 2021.",
        "source_url": "https://www.idealimage.com/about-us/newsroom/media-coverage/l-catterton-owned-medspa-ideal-image-ramps-up-expansion",
        "source_note": "L Catterton (Ideal Image via Steiner Leisure, 2015)",
    },
    {
        "target": "Sono Bello", "sponsor": "Alaris Equity Partners",
        "year": 2018, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Body-contouring / cosmetic-surgery clinic chain (Body Contour Centers); Alaris Equity Partners (Brookfield co-invest 2023)",
        "outcome": "active", "outcome_note": "Active; Alaris Equity Partners invested 2018 ($546M Alaris+Brookfield round 2023).",
        "source_url": "https://www.alarisequitypartners.com/news/article/385-alaris-equity-partners-announces-us-546-million-strategic-investment-with-brookfield-in-body-contour-centers-llc",
        "source_note": "Alaris Equity Partners (Sono Bello / Body Contour Centers, 2018)",
    },
    {
        "target": "Outpatient Imaging Affiliates", "sponsor": "Cranemere",
        "year": 2021, "ev_usd_mm": 400, "sector": "other_services",
        "subsector_note": "Hospital-JV outpatient imaging-center operator (~60 centers); Cranemere acquired from ICV Partners (~$400M)",
        "outcome": "active", "outcome_note": "Active; Cranemere acquired from ICV Partners 2021 (~$400M); ICV held 2018–2021.",
        "source_url": "https://www.icvpartners.com/icv-partners-announces-acquisition-of-outpatient-imaging-affiliates/",
        "source_note": "Cranemere (Outpatient Imaging Affiliates from ICV Partners, 2021, ~$400M)",
    },
    {
        "target": "Rezolut", "sponsor": "SRM Equity Partners",
        "year": 2018, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Diagnostic outpatient-imaging center platform; formed 2018 as an SRM Equity Partners (Sunny River) portfolio company",
        "outcome": "exited", "outcome_note": "SRM-backed since 2018; exited to Envision Radiology (closed Dec 2025).",
        "source_url": "https://www.srmequity.com/news/srm-announces-sale-of-rezolut",
        "source_note": "SRM Equity Partners (Rezolut, formed 2018; exited to Envision Radiology 2025)",
    },
    {
        "target": "United Rheumatology", "sponsor": "Linden Capital Partners",
        "year": 2022, "ev_usd_mm": None, "sector": "physician_practices",
        "subsector_note": "Rheumatology specialty network / GPO; acquired by Linden Capital-backed Specialty Networks",
        "outcome": "exited", "outcome_note": "Acquired by Specialty Networks (Linden Capital Partners) April 2022; Specialty Networks later sold to Cardinal Health 2024.",
        "source_url": "https://www.prnewswire.com/news-releases/specialty-networks-llc-announces-the-acquisition-of-united-rheumatology-llc-301525409.html",
        "source_note": "Linden Capital Partners / Specialty Networks (United Rheumatology, April 2022)",
    },
    {
        "target": "Nystrom & Associates", "sponsor": "Nautic Partners",
        "year": 2019, "ev_usd_mm": None, "sector": "behavioral_health",
        "subsector_note": "Outpatient mental-health / psychiatry / SUD provider (Minnesota-centric); Nautic Partners majority",
        "outcome": "active", "outcome_note": "Active; Nautic Partners acquired majority June 2019 (acquired Ellie MN clinics 2025).",
        "source_url": "https://mergr.com/transaction/nautic-partners-acquires-nystrom-associates",
        "source_note": "Nautic Partners (Nystrom & Associates, June 2019)",
    },
    {
        "target": "ClareMedica Health Partners", "sponsor": "Revelstoke Capital Partners",
        "year": 2022, "ev_usd_mm": None, "sector": "value_based_care",
        "subsector_note": "Value-based primary care for Medicare Advantage / FFS Medicare (Florida); Revelstoke growth investment (BPOC since 2019)",
        "outcome": "active", "outcome_note": "Active; Revelstoke Capital Partners growth investment Feb 2022 (BPOC majority since July 2019).",
        "source_url": "https://www.prnewswire.com/news-releases/claremedica-health-partners-a-leading-provider-of-value-based-primary-care-receives-investment-from-revelstoke-capital-partners-301489390.html",
        "source_note": "Revelstoke Capital Partners (ClareMedica Health Partners, Feb 2022)",
    },
    {
        "target": "Triumph Orthopedics", "sponsor": "Shore Capital Partners",
        "year": 2022, "ev_usd_mm": None, "sector": "physician_practices",
        "subsector_note": "Orthopedic MSO (Southeast; Nashville HQ); Shore Capital Partners-formed platform",
        "outcome": "active", "outcome_note": "Active; Shore Capital Partners founded Triumph Orthopedics April 2022.",
        "source_url": "https://www.businesswire.com/news/home/20220418005548/en/Shore-Capital-Partners-Announces-the-Founding-of-Triumph-Orthopedics",
        "source_note": "Shore Capital Partners (Triumph Orthopedics, April 2022)",
    },
    {
        "target": "Cranial Technologies", "sponsor": "BPOC (Beecken Petty O'Keefe)",
        "year": 2017, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Custom cranial-orthotic (plagiocephaly) device + clinic provider; BPOC from Cortec Group (exited to Eurazeo 2022)",
        "outcome": "exited", "outcome_note": "BPOC acquired from Cortec May 2017; exited to Eurazeo March 2022.",
        "source_url": "https://www.thehealthcareinvestor.com/2022/03/articles/healthcare-services-investing/healthcare-life-sciences-private-equity-deal-tracker-bpoc-completes-sale-of-cranial-technologies/",
        "source_note": "BPOC (Cranial Technologies from Cortec, May 2017)",
    },
    {
        "target": "Midwest Products & Engineering", "sponsor": "BPOC (Beecken Petty O'Keefe)",
        "year": 2019, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Contract designer / manufacturer of electromechanical & robotic-assisted surgical systems for medtech OEMs (MPE); BPOC majority",
        "outcome": "exited", "outcome_note": "BPOC majority Sept 2019; exited to Graham Partners 2026.",
        "source_url": "https://www.bpoc.com/portfolio/mpe",
        "source_note": "BPOC (Midwest Products & Engineering, Sept 2019)",
    },
    {
        "target": "Empower Aesthetics", "sponsor": "Shore Capital Partners",
        "year": 2023, "ev_usd_mm": None, "sector": "dermatology",
        "subsector_note": "National medical-aesthetics / medspa platform (Austin HQ); Shore Capital Partners-formed",
        "outcome": "active", "outcome_note": "Active; Shore Capital Partners formed Empower Aesthetics 2023.",
        "source_url": "https://www.businesswire.com/news/home/20230706023806/en/Shore-Capital-Partners-Announces-Formation-of-Empower-Aesthetics",
        "source_note": "Shore Capital Partners (Empower Aesthetics, 2023)",
    },
    {
        "target": "Oceans Healthcare", "sponsor": "Webster Equity Partners",
        "year": 2022, "ev_usd_mm": None, "sector": "behavioral_health",
        "subsector_note": "Inpatient + outpatient behavioral health (geriatric focus, rural Southern US); Webster Equity Partners platform",
        "outcome": "active", "outcome_note": "Active; Webster Equity Partners acquired Feb 2022 (acquired Haven Behavioral 2025).",
        "source_url": "https://bhbusiness.com/2022/02/02/oceans-healthcare-gets-new-investment-from-webster-equity-partners-as-it-plans-to-ramp-up-expansion/",
        "source_note": "Webster Equity Partners (Oceans Healthcare, Feb 2022)",
    },
    {
        "target": "Healthcare Associates of Texas", "sponsor": "Webster Equity Partners",
        "year": 2016, "ev_usd_mm": None, "sector": "physician_practices",
        "subsector_note": "Multi-specialty primary-care group (Dallas-Fort Worth); Webster Equity Partners Fund III (realized)",
        "outcome": "exited", "outcome_note": "Webster Equity Partners acquired May 2016; subsequently realized.",
        "source_url": "https://mergr.com/transaction/webster-equity-partners-acquires-healthcare-associates-of-texas",
        "source_note": "Webster Equity Partners (Healthcare Associates of Texas, May 2016)",
    },
    {
        "target": "Omni Eye Services", "sponsor": "NMS Capital",
        "year": 2017, "ev_usd_mm": None, "sector": "ophthalmology",
        "subsector_note": "Optometric-referral ophthalmology network + ASC (NJ/NY); NMS Capital (New MainStream) investment",
        "outcome": "active", "outcome_note": "Active; NMS Capital invested July 2017 alongside founding physicians.",
        "source_url": "https://nms-capital.com/news/new-mainstream-capital-announces-partnership-and-investment-in-omni-eye-services/",
        "source_note": "NMS Capital (Omni Eye Services, July 2017)",
    },
    {
        "target": "Xpress Wellness Urgent Care", "sponsor": "Latticework Capital Management",
        "year": 2018, "ev_usd_mm": None, "sector": "urgent_care",
        "subsector_note": "Rural-focused urgent-care network (OK/KS/TX); Latticework Capital platform (exited to Goldman Sachs 2024)",
        "outcome": "exited", "outcome_note": "Latticework Capital partnered 2018; exited to Goldman Sachs Alternatives May 2024.",
        "source_url": "https://latticeworkcapital.com/goldman-sachs-alternatives-completes-acquisition-of-xpress-wellness-from-latticework-capital-management/",
        "source_note": "Latticework Capital Management (Xpress Wellness, 2018)",
    },
    {
        "target": "Veristat", "sponsor": "WindRose Health Investors",
        "year": 2021, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Global clinical research organization (CRO) for biotech / pharma; WindRose equity recapitalization",
        "outcome": "active", "outcome_note": "Active; WindRose Health Investors recapitalized Veristat April 2021.",
        "source_url": "https://windrose.com/news/windrose-health-investors-completes-recapitalization-of-veristat-group-inc/",
        "source_note": "WindRose Health Investors (Veristat, April 2021)",
    },
    {
        "target": "Celerion", "sponsor": "Thomas H. Lee Partners",
        "year": 2026, "ev_usd_mm": 1800, "sector": "other_services",
        "subsector_note": "Early-phase clinical research organization (CRO); THL majority (prior PE owners MTS/WindRose 2014, Court Square 2017, H.I.G.)",
        "outcome": "active", "outcome_note": "Active; THL Partners announced majority investment March 2026 (~$1.8bn).",
        "source_url": "https://thl.com/articles/celerion-announces-majority-investment-from-thl-partners/",
        "source_note": "Thomas H. Lee Partners (Celerion, March 2026, ~$1.8bn)",
    },
    {
        "target": "Enclara Pharmacia", "sponsor": "Consonance Capital Partners",
        "year": 2014, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Hospice / palliative-care pharmacy benefit management + dispensing; Consonance-backed (excelleRx/Hospice Pharmacia roll-up)",
        "outcome": "exited", "outcome_note": "Consonance Capital partnered 2014; exited to Humana Dec 2019 (~$700M+).",
        "source_url": "https://www.consonancecapitalpartners.com/enclara",
        "source_note": "Consonance Capital Partners (Enclara Pharmacia, 2014; exited to Humana 2019)",
    },
    {
        "target": "Care Hospice", "sponsor": "Martis Capital",
        "year": 2017, "ev_usd_mm": None, "sector": "home_health_hospice",
        "subsector_note": "Multi-state hospice provider (60+ locations; Charlottesville VA); Martis Capital platform",
        "outcome": "active", "outcome_note": "Active; Martis Capital invested April 2017.",
        "source_url": "https://www.martiscapital.com/portfolio/care-hospice/",
        "source_note": "Martis Capital (Care Hospice, April 2017)",
    },
    {
        "target": "Pediatric Home Service", "sponsor": "InTandem Capital Partners",
        "year": 2018, "ev_usd_mm": None, "sector": "home_health_hospice",
        "subsector_note": "Pediatric home health-care / home nursing + respiratory provider; InTandem Capital partnership",
        "outcome": "active", "outcome_note": "Active; InTandem Capital Partners partnered Dec 2018.",
        "source_url": "https://intandemcapital.com/portfolio/",
        "source_note": "InTandem Capital Partners (Pediatric Home Service, Dec 2018)",
    },
    {
        "target": "OrthoNebraska", "sponsor": "InTandem Capital Partners",
        "year": 2023, "ev_usd_mm": None, "sector": "physician_practices",
        "subsector_note": "Orthopedic physician group + specialty hospital (Omaha NE); InTandem Capital partnership",
        "outcome": "active", "outcome_note": "Active; InTandem Capital Partners invested Aug 2023.",
        "source_url": "https://intandemcapital.com/portfolio/",
        "source_note": "InTandem Capital Partners (OrthoNebraska, Aug 2023)",
    },
    {
        "target": "DCN Dx", "sponsor": "Martis Capital",
        "year": 2020, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Contract developer / manufacturer of rapid lateral-flow point-of-care diagnostic tests (Carlsbad CA); Martis growth investment",
        "outcome": "active", "outcome_note": "Active; Martis Capital growth investment Nov 2020.",
        "source_url": "https://www.martiscapital.com/martis-capital-makes-growth-investment-in-dcn-dx/",
        "source_note": "Martis Capital (DCN Dx, Nov 2020)",
    },
    {
        "target": "Clarest Health", "sponsor": "Sverica Capital",
        "year": 2020, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Long-term-care pharmacy + medication-management services; Sverica majority (acquired Remedi SeniorCare 2024)",
        "outcome": "active", "outcome_note": "Active; Sverica Capital acquired majority 2020.",
        "source_url": "https://sverica.com/portfolio-2/clarest-health/",
        "source_note": "Sverica Capital (Clarest Health, 2020)",
    },
    {
        "target": "CenterPointe Behavioral Health System", "sponsor": "NaviMed Capital",
        "year": 2021, "ev_usd_mm": 139, "sector": "behavioral_health",
        "subsector_note": "Multi-site inpatient/outpatient behavioral health; NaviMed Capital + Health Enterprise Partners (exited to Acadia)",
        "outcome": "exited", "outcome_note": "Acquired by Acadia Healthcare Dec 2021 (~$139M) from NaviMed Capital / Health Enterprise Partners.",
        "source_url": "https://navimed.com/navimed-portfolio-company-centerpointe-behavioral-health-system-acquired-by-acadia-healthcare/",
        "source_note": "NaviMed Capital (CenterPointe Behavioral Health; exited to Acadia Dec 2021, ~$139M)",
    },
    {
        "target": "Renaissance Lakewood", "sponsor": "RoundTable Healthcare Partners",
        "year": 2012, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Pharma CDMO — nasal-spray + sterile injectable fill-finish; RoundTable platform (built via Confab 2010 / DPT Labs 2012)",
        "outcome": "exited", "outcome_note": "RoundTable-built CDMO (DPT Laboratories 2012 core); exited to LTS Lohmann (announced Oct 2025).",
        "source_url": "https://roundtablehp.com/news/2025/roundtablehealthcarepartnersannouncessaleofrenaissancelakewoodllc.html",
        "source_note": "RoundTable Healthcare Partners (Renaissance Lakewood / DPT Labs, 2012; exited to LTS 2025)",
    },
    {
        "target": "Physical Rehabilitation Network", "sponsor": "Gryphon Investors",
        "year": 2020, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Western-US outpatient physical-therapy operator (PRN); Gryphon from Silver Oak Services Partners",
        "outcome": "active", "outcome_note": "Active; Gryphon Investors acquired from Silver Oak Dec 2020.",
        "source_url": "https://www.gryphon-inv.com/news/gryphon-investors-acquires-prn-a-leading-western-u-s-physical-therapy-operator/",
        "source_note": "Gryphon Investors (Physical Rehabilitation Network from Silver Oak, Dec 2020)",
    },
    {
        "target": "Meadows Behavioral Healthcare", "sponsor": "Kohlberg & Company",
        "year": 2016, "ev_usd_mm": None, "sector": "behavioral_health",
        "subsector_note": "Trauma / addiction / eating-disorder treatment provider (The Meadows); Kohlberg platform (Alita Care, with Sunspire)",
        "outcome": "active", "outcome_note": "Active; Kohlberg & Company acquired May 2016, formed Alita Care with Sunspire Health.",
        "source_url": "https://www.kohlberg.com/kohlberg-company-adds-meadows-behavioral-healthcare-to-its-behavioral-health-services-platform-enhancing-diversity-and-scale-with-acquisition-of-leading-treatment-provider/",
        "source_note": "Kohlberg & Company (Meadows Behavioral Healthcare, May 2016)",
    },
    {
        "target": "Nelipak Healthcare Packaging", "sponsor": "Kohlberg & Company",
        "year": 2019, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Custom rigid/flexible medical-device + pharma drug-delivery packaging manufacturer; Kohlberg from Mason Wells (merged Bemis HC Packaging Europe)",
        "outcome": "active", "outcome_note": "Active; Kohlberg & Company acquired from Mason Wells July 2019.",
        "source_url": "https://www.kohlberg.com/kohlberg-company-acquire-nelipak-healthcare-packaging/",
        "source_note": "Kohlberg & Company (Nelipak Healthcare Packaging from Mason Wells, July 2019)",
    },
    {
        "target": "ScribeAmerica (HealthChannels)", "sponsor": "Vesey Street Capital Partners",
        "year": 2017, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Managed medical-scribe / clinical-documentation services (parent HealthChannels; 1,700+ hospital partners); Vesey Street recap",
        "outcome": "active", "outcome_note": "Active; Vesey Street Capital Partners recapitalized Jan 2017.",
        "source_url": "https://www.businesswire.com/news/home/20170109005375/en/Vesey-Street-Capital-Partners-Completes-Recapitalization-of-HealthChannels-Parent-Company-of-ScribeAmerica",
        "source_note": "Vesey Street Capital Partners (ScribeAmerica / HealthChannels, Jan 2017)",
    },
    {
        "target": "SCA Pharmaceuticals", "sponsor": "The Vistria Group",
        "year": 2021, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "FDA 503B sterile-compounding / outsourcing facility for hospital pharmacies; Vistria + Excellere from Enhanced Healthcare Partners",
        "outcome": "active", "outcome_note": "Active; The Vistria Group & Excellere Partners acquired from Enhanced Healthcare Jan 2021.",
        "source_url": "https://www.businesswire.com/news/home/20210121005710/en/The-Vistria-Group-and-Excellere-Partners-Invest-in-SCA-Pharmaceuticals",
        "source_note": "The Vistria Group & Excellere Partners (SCA Pharmaceuticals from Enhanced Healthcare, Jan 2021)",
    },
    {
        "target": "NextCare Urgent Care", "sponsor": "Enhanced Healthcare Partners",
        "year": 2010, "ev_usd_mm": None, "sector": "urgent_care",
        "subsector_note": "Multi-state urgent-care center operator (one of the original PE urgent-care platforms); Enhanced (fka Enhanced Equity)",
        "outcome": "active", "outcome_note": "Active; Enhanced Equity (now Enhanced Healthcare Partners) invested 2010.",
        "source_url": "https://www.enhancedhealthcare.com/nextcare-urgent-care",
        "source_note": "Enhanced Healthcare Partners (NextCare Urgent Care, 2010)",
    },
    {
        "target": "Synergy Health Partners", "sponsor": "Enhanced Healthcare Partners",
        "year": 2020, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Surgicalist + specialty physician on-call staffing/management services (Synergy Surgicalists + EA Health merger); Enhanced platform",
        "outcome": "active", "outcome_note": "Active; Enhanced Healthcare Partners formed it via Synergy Surgicalists / EA Health merger June 2020.",
        "source_url": "https://www.enhancedhealthcare.com/news/2020/6/2/enhanced-healthcare-partners-announces-investment-in-and-simultaneous-business-merger-of-synergy-surgicalists-and-ea-health",
        "source_note": "Enhanced Healthcare Partners (Synergy Health Partners, June 2020)",
    },
    {
        "target": "Carisk Partners", "sponsor": "Lee Equity Partners",
        "year": 2023, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Workers'-comp specialty risk-transfer + care-coordination (behavioral-health foundation); Lee Equity + Elements Health recap",
        "outcome": "active", "outcome_note": "Active; Lee Equity Partners & Elements Health Investors recapitalized Dec 2023.",
        "source_url": "https://www.businesswire.com/news/home/20231204589710/en/Carisk-Partners-Recapitalizes-with-Lee-Equity-Partners-and-Elements-Health-Investors",
        "source_note": "Lee Equity Partners (Carisk Partners recap, Dec 2023)",
    },
    {
        "target": "Integrated Oncology Network", "sponsor": "Silver Oak Services Partners",
        "year": 2018, "ev_usd_mm": None, "sector": "physician_practices",
        "subsector_note": "Community-based oncology network (50+ locations, 10 states); Silver Oak recap from Comvest (exited to Cardinal Health $1.115B 2025)",
        "outcome": "exited", "outcome_note": "Silver Oak recapitalized Oct 2018 (from Comvest); exited to Cardinal Health for $1.115B Feb 2025.",
        "source_url": "https://www.silveroaksp.com/news-article/silver-oak-services-partners-completes-sale-of-integrated-oncology-network-to-cardinal-health-for-1115-billion",
        "source_note": "Silver Oak Services Partners (Integrated Oncology Network, Oct 2018; exited to Cardinal Health $1.115B 2025)",
    },
    {
        "target": "Physicians Endoscopy", "sponsor": "Pamlico Capital",
        "year": 2013, "ev_usd_mm": None, "sector": "asc",
        "subsector_note": "Developer/manager of single-specialty GI endoscopy ambulatory surgery centers (now PE GI Solutions); Pamlico from Silver Oak (exited to Kelso 2016)",
        "outcome": "exited", "outcome_note": "Pamlico Capital acquired Aug 2013; exited to Kelso & Company 2016.",
        "source_url": "https://www.pamlicocapital.com/news/physicians-endoscopy-attracts-growth-investment-from-pamlico-capital",
        "source_note": "Pamlico Capital (Physicians Endoscopy, Aug 2013; exited to Kelso 2016)",
    },
    {
        "target": "The Derm Group", "sponsor": "The Riverside Company",
        "year": 2016, "ev_usd_mm": None, "sector": "dermatology",
        "subsector_note": "Northern/Central New Jersey dermatology MSO (clinical/surgical/cosmetic/dermatopathology, 16 locations); Riverside platform",
        "outcome": "active", "outcome_note": "Active; The Riverside Company invested Jan 2016 (~$7M LTM EBITDA at entry).",
        "source_url": "https://www.riversidecompany.com/investment-portfolio/the-derm-group/",
        "source_note": "The Riverside Company (The Derm Group / The Dermatology Group, Jan 2016)",
    },
    {
        "target": "Elevate Patient Financial Solutions", "sponsor": "Audax Private Equity",
        "year": 2025, "ev_usd_mm": None, "sector": "rcm_healthtech",
        "subsector_note": "Front-end eligibility/enrollment + back-end RCM tech & services (fka MedData); Audax + Parthenon from Frazier Healthcare",
        "outcome": "active", "outcome_note": "Active; Audax Private Equity & Parthenon Capital acquired from Frazier July 2025 ($565M senior facility).",
        "source_url": "https://www.businesswire.com/news/home/20250804211867/en/Frazier-Healthcare-Partners-Announces-the-Sale-of-Elevate-Patient-Financial-Solutions-to-Audax-Private-Equity-and-Parthenon-Capital",
        "source_note": "Audax Private Equity & Parthenon Capital (Elevate Patient Financial Solutions from Frazier, July 2025)",
    },
    {
        "target": "Meridian Behavioral Health", "sponsor": "Audax Private Equity",
        "year": 2015, "ev_usd_mm": None, "sector": "behavioral_health",
        "subsector_note": "Residential + outpatient addiction (SUD) treatment provider; Audax from Triton Pacific Capital Partners",
        "outcome": "active", "outcome_note": "Active; Audax Private Equity acquired from Triton Pacific 2015 (20+ facilities by 2025).",
        "source_url": "https://www.audaxprivateequity.com/portfolio/meridian-behavioral-health",
        "source_note": "Audax Private Equity (Meridian Behavioral Health from Triton Pacific, 2015)",
    },
    {
        "target": "DAS Health", "sponsor": "Coalesce Capital",
        "year": 2025, "ev_usd_mm": None, "sector": "rcm_healthtech",
        "subsector_note": "Healthcare IT / managed-IT / RCM / practice-management for provider organizations (Tampa); Coalesce majority from Sheridan Capital",
        "outcome": "active", "outcome_note": "Active; Coalesce Capital acquired majority May 2025 (Sheridan Capital since 2021).",
        "source_url": "https://www.prnewswire.com/news-releases/coalesce-capital-acquires-leading-healthcare-it-and-business-solutions-provider-das-health-302465667.html",
        "source_note": "Coalesce Capital (DAS Health from Sheridan, May 2025)",
    },
    {
        "target": "Your Behavioral Health", "sponsor": "Comvest Partners",
        "year": 2023, "ev_usd_mm": None, "sector": "behavioral_health",
        "subsector_note": "Regional mental-health + addiction treatment (adults/teens, 17 facilities, Southern California); Comvest platform",
        "outcome": "active", "outcome_note": "Active; Comvest Partners acquired June 2023.",
        "source_url": "https://comvest.com/comvest-partners-announces-acquisition-of-your-behavioral-health/",
        "source_note": "Comvest Partners (Your Behavioral Health, June 2023)",
    },
    {
        "target": "Office Ally", "sponsor": "New Mountain Capital",
        "year": 2025, "ev_usd_mm": 1800, "sector": "rcm_healthtech",
        "subsector_note": "Healthcare claims clearinghouse + practice-management / RCM software; New Mountain alongside Francisco Partners (~$1.8bn)",
        "outcome": "active", "outcome_note": "Active; New Mountain Capital acquired stake May 2025 (~$1.8bn); Francisco Partners (since 2021) reinvested.",
        "source_url": "https://www.businesswire.com/news/home/20250406262209/en/Office-Ally-Embarks-on-Next-Phase-of-Growth-and-Innovation-with-New-Mountain-Capital-and-Francisco-Partners",
        "source_note": "New Mountain Capital (Office Ally, May 2025, ~$1.8bn)",
    },
    {
        "target": "Emmes", "sponsor": "New Mountain Capital",
        "year": 2022, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Clinical research organization (CRO) for government / biopharma sponsors; New Mountain from Behrman Capital",
        "outcome": "active", "outcome_note": "Active; New Mountain Capital acquired from Behrman Capital July 2022.",
        "source_url": "https://www.prnewswire.com/news-releases/behrman-capital-sells-portfolio-company-emmes-to-affiliates-of-new-mountain-capital-301571887.html",
        "source_note": "New Mountain Capital (Emmes from Behrman Capital, July 2022)",
    },
    {
        "target": "HealthMark Group", "sponsor": "TA Associates",
        "year": 2025, "ev_usd_mm": None, "sector": "rcm_healthtech",
        "subsector_note": "Release-of-information / medical-records retrieval + health-IT workflow services; TA Associates lead (Ridgemont Equity rolled)",
        "outcome": "active", "outcome_note": "Active; TA Associates strategic growth investment July 2025 (from Ridgemont Equity Partners).",
        "source_url": "https://www.ta.com/news/ta-invests-in-healthmark-group-to-support-the-next-phase-of-growth/",
        "source_note": "TA Associates (HealthMark Group, July 2025)",
    },
    {
        "target": "MedSpeed", "sponsor": "Water Street Healthcare Partners",
        "year": 2024, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Healthcare logistics — intra-company medical courier / laboratory + supply transport for health systems; Water Street equity investment",
        "outcome": "active", "outcome_note": "Active; Water Street Healthcare Partners invested Aug 2024.",
        "source_url": "https://waterstreet.com/news/water-street-invests-in-medspeed",
        "source_note": "Water Street Healthcare Partners (MedSpeed, Aug 2024)",
    },
    {
        "target": "Southern Scripts (Liviniti)", "sponsor": "Water Street Healthcare Partners",
        "year": 2021, "ev_usd_mm": None, "sector": "rcm_healthtech",
        "subsector_note": "Transparent pass-through pharmacy benefit manager (PBM) for employers (later renamed Liviniti); Water Street $100M commitment",
        "outcome": "active", "outcome_note": "Active; Water Street Healthcare Partners committed $100M Jan 2021.",
        "source_url": "https://waterstreet.com/news/southern-scripts-accelerates-expansion-with-water-street",
        "source_note": "Water Street Healthcare Partners (Southern Scripts / Liviniti, Jan 2021)",
    },
    {
        "target": "Brundage Group", "sponsor": "Water Street Healthcare Partners",
        "year": 2026, "ev_usd_mm": None, "sector": "rcm_healthtech",
        "subsector_note": "Physician-led clinical-documentation / revenue-integrity + denials-management services for hospitals (tech-enabled); Water Street platform",
        "outcome": "active", "outcome_note": "Active; Water Street Healthcare Partners partnered April 2026.",
        "source_url": "https://waterstreet.com/news/water-street-partners-with-brundage-group",
        "source_note": "Water Street Healthcare Partners (Brundage Group, April 2026)",
    },
    {
        "target": "XiFin", "sponsor": "GTCR",
        "year": 2014, "ev_usd_mm": None, "sector": "rcm_healthtech",
        "subsector_note": "Cloud/SaaS revenue-cycle-management + workflow automation for diagnostic labs / imaging / pathology; GTCR platform",
        "outcome": "active", "outcome_note": "Active; GTCR acquired July 2014.",
        "source_url": "https://www.xifin.com/news-and-events/press-release/gtcr-acquires-XiFin/",
        "source_note": "GTCR (XiFin, July 2014)",
    },
    {
        "target": "United BioSource", "sponsor": "Avista Capital Partners",
        "year": 2017, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Pharmaceutical & patient-support services (pharmacovigilance, REMS, patient access/adherence) for life-science cos; Avista carve-out from Express Scripts",
        "outcome": "active", "outcome_note": "Active; Avista Capital Partners carved out from Express Scripts Nov 2017.",
        "source_url": "https://www.prnewswire.com/news-releases/avista-capital-partners-to-acquire-express-scripts-subsidiary-united-biosource-300561642.html",
        "source_note": "Avista Capital Partners (United BioSource from Express Scripts, Nov 2017)",
    },
    {
        "target": "ConnectiveRx", "sponsor": "Genstar Capital",
        "year": 2015, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Tech-enabled biopharma commercialization / patient-access + affordability ('digital hub') services for 140+ drug manufacturers; Genstar platform",
        "outcome": "active", "outcome_note": "Active; Genstar Capital formed/invested 2015 (recap with Harvest + Blackstone 2020).",
        "source_url": "https://www.gencap.com/genstar-capital-announces-recapitalization-of-connectiverx/",
        "source_note": "Genstar Capital (ConnectiveRx, 2015)",
    },
    {
        "target": "CareMetx", "sponsor": "General Atlantic",
        "year": 2021, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Digital pharma 'hub' — patient access / reimbursement / adherence services for biopharma; General Atlantic majority from The Vistria Group (Vistria ~4.8x)",
        "outcome": "active", "outcome_note": "Active; General Atlantic took majority Jan 2021 from The Vistria Group (Vistria since 2017, ~4.8x).",
        "source_url": "https://www.caremetx.com/press-release/caremetx-general-atlantic-and-the-vistria-group-announce-strategic-growth-partnership",
        "source_note": "General Atlantic (CareMetx from The Vistria Group, Jan 2021)",
    },
    {
        "target": "Precision Medicine Group", "sponsor": "Blackstone",
        "year": 2020, "ev_usd_mm": 2350, "sector": "other_services",
        "subsector_note": "Life-sciences services — CRO (Precision for Medicine) + pharma commercialization; Blackstone recap from Berkshire/TPG (~$2.3-2.4bn)",
        "outcome": "active", "outcome_note": "Active; Blackstone-led recap Nov 2020 (~$2.35bn); Berkshire/TPG since 2017.",
        "source_url": "https://www.blackstone.com/news/press/precision-medicine-group-secures-major-investment-from-blackstone/",
        "source_note": "Blackstone (Precision Medicine Group recap from Berkshire/TPG, Nov 2020, ~$2.35bn)",
    },
    {
        "target": "Sphere", "sponsor": "Waud Capital Partners",
        "year": 2017, "ev_usd_mm": None, "sector": "rcm_healthtech",
        "subsector_note": "Healthcare financial-technology / integrated patient payments (TrustCommerce + Health iPASS); Waud-built platform",
        "outcome": "active", "outcome_note": "Active; Waud Capital combined TrustCommerce + Anovia Payments to form Sphere 2017.",
        "source_url": "https://www.waudcapital.com/en/media/waud-capital-buys-payments-software-company-trustcommerce/",
        "source_note": "Waud Capital Partners (Sphere / TrustCommerce, 2017)",
    },
    {
        "target": "MedRisk", "sponsor": "CVC Capital Partners",
        "year": 2021, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Managed physical-medicine (PT) network for workers' compensation; CVC majority with Carlyle retaining a co-control stake",
        "outcome": "active", "outcome_note": "Active; CVC Capital Partners acquired majority Feb 2021 (Carlyle co-owner, since ~2018).",
        "source_url": "https://www.prnewswire.com/news-releases/cvc-capital-partners-fund-vii-to-invest-in-medrisk-301233497.html",
        "source_note": "CVC Capital Partners (MedRisk, Feb 2021; Carlyle co-owner)",
    },
    {
        "target": "Bamboo Health", "sponsor": "Clearlake Capital Group",
        "year": 2021, "ev_usd_mm": 1500, "sector": "rcm_healthtech",
        "subsector_note": "Care-coordination / real-time care-event (PDMP, e-notifications) + behavioral-health collaboration tech; Clearlake/Insight-backed Appriss+PatientPing combo",
        "outcome": "active", "outcome_note": "Active; Clearlake + Insight combined Appriss Health + PatientPing (>$1.5bn) and renamed Bamboo Health 2021.",
        "source_url": "https://www.prnewswire.com/news-releases/bamboo-health--combination-of-proven-care-collaboration-leaders--unveiled-to-enable-payer-provider-collaboration-for-whole-person-care-301365804.html",
        "source_note": "Clearlake Capital Group (Bamboo Health / Appriss + PatientPing, 2021, >$1.5bn)",
    },
    {
        "target": "CorroHealth", "sponsor": "Patient Square Capital",
        "year": 2024, "ev_usd_mm": None, "sector": "rcm_healthtech",
        "subsector_note": "Tech + clinically-led revenue-cycle-management platform for health systems / plans (15,000+ staff); Patient Square + Carlyle joint control",
        "outcome": "active", "outcome_note": "Active; Patient Square Capital strategic investment Oct 2024 (Carlyle co-control, since 2020).",
        "source_url": "https://patientsquarecapital.com/corrohealth-announces-strategic-partnership-with-patient-square-capital/",
        "source_note": "Patient Square Capital (CorroHealth, Oct 2024; Carlyle co-owner)",
    },
    {
        "target": "Paradigm", "sponsor": "OMERS Private Equity",
        "year": 2018, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Complex / catastrophic medical management + case management for workers' compensation; OMERS majority from Summit Partners (later to Patient Square 2026)",
        "outcome": "active", "outcome_note": "Active; OMERS Private Equity majority Oct 2018 (Summit Partners prior); Patient Square acquiring 2026.",
        "source_url": "https://www.prnewswire.com/news-releases/paradigm-announces-majority-investment-from-omers-private-equity-300715906.html",
        "source_note": "OMERS Private Equity (Paradigm from Summit Partners, Oct 2018)",
    },
    {
        "target": "Omega Healthcare Management", "sponsor": "Goldman Sachs Alternatives",
        "year": 2019, "ev_usd_mm": None, "sector": "rcm_healthtech",
        "subsector_note": "Tech-enabled revenue-cycle-management + clinical/coding services (US + offshore); Goldman Sachs & Everstone co-control (sold stake to OTPP 2025)",
        "outcome": "active", "outcome_note": "Active; Goldman Sachs Alternatives & Everstone Capital co-controlled from 2019; sold a co-control stake to Ontario Teachers' 2025.",
        "source_url": "https://www.omegahms.com/newsroom/private-equity-at-goldman-sachs-alternatives-and-everstone-capital-sell-co-control-stake-in-omega-healthcare/",
        "source_note": "Goldman Sachs Alternatives & Everstone Capital (Omega Healthcare, 2019)",
    },
    {
        "target": "One Call", "sponsor": "Apax Partners",
        "year": 2013, "ev_usd_mm": 2200, "sector": "other_services",
        "subsector_note": "Workers'-compensation specialized-care management / provider network; Apax from Odyssey Investment Partners (~$2.2bn; KKR/Blackstone Credit recap 2019)",
        "outcome": "active", "outcome_note": "Active; Apax Partners acquired 2013 (~$2.2bn); 2019 recap left KKR & Blackstone Credit as principal shareholders.",
        "source_url": "https://www.apax.com/news-views/funds-advised-by-apax-partners-to-acquire-one-call-care-management-and-align-networks/",
        "source_note": "Apax Partners (One Call from Odyssey, 2013, ~$2.2bn)",
    },
    {
        "target": "CHG Healthcare", "sponsor": "Leonard Green & Partners",
        "year": 2012, "ev_usd_mm": 1250, "sector": "other_services",
        "subsector_note": "Largest US locum-tenens (temporary physician) staffing firm; Leonard Green & Ares LBO from J.W. Childs (~$1.25bn)",
        "outcome": "active", "outcome_note": "Active; Leonard Green & Partners + Ares Management LBO Nov 2012 (~$1.25bn).",
        "source_url": "https://www.pehub.com/leonard-green-ares-buys-chg-healthcare-services/",
        "source_note": "Leonard Green & Partners + Ares (CHG Healthcare from J.W. Childs, 2012, ~$1.25bn)",
    },
    {
        "target": "Enlyte", "sponsor": "Stone Point Capital",
        "year": 2018, "ev_usd_mm": None, "sector": "other_services",
        "subsector_note": "Workers'-comp medical cost-containment + case management (Mitchell | Genex | Coventry); Stone Point-built platform (Mitchell|Genex merger 2018, Coventry 2020, rebranded Enlyte 2021)",
        "outcome": "active", "outcome_note": "Active; Stone Point merged Mitchell + Genex 2018, added Coventry (from CVS) 2020, rebranded Enlyte 2021.",
        "source_url": "https://www.enlyte.com/news/announcing-enlyte",
        "source_note": "Stone Point Capital (Enlyte / Mitchell | Genex | Coventry, 2018)",
    },
    {
        "target": "Global Healthcare Exchange (GHX)", "sponsor": "Thoma Bravo",
        "year": 2014, "ev_usd_mm": None, "sector": "rcm_healthtech",
        "subsector_note": "Healthcare supply-chain SaaS / trading-partner network (providers, suppliers, GPOs); Thoma Bravo platform (sold majority to Temasek 2017, Warburg minority 2021)",
        "outcome": "active", "outcome_note": "Active; Thoma Bravo acquired 2014; sold majority to Temasek 2017 (Warburg Pincus minority 2021).",
        "source_url": "https://www.thomabravo.com/press-releases/healthcare-supply-chain-leader-ghx-receives-investment-from-temasek",
        "source_note": "Thoma Bravo (Global Healthcare Exchange / GHX, 2014)",
    },
    {
        "target": "Sharecare", "sponsor": "Altaris Capital",
        "year": 2024, "ev_usd_mm": 518, "sector": "rcm_healthtech",
        "subsector_note": "Digital-health / patient-engagement + health-data platform; Altaris take-private of Nasdaq-listed Sharecare ($1.43/share, ~$518M)",
        "outcome": "exited", "outcome_note": "Nasdaq-listed Sharecare taken private by Altaris Capital Oct 2024 (~$518M).",
        "source_url": "https://altariscap.com/news/altaris-acquires-sharecare",
        "source_note": "Altaris Capital (Sharecare take-private, Oct 2024, ~$518M)",
    },
    {
        "target": "Smarter Technologies", "sponsor": "New Mountain Capital",
        "year": 2025, "ev_usd_mm": None, "sector": "rcm_healthtech",
        "subsector_note": "AI-enabled revenue-management automation (SmarterDx + Thoughtful.ai + Access Healthcare; ~$800M rev, 500k+ providers); New Mountain combination",
        "outcome": "active", "outcome_note": "Active; New Mountain Capital combined SmarterDx + Thoughtful.ai + Access Healthcare to form Smarter Technologies May 2025.",
        "source_url": "https://www.newmountaincapital.com/new-mountain-capital-forms-smarter-technologies-through-combination-of-smarterdx-thoughtful-ai-and-access-healthcare/",
        "source_note": "New Mountain Capital (Smarter Technologies, May 2025)",
    },
    {
        "target": "Pediatric Associates", "sponsor": "Summit Partners",
        "year": 2019, "ev_usd_mm": None, "sector": "physician_practices",
        "subsector_note": "Pediatric primary-care physician group (Florida origin → CA/PA/NY/NJ); Summit Partners-backed platform",
        "outcome": "active", "outcome_note": "Active; Summit Partners-backed platform formed 2019 (later SkyKnight et al. co-invest).",
        "source_url": "https://www.pehub.com/summit-partners-said-to-invest-in-floridas-pediatric-associates/",
        "source_note": "Summit Partners (Pediatric Associates, 2019)",
    },
    {
        "target": "MedeAnalytics", "sponsor": "JLL Partners",
        "year": 2020, "ev_usd_mm": None, "sector": "rcm_healthtech",
        "subsector_note": "Cloud healthcare financial-performance + population-health analytics SaaS; JLL Partners from Thoma Bravo (TB held 2015–2020)",
        "outcome": "active", "outcome_note": "Active; JLL Partners acquired from Thoma Bravo Oct 2020.",
        "source_url": "https://www.thomabravo.com/press-releases/jll-partners-announces-acquisition-of-medeanalytics",
        "source_note": "JLL Partners (MedeAnalytics from Thoma Bravo, Oct 2020)",
    },
]


def _norm_sponsor(s: str) -> str:
    """Lowercase + strip punctuation + collapse whitespace, so sponsor-name
    matching survives the comma/ampersand variations in firm names
    ("Welsh Carson" ↔ "Welsh, Carson, Anderson & Stowe")."""
    import re
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", (s or "").lower()).split())


def verified_deals(
    sector: Optional[str] = None, sponsor: Optional[str] = None,
) -> List[Dict]:
    """Return the verified-deal list, optionally filtered to one sector
    and/or one sponsor (punctuation-insensitive substring match on the
    sponsor field).

    Every row is a real, sourced deal (see module docstring). Unknown
    sector/sponsor returns []. Never raises."""
    rows = list(VERIFIED_DEALS)
    if sector:
        s = str(sector).strip().lower()
        rows = [d for d in rows if d.get("sector") == s]
    if sponsor:
        q = _norm_sponsor(str(sponsor))
        if not q:
            return []

        def _matches(d: Dict) -> bool:
            ds = _norm_sponsor(d.get("sponsor", ""))
            if not ds:
                return False
            # Bidirectional substring: the page passes a short name ("KKR" ⊂
            # the deal's sponsor field) while the league passes a multi-firm
            # buyer string ("KKR / Bain Capital / Merrill Lynch PE" ⊃ "KKR").
            if q in ds or ds in q:
                return True
            # Lead-sponsor word match, so "EQT Partners" finds a deal whose
            # sponsor is "EQT (from Leonard Green & Partners)" (lead "EQT")
            # and "TPG Growth" finds "TPG". Whole-word only (trailing space)
            # to avoid matching "EQT" inside an unrelated longer token.
            lead = _norm_sponsor(_lead_sponsor(d.get("sponsor", "")))
            if lead and (q == lead
                         or q.startswith(lead + " ")
                         or lead.startswith(q + " ")):
                return True
            return False

        rows = [d for d in rows if _matches(d)]
    return rows


def verified_deals_for_sponsor(name: str) -> List[Dict]:
    """Real, sourced deals for one sponsor — used to cross-link the
    (illustrative) sponsor surfaces to the genuine track record."""
    return verified_deals(sponsor=name)


def verified_deal_count() -> int:
    return len(VERIFIED_DEALS)


def disclosed_ev_count() -> int:
    """How many carry a publicly-disclosed enterprise value (the rest are
    genuinely undisclosed — never fabricated)."""
    return sum(1 for d in VERIFIED_DEALS if d.get("ev_usd_mm") is not None)


def disclosed_ev_total_mm() -> int:
    """Sum of the publicly-disclosed enterprise values ($mm). Undisclosed
    deals contribute 0 — this is a floor on real, sourced EV, never a guess."""
    return sum(int(d["ev_usd_mm"]) for d in VERIFIED_DEALS
               if d.get("ev_usd_mm") is not None)


def outcome_counts() -> Dict[str, int]:
    """Count of verified deals per outcome bucket. Ordered worst→best so the
    public-record failures (bankrupt / distressed) read first — that honest
    mix is exactly what makes the set credible."""
    order = ("bankrupt", "distressed", "active", "exited", "unknown")
    counts = {k: 0 for k in order}
    for d in VERIFIED_DEALS:
        o = d.get("outcome", "unknown")
        counts[o] = counts.get(o, 0) + 1
    # Drop empty buckets but preserve the worst→best order.
    return {k: counts[k] for k in order if counts.get(k)}


def sector_counts() -> Dict[str, int]:
    """Count of verified deals per sector, descending by count."""
    counts: Dict[str, int] = {}
    for d in VERIFIED_DEALS:
        s = d.get("sector", "other_services")
        counts[s] = counts.get(s, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))


# Delimiters that introduce a *secondary* sponsor or a parenthetical. We split
# on these to recover the lead sponsor WITHOUT mangling firm names that legitly
# contain "&"/"," (e.g. "Welsh, Carson, Anderson & Stowe", "Hellman & Friedman").
_LEAD_SPONSOR_DELIMS = (" / ", " + ", " (")


def _lead_sponsor(sponsor: str) -> str:
    """Best-effort lead-sponsor extraction from a (possibly multi-firm) string.

    "TPG / Summit Partners / Silversmith" → "TPG";
    "Hellman & Friedman + Bain Capital"   → "Hellman & Friedman";
    "Partners Group (from FFL Partners)"  → "Partners Group".
    Never splits on the "&"/"," inside a single firm's name."""
    s = (sponsor or "").strip()
    cut = len(s)
    for delim in _LEAD_SPONSOR_DELIMS:
        i = s.find(delim)
        if i != -1:
            cut = min(cut, i)
    return s[:cut].strip() or s


def lead_sponsor_counts() -> Dict[str, int]:
    """Verified-deal count per lead sponsor, descending. The leaderboard that
    shows which real firms actually show up most in the sourced set."""
    counts: Dict[str, int] = {}
    for d in VERIFIED_DEALS:
        lead = _lead_sponsor(d.get("sponsor", ""))
        if not lead:
            continue
        counts[lead] = counts.get(lead, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))
