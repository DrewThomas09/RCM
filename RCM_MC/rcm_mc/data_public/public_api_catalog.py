"""Catalog of free, API-accessible public healthcare datasets (non-CMS-claims).

The reference table behind ``/data-apis``: every free / key-optional public
data source worth wiring into PEdesk for commercial due diligence, organized by
the *diligence question* it answers rather than by the agency that publishes it.

Why a single catalog: the codebase already has scattered clients and vendored
loaders (NPPES, SEC EDGAR, ClinicalTrials.gov, openFDA, Census, ProPublica 990,
AHRQ HCUP). A partner asking "what can I pull, for free, to answer question X?"
had no one place to look. This module is that source of truth — it does NOT
fetch anything at import or render time; it is metadata only. Live clients live
in ``public_api_clients.py`` and the per-source loader modules.

Status taxonomy (honest about what actually runs in-repo today):
  live-client  – a runtime stdlib HTTP client exists and hits the API directly.
  vendored     – data is ingested at build time and read from a committed
                 offline snapshot (no runtime network); the API is the source.
  registered   – cataloged + linked here; no in-repo client/loader yet.

Estate connectors: sources whose ``client_module`` starts with
``connectors.`` are served by the repo-root connector estate (13 stdlib
connectors, one uniform /v1 query surface — see ``connector_estate.py``
and the /connector-estate page). They count as live-client; the estate is
optional at runtime (wheel installs don't ship the repo root), which is
why the module path is dotted rather than an in-package file path.

Cost taxonomy:
  free            – fully free, key optional or none.
  free-key        – free but an API key (no charge) raises rate limits.
  paywall-micro   – aggregate/query access is free; patient-level microdata is
                    purchase-only (e.g. HCUP Central Distributor).

One flag, repeated from the field guide: NPPES (the NPI registry) is operated by
CMS, but it is the provider *universe* every CDD build starts from — so it is
cataloged here alongside the non-CMS sources, separate from CMS claims/utilization.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


# Diligence question -> display label, in render order.
CATEGORIES: List[tuple] = [
    ("provider_universe", "Provider universe & market structure"),
    ("volume_outcomes", "Volume, utilization & outcomes"),
    ("drugs_devices", "Drugs & devices"),
    ("financials", "Financials"),
    ("demographics_labor", "Demographics, payer mix & labor"),
    ("behavioral_global", "Behavioral health & global"),
]

# Access models -> display label + tone hint for the UI badge.
ACCESS_LABELS: Dict[str, str] = {
    "none": "No key",
    "key-optional": "Key optional",
    "key-required": "Free key",
    "registration": "Registration",
}

STATUS_LABELS: Dict[str, str] = {
    "live-client": "Live client",
    "vendored": "Vendored offline",
    "registered": "Registered",
}


@dataclass(frozen=True)
class ApiSource:
    id: str
    name: str
    operator: str
    category: str           # one of CATEGORIES ids
    base_url: str
    docs_url: str
    access: str             # one of ACCESS_LABELS keys
    rate_limit: str
    formats: str
    cost: str               # free | free-key | paywall-micro
    status: str             # one of STATUS_LABELS keys
    answers: str            # the diligence question this source answers
    why: str                # why it matters for CDD (one line)
    records: str = ""       # scale, if notable
    client_module: str = "" # in-repo module path, if wired
    explore_route: str = "" # in-repo page that already charts this source

    @property
    def key_required(self) -> bool:
        return self.access == "key-required"

    @property
    def is_wired(self) -> bool:
        return self.status in ("live-client", "vendored")


# --------------------------------------------------------------------------
# The catalog. Endpoints, auth models and rate limits are the documented
# public values as of 2025-2026; ``status``/``client_module`` reflect what
# actually exists in this repo today (kept honest — see module docstring).
# --------------------------------------------------------------------------
_SOURCES: List[ApiSource] = [
    # ── Provider universe & market structure ─────────────────────────────
    ApiSource(
        id="nppes", name="NPPES NPI Registry", operator="CMS (provider universe)",
        category="provider_universe",
        base_url="https://npiregistry.cms.hhs.gov/api/?version=2.1",
        docs_url="https://npiregistry.cms.hhs.gov/api-page",
        access="none", rate_limit="~200 results/request; 503 under load",
        formats="JSON", cost="free", status="live-client",
        records="7M+ providers & facilities",
        client_module="connectors.npi_registry",
        answers="Who are the providers/competitors in a target's geography?",
        why="Canonical list of every US provider and facility — the starting "
            "point for counting competitors and building a specialty TAM.",
        explore_route="/connector-estate?connector=npi_registry",
    ),
    ApiSource(
        id="oig_leie", name="OIG LEIE (exclusions)",
        operator="HHS Office of Inspector General",
        category="provider_universe",
        base_url="https://oig.hhs.gov/exclusions/exclusions_list.asp",
        docs_url="https://oig.hhs.gov/exclusions/index.asp",
        access="none", rate_limit="monthly CSV download",
        formats="CSV", cost="free", status="vendored",
        records="83K+ excluded parties",
        client_module="rcm_mc/data/oig_leie.py",
        answers="Is anyone tied to the target barred from federal health programs?",
        why="The List of Excluded Individuals/Entities — a compliance / "
            "integrity screen for acquisitions and credentialing.",
        explore_route="/further-analysis?dataset=oig_exclusions_state",
    ),
    ApiSource(
        id="census_cbp", name="Census County Business Patterns",
        operator="US Census Bureau", category="provider_universe",
        base_url="https://api.census.gov/data/{year}/cbp",
        docs_url="https://www.census.gov/data/developers/data-sets/cbp-nonemp.html",
        access="key-required", rate_limit="500/day without key; higher with key",
        formats="JSON", cost="free-key", status="live-client",
        client_module="rcm_mc/data_public/census_market.py",
        answers="How fragmented is this provider market, and is there roll-up runway?",
        why="Establishment + employment counts by NAICS (e.g. 621111 physician "
            "offices) — the cleanest free way to size a fragmented market.",
    ),
    ApiSource(
        id="hrsa", name="HRSA Data Warehouse", operator="HRSA",
        category="provider_universe",
        base_url="https://data.hrsa.gov/api",
        docs_url="https://data.hrsa.gov/data/about",
        access="none", rate_limit="public; courtesy throttle",
        formats="JSON/OData", cost="free", status="live-client",
        client_module="connectors.hrsa_data",
        answers="Where are the underserved markets and reimbursement-uplift angles?",
        why="FQHCs/health centers, HPSA/MUA-MUP shortage designations, and the "
            "Area Health Resource Files — site-of-care expansion theses.",
        explore_route="/connector-estate?connector=hrsa_data",
    ),

    # ── Volume, utilization & outcomes ───────────────────────────────────
    ApiSource(
        id="cms_open_data", name="CMS Open Data (data.cms.gov)",
        operator="CMS", category="volume_outcomes",
        base_url="https://data.cms.gov/data-api",
        docs_url="https://data.cms.gov/api-docs",
        access="none", rate_limit="public; courtesy throttle",
        formats="JSON", cost="free", status="live-client",
        records="158-dataset catalog · 45 curated estate datasets",
        client_module="connectors.cms_open_data",
        answers="What are Medicare utilization, payment and cost-report facts "
                "by provider and geography?",
        why="Provider-level Medicare utilization & payment, Part B/D drug "
            "spending, geographic variation, HCRIS cost reports and PECOS "
            "ownership — the claims-adjacent core of any provider CDD.",
        explore_route="/connector-estate?connector=cms_open_data",
    ),
    ApiSource(
        id="provider_data", name="CMS Provider Data Catalog (Care Compare)",
        operator="CMS", category="volume_outcomes",
        base_url="https://data.cms.gov/provider-data",
        docs_url="https://data.cms.gov/provider-data/docs",
        access="none", rate_limit="public; courtesy throttle",
        formats="JSON", cost="free", status="live-client",
        records="234-dataset catalog · 20 curated estate datasets",
        client_module="connectors.provider_data",
        answers="How do target facilities score on stars, quality and "
                "patient experience?",
        why="The Care Compare quality universe — hospital stars/HCAHPS, "
            "nursing-home 5-star and penalties, home health, hospice, "
            "dialysis, clinicians — quality diligence for any facility roll-up.",
        explore_route="/connector-estate?connector=provider_data",
    ),
    ApiSource(
        id="cms_coverage", name="CMS Medicare Coverage Database (MCD)",
        operator="CMS", category="volume_outcomes",
        base_url="https://api.coverage.cms.gov",
        docs_url="https://www.cms.gov/medicare-coverage-database",
        access="none", rate_limit="public; courtesy throttle",
        formats="JSON", cost="free", status="live-client",
        records="9 estate datasets — NCD/LCD/articles/MAC contractors",
        client_module="connectors.cms_coverage",
        answers="Is a service or device covered by Medicare, and under "
                "which NCD/LCD?",
        why="National + local coverage determinations and the MAC contractor "
            "map — reimbursement-risk screening for procedure-driven targets.",
        explore_route="/connector-estate?connector=cms_coverage",
    ),
    ApiSource(
        id="icd10", name="ICD-10-CM / PCS (NLM Clinical Tables)",
        operator="NLM", category="volume_outcomes",
        base_url="https://clinicaltables.nlm.nih.gov/api",
        docs_url="https://clinicaltables.nlm.nih.gov/apidoc/icd10cm/v3/doc.html",
        access="none", rate_limit="public; courtesy throttle",
        formats="JSON", cost="free", status="live-client",
        client_module="connectors.icd10",
        answers="How do I search and resolve diagnosis / procedure codes?",
        why="Canonical ICD-10-CM/PCS code search — the code spine that joins "
            "claims volume, coverage policy and quality data in one grammar.",
        explore_route="/connector-estate?connector=icd10",
    ),
    ApiSource(
        id="cdc_data", name="CDC Open Data (data.cdc.gov)",
        operator="CDC", category="volume_outcomes",
        base_url="https://data.cdc.gov",
        docs_url="https://dev.socrata.com",
        access="key-optional",
        rate_limit="throttled without app token; higher with free token",
        formats="JSON (SODA)", cost="free-key", status="live-client",
        records="~1,500-dataset catalog · PLACES, mortality, BRFSS, overdose",
        client_module="connectors.cdc_data",
        answers="What is disease prevalence and mortality by county?",
        why="PLACES county-level prevalence, provisional mortality and BRFSS "
            "risk factors — the demand/severity layer under market sizing.",
        explore_route="/connector-estate?connector=cdc_data",
    ),
    ApiSource(
        id="hcupnet", name="AHRQ HCUPnet", operator="AHRQ (HCUP)",
        category="volume_outcomes",
        base_url="https://datatools.ahrq.gov/hcupnet",
        docs_url="https://hcupnet.ahrq.gov/",
        access="none", rate_limit="interactive query tool",
        formats="HTML/CSV query", cost="paywall-micro", status="vendored",
        client_module="rcm_mc/data/ahrq_hcup.py",
        answers="What are the inpatient/ED/ambulatory-surgery volumes by DRG/CPT?",
        why="Free aggregate query access to the nation's largest all-payer "
            "inpatient data (NIS); microdata is purchase-only via the HCUP "
            "Central Distributor.",
    ),
    ApiSource(
        id="meps", name="AHRQ MEPS", operator="AHRQ",
        category="volume_outcomes",
        base_url="https://meps.ahrq.gov/mepsweb/data_stats/download_data_files.jsp",
        docs_url="https://meps.ahrq.gov/mepsweb/",
        access="none", rate_limit="data-file download",
        formats="ASCII/CSV/SAS", cost="free", status="registered",
        answers="What does care cost per patient, and how is it utilized/insured?",
        why="Household-level spend, utilization and insurance — per-patient "
            "economics for an operating model.",
    ),

    # ── Drugs & devices ──────────────────────────────────────────────────
    ApiSource(
        id="openfda", name="openFDA", operator="US FDA",
        category="drugs_devices",
        base_url="https://api.fda.gov",
        docs_url="https://open.fda.gov/apis/",
        access="key-optional", rate_limit="240/min, 1k/day no key; "
            "240/min, 120k/day with free key",
        formats="JSON", cost="free-key", status="live-client",
        records="12 estate datasets — NDC, labels, FAERS, recalls, 510(k), PMA, MAUDE, UDI",
        client_module="connectors.openfda",
        answers="What is a device/drug target's regulatory moat and competitive set?",
        why="510(k)/PMA/UDI/recalls/MAUDE for devices; NDC/labeling/recalls/FAERS "
            "for drugs — map clearances and adverse-event exposure.",
        explore_route="/connector-estate?connector=openfda",
    ),
    ApiSource(
        id="rxnorm", name="NLM RxNorm (RxNav)", operator="NLM",
        category="drugs_devices",
        base_url="https://rxnav.nlm.nih.gov/REST",
        docs_url="https://lhncbc.nlm.nih.gov/RxNav/APIs/",
        access="none", rate_limit="20 requests/sec/IP",
        formats="JSON", cost="free", status="live-client",
        client_module="rcm_mc/data_public/rxnorm/connector.py",
        answers="How do I normalize drug names/NDCs to standard concepts?",
        why="Normalizes drug names/NDCs to RxNorm concepts and owns the "
            "NDC→RxCUI crosswalk other sources join to; pair with DailyMed "
            "labeling for a full drug-reference layer.",
    ),
    ApiSource(
        id="dailymed", name="DailyMed", operator="NLM",
        category="drugs_devices",
        base_url="https://dailymed.nlm.nih.gov/dailymed/services/v2",
        docs_url="https://dailymed.nlm.nih.gov/dailymed/app-support-web-services.cfm",
        access="none", rate_limit="public; courtesy throttle",
        formats="JSON/XML", cost="free", status="registered",
        answers="What is the structured FDA label for a drug product?",
        why="Official structured product labeling — the reference layer paired "
            "with RxNorm normalization.",
    ),
    ApiSource(
        id="clinicaltrials", name="ClinicalTrials.gov API v2", operator="NLM",
        category="drugs_devices",
        base_url="https://clinicaltrials.gov/api/v2",
        docs_url="https://clinicaltrials.gov/data-api/api",
        access="none", rate_limit="public; no key",
        formats="JSON", cost="free", status="vendored",
        client_module="rcm_mc/data/clinical_trials.py",
        answers="What is the pipeline/competitive landscape for this asset or site?",
        why="Sponsor, phase, enrollment, sites and status — the core dataset for "
            "biotech, CRO and trial-site competitive work.",
        explore_route="/further-analysis?dataset=clinical_trial_phase",
    ),

    # ── Drugs & devices (estate) ─────────────────────────────────────────
    ApiSource(
        id="medicaid_data", name="Medicaid Open Data (data.medicaid.gov)",
        operator="CMS (Medicaid)", category="drugs_devices",
        base_url="https://data.medicaid.gov/api",
        docs_url="https://data.medicaid.gov/about",
        access="none", rate_limit="public; courtesy throttle",
        formats="JSON", cost="free", status="live-client",
        records="541-dataset catalog · NADAC, state drug utilization, enrollment",
        client_module="connectors.medicaid_data",
        answers="What do drugs actually cost (NADAC) and how do states "
                "utilize and rebate them?",
        why="NADAC acquisition costs, State Drug Utilization, rebate products "
            "and managed-care enrollment — pharmacy economics and Medicaid "
            "exposure in one place.",
        explore_route="/connector-estate?connector=medicaid_data",
    ),

    # ── Financials ───────────────────────────────────────────────────────
    ApiSource(
        id="propublica_990", name="ProPublica Nonprofit Explorer",
        operator="ProPublica (IRS Form 990)", category="financials",
        base_url="https://projects.propublica.org/nonprofits/api/v2",
        docs_url="https://projects.propublica.org/nonprofits/api",
        access="none", rate_limit="public; courtesy throttle",
        formats="JSON", cost="free", status="vendored",
        client_module="rcm_mc/data/irs990.py",
        answers="What are the financials of a nonprofit hospital/system target?",
        why="Form 990 revenue, margins, exec comp and balance sheets — the "
            "closest thing to free financials for nonprofit targets & comps.",
    ),
    ApiSource(
        id="sec_edgar", name="SEC EDGAR", operator="US SEC",
        category="financials",
        base_url="https://data.sec.gov",
        docs_url="https://www.sec.gov/edgar/sec-api-documentation",
        access="none", rate_limit="10 requests/sec; User-Agent required",
        formats="JSON", cost="free", status="live-client",
        client_module="rcm_mc/data/sec_edgar.py",
        answers="What do public-company comps and segments look like?",
        why="Company facts and segment data for public comps — XBRL financials "
            "with a required contact User-Agent.",
    ),
    ApiSource(
        id="usaspending", name="USAspending.gov", operator="US Treasury",
        category="financials",
        base_url="https://api.usaspending.gov/api/v2",
        docs_url="https://api.usaspending.gov/",
        access="none", rate_limit="public; no key",
        formats="JSON", cost="free", status="registered",
        answers="Does the target have government grant/contract revenue exposure?",
        why="Federal grants and contracts — flags government-payer or research "
            "revenue concentration.",
    ),

    ApiSource(
        id="open_payments", name="CMS Open Payments (Sunshine Act)",
        operator="CMS", category="financials",
        base_url="https://openpaymentsdata.cms.gov/api",
        docs_url="https://openpaymentsdata.cms.gov/about/api",
        access="none", rate_limit="public; courtesy throttle",
        formats="JSON", cost="free", status="live-client",
        records="74-dataset catalog · PY2024 general/research/ownership",
        client_module="connectors.open_payments",
        answers="What industry money flows to the target's physicians?",
        why="Manufacturer-to-physician payments and ownership interests — "
            "conflict screening and pharma-alignment mapping for acquisitions.",
        explore_route="/connector-estate?connector=open_payments",
    ),
    ApiSource(
        id="nih_reporter", name="NIH RePORTER v2",
        operator="NIH", category="financials",
        base_url="https://api.reporter.nih.gov/v2",
        docs_url="https://api.reporter.nih.gov",
        access="none", rate_limit="POST JSON; ~1 req/sec courtesy",
        formats="JSON", cost="free", status="live-client",
        records="funded projects + linked publications",
        client_module="connectors.nih_reporter",
        answers="What NIH grant funding flows to a target or its "
                "site investigators?",
        why="Funded projects and linked publications — research-revenue "
            "exposure and KOL mapping for academic-adjacent assets.",
        explore_route="/connector-estate?connector=nih_reporter",
    ),

    # ── Demographics, payer mix & labor ──────────────────────────────────
    ApiSource(
        id="census_acs", name="Census ACS (5-year)", operator="US Census Bureau",
        category="demographics_labor",
        base_url="https://api.census.gov/data/{year}/acs/acs5",
        docs_url="https://www.census.gov/data/developers/data-sets/acs-5year.html",
        access="key-required", rate_limit="500/day without key; higher with key",
        formats="JSON", cost="free-key", status="live-client",
        client_module="connectors.census_acs",
        answers="What is the population, income and demand profile of a market?",
        why="County/ZIP population, age and income — drives demand and "
            "catchment modeling.",
        explore_route="/connector-estate?connector=census_acs",
    ),
    ApiSource(
        id="census_sahie", name="Census SAHIE", operator="US Census Bureau",
        category="demographics_labor",
        base_url="https://api.census.gov/data/timeseries/healthins/sahie",
        docs_url="https://www.census.gov/data/developers/data-sets/Health-Insurance-SAHIE.html",
        access="key-required", rate_limit="500/day without key; higher with key",
        formats="JSON", cost="free-key", status="live-client",
        client_module="rcm_mc/data_public/census_market.py",
        answers="What is the payer mix / uninsured rate for a county?",
        why="Small-Area Health Insurance Estimates — uninsured rate and Medicaid "
            "eligibility proxy for payer-mix modeling.",
    ),
    ApiSource(
        id="bls_oews", name="BLS OEWS", operator="US BLS",
        category="demographics_labor",
        base_url="https://api.bls.gov/publicAPI/v2",
        docs_url="https://www.bls.gov/developers/",
        access="key-required", rate_limit="25/day no key; 500/day with free key",
        formats="JSON", cost="free-key", status="registered",
        answers="What are clinical wage assumptions by occupation and metro?",
        why="Occupational Employment & Wage Statistics — labor-cost assumptions "
            "for the operating model.",
    ),

    ApiSource(
        id="healthcare_gov", name="Healthcare.gov Marketplace PUFs",
        operator="CMS (Marketplace)", category="demographics_labor",
        base_url="https://data.healthcare.gov/api",
        docs_url="https://data.healthcare.gov/about",
        access="none", rate_limit="public; courtesy throttle",
        formats="JSON", cost="free", status="live-client",
        records="337-dataset catalog · PY2026 QHP plan/benefit/rate PUFs",
        client_module="connectors.healthcare_gov",
        answers="What do marketplace plans, benefits and rates look like "
                "in a county?",
        why="QHP plan attributes, benefits & cost sharing and rates by "
            "county — exchange payer-mix and premium modeling for "
            "ambulatory targets.",
        explore_route="/connector-estate?connector=healthcare_gov",
    ),

    # ── Behavioral health & global ───────────────────────────────────────
    ApiSource(
        id="samhsa", name="SAMHSA SAMHDA (N-SSATS/N-MHSS)", operator="SAMHSA",
        category="behavioral_global",
        base_url="https://www.samhsa.gov/data/data-we-collect",
        docs_url="https://www.datafiles.samhsa.gov/",
        access="registration", rate_limit="data-file download (ICPSR)",
        formats="CSV/SAS/SPSS", cost="free", status="registered",
        answers="How big is the behavioral-health / SUD treatment market?",
        why="Facility files (N-SSATS, N-MHSS) for behavioral-health and "
            "substance-use treatment market sizing.",
    ),
    ApiSource(
        id="who_gho", name="WHO Global Health Observatory", operator="WHO",
        category="behavioral_global",
        base_url="https://ghoapi.azureedge.net/api",
        docs_url="https://www.who.int/data/gho/info/gho-odata-api",
        access="none", rate_limit="public OData; no key",
        formats="JSON (OData)", cost="free", status="registered",
        answers="What is ex-US disease prevalence for an international thesis?",
        why="Global health indicators via OData — ex-US prevalence and access "
            "metrics for international angles.",
    ),
    ApiSource(
        id="ihme_gbd", name="IHME Global Burden of Disease", operator="IHME",
        category="behavioral_global",
        base_url="https://www.healthdata.org/research-analysis/gbd",
        docs_url="https://www.healthdata.org/research-analysis/about-gbd/gbd-api",
        access="registration", rate_limit="account-gated results API",
        formats="JSON/CSV", cost="free", status="registered",
        answers="What is the global disease burden by cause/region/year?",
        why="The most granular global disease-burden estimates for ex-US market "
            "sizing — account-gated results tool/API.",
    ),
]

CATALOG: Dict[str, ApiSource] = {s.id: s for s in _SOURCES}
_CAT_LABEL = dict(CATEGORIES)


def all_sources() -> List[ApiSource]:
    """Every source, in catalog order."""
    return list(_SOURCES)


def get(source_id: str) -> Optional[ApiSource]:
    return CATALOG.get(source_id)


def category_label(cat_id: str) -> str:
    return _CAT_LABEL.get(cat_id, cat_id)


def by_category() -> List[tuple]:
    """``[(cat_id, label, [ApiSource, ...]), ...]`` in render order."""
    out: List[tuple] = []
    for cid, label in CATEGORIES:
        members = [s for s in _SOURCES if s.category == cid]
        out.append((cid, label, members))
    return out


def status_counts() -> Dict[str, int]:
    counts: Dict[str, int] = {k: 0 for k in STATUS_LABELS}
    for s in _SOURCES:
        counts[s.status] = counts.get(s.status, 0) + 1
    return counts


def access_counts() -> Dict[str, int]:
    counts: Dict[str, int] = {k: 0 for k in ACCESS_LABELS}
    for s in _SOURCES:
        counts[s.access] = counts.get(s.access, 0) + 1
    return counts


def wired_sources() -> List[ApiSource]:
    """Sources with a live client or a vendored offline loader."""
    return [s for s in _SOURCES if s.is_wired]


def key_optional_sources() -> List[ApiSource]:
    """Sources you can hit with no key at all (access == none)."""
    return [s for s in _SOURCES if s.access == "none"]


def summary() -> Dict[str, object]:
    return {
        "total": len(_SOURCES),
        "categories": len(CATEGORIES),
        "wired": len(wired_sources()),
        "no_key": len(key_optional_sources()),
        "status": status_counts(),
        "access": access_counts(),
    }
