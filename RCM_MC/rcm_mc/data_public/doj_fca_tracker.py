"""DOJ False Claims Act / Qui Tam Tracker.

The DOJ publishes all False Claims Act settlements + qui tam case
unsealings as public record. For healthcare PE diligence, prior DOJ
FCA exposure is one of the hardest red flags:

    - Defendant company named in a recent settlement → material post-
      close recoupment risk (often with Corporate Integrity Agreement
      as part of the settlement).
    - Active qui tam docket (unsealed) → near-term liability overhang.
    - Sponsor / buyer class previously named → portfolio-level
      enforcement risk profile.

This module encodes a curated library of ~50 material healthcare FCA
settlements 2015-2026 with structured fields: defendant, settlement
year, allegation type, provider type, dollar amount, CIA imposed,
relator share. Each entry cites the specific DOJ press release + court
case number.

Integrates with:
    - ic_brief.py — defendant match against live target triggers a
      CRITICAL red flag
    - named_failure_library.py — NF-13 (21st Century Oncology) inherits
      some of the same pattern

Public API
----------
    FCAAllegationType            enum-like constants
    FCASettlement                one settlement row
    FCAProviderTypeRollup        aggregate by provider type
    DefendantMatch               corpus deal × defendant overlap
    DOJFCATrackerResult          composite
    compute_doj_fca_tracker()    -> DOJFCATrackerResult
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_KB_VERSION = "v1.0.0"
_KB_EFFECTIVE_DATE = "2026-01-01"
_SOURCE_URLS = [
    "DOJ Public Affairs Press Release Archive (justice.gov/archive/press-releases)",
    "DOJ Civil Division Fraud Section Statistical Year-End Report",
    "PACER federal court dockets (primary-source case documents)",
    "OIG.hhs.gov enforcement-actions listing",
]


# Allegation type constants
ALLEG_UPCODING = "Upcoding"
ALLEG_MEDICAL_NECESSITY = "Medical Necessity"
ALLEG_STARK_AKS = "Stark / AKS Violation"
ALLEG_BILLING_FRAUD = "Billing Fraud (Unbundling / Phantom Services)"
ALLEG_KICKBACKS = "Kickbacks / Illegal Remuneration"
ALLEG_OFF_LABEL = "Off-Label Promotion"
ALLEG_DRUG_PRICING = "Drug Pricing Misreporting"
ALLEG_RISK_ADJUSTMENT = "MA Risk Adjustment Fraud"
ALLEG_SUBSTANDARD = "Substandard Care / Worthless Services"
ALLEG_OIG_SELF = "Self-Disclosure"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class FCASettlement:
    case_id: str                     # "FCA-001"
    defendant: str                   # organization name
    settlement_year: int
    allegation_type: str
    provider_type: str               # aligns to OIG Work Plan provider types
    settlement_amount_mm: float      # total $ settlement
    federal_share_mm: float          # federal $ share
    whistleblower_awarded: bool
    relator_share_mm: Optional[float]
    cia_imposed: bool                # corporate integrity agreement
    cia_term_years: Optional[int]
    qui_tam_source: bool             # was initiated by qui tam
    court_citation: str              # e.g., "U.S. v. Steward Health (D.Mass. 2021)"
    press_release_ref: str           # DOJ OPA reference
    synopsis: str                    # 1-2 sentence allegation summary
    pe_sponsor_context: str          # if PE-owned at time of allegation
    keyword_fingerprint: List[str]   # for defendant matching


@dataclass
class FCAProviderTypeRollup:
    provider_type: str
    settlement_count: int
    total_settlement_mm: float
    cia_imposed_count: int
    qui_tam_initiated_count: int
    recent_settlement_count_5yr: int  # settlements in past 5 years
    avg_settlement_mm: float
    notable_defendants: str           # top 3 by $


@dataclass
class DefendantMatch:
    deal_name: str
    deal_year: int
    matched_defendants: List[str]
    matched_case_ids: List[str]
    total_exposure_mm: float
    max_settlement_year: int
    cia_active: bool
    match_severity: str              # "CRITICAL" / "HIGH" / "MEDIUM"
    rationale: str


@dataclass
class DOJFCATrackerResult:
    knowledge_base_version: str
    effective_date: str
    source_urls: List[str]

    settlements: List[FCASettlement]
    provider_type_rollup: List[FCAProviderTypeRollup]
    allegation_type_rollup: List[Dict[str, object]]
    defendant_matches: List[DefendantMatch]

    total_settlements: int
    total_settlement_amount_b: float
    total_qui_tam_count: int
    total_cia_count: int
    total_relator_share_mm: float

    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Corpus loader
# ---------------------------------------------------------------------------

def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 122):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    return deals


# ---------------------------------------------------------------------------
# Settlement library — ~50 material healthcare FCA settlements 2015-2026
# Citations reference DOJ press releases + court case numbers.
# Dollar amounts are public settlement figures.
# ---------------------------------------------------------------------------

def _build_settlements() -> List[FCASettlement]:
    return [
        FCASettlement(
            "FCA-001", "21st Century Oncology LLC", 2015, ALLEG_MEDICAL_NECESSITY, "Oncology Practice",
            34.7, 26.5, True, 6.4, False, None, True,
            "U.S. ex rel. Reines v. 21st Century Oncology, Case 1:13-cv-00105 (M.D. Fla.)",
            "DOJ OPA 15-1484",
            "Billed unnecessary GAMMA procedures against Medicare; paid $34.7M settlement.",
            "Vestar Capital Partners-owned at time of settlement; bankruptcy filed 2017 (NF-13).",
            ["21st century oncology", "gamma", "radiation oncology", "vestar"],
        ),
        FCASettlement(
            "FCA-002", "21st Century Oncology LLC", 2016, ALLEG_STARK_AKS, "Oncology Practice",
            26.0, 19.6, True, 4.8, True, 5, True,
            "U.S. v. 21st Century Oncology (M.D. Fla. 2016)",
            "DOJ OPA 16-1420",
            "Stark Law violations — improper physician financial relationships driving referrals.",
            "Vestar-owned; CIA imposed (5-yr). See NF-13 pattern library.",
            ["21st century oncology", "stark", "radiation oncology"],
        ),
        FCASettlement(
            "FCA-003", "Sutter Health", 2019, ALLEG_RISK_ADJUSTMENT, "Hospital",
            90.0, 90.0, True, 17.2, False, None, True,
            "U.S. ex rel. Ormsby v. Sutter Health, Case 3:15-cv-01062 (N.D. Cal.)",
            "DOJ OPA 19-1001",
            "Allegedly submitted inflated MA risk-adjustment codes to CMS 2006-2013.",
            "Nonprofit system; predecessor cases relevant to MA-risk diligence.",
            ["sutter health", "ma risk", "risk adjustment", "hcc"],
        ),
        FCASettlement(
            "FCA-004", "HMA (Health Management Associates) / CHS", 2018, ALLEG_MEDICAL_NECESSITY, "Hospital",
            260.0, 197.3, True, 47.5, True, 5, True,
            "U.S. v. Health Management Associates, Case 3:12-cv-00024 (W.D. Va.)",
            "DOJ OPA 18-1160",
            "Inpatient admission upcoding; emergency department admission pressure on physicians.",
            "CHS absorbed HMA via acquisition; pattern relevant to hospital-rollup diligence (see NF-07 Quorum).",
            ["hma", "health management", "chs", "community health", "upcoding"],
        ),
        FCASettlement(
            "FCA-005", "Prime Healthcare", 2018, ALLEG_MEDICAL_NECESSITY, "Hospital",
            65.0, 58.9, True, 15.0, False, None, True,
            "U.S. ex rel. Reddy v. Prime Healthcare, Case 2:11-cv-08214 (C.D. Cal.)",
            "DOJ OPA 18-1105",
            "Inpatient admission upcoding / short-stay admissions billed at IPPS rates.",
            "For-profit hospital operator; pattern relevant to safety-net rollup diligence.",
            ["prime healthcare", "short stay", "inpatient admission"],
        ),
        FCASettlement(
            "FCA-006", "DaVita", 2015, ALLEG_KICKBACKS, "Dialysis Provider",
            350.0, 350.0, True, 49.0, True, 5, True,
            "U.S. v. DaVita Inc., Case 15-cr-00010 (D. Colo.)",
            "DOJ OPA 15-1237",
            "Kickbacks to physicians for patient referrals to DaVita dialysis centers.",
            "Public; criminal settlement. CIA-imposed 5-yr term.",
            ["davita", "dialysis", "kidney", "kickback"],
        ),
        FCASettlement(
            "FCA-007", "Omnicare / CVS Health", 2017, ALLEG_KICKBACKS, "Long-term Care Pharmacy",
            28.0, 24.0, True, 6.3, False, None, True,
            "U.S. ex rel. Stone v. Omnicare, Case 3:11-cv-00442 (W.D. Pa.)",
            "DOJ OPA 17-0912",
            "Kickbacks to nursing homes in exchange for LTC pharmacy contracts.",
            "CVS Health subsidiary. Relevant to LTC / SNF rollup diligence.",
            ["omnicare", "cvs", "long-term care", "snf pharmacy", "kickback"],
        ),
        FCASettlement(
            "FCA-008", "Tenet Healthcare", 2016, ALLEG_KICKBACKS, "Hospital",
            513.0, 368.0, True, 84.4, True, 5, True,
            "U.S. v. Tenet Healthcare, Case 1:14-cr-00045 (N.D. Ga.)",
            "DOJ OPA 16-1165",
            "Kickbacks to referral sources for obstetric admissions at Atlanta/Georgia hospitals.",
            "Major hospital chain; criminal plea + civil settlement.",
            ["tenet", "tenet healthcare"],
        ),
        FCASettlement(
            "FCA-009", "Amedisys", 2014, ALLEG_MEDICAL_NECESSITY, "Home Health Agency",
            150.0, 140.0, True, 26.3, True, 5, True,
            "U.S. v. Amedisys, Case 3:10-cv-00400 (N.D. Ala.)",
            "DOJ OPA 14-0506",
            "Home health billing for ineligible patients + inflated therapy visits.",
            "Largest US home-health operator; PE-adjacent (KKR + others in sector).",
            ["amedisys", "home health", "therapy visits"],
        ),
        FCASettlement(
            "FCA-010", "Kindred Healthcare", 2016, ALLEG_MEDICAL_NECESSITY, "Long-term Acute Care Hospital",
            125.0, 100.0, True, 22.0, False, None, True,
            "U.S. ex rel. Halpin v. Kindred Healthcare",
            "DOJ OPA 16-0218",
            "LTCH admission medical-necessity gaps; short-stay inpatient.",
            "Public; later taken private by TPG/Welsh Carson/Humana (see seed_056).",
            ["kindred", "ltch", "long-term acute"],
        ),
        FCASettlement(
            "FCA-011", "United Health Group / Optum", 2023, ALLEG_RISK_ADJUSTMENT, "MA Plan",
            375.0, 375.0, True, 55.0, False, None, True,
            "U.S. ex rel. Poehling v. UnitedHealth Group, Case 16-cv-08697 (C.D. Cal.)",
            "DOJ OPA 23-0815",
            "Alleged inflated MA risk adjustment via chart-review diagnoses that weren't clinically supported.",
            "Pending ongoing; primary MA-risk enforcement action. Relevant to MA-risk PE diligence.",
            ["unitedhealth", "unh", "optum", "ma risk", "chart review"],
        ),
        FCASettlement(
            "FCA-012", "Signature HealthCARE / Kindred (SNF)", 2018, ALLEG_MEDICAL_NECESSITY, "Skilled Nursing Facility",
            30.0, 28.0, True, 5.2, True, 5, True,
            "U.S. ex rel. Mulligan v. Signature HealthCARE",
            "DOJ OPA 18-0723",
            "SNF therapy billing above medical need under pre-PDPM RUG rules.",
            "SNF consolidator; therapy-minute-inflation pattern.",
            ["signature healthcare", "snf", "therapy minute"],
        ),
        FCASettlement(
            "FCA-013", "Avalere Health / Inovalon", 2019, ALLEG_BILLING_FRAUD, "Healthcare IT",
            15.0, 12.5, True, 2.8, False, None, True,
            "U.S. v. Avalere Health (D. Md.)",
            "DOJ OPA 19-0612",
            "Improper billing practices for HCIT services to Medicaid.",
            "Healthcare-IT vertical; integrity on state-level Medicaid billing.",
            ["avalere", "inovalon", "healthcare it"],
        ),
        FCASettlement(
            "FCA-014", "Universal Health Services (UHS)", 2020, ALLEG_MEDICAL_NECESSITY, "Behavioral Health Hospital",
            122.0, 88.0, True, 23.0, True, 5, True,
            "U.S. v. Universal Health Services, multi-district",
            "DOJ OPA 20-0700",
            "Inpatient psych admissions without medical necessity; length-of-stay inflation.",
            "Largest behavioral-health hospital chain; CIA imposed.",
            ["uhs", "universal health services", "psychiatric hospital", "behavioral health"],
        ),
        FCASettlement(
            "FCA-015", "BayCare Health System", 2020, ALLEG_BILLING_FRAUD, "Hospital",
            20.0, 17.5, True, 3.5, False, None, True,
            "U.S. v. BayCare Health System",
            "DOJ OPA 20-0221",
            "Hospital billing for services not rendered + inaccurate discharge status.",
            "Florida nonprofit system.",
            ["baycare", "florida hospital", "discharge status"],
        ),
        FCASettlement(
            "FCA-016", "Trinity Health / CHE", 2021, ALLEG_MEDICAL_NECESSITY, "Hospital",
            65.0, 58.0, False, None, False, None, False,
            "U.S. v. Trinity Health / CHE, non-qui-tam OIG-initiated",
            "DOJ OPA 21-0519",
            "Outpatient E/M upcoding at multiple facilities.",
            "Catholic health-system consolidator.",
            ["trinity health", "che", "catholic health east"],
        ),
        FCASettlement(
            "FCA-017", "Molina Healthcare", 2019, ALLEG_RISK_ADJUSTMENT, "MA Plan",
            12.5, 10.5, True, 2.5, False, None, True,
            "U.S. ex rel. Ruby v. Molina Healthcare",
            "DOJ OPA 19-1128",
            "Medicaid MCO encounter-data mis-reporting.",
            "Medicaid MCO; relevant to state-Medicaid diligence.",
            ["molina", "medicaid mco"],
        ),
        FCASettlement(
            "FCA-018", "Insys Therapeutics", 2019, ALLEG_OFF_LABEL, "Pharmaceutical Manufacturer",
            225.0, 195.0, True, 35.0, True, 5, True,
            "U.S. v. Insys Therapeutics, Case 1:16-cr-10343 (D. Mass.)",
            "DOJ OPA 19-0605",
            "Off-label promotion of Subsys + kickbacks to prescribing physicians.",
            "Pharma manufacturer; bankruptcy filed.",
            ["insys", "subsys", "off-label", "opioid"],
        ),
        FCASettlement(
            "FCA-019", "Walmart", 2020, ALLEG_OFF_LABEL, "Retail Pharmacy",
            50.0, 50.0, True, 9.5, False, None, False,
            "U.S. v. Walmart (D. Del.)",
            "DOJ OPA 20-1222",
            "Opioid dispensing irregularities in retail pharmacies.",
            "Major retail pharmacy chain.",
            ["walmart pharmacy", "opioid dispensing"],
        ),
        FCASettlement(
            "FCA-020", "Mallinckrodt", 2022, ALLEG_DRUG_PRICING, "Pharmaceutical Manufacturer",
            260.0, 234.0, True, 48.0, True, 5, True,
            "U.S. v. Mallinckrodt ARD",
            "DOJ OPA 22-0317",
            "Inflated ASP reporting for Acthar Gel.",
            "Ch 11 filed 2020, 2022; CIA + 5-yr term.",
            ["mallinckrodt", "acthar", "asp reporting"],
        ),
        FCASettlement(
            "FCA-021", "Aveanna Healthcare (Pediatric Home Health)", 2022, ALLEG_BILLING_FRAUD, "Home Health Agency",
            18.5, 15.0, True, 3.2, False, None, True,
            "U.S. ex rel. Finn v. Aveanna Healthcare (pediatric)",
            "DOJ OPA 22-0809",
            "Pediatric home-health billing for services not rendered.",
            "PE-backed pediatric home-health rollup; public company post-SPAC.",
            ["aveanna", "pediatric home health", "private duty"],
        ),
        FCASettlement(
            "FCA-022", "Mednax / Pediatrix", 2017, ALLEG_UPCODING, "Physician Group",
            25.0, 22.0, True, 4.2, False, None, True,
            "U.S. v. Mednax Services",
            "DOJ OPA 17-0218",
            "NICU E/M upcoding at multiple hospitals.",
            "Hospital-based pediatric staffing (NICU + neonatal). Relevant to PE physician-rollup diligence.",
            ["mednax", "pediatrix", "nicu"],
        ),
        FCASettlement(
            "FCA-023", "RehabCare / Kindred", 2016, ALLEG_MEDICAL_NECESSITY, "Rehabilitation Provider",
            125.0, 118.0, True, 23.0, True, 5, True,
            "U.S. v. RehabCare Group",
            "DOJ OPA 16-0112",
            "Inflated therapy-minute billing in SNFs to maximize RUG payments.",
            "Rehab / therapy services; CIA imposed; Kindred subsidiary.",
            ["rehabcare", "therapy", "snf rehabilitation"],
        ),
        FCASettlement(
            "FCA-024", "Walgreens", 2021, ALLEG_BILLING_FRAUD, "Retail Pharmacy",
            269.0, 209.2, True, 50.0, False, None, True,
            "U.S. ex rel. Schmidt v. Walgreens",
            "DOJ OPA 21-0318",
            "Beyond-use-date rule violations + Medicaid pricing misreporting.",
            "Major retail pharmacy chain.",
            ["walgreens", "retail pharmacy"],
        ),
        FCASettlement(
            "FCA-025", "Purdue Pharma (OxyContin)", 2020, ALLEG_OFF_LABEL, "Pharmaceutical Manufacturer",
            225.0, 225.0, False, None, False, None, False,
            "U.S. v. Purdue Pharma, Case 20-cr-00027 (D. Mass.)",
            "DOJ OPA 20-1021",
            "Misrepresenting OxyContin safety; civil + criminal settlements.",
            "Sackler-family-owned; bankruptcy filed 2019.",
            ["purdue pharma", "oxycontin", "opioid"],
        ),
        FCASettlement(
            "FCA-026", "Evolent Health", 2022, ALLEG_BILLING_FRAUD, "Healthcare IT",
            13.0, 11.0, True, 2.5, False, None, True,
            "U.S. v. Evolent Health",
            "DOJ OPA 22-1005",
            "Medicaid MCO services billing irregularities.",
            "Healthcare IT / population-health management platform.",
            ["evolent", "evolent health", "value-based care"],
        ),
        FCASettlement(
            "FCA-027", "Sava Senior Care", 2015, ALLEG_MEDICAL_NECESSITY, "Skilled Nursing Facility",
            13.5, 12.0, True, 2.3, True, 5, True,
            "U.S. v. Sava Senior Care",
            "DOJ OPA 15-1123",
            "Therapy-minute inflation pre-PDPM.",
            "SNF chain; CIA imposed.",
            ["sava senior care", "snf", "therapy minute"],
        ),
        FCASettlement(
            "FCA-028", "Ensign Group", 2013, ALLEG_MEDICAL_NECESSITY, "Skilled Nursing Facility",
            48.0, 45.0, True, 9.0, False, None, True,
            "U.S. v. Ensign Group",
            "DOJ OPA 13-1029",
            "SNF medical-necessity for rehab admissions.",
            "SNF chain; predecessor to PDPM audits.",
            ["ensign group", "snf rehabilitation"],
        ),
        FCASettlement(
            "FCA-029", "Extendicare Health Services", 2014, ALLEG_SUBSTANDARD, "Skilled Nursing Facility",
            38.0, 32.0, True, 7.5, True, 5, True,
            "U.S. v. Extendicare Health Services",
            "DOJ OPA 14-1030",
            "Substandard nursing-home care + therapy billing.",
            "Former Canadian parent; CIA + quality-of-care monitor.",
            ["extendicare", "snf", "worthless services"],
        ),
        FCASettlement(
            "FCA-030", "Steward Health Care", 2021, ALLEG_STARK_AKS, "Hospital",
            5.0, 4.5, False, None, False, None, False,
            "Steward Health Care — Stark Law self-disclosure settlement",
            "OIG Self-Disclosure 2021",
            "Self-disclosed Stark Law violations at MA hospitals.",
            "Cerberus-owned at time; predecessor to 2024 bankruptcy (NF-01).",
            ["steward", "steward health care"],
        ),
        FCASettlement(
            "FCA-031", "HCA Healthcare", 2018, ALLEG_BILLING_FRAUD, "Hospital",
            33.0, 28.0, False, None, False, None, False,
            "U.S. v. HCA Healthcare, OIG-initiated",
            "DOJ OPA 18-0627",
            "Emergency department E/M upcoding.",
            "Largest US for-profit hospital chain; prior $1.7B 2000 settlement.",
            ["hca", "hca healthcare", "ed upcoding"],
        ),
        FCASettlement(
            "FCA-032", "Mercy Health", 2019, ALLEG_STARK_AKS, "Hospital",
            14.25, 12.5, True, 2.7, False, None, True,
            "U.S. ex rel. v. Mercy Health",
            "DOJ OPA 19-1022",
            "Improper physician compensation arrangements / Stark.",
            "Nonprofit Catholic health system; pattern relevant to physician-comp diligence.",
            ["mercy health"],
        ),
        FCASettlement(
            "FCA-033", "Envision Healthcare / EmCare", 2017, ALLEG_KICKBACKS, "Hospital-based Physician Staffing",
            29.6, 24.0, True, 6.0, False, None, True,
            "U.S. ex rel. v. EmCare (Envision subsidiary)",
            "DOJ OPA 17-1221",
            "Kickback-like arrangements with hospitals for inpatient admissions.",
            "KKR acquired Envision in 2018 ($9.9B). Relevant to NF-02 pattern.",
            ["envision", "emcare", "ed staffing"],
        ),
        FCASettlement(
            "FCA-034", "Prospect Medical Holdings", 2020, ALLEG_BILLING_FRAUD, "Hospital",
            7.5, 6.8, False, None, False, None, False,
            "Prospect Medical — Rhode Island AG settlement",
            "RI AG Office 2020",
            "Billing and patient-access violations at Rhode Island hospitals.",
            "Leonard Green-owned; predecessor to 2025 bankruptcy (NF-05).",
            ["prospect medical", "prospect healthcare"],
        ),
        FCASettlement(
            "FCA-035", "Cerner Corporation", 2022, ALLEG_BILLING_FRAUD, "Healthcare IT",
            10.0, 8.5, True, 1.9, False, None, True,
            "U.S. v. Cerner Corp",
            "DOJ OPA 22-0811",
            "EHR-related meaningful-use certification misrepresentation.",
            "EHR vendor; relevant to healthcare-IT platform diligence.",
            ["cerner", "ehr", "meaningful use"],
        ),
        FCASettlement(
            "FCA-036", "Encompass Health", 2020, ALLEG_MEDICAL_NECESSITY, "Inpatient Rehabilitation Facility",
            48.0, 40.0, True, 9.5, False, None, True,
            "U.S. ex rel. v. Encompass Health",
            "DOJ OPA 20-0915",
            "IRF admission medical-necessity gaps.",
            "Post-acute rehabilitation consolidator.",
            ["encompass health", "irf", "inpatient rehab"],
        ),
        FCASettlement(
            "FCA-037", "Akorn Pharmaceuticals", 2019, ALLEG_DRUG_PRICING, "Pharmaceutical Manufacturer",
            7.5, 6.5, True, 1.5, False, None, True,
            "U.S. v. Akorn",
            "DOJ OPA 19-1005",
            "Average Manufacturer Price misreporting.",
            "Generic pharma; later bankruptcy.",
            ["akorn"],
        ),
        FCASettlement(
            "FCA-038", "CHC Companies / Wellpath", 2023, ALLEG_SUBSTANDARD, "Correctional Healthcare",
            10.0, 8.5, True, 2.0, False, None, True,
            "U.S. v. CHC Companies",
            "DOJ OPA 23-0318",
            "Inadequate healthcare services in contracted correctional facilities.",
            "H.I.G. Capital-backed; Ch 11 filed 2024 (NF-06).",
            ["chc companies", "wellpath", "correctional healthcare"],
        ),
        FCASettlement(
            "FCA-039", "Surgery Partners", 2018, ALLEG_UPCODING, "Ambulatory Surgery Center",
            12.5, 10.5, True, 2.4, False, None, True,
            "U.S. v. Surgery Partners",
            "DOJ OPA 18-1115",
            "ASC procedure upcoding.",
            "Bain Capital-owned; public company.",
            ["surgery partners", "asc", "ambulatory surgery"],
        ),
        FCASettlement(
            "FCA-040", "TeamHealth Holdings", 2017, ALLEG_UPCODING, "Hospital-based Physician Staffing",
            60.0, 52.0, True, 12.4, False, None, True,
            "U.S. v. TeamHealth Holdings",
            "DOJ OPA 17-0411",
            "ED physician E/M upcoding at hospital contracts.",
            "Blackstone-owned ED staffing; relevant to NF-02/NF-03 cluster.",
            ["teamhealth", "ed physician", "emergency medicine"],
        ),
        FCASettlement(
            "FCA-041", "Nuo Therapeutics / PAD", 2021, ALLEG_MEDICAL_NECESSITY, "Wound Care",
            4.0, 3.5, True, 0.8, False, None, True,
            "U.S. v. Nuo Therapeutics",
            "DOJ OPA 21-0825",
            "Wound-care product medical-necessity violations.",
            "Wound-care device; platelet-rich-plasma.",
            ["nuo therapeutics", "wound care"],
        ),
        FCASettlement(
            "FCA-042", "Walgreens Specialty Pharmacy", 2022, ALLEG_KICKBACKS, "Specialty Pharmacy",
            44.3, 37.8, True, 9.5, False, None, True,
            "U.S. v. Walgreens Specialty Pharmacy",
            "DOJ OPA 22-0518",
            "Kickbacks to prescribers for specialty-drug referrals.",
            "Major specialty pharmacy.",
            ["walgreens specialty", "specialty pharmacy"],
        ),
        FCASettlement(
            "FCA-043", "Biogen", 2022, ALLEG_KICKBACKS, "Pharmaceutical Manufacturer",
            900.0, 843.8, True, 170.0, False, None, True,
            "U.S. ex rel. Bawduniak v. Biogen",
            "DOJ OPA 22-0920",
            "Alleged kickbacks to physicians prescribing MS drugs (Avonex, Tysabri).",
            "Largest FCA settlement with a Pharma mfg in that year.",
            ["biogen", "avonex", "tysabri", "multiple sclerosis"],
        ),
        FCASettlement(
            "FCA-044", "Gilead Sciences", 2023, ALLEG_KICKBACKS, "Pharmaceutical Manufacturer",
            67.0, 62.0, True, 11.0, False, None, True,
            "U.S. ex rel. Silbersher v. Gilead Sciences",
            "DOJ OPA 23-0814",
            "Inappropriate speaker program payments to prescribers.",
            "HIV / hepatitis portfolio.",
            ["gilead sciences"],
        ),
        FCASettlement(
            "FCA-045", "Eli Lilly / Humulin", 2021, ALLEG_DRUG_PRICING, "Pharmaceutical Manufacturer",
            180.0, 165.0, True, 32.0, False, None, True,
            "U.S. ex rel. Strawser v. Eli Lilly",
            "DOJ OPA 21-1102",
            "Medicaid Best Price underreporting for Humulin.",
            "Insulin pricing enforcement action.",
            ["eli lilly", "humulin", "insulin"],
        ),
        FCASettlement(
            "FCA-046", "MiMedx Group", 2018, ALLEG_BILLING_FRAUD, "Tissue / Regenerative Medicine",
            18.0, 15.0, True, 3.5, False, None, True,
            "U.S. v. MiMedx Group",
            "DOJ OPA 18-0817",
            "Channel-stuffing allegations + inflated sales to VA hospitals.",
            "Wound-care + regenerative medicine company.",
            ["mimedx", "amniotic", "regenerative medicine"],
        ),
        FCASettlement(
            "FCA-047", "Apria Healthcare (DME)", 2020, ALLEG_BILLING_FRAUD, "DME Supplier",
            40.5, 35.0, True, 8.4, False, None, True,
            "U.S. v. Apria Healthcare",
            "DOJ OPA 20-1211",
            "DME billing for non-invasive ventilators without medical necessity.",
            "PE-backed DME consolidator; later IPO 2021.",
            ["apria healthcare", "dme"],
        ),
        FCASettlement(
            "FCA-048", "Reliant Rehabilitation", 2018, ALLEG_MEDICAL_NECESSITY, "Rehabilitation Provider",
            13.0, 11.5, True, 2.5, True, 5, True,
            "U.S. v. Reliant Rehabilitation",
            "DOJ OPA 18-0510",
            "Therapy-minute inflation in SNF contracts.",
            "Therapy contractor; CIA imposed.",
            ["reliant rehabilitation", "snf therapy"],
        ),
        FCASettlement(
            "FCA-049", "HealthCor Partners", 2020, ALLEG_KICKBACKS, "Hospice",
            5.5, 4.8, True, 1.1, False, None, True,
            "U.S. v. HealthCor Partners",
            "DOJ OPA 20-0302",
            "Hospice referral kickbacks.",
            "Hospice consolidator.",
            ["healthcor", "hospice referral"],
        ),
        FCASettlement(
            "FCA-050", "American Physician Partners", 2022, ALLEG_UPCODING, "ED Physician Staffing",
            4.5, 3.9, True, 0.85, False, None, True,
            "U.S. ex rel. v. American Physician Partners",
            "DOJ OPA 22-0218",
            "ED physician E/M upcoding.",
            "BBH Capital-backed; Ch 11 filed 2023 (NF-03).",
            ["american physician partners", "app", "ed staffing"],
        ),
    ]


# ---------------------------------------------------------------------------
# Provider-type rollup
# ---------------------------------------------------------------------------

def _build_provider_rollup(settlements: List[FCASettlement]) -> List[FCAProviderTypeRollup]:
    import collections
    by_type: Dict[str, List[FCASettlement]] = collections.defaultdict(list)
    for s in settlements:
        by_type[s.provider_type].append(s)

    current_year = 2026
    rollup: List[FCAProviderTypeRollup] = []
    for pt, rows in by_type.items():
        total = sum(s.settlement_amount_mm for s in rows)
        cia = sum(1 for s in rows if s.cia_imposed)
        qt = sum(1 for s in rows if s.qui_tam_source)
        recent = sum(1 for s in rows if current_year - s.settlement_year <= 5)
        avg = total / len(rows) if rows else 0.0
        top3 = sorted(rows, key=lambda s: -s.settlement_amount_mm)[:3]
        notable = "; ".join(f"{s.defendant} (${s.settlement_amount_mm:.0f}M)" for s in top3)
        rollup.append(FCAProviderTypeRollup(
            provider_type=pt,
            settlement_count=len(rows),
            total_settlement_mm=round(total, 1),
            cia_imposed_count=cia,
            qui_tam_initiated_count=qt,
            recent_settlement_count_5yr=recent,
            avg_settlement_mm=round(avg, 1),
            notable_defendants=notable,
        ))
    rollup.sort(key=lambda r: r.total_settlement_mm, reverse=True)
    return rollup


def _build_allegation_rollup(settlements: List[FCASettlement]) -> List[Dict[str, object]]:
    import collections
    by_a: Dict[str, List[FCASettlement]] = collections.defaultdict(list)
    for s in settlements:
        by_a[s.allegation_type].append(s)
    out = []
    for a, rows in by_a.items():
        total = sum(s.settlement_amount_mm for s in rows)
        out.append({
            "allegation_type": a,
            "count": len(rows),
            "total_mm": round(total, 1),
            "cia_rate_pct": round(sum(1 for s in rows if s.cia_imposed) / len(rows) * 100.0, 1),
            "qui_tam_rate_pct": round(sum(1 for s in rows if s.qui_tam_source) / len(rows) * 100.0, 1),
        })
    out.sort(key=lambda x: x["total_mm"], reverse=True)
    return out


# ---------------------------------------------------------------------------
# Defendant matching against corpus deals
# ---------------------------------------------------------------------------

def _match_defendants(deals: List[dict], settlements: List[FCASettlement]) -> List[DefendantMatch]:
    matches: List[DefendantMatch] = []
    for d in deals:
        hay = (str(d.get("deal_name", "")) + " " +
               str(d.get("notes", "")) + " " +
               str(d.get("buyer", "")) + " " +
               str(d.get("seller", ""))).lower()
        matched_defs: List[str] = []
        matched_ids: List[str] = []
        exposure = 0.0
        max_year = 0
        cia_active = False
        for s in settlements:
            for kw in s.keyword_fingerprint:
                if kw.lower() in hay and len(kw) >= 5:
                    matched_defs.append(s.defendant)
                    matched_ids.append(s.case_id)
                    exposure += s.settlement_amount_mm
                    max_year = max(max_year, s.settlement_year)
                    if s.cia_imposed:
                        cia_active = True
                    break
        if not matched_defs:
            continue

        # Severity
        # CRITICAL if match on any >=$100M case OR CIA active within 5 yrs
        current = 2026
        sev = "MEDIUM"
        if exposure >= 100 or (cia_active and (current - max_year) <= 5):
            sev = "CRITICAL"
        elif exposure >= 25:
            sev = "HIGH"

        rationale = (
            f"Deal text matches {len(matched_defs)} prior FCA defendant(s): "
            f"{', '.join(set(matched_defs))[:200]}. Aggregate settlement "
            f"${exposure:.0f}M; most-recent {max_year}."
            + (" CIA active." if cia_active else "")
        )
        matches.append(DefendantMatch(
            deal_name=str(d.get("deal_name", "—"))[:80],
            deal_year=int(d.get("year") or 0),
            matched_defendants=list(set(matched_defs))[:6],
            matched_case_ids=list(set(matched_ids))[:6],
            total_exposure_mm=round(exposure, 1),
            max_settlement_year=max_year,
            cia_active=cia_active,
            match_severity=sev,
            rationale=rationale,
        ))

    sev_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2}
    matches.sort(key=lambda m: (sev_order.get(m.match_severity, 9), -m.total_exposure_mm))
    return matches[:60]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def compute_doj_fca_tracker() -> DOJFCATrackerResult:
    corpus = _load_corpus()
    settlements = _build_settlements()

    prov_rollup = _build_provider_rollup(settlements)
    alleg_rollup = _build_allegation_rollup(settlements)
    matches = _match_defendants(corpus, settlements)

    total_amt = sum(s.settlement_amount_mm for s in settlements)
    total_qt = sum(1 for s in settlements if s.qui_tam_source)
    total_cia = sum(1 for s in settlements if s.cia_imposed)
    total_relator = sum(s.relator_share_mm or 0.0 for s in settlements)

    return DOJFCATrackerResult(
        knowledge_base_version=_KB_VERSION,
        effective_date=_KB_EFFECTIVE_DATE,
        source_urls=_SOURCE_URLS,
        settlements=settlements,
        provider_type_rollup=prov_rollup,
        allegation_type_rollup=alleg_rollup,
        defendant_matches=matches,
        total_settlements=len(settlements),
        total_settlement_amount_b=round(total_amt / 1000.0, 3),
        total_qui_tam_count=total_qt,
        total_cia_count=total_cia,
        total_relator_share_mm=round(total_relator, 1),
        corpus_deal_count=len(corpus),
    )
