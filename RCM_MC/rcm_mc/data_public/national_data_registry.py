"""National public-data catalog — the map of every major U.S. health database.

The estate connectors (``connectors/``) cover the free, API-accessible
public data. But a research desk needs to know the *whole* universe of
national databases used in healthcare diligence — including the ones that
are NOT freely scrapable (HCUP's NEDS/NIS/NRD need a Data Use Agreement +
purchase; USRDS, NTDB, TEDS require registration). Pretending those can be
one-click ingested would be dishonest; omitting them would leave a partner
not knowing they exist.

So this is a curated, accurate catalog: what each national database is, who
publishes it, its **access model**, and — critically — whether PE Desk
already ingests it (``wired`` → an estate connector) or how you'd get it if
not. Nothing here is fetched; it is reference metadata about real databases.

Access models (``access``):
  estate     – already ingested by an estate connector (``wired`` names it);
               browse/query it now on /connector-estate and /data-hub.
  api        – free public HTTP API, not yet wired (candidate ingest).
  bulk       – free public-use files to download (no API), not yet wired.
  query      – free online query tool only; aggregate output, no microdata
               (e.g. HCUPnet, CDC WONDER web) — can't be bulk-ingested.
  restricted – requires a Data Use Agreement, registration, and/or purchase
               (HCUP nationwide/state files, USRDS, NTDB, TEDS). Documented
               here so a partner knows it exists and how to obtain it.

Keep entries ACCURATE — agency, access model, and URL are load-bearing. When
an estate connector graduates to cover a source, set ``access="estate"`` and
``wired`` to the connector name so the coverage stats stay honest.
"""
from __future__ import annotations

from typing import Dict, List

# Agency id -> display label, in render order.
AGENCIES: List[tuple] = [
    ("cms", "CMS — Centers for Medicare & Medicaid Services"),
    ("ahrq", "AHRQ — HCUP & national surveys"),
    ("cdc", "CDC / NCHS — surveillance & vital statistics"),
    ("samhsa", "SAMHSA — behavioral health"),
    ("hrsa", "HRSA — access, workforce & safety net"),
    ("census", "Census — demographics & coverage"),
    ("nih", "NIH / NCI — research & cancer"),
    ("fda", "FDA — drugs & devices"),
    ("other", "Other national registries"),
]

_ACCESS_ORDER = {"estate": 0, "api": 1, "bulk": 2, "query": 3, "restricted": 4}

# Each entry: id, name, agency, access, url, blurb, relevance, wired.
# ``wired`` = estate connector name when access == "estate", else "".
DATABASES: List[Dict[str, str]] = [
    # ── CMS ──────────────────────────────────────────────────────────────
    {"id": "cms_mup", "name": "Medicare Provider Utilization & Payment (Physician / Inpatient / Outpatient / DME / Part D)",
     "agency": "cms", "access": "estate", "wired": "cms_open_data",
     "url": "https://data.cms.gov/provider-summary-by-type-of-service",
     "blurb": "Provider- and service-level Medicare fee-for-service volumes, charges, allowed amounts, and payments.",
     "relevance": "Provider productivity, billing-pattern and site-of-service analysis, revenue benchmarking."},
    {"id": "cms_geovar", "name": "Medicare Geographic Variation", "agency": "cms",
     "access": "estate", "wired": "cms_open_data",
     "url": "https://data.cms.gov/summary-statistics-on-use-and-payments/medicare-geographic-comparisons",
     "blurb": "State/county per-capita Medicare spending, utilization, and demographic/health-status indices.",
     "relevance": "Market spend intensity, utilization outliers, rate-setting context."},
    {"id": "cms_market_sat", "name": "Market Saturation & Utilization", "agency": "cms",
     "access": "estate", "wired": "cms_open_data",
     "url": "https://data.cms.gov/summary-statistics-on-use-and-payments/program-integrity-market-saturation-by-type-of-service",
     "blurb": "County/CBSA provider and beneficiary counts by service type — a saturation and fraud-risk lens.",
     "relevance": "Roll-up whitespace, competitive density, program-integrity risk."},
    {"id": "cms_enrollment", "name": "Medicare Monthly Enrollment", "agency": "cms",
     "access": "estate", "wired": "cms_open_data",
     "url": "https://data.cms.gov/summary-statistics-on-beneficiary-enrollment/medicare-and-medicaid-reports/medicare-monthly-enrollment",
     "blurb": "Monthly Medicare enrollment by geography, entitlement, and MA-vs-FFS split.",
     "relevance": "Addressable-lives sizing, MA penetration trend."},
    {"id": "cms_open_payments", "name": "Open Payments (Sunshine Act)", "agency": "cms",
     "access": "estate", "wired": "open_payments",
     "url": "https://openpaymentsdata.cms.gov/",
     "blurb": "Manufacturer/GPO payments and ownership interests to physicians and teaching hospitals.",
     "relevance": "Conflict-of-interest screening, FCA/DOJ diligence, KOL mapping."},
    {"id": "cms_pos", "name": "Provider of Services (POS)", "agency": "cms",
     "access": "estate", "wired": "cms_open_data",
     "url": "https://data.cms.gov/provider-characteristics/hospitals-and-other-facilities/provider-of-services-file-hospital-non-hospital-facilities",
     "blurb": "Certification-level characteristics for every Medicare-certified facility (beds, type, ownership).",
     "relevance": "Facility universe, bed counts, ownership structure."},
    {"id": "cms_hcris", "name": "Medicare Cost Reports (HCRIS)", "agency": "cms",
     "access": "estate", "wired": "cms_open_data",
     "url": "https://www.cms.gov/data-research/statistics-trends-reports/cost-reports",
     "blurb": "Annual audited-basis cost reports for hospitals, SNFs, HHAs, hospices, RHCs, FQHCs.",
     "relevance": "Operating margin, payer mix, occupancy, case-mix — core provider diligence."},
    {"id": "cms_care_compare", "name": "Care Compare (Hospital / SNF / Home Health / Hospice / Dialysis)",
     "agency": "cms", "access": "estate", "wired": "provider_data",
     "url": "https://data.cms.gov/provider-data/",
     "blurb": "Quality, staffing, deficiency, and star-rating measures across every Care Compare setting.",
     "relevance": "Quality benchmarking, VBP exposure, deficiency risk."},
    {"id": "cms_partd_drug", "name": "Medicare Part D Prescriber & Drug Spending", "agency": "cms",
     "access": "estate", "wired": "cms_open_data",
     "url": "https://data.cms.gov/summary-statistics-on-use-and-payments/medicare-medicaid-spending-by-drug",
     "blurb": "Prescriber- and drug-level Part D claims, spending, and beneficiary counts.",
     "relevance": "Drug pricing, IRA-negotiation exposure, prescriber patterns."},
    {"id": "cms_ma_star", "name": "Medicare Advantage / Part D Star Ratings", "agency": "cms",
     "access": "bulk", "wired": "",
     "url": "https://www.cms.gov/medicare/health-drug-plans/part-c-d-performance-data",
     "blurb": "Annual contract-level Star Ratings and underlying measure scores (published as CMS zip files).",
     "relevance": "MA Star bonus, plan quality benchmarking, RADV context."},
    {"id": "cms_ma_enroll", "name": "MA / Part D Plan & Enrollment Files", "agency": "cms",
     "access": "bulk", "wired": "",
     "url": "https://www.cms.gov/data-research/statistics-trends-reports/medicare-advantagepart-d-contract-and-enrollment-data",
     "blurb": "Monthly contract/plan enrollment by county, plan type, and SNP status.",
     "relevance": "MA market share, SNP penetration, competitive mapping."},
    {"id": "cms_chronic", "name": "CMS Chronic Conditions", "agency": "cms",
     "access": "bulk", "wired": "",
     "url": "https://www.cms.gov/data-research/statistics-trends-reports/chronic-conditions",
     "blurb": "Prevalence, utilization, and spending for 21 chronic conditions among Medicare beneficiaries.",
     "relevance": "MA plan design, chronic-care management sizing, risk-adjustment context."},
    {"id": "cms_innovation", "name": "CMS Innovation Center Models (ACO REACH, OCM, BPCI, …)",
     "agency": "cms", "access": "bulk", "wired": "",
     "url": "https://www.cms.gov/priorities/innovation/data-and-reports",
     "blurb": "Participant lists and public-use results for alternative payment / value-based-care models.",
     "relevance": "VBC diligence, CMMI outcomes, risk-model participation."},
    {"id": "cms_taf", "name": "Medicaid/CHIP T-MSIS Analytic Files (TAF)", "agency": "cms",
     "access": "restricted", "wired": "",
     "url": "https://www.medicaid.gov/dq-atlas/",
     "blurb": "Beneficiary-level Medicaid/CHIP claims and enrollment; the definitive Medicaid microdata (DUA required via ResDAC).",
     "relevance": "Medicaid utilization, rate-setting, MLTSS/managed-care diligence."},

    # ── AHRQ — HCUP & surveys ────────────────────────────────────────────
    {"id": "hcup_nis", "name": "HCUP NIS — National (Nationwide) Inpatient Sample", "agency": "ahrq",
     "access": "restricted", "wired": "",
     "url": "https://hcup-us.ahrq.gov/nisoverview.jsp",
     "blurb": "Largest all-payer inpatient database in the U.S. — a ~20% stratified sample of discharges from ~4,800 hospitals.",
     "relevance": "National inpatient volume, DRG mix, payer shift, length-of-stay and cost benchmarks. DUA + purchase via the HCUP Central Distributor."},
    {"id": "hcup_neds", "name": "HCUP NEDS — Nationwide Emergency Department Sample", "agency": "ahrq",
     "access": "restricted", "wired": "",
     "url": "https://hcup-us.ahrq.gov/nedsoverview.jsp",
     "blurb": "Largest all-payer ED database — ~30M+ ED visits/year from a national sample of hospital-owned EDs.",
     "relevance": "ED volume, acuity, disposition, payer mix — core for EM, freestanding-ED, and IFT diligence. DUA + purchase."},
    {"id": "hcup_nrd", "name": "HCUP NRD — Nationwide Readmissions Database", "agency": "ahrq",
     "access": "restricted", "wired": "",
     "url": "https://hcup-us.ahrq.gov/nrdoverview.jsp",
     "blurb": "All-payer, all-ages readmissions with verified patient linkage across hospitals within a state-year.",
     "relevance": "Readmission rates, care-transition and VBC exposure. DUA + purchase."},
    {"id": "hcup_kid", "name": "HCUP KID — Kids' Inpatient Database", "agency": "ahrq",
     "access": "restricted", "wired": "",
     "url": "https://hcup-us.ahrq.gov/kidoverview.jsp",
     "blurb": "Largest pediatric all-payer inpatient database, released every three years.",
     "relevance": "Pediatric volume, children's-hospital and NICU diligence. DUA + purchase."},
    {"id": "hcup_sid", "name": "HCUP SID / SASD / SEDD — State Databases", "agency": "ahrq",
     "access": "restricted", "wired": "",
     "url": "https://hcup-us.ahrq.gov/databases.jsp",
     "blurb": "State-level inpatient (SID), ambulatory-surgery (SASD), and ED (SEDD) census databases — the encounter-level backbone behind the nationwide samples.",
     "relevance": "Market-level facility share, migration, and site-of-service mix. DUA + purchase, per state."},
    {"id": "hcupnet", "name": "HCUPnet — free online HCUP query tool", "agency": "ahrq",
     "access": "query", "wired": "",
     "url": "https://datatools.ahrq.gov/hcupnet",
     "blurb": "Free web query tool over HCUP — national/state aggregate statistics (rates, costs, DRG tables). No microdata.",
     "relevance": "Quick, citable inpatient/ED aggregates without a DUA — the free front door to HCUP."},
    {"id": "meps", "name": "MEPS — Medical Expenditure Panel Survey", "agency": "ahrq",
     "access": "bulk", "wired": "",
     "url": "https://meps.ahrq.gov/mepsweb/",
     "blurb": "Household + provider panel on health-care use, expenditures, sources of payment, and insurance coverage.",
     "relevance": "Out-of-pocket burden, coverage-source mix, condition-level spend. Free public-use files."},

    # ── CDC / NCHS ───────────────────────────────────────────────────────
    {"id": "cdc_wonder", "name": "CDC WONDER (Mortality, Natality, Cancer, …)", "agency": "cdc",
     "access": "query", "wired": "",
     "url": "https://wonder.cdc.gov/",
     "blurb": "Query system over CDC vital-statistics and surveillance datasets; also exposes an API for many databases.",
     "relevance": "Cause-specific mortality, birth trends, and disease burden by county/age/race."},
    {"id": "nhanes", "name": "NHANES — National Health & Nutrition Examination Survey", "agency": "cdc",
     "access": "bulk", "wired": "",
     "url": "https://www.cdc.gov/nchs/nhanes/",
     "blurb": "Exam + interview survey with labs, biometrics, and questionnaires on a national sample.",
     "relevance": "Disease-prevalence and undiagnosed-burden estimates (diabetes, CKD, obesity). Free public-use files."},
    {"id": "nhis", "name": "NHIS — National Health Interview Survey", "agency": "cdc",
     "access": "bulk", "wired": "",
     "url": "https://www.cdc.gov/nchs/nhis/",
     "blurb": "Principal source of information on the health of the civilian non-institutionalized U.S. population.",
     "relevance": "Coverage, access-to-care, and condition prevalence trends. Free public-use files."},
    {"id": "brfss", "name": "BRFSS — Behavioral Risk Factor Surveillance System", "agency": "cdc",
     "access": "bulk", "wired": "",
     "url": "https://www.cdc.gov/brfss/",
     "blurb": "Largest continuous health-survey system — state-level risk behaviors, conditions, and preventive care.",
     "relevance": "State/market risk-factor and prevalence estimates. Free public-use files + some API."},
    {"id": "cdc_places", "name": "PLACES — Local Data for Better Health", "agency": "cdc",
     "access": "estate", "wired": "cdc_data",
     "url": "https://www.cdc.gov/places/",
     "blurb": "Model-based county/place/tract/ZCTA estimates of chronic-disease measures and risk factors.",
     "relevance": "Small-area disease burden for market and SDOH analysis."},
    {"id": "nvss", "name": "NVSS — National Vital Statistics (Mortality & Natality)", "agency": "cdc",
     "access": "bulk", "wired": "",
     "url": "https://www.cdc.gov/nchs/nvss/",
     "blurb": "Birth and death certificate data — the authoritative U.S. vital-events record.",
     "relevance": "Birth-volume trends (OB/maternity), cause-of-death, mortality rates. Public-use + restricted geo files."},
    {"id": "nndss", "name": "NNDSS — Notifiable Diseases", "agency": "cdc",
     "access": "api", "wired": "",
     "url": "https://data.cdc.gov/browse?category=NNDSS",
     "blurb": "Weekly nationally-notifiable disease surveillance counts by jurisdiction (Socrata API on data.cdc.gov).",
     "relevance": "Outbreak/infectious-disease signal for public-health and lab demand."},
    {"id": "cdc_vsrr_overdose", "name": "VSRR — Provisional Drug Overdose Deaths", "agency": "cdc",
     "access": "estate", "wired": "cdc_data",
     "url": "https://data.cdc.gov/NCHS/VSRR-Provisional-Drug-Overdose-Death-Counts/xkb8-kh2a",
     "blurb": "Provisional monthly drug-overdose death counts by state and drug class.",
     "relevance": "Behavioral-health / SUD-treatment demand signal."},

    # ── SAMHSA ───────────────────────────────────────────────────────────
    {"id": "nsduh", "name": "NSDUH — National Survey on Drug Use & Health", "agency": "samhsa",
     "access": "bulk", "wired": "",
     "url": "https://www.samhsa.gov/data/data-we-collect/nsduh-national-survey-drug-use-and-health",
     "blurb": "Primary national source on prevalence of substance use and mental illness.",
     "relevance": "SUD/behavioral-health demand sizing, unmet-need estimates. Free public-use files."},
    {"id": "teds", "name": "TEDS — Treatment Episode Data Set", "agency": "samhsa",
     "access": "restricted", "wired": "",
     "url": "https://www.samhsa.gov/data/data-we-collect/teds-treatment-episode-data-set",
     "blurb": "Admissions to and discharges from state-licensed substance-use treatment facilities.",
     "relevance": "SUD treatment volume, LOS, and payer mix. Restricted-use files via SAMHDA."},
    {"id": "samhsa_facilities", "name": "N-SUMHSS — Substance Use & Mental Health Facility Surveys",
     "agency": "samhsa", "access": "bulk", "wired": "",
     "url": "https://www.samhsa.gov/data/data-we-collect/n-sumhss-national-substance-use-and-mental-health-services-survey",
     "blurb": "National census of substance-use and mental-health treatment facilities and their services.",
     "relevance": "Behavioral-health facility universe, service lines, capacity. Free public-use files + treatment locator."},

    # ── HRSA ─────────────────────────────────────────────────────────────
    {"id": "hrsa_hpsa", "name": "HPSA — Health Professional Shortage Areas", "agency": "hrsa",
     "access": "estate", "wired": "hrsa_data",
     "url": "https://data.hrsa.gov/topics/health-workforce/shortage-areas",
     "blurb": "Designated primary-care, dental, and mental-health shortage areas with scores.",
     "relevance": "Reimbursement bonuses, site selection, workforce risk."},
    {"id": "hrsa_mua", "name": "MUA/P — Medically Underserved Areas / Populations", "agency": "hrsa",
     "access": "estate", "wired": "hrsa_data",
     "url": "https://data.hrsa.gov/tools/shortage-area/mua-find",
     "blurb": "Areas/populations designated as having too few primary-care providers, high infant mortality, or poverty.",
     "relevance": "FQHC eligibility, 340B and site-selection context."},
    {"id": "hrsa_uds", "name": "Health Center Program (UDS)", "agency": "hrsa",
     "access": "estate", "wired": "hrsa_data",
     "url": "https://data.hrsa.gov/tools/data-reporting/program-data",
     "blurb": "Uniform Data System — annual patient, visit, service, and financial reporting for FQHCs.",
     "relevance": "Safety-net volume, payer mix, and 340B footprint."},
    {"id": "hrsa_ahrf", "name": "AHRF — Area Health Resources Files", "agency": "hrsa",
     "access": "bulk", "wired": "",
     "url": "https://data.hrsa.gov/topics/health-workforce/ahrf",
     "blurb": "County/state file combining >6,000 workforce, facility, utilization, and demographic variables.",
     "relevance": "One-stop market file for supply, demand, and demographics. Free download."},

    # ── Census ───────────────────────────────────────────────────────────
    {"id": "acs", "name": "ACS — American Community Survey", "agency": "census",
     "access": "estate", "wired": "census_acs",
     "url": "https://www.census.gov/programs-surveys/acs",
     "blurb": "Annual demographic, income, insurance, and disability estimates down to tract level.",
     "relevance": "Market demographics, payer/coverage mix, SDOH denominators."},
    {"id": "sahie", "name": "SAHIE — Small Area Health Insurance Estimates", "agency": "census",
     "access": "api", "wired": "",
     "url": "https://www.census.gov/programs-surveys/sahie.html",
     "blurb": "Model-based county-level uninsured and coverage estimates by age/sex/income.",
     "relevance": "Uninsured burden, Medicaid/marketplace sizing (Census API)."},
    {"id": "saipe", "name": "SAIPE — Small Area Income & Poverty Estimates", "agency": "census",
     "access": "api", "wired": "",
     "url": "https://www.census.gov/programs-surveys/saipe.html",
     "blurb": "Annual county/school-district income and poverty estimates.",
     "relevance": "SDOH, self-pay risk, and rate-setting context (Census API)."},

    # ── NIH / NCI ────────────────────────────────────────────────────────
    {"id": "seer", "name": "SEER — Surveillance, Epidemiology & End Results (NCI)", "agency": "nih",
     "access": "restricted", "wired": "",
     "url": "https://seer.cancer.gov/",
     "blurb": "Authoritative population-based cancer incidence and survival covering ~48% of the U.S. population.",
     "relevance": "Oncology incidence, stage mix, and survival — oncology-services diligence. Free with a signed research agreement."},
    {"id": "nih_reporter", "name": "NIH RePORTER — Funded Research Projects", "agency": "nih",
     "access": "estate", "wired": "nih_reporter",
     "url": "https://reporter.nih.gov/",
     "blurb": "Every NIH-funded grant/project with funding, institution, and publication links.",
     "relevance": "Research-intensity mapping, academic-affiliation and pipeline signal."},
    {"id": "clinicaltrials", "name": "ClinicalTrials.gov", "agency": "nih",
     "access": "api", "wired": "",
     "url": "https://clinicaltrials.gov/data-api/api",
     "blurb": "Registry of clinical studies worldwide with conditions, interventions, sponsors, sites, and status.",
     "relevance": "Site-of-care trial activity, sponsor/CRO footprint, therapeutic pipeline (free API)."},

    # ── FDA ──────────────────────────────────────────────────────────────
    {"id": "openfda", "name": "openFDA — Drugs, Devices, Adverse Events, Recalls", "agency": "fda",
     "access": "estate", "wired": "openfda",
     "url": "https://open.fda.gov/",
     "blurb": "APIs over FDA drug/device labeling, NDC directory, adverse events (FAERS/MAUDE), recalls, and enforcement.",
     "relevance": "Product-safety and recall exposure, device/drug reference, pharmacovigilance."},

    # ── Other national registries ────────────────────────────────────────
    {"id": "nppes", "name": "NPPES — NPI Registry", "agency": "other",
     "access": "estate", "wired": "npi_registry",
     "url": "https://npiregistry.cms.hhs.gov/",
     "blurb": "The national provider identifier registry — every enumerated provider and organization with taxonomy and address.",
     "relevance": "Provider universe, roster verification, taxonomy/specialty mapping."},
    {"id": "oig_leie", "name": "OIG LEIE — Exclusions List", "agency": "other",
     "access": "estate", "wired": "oig_leie",
     "url": "https://oig.hhs.gov/exclusions/",
     "blurb": "Providers/entities excluded from federal health-care programs.",
     "relevance": "Compliance screening, billing-eligibility diligence."},
    {"id": "bls_qcew", "name": "BLS QCEW — Healthcare Employment & Wages", "agency": "other",
     "access": "estate", "wired": "bls_qcew",
     "url": "https://www.bls.gov/cew/",
     "blurb": "Quarterly employment and wages by detailed industry and county.",
     "relevance": "Labor-cost benchmarking, staffing-market tightness."},
    {"id": "marketplace", "name": "Healthcare.gov Marketplace (QHP PUFs)", "agency": "other",
     "access": "estate", "wired": "healthcare_gov",
     "url": "https://www.cms.gov/marketplace/resources/data/public-use-files",
     "blurb": "Qualified health plan attributes, rates, service areas, and quality for the federal marketplace.",
     "relevance": "Exchange plan landscape, network and rate benchmarking."},
    {"id": "medicaid_open", "name": "Medicaid Open Data (data.medicaid.gov)", "agency": "other",
     "access": "estate", "wired": "medicaid_data",
     "url": "https://data.medicaid.gov/",
     "blurb": "NADAC drug pricing, enrollment, managed-care, and program datasets (the free Medicaid tables).",
     "relevance": "Medicaid drug pricing, enrollment, and managed-care penetration."},
    {"id": "usrds", "name": "USRDS — U.S. Renal Data System", "agency": "other",
     "access": "restricted", "wired": "",
     "url": "https://usrds.org/",
     "blurb": "National ESRD/CKD data system — the authoritative dialysis and kidney-disease registry.",
     "relevance": "Dialysis incidence/prevalence, modality mix, mortality — dialysis diligence. DUA required."},
    {"id": "optn", "name": "OPTN / SRTR — Organ Transplant Data", "agency": "other",
     "access": "bulk", "wired": "",
     "url": "https://optn.transplant.hrsa.gov/data/",
     "blurb": "Waitlist, transplant, and outcome data for every U.S. transplant program.",
     "relevance": "Transplant-program volume and outcomes; center-level diligence. Free national reports + request-based data."},
    {"id": "nemsis", "name": "NEMSIS — National EMS Information System", "agency": "other",
     "access": "restricted", "wired": "",
     "url": "https://nemsis.org/",
     "blurb": "Standardized EMS activation and transport records aggregated nationally.",
     "relevance": "Ambulance/IFT volume, response, and payer signal — EMS diligence. Research requests via NEMSIS TAC."},
    {"id": "dartmouth", "name": "Dartmouth Atlas of Health Care", "agency": "other",
     "access": "bulk", "wired": "",
     "url": "https://www.dartmouthatlas.org/",
     "blurb": "Hospital/region-level Medicare utilization, spending, and end-of-life care variation.",
     "relevance": "Practice-pattern variation, referral regions (HRR/HSA), utilization intensity. Free downloads."},
    {"id": "healthdata_gov", "name": "HealthData.gov — HHS-wide catalog", "agency": "other",
     "access": "estate", "wired": "healthdata_gov",
     "url": "https://healthdata.gov/",
     "blurb": "The HHS-wide meta-catalog indexing thousands of federal health datasets.",
     "relevance": "Discovery layer — find the dataset behind a question across all HHS agencies."},
]


# ── helpers ──────────────────────────────────────────────────────────────
def all_databases() -> List[Dict[str, str]]:
    """Every catalog entry (copy — callers may sort/mutate freely)."""
    return [dict(d) for d in DATABASES]


def get(db_id: str) -> Dict[str, str]:
    for d in DATABASES:
        if d["id"] == db_id:
            return dict(d)
    return {}


def agency_label(aid: str) -> str:
    for a, label in AGENCIES:
        if a == aid:
            return label
    return aid


def by_agency() -> List[tuple]:
    """``[(agency_id, label, [entries])]`` in render order, access-sorted
    within each agency (wired first, restricted last)."""
    out: List[tuple] = []
    for aid, label in AGENCIES:
        rows = [d for d in DATABASES if d["agency"] == aid]
        rows.sort(key=lambda d: (_ACCESS_ORDER.get(d["access"], 9),
                                 d["name"]))
        if rows:
            out.append((aid, label, rows))
    return out


def access_counts() -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for d in DATABASES:
        counts[d["access"]] = counts.get(d["access"], 0) + 1
    return counts


def coverage() -> Dict[str, int]:
    """Headline coverage stats for the catalog summary.

    ``wired`` = ingested by an estate connector; ``free`` = free but not yet
    wired (api/bulk/query — a candidate ingest); ``restricted`` = needs a
    DUA/registration/purchase (documented, not auto-ingestable).
    """
    counts = access_counts()
    free = counts.get("api", 0) + counts.get("bulk", 0) + counts.get("query", 0)
    return {
        "total": len(DATABASES),
        "wired": counts.get("estate", 0),
        "free": free,
        "restricted": counts.get("restricted", 0),
        "agencies": len({d["agency"] for d in DATABASES}),
    }
