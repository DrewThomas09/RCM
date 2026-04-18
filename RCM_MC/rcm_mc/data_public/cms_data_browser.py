"""CMS Public Data Browser.

Curated index of CMS public datasets used in healthcare PE diligence:
PFS fee schedule, OPPS/APC rates, DRG weights, HCRIS cost reports,
MDS, SNF/HH PPS, MA bid data, quality reporting, provider enrollment.

Consolidates what's in /cms-sources (high-level) into a detailed,
searchable catalog with dataset metadata, refresh schedules, sample
records, and links to ingestion status.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class CMSDataset:
    dataset_name: str
    category: str
    description: str
    update_frequency: str
    last_refresh: str
    record_count: int
    key_fields: str
    primary_use_case: str
    ingestion_status: str


@dataclass
class FeeScheduleSample:
    cpt_hcpcs: str
    descriptor: str
    work_rvu: float
    total_rvu: float
    facility_rate: float
    non_facility_rate: float
    effective_year: int


@dataclass
class DRGSample:
    drg_code: int
    drg_description: str
    weight: float
    geometric_los: float
    arithmetic_los: float
    base_rate: float
    fy_payment_year: int


@dataclass
class HCRISSample:
    provider_type: str
    reports_filed_latest: int
    latest_filing_year: int
    median_occupancy_pct: float
    median_total_margin_pct: float
    median_case_mix_index: float


@dataclass
class DataConnection:
    source: str
    api_endpoint: str
    api_version: str
    auth_required: bool
    rate_limit: str
    cache_ttl_hours: int
    last_successful_pull: str


@dataclass
class QualityMeasure:
    measure: str
    program: str
    measure_type: str
    reporting_year: int
    national_median: float
    measure_steward: str


@dataclass
class CMSDataResult:
    total_datasets: int
    datasets_active: int
    total_records_mm: int
    last_full_refresh: str
    datasets: List[CMSDataset]
    fee_schedule_sample: List[FeeScheduleSample]
    drg_sample: List[DRGSample]
    hcris_samples: List[HCRISSample]
    connections: List[DataConnection]
    quality_measures: List[QualityMeasure]
    corpus_deal_count: int


def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 111):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    return deals


def _build_datasets() -> List[CMSDataset]:
    return [
        CMSDataset("Medicare Physician Fee Schedule (PFS)", "Fee Schedule",
                   "National PFS relative value units (RVU) and payment rates for CPT/HCPCS codes",
                   "annual (Nov/Dec release)", "2024-12-15", 8850,
                   "cpt_hcpcs, work_rvu, pe_rvu, mp_rvu, total_rvu, non_facility_rate, facility_rate",
                   "Professional rate benchmarking, RVU analysis, practice valuation", "current"),
        CMSDataset("OPPS / APC Rates", "Fee Schedule",
                   "Outpatient Prospective Payment System ambulatory payment classification rates",
                   "annual (Nov/Dec release)", "2024-12-15", 1180,
                   "apc_code, hcpcs, status_indicator, apc_weight, base_rate",
                   "HOPD / ASC site-of-service analysis, HOPPS repricing", "current"),
        CMSDataset("MS-DRG / IPPS Rates", "Fee Schedule",
                   "Inpatient Prospective Payment System MS-DRG relative weights and rates",
                   "annual (Aug FY release)", "2024-10-01", 748,
                   "drg_code, ms_drg_description, weight, geometric_mean_los, arithmetic_mean_los",
                   "Inpatient rate benchmarking, DRG shift analysis, 3M coding audit", "current"),
        CMSDataset("HCRIS Cost Reports - Hospitals", "Cost Reports",
                   "Medicare cost reports filed by ~6,000 US acute care / CAH / specialty hospitals",
                   "continuous (quarterly refresh)", "2024-12-31", 28500,
                   "provider_id, filing_year, total_revenue, operating_expense, case_mix_index, occupancy",
                   "Hospital operating performance, benchmarking", "current"),
        CMSDataset("HCRIS Cost Reports - SNF", "Cost Reports",
                   "Medicare cost reports for ~15,000 skilled nursing facilities",
                   "continuous (quarterly refresh)", "2024-12-31", 65000,
                   "provider_id, total_days, medicare_pct, private_pay_pct, medicaid_pct, margin",
                   "SNF diligence, payer mix analysis", "current"),
        CMSDataset("HCRIS Cost Reports - Home Health", "Cost Reports",
                   "Medicare home health agency cost reports",
                   "continuous (quarterly refresh)", "2024-12-31", 48000,
                   "provider_id, total_episodes, lupa_pct, case_mix, margin",
                   "Home health diligence, PDGM compliance", "current"),
        CMSDataset("Medicare Advantage Plan Enrollment (PPQs)", "MA Data",
                   "Plan-level MA enrollment by county, CCP/MAP PPO/HMO, SNP",
                   "monthly", "2025-02-15", 185000,
                   "contract_id, plan_id, county_ssa, enrollment, plan_type",
                   "MA market share, SNP penetration, competitive benchmarking", "current"),
        CMSDataset("MA Star Ratings", "Quality",
                   "Annual Star Ratings for MA-PD and standalone PDP contracts",
                   "annual (October release)", "2024-10-15", 625,
                   "contract_id, overall_stars, measure_stars, hei_flag",
                   "MA Star bonus payment analysis, benchmark", "current"),
        CMSDataset("Provider Enrollment / PECOS", "Provider Data",
                   "CMS provider/supplier enrollment status and ownership",
                   "continuous", "2025-02-28", 2850000,
                   "npi, tin, provider_type, enrollment_status, specialty",
                   "Due diligence, credentialing, provider verification", "current"),
        CMSDataset("Open Payments / Sunshine Act", "Transparency",
                   "Payments from manufacturers to physicians and teaching hospitals",
                   "annual (June release)", "2024-06-30", 12500000,
                   "physician_npi, manufacturer, payment_type, amount, date",
                   "Conflict-of-interest screening, DOJ FCA diligence", "current"),
        CMSDataset("Medicare Utilization - Physician", "Utilization",
                   "Annual physician Medicare Part B service utilization and payments",
                   "annual (July release)", "2024-07-15", 1850000,
                   "npi, specialty, hcpcs, services, beneficiaries, medicare_payment",
                   "Provider productivity, billing pattern analysis", "current"),
        CMSDataset("Medicare Utilization - Hospital Inpatient", "Utilization",
                   "Hospital inpatient MS-DRG utilization by facility",
                   "annual (July release)", "2024-07-15", 425000,
                   "provider_id, drg, discharges, avg_covered_charges, medicare_payment",
                   "Hospital volume benchmarking, DRG mix", "current"),
        CMSDataset("Hospital Compare", "Quality",
                   "Quality measures: readmission, mortality, safety, patient experience",
                   "quarterly", "2024-12-15", 128500,
                   "provider_id, measure_id, score, national_comparison",
                   "Quality benchmarking, VBP analysis", "current"),
        CMSDataset("Nursing Home Care Compare", "Quality",
                   "SNF 5-star ratings, deficiency reports, staffing",
                   "quarterly", "2024-12-15", 185000,
                   "provider_id, overall_rating, staffing_rating, health_inspection, qm_rating",
                   "SNF quality, diligence", "current"),
        CMSDataset("Home Health Compare", "Quality",
                   "Home health quality and patient experience measures",
                   "quarterly", "2024-12-15", 125000,
                   "provider_id, quality_of_care, patient_experience, outcome_measures",
                   "Home health diligence, HHVBP", "current"),
        CMSDataset("Hospice Care Compare", "Quality",
                   "Hospice quality measures and CAHPS survey data",
                   "quarterly", "2024-12-15", 45000,
                   "provider_id, quality_measures, cahps, star_rating",
                   "Hospice diligence, survey trends", "current"),
        CMSDataset("CMS Chronic Conditions", "Population Health",
                   "Beneficiary-level chronic condition prevalence",
                   "annual (December release)", "2024-12-15", 35500000,
                   "bene_id, state, county, chronic_conditions_flag",
                   "MA plan design, chronic disease management", "current"),
        CMSDataset("Part D Drug Spending Dashboard", "Drug Data",
                   "Medicare Part D prescription drug costs and utilization",
                   "annual (September release)", "2024-09-30", 485000,
                   "drug, manufacturer, total_spending, claims, avg_spending_per_dose",
                   "Drug pricing, IRA negotiation analysis", "current"),
        CMSDataset("DAC (Data-at-a-Click)", "Custom Analytics",
                   "Pre-built CMS provider dashboards and mini-reports",
                   "quarterly", "2024-12-15", 1250,
                   "dashboard_id, topic, update_date",
                   "Ad-hoc analytical queries", "current"),
        CMSDataset("Innovation Center Model Data", "VBC / Alternative Payment",
                   "CMMI alternative payment model data (ACO REACH, OCM, etc.)",
                   "model-specific", "varies", 2850,
                   "model_id, participant_tin, savings, quality_score",
                   "VBC diligence, CMMI outcomes analysis", "current"),
    ]


def _build_fee_sample() -> List[FeeScheduleSample]:
    return [
        FeeScheduleSample("99213", "Office Visit, Established, Level 3", 0.97, 2.28, 72.53, 105.10, 2025),
        FeeScheduleSample("99214", "Office Visit, Established, Level 4", 1.50, 3.33, 107.83, 149.81, 2025),
        FeeScheduleSample("99215", "Office Visit, Established, Level 5", 2.11, 4.42, 151.95, 210.44, 2025),
        FeeScheduleSample("90837", "Psychotherapy, 60 min", 2.00, 4.05, 138.89, 161.19, 2025),
        FeeScheduleSample("45378", "Diagnostic Colonoscopy", 3.36, 10.20, 352.98, 0.00, 2025),
        FeeScheduleSample("45385", "Colonoscopy w/ Biopsy", 4.21, 12.81, 443.21, 0.00, 2025),
        FeeScheduleSample("93458", "Cardiac Cath, Left Heart", 7.56, 18.50, 611.50, 0.00, 2025),
        FeeScheduleSample("66984", "Cataract Surgery w/ IOL", 7.35, 20.45, 678.95, 0.00, 2025),
        FeeScheduleSample("17311", "Mohs Surgery, First Stage", 7.45, 14.25, 485.68, 0.00, 2025),
        FeeScheduleSample("27447", "Total Knee Replacement", 20.25, 36.85, 1252.45, 0.00, 2025),
        FeeScheduleSample("43239", "EGD w/ Biopsy", 2.64, 6.85, 236.15, 0.00, 2025),
        FeeScheduleSample("97140", "Manual Therapy (PT)", 0.43, 1.25, 43.18, 0.00, 2025),
    ]


def _build_drg_sample() -> List[DRGSample]:
    return [
        DRGSample(470, "Major Hip and Knee Joint Replacement (No MCC)", 1.8539, 2.5, 2.9, 11650.0, 2025),
        DRGSample(469, "Major Hip and Knee Joint Replacement w/ MCC", 3.2415, 5.3, 6.8, 20485.0, 2025),
        DRGSample(247, "Percutaneous Cardiovascular Procedure", 2.1254, 2.1, 2.6, 13425.0, 2025),
        DRGSample(872, "Septicemia / Severe Sepsis", 1.3428, 4.9, 6.2, 8485.0, 2025),
        DRGSample(392, "Esophagitis / Gastro", 0.7518, 2.5, 3.1, 4752.0, 2025),
        DRGSample(291, "Heart Failure w/ MCC", 1.3425, 4.5, 5.6, 8485.0, 2025),
        DRGSample(3, "ECMO or Trach with MV 96+ hrs", 19.8542, 28.5, 35.2, 125485.0, 2025),
        DRGSample(765, "Cesarean Section w/ CC", 1.1254, 3.2, 3.8, 7112.0, 2025),
        DRGSample(775, "Vaginal Delivery w/o CC", 0.5218, 2.1, 2.4, 3296.0, 2025),
        DRGSample(885, "Psychoses", 1.0825, 6.8, 8.2, 6842.0, 2025),
    ]


def _build_hcris() -> List[HCRISSample]:
    return [
        HCRISSample("Acute Care Hospital", 5250, 2023, 65.2, 2.85, 1.65),
        HCRISSample("Critical Access Hospital (CAH)", 1350, 2023, 48.5, 1.20, 1.15),
        HCRISSample("Specialty Hospital", 385, 2023, 58.5, 5.20, 1.45),
        HCRISSample("Long-Term Acute Care (LTACH)", 325, 2023, 72.5, 3.85, 1.85),
        HCRISSample("Inpatient Rehab Facility (IRF)", 1250, 2023, 68.5, 6.45, 1.55),
        HCRISSample("Skilled Nursing Facility (SNF)", 14850, 2023, 78.5, 0.85, 1.08),
        HCRISSample("Home Health Agency (HHA)", 11250, 2023, 0.0, 14.50, 1.12),
        HCRISSample("Hospice", 4850, 2023, 0.0, 12.85, 0.0),
    ]


def _build_connections() -> List[DataConnection]:
    return [
        DataConnection("CMS Data.CMS.gov", "https://data.cms.gov/provider-data/api/1/", "v1", False, "100 req/min", 24, "2025-03-15 03:00 UTC"),
        DataConnection("CMS QPP API", "https://qpp.cms.gov/api/auth/v1/", "v1", True, "50 req/min", 24, "2025-03-14 03:00 UTC"),
        DataConnection("HRSA Data Warehouse", "https://data.hrsa.gov/api/odata/", "odata v4", False, "100 req/min", 72, "2025-03-10 03:00 UTC"),
        DataConnection("NPPES NPI Registry", "https://npiregistry.cms.hhs.gov/api/", "v2.1", False, "200 req/min", 168, "2025-03-12 03:00 UTC"),
        DataConnection("FDA Open Data", "https://api.fda.gov/", "v1", False, "240 req/min", 24, "2025-03-15 03:00 UTC"),
        DataConnection("Socrata (multiple CMS)", "https://data.cms.gov/resource/", "v2.1", False, "1000 req/hr (app token)", 24, "2025-03-15 03:00 UTC"),
        DataConnection("data.healthcare.gov", "https://www.healthcare.gov/api/", "v1", False, "100 req/min", 72, "2025-03-10 03:00 UTC"),
        DataConnection("CMS Innovation Center", "https://innovation.cms.gov/api/", "v1", False, "50 req/min", 168, "2025-03-08 03:00 UTC"),
    ]


def _build_quality() -> List[QualityMeasure]:
    return [
        QualityMeasure("Hospital 30-day Readmission", "HRRP", "outcome", 2024, 0.148, "CMS / Yale-CORE"),
        QualityMeasure("SNF 30-day Readmission (SNFRM)", "SNF VBP", "outcome", 2024, 0.195, "CMS"),
        QualityMeasure("HCAHPS Overall Rating 9-10", "Hospital Compare", "experience", 2024, 0.73, "CMS / AHRQ"),
        QualityMeasure("CG-CAHPS Overall Provider Rating", "Merit-Based Incentive (MIPS)", "experience", 2024, 4.32, "CMS"),
        QualityMeasure("HEDIS Diabetes HbA1c Control (<8)", "MA Stars", "process", 2024, 0.72, "NCQA"),
        QualityMeasure("HEDIS Breast Cancer Screening", "MA Stars", "process", 2024, 0.745, "NCQA"),
        QualityMeasure("MA Medication Adherence - Diabetes", "MA Stars", "pharmacy", 2024, 0.82, "PQA"),
        QualityMeasure("Hospital-Acquired Conditions (HAC) Reduction", "HAC Program", "safety", 2024, 1.00, "CMS"),
        QualityMeasure("PSI-90 Composite", "Hospital Compare", "safety", 2024, 1.00, "AHRQ"),
        QualityMeasure("Home Health Improvement in Ambulation", "HHVBP", "outcome", 2024, 0.685, "CMS"),
    ]


def compute_cms_data_browser() -> CMSDataResult:
    corpus = _load_corpus()

    datasets = _build_datasets()
    fee_sample = _build_fee_sample()
    drg_sample = _build_drg_sample()
    hcris = _build_hcris()
    connections = _build_connections()
    quality = _build_quality()

    active = sum(1 for d in datasets if d.ingestion_status == "current")
    total_records = sum(d.record_count for d in datasets) // 1000000

    return CMSDataResult(
        total_datasets=len(datasets),
        datasets_active=active,
        total_records_mm=total_records,
        last_full_refresh="2025-03-15 03:00 UTC",
        datasets=datasets,
        fee_schedule_sample=fee_sample,
        drg_sample=drg_sample,
        hcris_samples=hcris,
        connections=connections,
        quality_measures=quality,
        corpus_deal_count=len(corpus),
    )
