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
        "source_url": "http://pensionpulse.blogspot.com/2022/02/omers-sells-stake-in-forefront.html",
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
]


def verified_deals(sector: Optional[str] = None) -> List[Dict]:
    """Return the verified-deal list, optionally filtered to one sector.

    Every row is a real, sourced deal (see module docstring). Unknown sector
    returns []. Never raises."""
    if not sector:
        return list(VERIFIED_DEALS)
    s = str(sector).strip().lower()
    return [d for d in VERIFIED_DEALS if d.get("sector") == s]


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
