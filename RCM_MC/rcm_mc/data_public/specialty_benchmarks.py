"""Specialty Benchmarks Library.

MGMA / Sullivan Cotter / Radford operational and compensation benchmarks
across 30+ healthcare specialties: physician comp, RVU productivity,
overhead ratios, margin structure.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class SpecialtyBenchmark:
    specialty: str
    category: str
    median_total_comp_k: float
    p25_comp_k: float
    p75_comp_k: float
    median_wrvu_production: int
    median_wrvu_comp_per_rvu: float
    median_patient_per_day: int
    median_overhead_pct: float
    median_collections_per_rvu: float


@dataclass
class PracticeEconomics:
    specialty: str
    median_revenue_per_fte_k: float
    median_ebitda_margin_pct: float
    median_payer_mix_commercial: float
    median_payer_mix_medicare: float
    median_payer_mix_medicaid: float
    avg_pto_days: int
    typical_signing_bonus_k: float
    loan_repayment_k: float


@dataclass
class NewPatientMetric:
    specialty: str
    median_new_patients_monthly: int
    median_new_patient_spend_monthly_k: float
    avg_marketing_cost_per_new_k: float
    referral_vs_direct_pct: float
    digital_channel_pct: float


@dataclass
class AncillaryRevenue:
    specialty: str
    ancillary_services: str
    median_ancillary_rev_pct: float
    typical_capex_required_k: int
    payback_months: int
    incremental_ebitda_pct: float


@dataclass
class QualityBenchmark:
    specialty: str
    measure: str
    industry_median: float
    top_decile: float
    portfolio_median: float
    mips_weight: str
    payer_incentive_bps: int


@dataclass
class StaffingRatio:
    specialty: str
    role: str
    median_per_physician: float
    p25_ratio: float
    p75_ratio: float
    typical_comp_k: float
    turnover_pct: float


@dataclass
class BenchmarkResult:
    total_specialties: int
    specialties_with_portfolio_coverage: int
    avg_comp_k: float
    avg_wrvu: float
    avg_overhead_pct: float
    avg_ebitda_margin_pct: float
    benchmarks: List[SpecialtyBenchmark]
    economics: List[PracticeEconomics]
    new_patients: List[NewPatientMetric]
    ancillary: List[AncillaryRevenue]
    quality: List[QualityBenchmark]
    staffing: List[StaffingRatio]
    corpus_deal_count: int


def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 122):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    return deals


def _build_benchmarks() -> List[SpecialtyBenchmark]:
    return [
        SpecialtyBenchmark("Primary Care (Internal Medicine)", "Primary Care", 285.0, 225.0, 345.0, 4850, 58.5, 22, 0.42, 62.5),
        SpecialtyBenchmark("Primary Care (Family Medicine)", "Primary Care", 275.0, 220.0, 335.0, 5100, 54.2, 23, 0.42, 58.8),
        SpecialtyBenchmark("Pediatrics", "Primary Care", 245.0, 195.0, 305.0, 4800, 51.2, 22, 0.43, 55.0),
        SpecialtyBenchmark("Gastroenterology", "Medical Specialty", 625.0, 485.0, 845.0, 7500, 83.5, 16, 0.36, 85.2),
        SpecialtyBenchmark("Cardiology (non-invasive)", "Medical Specialty", 595.0, 465.0, 785.0, 7200, 82.5, 14, 0.35, 82.0),
        SpecialtyBenchmark("Cardiology (interventional)", "Medical Specialty", 725.0, 565.0, 985.0, 8500, 85.2, 12, 0.36, 86.8),
        SpecialtyBenchmark("Dermatology", "Medical Specialty", 575.0, 445.0, 745.0, 8200, 70.2, 28, 0.38, 72.5),
        SpecialtyBenchmark("Neurology", "Medical Specialty", 395.0, 315.0, 515.0, 5800, 68.2, 18, 0.42, 70.5),
        SpecialtyBenchmark("Oncology (medical)", "Medical Specialty", 595.0, 465.0, 785.0, 7200, 82.5, 16, 0.42, 85.2),
        SpecialtyBenchmark("Psychiatry", "Medical Specialty", 335.0, 275.0, 435.0, 4800, 69.8, 22, 0.38, 71.5),
        SpecialtyBenchmark("Endocrinology", "Medical Specialty", 325.0, 260.0, 425.0, 5200, 62.5, 16, 0.42, 64.2),
        SpecialtyBenchmark("Rheumatology", "Medical Specialty", 335.0, 265.0, 435.0, 5100, 65.7, 18, 0.42, 67.8),
        SpecialtyBenchmark("Pulmonology", "Medical Specialty", 425.0, 335.0, 565.0, 5500, 77.2, 14, 0.38, 78.5),
        SpecialtyBenchmark("Nephrology", "Medical Specialty", 445.0, 355.0, 585.0, 5800, 76.7, 14, 0.38, 78.2),
        SpecialtyBenchmark("Infectious Disease", "Medical Specialty", 295.0, 235.0, 385.0, 4800, 61.5, 14, 0.42, 62.5),
        SpecialtyBenchmark("Urology", "Surgical Specialty", 525.0, 415.0, 695.0, 7200, 72.9, 14, 0.38, 75.5),
        SpecialtyBenchmark("Orthopedic Surgery", "Surgical Specialty", 685.0, 545.0, 925.0, 8800, 77.8, 12, 0.36, 82.5),
        SpecialtyBenchmark("Orthopedic Sports Medicine", "Surgical Specialty", 785.0, 625.0, 1060.0, 9500, 82.6, 12, 0.34, 88.2),
        SpecialtyBenchmark("ENT (Otolaryngology)", "Surgical Specialty", 525.0, 415.0, 695.0, 7500, 70.0, 14, 0.38, 72.5),
        SpecialtyBenchmark("Ophthalmology", "Surgical Specialty", 525.0, 415.0, 685.0, 7800, 67.3, 22, 0.40, 68.5),
        SpecialtyBenchmark("OB/GYN", "Surgical Specialty", 395.0, 315.0, 525.0, 6500, 60.8, 18, 0.40, 62.5),
        SpecialtyBenchmark("General Surgery", "Surgical Specialty", 485.0, 385.0, 635.0, 7200, 67.4, 14, 0.38, 70.0),
        SpecialtyBenchmark("Plastic Surgery", "Surgical Specialty", 585.0, 465.0, 785.0, 6800, 85.8, 10, 0.36, 88.5),
        SpecialtyBenchmark("Anesthesiology", "Hospital-based", 485.0, 385.0, 625.0, 8500, 57.1, 0, 0.25, 62.0),
        SpecialtyBenchmark("Radiology (diagnostic)", "Hospital-based", 525.0, 425.0, 685.0, 8800, 59.7, 0, 0.32, 63.5),
        SpecialtyBenchmark("Interventional Radiology", "Hospital-based", 625.0, 495.0, 815.0, 9200, 67.9, 0, 0.34, 72.5),
        SpecialtyBenchmark("Pathology", "Hospital-based", 425.0, 335.0, 545.0, 6200, 68.5, 0, 0.38, 70.0),
        SpecialtyBenchmark("Emergency Medicine", "Hospital-based", 435.0, 345.0, 555.0, 6500, 66.9, 0, 0.28, 68.5),
        SpecialtyBenchmark("Hospitalist", "Hospital-based", 345.0, 275.0, 445.0, 4800, 71.9, 0, 0.28, 73.5),
        SpecialtyBenchmark("Physical Medicine & Rehab", "Medical Specialty", 325.0, 260.0, 415.0, 4900, 66.3, 18, 0.42, 68.0),
        SpecialtyBenchmark("Sleep Medicine", "Medical Specialty", 335.0, 265.0, 425.0, 4800, 69.8, 14, 0.42, 71.2),
        SpecialtyBenchmark("Pain Management", "Procedural", 485.0, 385.0, 635.0, 7500, 64.7, 18, 0.40, 66.5),
    ]


def _build_economics() -> List[PracticeEconomics]:
    return [
        PracticeEconomics("Primary Care (Internal Med)", 585.0, 0.125, 0.52, 0.28, 0.12, 22, 15, 50),
        PracticeEconomics("Pediatrics", 485.0, 0.125, 0.48, 0.02, 0.35, 22, 15, 35),
        PracticeEconomics("Gastroenterology", 1250.0, 0.285, 0.58, 0.28, 0.09, 28, 45, 75),
        PracticeEconomics("Cardiology (interventional)", 1485.0, 0.265, 0.52, 0.32, 0.10, 24, 85, 75),
        PracticeEconomics("Dermatology", 985.0, 0.315, 0.62, 0.22, 0.06, 22, 30, 50),
        PracticeEconomics("Orthopedic Sports Medicine", 1585.0, 0.385, 0.62, 0.28, 0.08, 24, 65, 75),
        PracticeEconomics("Ophthalmology", 1185.0, 0.245, 0.38, 0.52, 0.08, 24, 45, 50),
        PracticeEconomics("Urology", 985.0, 0.225, 0.52, 0.32, 0.10, 22, 35, 50),
        PracticeEconomics("OB/GYN", 785.0, 0.165, 0.58, 0.08, 0.28, 22, 25, 50),
        PracticeEconomics("Psychiatry", 650.0, 0.195, 0.52, 0.18, 0.22, 22, 15, 50),
        PracticeEconomics("Oncology (medical)", 1150.0, 0.105, 0.42, 0.42, 0.14, 22, 45, 75),
        PracticeEconomics("Radiology (diagnostic)", 1085.0, 0.285, 0.45, 0.38, 0.12, 30, 50, 75),
        PracticeEconomics("Plastic Surgery (aesthetic)", 1385.0, 0.425, 0.85, 0.08, 0.02, 22, 25, 25),
        PracticeEconomics("Emergency Medicine", 895.0, 0.145, 0.35, 0.35, 0.25, 28, 35, 50),
        PracticeEconomics("Pain Management", 985.0, 0.225, 0.48, 0.38, 0.12, 22, 30, 50),
    ]


def _build_new_patients() -> List[NewPatientMetric]:
    return [
        NewPatientMetric("Primary Care (Internal Med)", 65, 8.5, 0.12, 0.45, 0.22),
        NewPatientMetric("Pediatrics", 75, 7.2, 0.08, 0.55, 0.18),
        NewPatientMetric("Gastroenterology", 55, 18.5, 0.18, 0.88, 0.18),
        NewPatientMetric("Cardiology (interventional)", 45, 25.2, 0.22, 0.95, 0.12),
        NewPatientMetric("Dermatology", 125, 12.5, 0.15, 0.35, 0.42),
        NewPatientMetric("Orthopedic Sports Medicine", 65, 28.5, 0.32, 0.55, 0.35),
        NewPatientMetric("Ophthalmology", 85, 14.2, 0.12, 0.55, 0.25),
        NewPatientMetric("Urology", 48, 16.5, 0.18, 0.72, 0.15),
        NewPatientMetric("OB/GYN", 65, 12.0, 0.15, 0.52, 0.28),
        NewPatientMetric("Psychiatry", 38, 10.5, 0.25, 0.42, 0.38),
        NewPatientMetric("Oncology (medical)", 25, 45.0, 0.18, 0.92, 0.08),
        NewPatientMetric("Plastic Surgery (aesthetic)", 45, 28.5, 0.42, 0.25, 0.62),
        NewPatientMetric("Fertility / IVF", 38, 18.5, 0.65, 0.15, 0.72),
        NewPatientMetric("Pain Management", 55, 14.5, 0.22, 0.78, 0.15),
    ]


def _build_ancillary() -> List[AncillaryRevenue]:
    return [
        AncillaryRevenue("Gastroenterology", "ASC / Endoscopy Center", 0.42, 2850, 24, 0.125),
        AncillaryRevenue("Cardiology", "Cath lab / imaging / echo", 0.38, 3850, 30, 0.115),
        AncillaryRevenue("Orthopedic Surgery", "ASC / PT / imaging", 0.45, 3200, 22, 0.145),
        AncillaryRevenue("Dermatology", "Mohs / aesthetics / pathology in-house", 0.38, 950, 18, 0.105),
        AncillaryRevenue("Urology", "ASC / in-office procedures / lithotripsy", 0.32, 1850, 28, 0.085),
        AncillaryRevenue("Ophthalmology", "ASC / optical dispensary / LASIK", 0.42, 2250, 24, 0.125),
        AncillaryRevenue("Pain Management", "ASC / in-office interventional", 0.38, 1450, 22, 0.115),
        AncillaryRevenue("OB/GYN", "Ultrasound / lab / in-office procedures", 0.22, 585, 18, 0.045),
        AncillaryRevenue("ENT", "Balloon sinuplasty / in-office / allergy testing", 0.28, 685, 18, 0.062),
        AncillaryRevenue("Oncology", "Infusion suite / in-office pharmacy", 0.55, 4500, 30, 0.180),
        AncillaryRevenue("Primary Care", "Lab / vaccines / CCM / CGM", 0.15, 225, 12, 0.032),
        AncillaryRevenue("Pulmonology", "Sleep lab / PFT / bronchoscopy", 0.25, 450, 18, 0.045),
    ]


def _build_quality() -> List[QualityBenchmark]:
    return [
        QualityBenchmark("Primary Care", "BP control <140/90", 0.72, 0.84, 0.75, "MIPS primary", 200),
        QualityBenchmark("Primary Care", "DM A1c <8%", 0.68, 0.80, 0.72, "MIPS primary", 200),
        QualityBenchmark("Primary Care", "Colorectal Screening 50-75", 0.68, 0.78, 0.71, "MIPS primary", 200),
        QualityBenchmark("Cardiology", "LDL <100 in CAD patients", 0.75, 0.86, 0.78, "MIPS specialty", 150),
        QualityBenchmark("Cardiology", "Anticoag in AFib", 0.82, 0.92, 0.84, "MIPS specialty", 150),
        QualityBenchmark("Orthopedic Surgery", "Hip/Knee — 90-day readmission", 0.048, 0.028, 0.042, "MIPS specialty + BPCI-A", 250),
        QualityBenchmark("Gastroenterology", "Colonoscopy — ADR rate", 0.28, 0.38, 0.32, "MIPS specialty", 200),
        QualityBenchmark("OB/GYN", "NTSV C-section rate", 0.265, 0.225, 0.255, "MIPS specialty + Leapfrog", 150),
        QualityBenchmark("Oncology", "Pain assessment at each encounter", 0.82, 0.92, 0.85, "MIPS / OCM", 200),
        QualityBenchmark("Dermatology", "Biopsy concordance", 0.92, 0.96, 0.94, "MIPS specialty", 100),
        QualityBenchmark("Urology", "PSA screening appropriateness", 0.78, 0.88, 0.82, "MIPS specialty", 150),
        QualityBenchmark("Ophthalmology", "DR screening in DM patients", 0.72, 0.82, 0.75, "MIPS specialty", 150),
        QualityBenchmark("Psychiatry", "Depression screening + follow-up", 0.68, 0.82, 0.72, "MIPS behavioral", 200),
    ]


def _build_staffing() -> List[StaffingRatio]:
    return [
        StaffingRatio("Primary Care", "Medical Assistant", 1.8, 1.5, 2.2, 48, 0.215),
        StaffingRatio("Primary Care", "RN Care Coordinator", 0.5, 0.3, 0.8, 82, 0.145),
        StaffingRatio("Primary Care", "Front Desk / Scheduling", 1.5, 1.2, 1.8, 42, 0.285),
        StaffingRatio("Gastroenterology", "Medical Assistant", 1.8, 1.5, 2.2, 52, 0.195),
        StaffingRatio("Gastroenterology", "Scope Technician", 1.0, 0.8, 1.3, 65, 0.125),
        StaffingRatio("Gastroenterology", "Endoscopy RN", 1.5, 1.2, 1.9, 95, 0.115),
        StaffingRatio("Cardiology", "Medical Assistant", 2.0, 1.7, 2.4, 52, 0.175),
        StaffingRatio("Cardiology", "Echo Technician", 0.8, 0.5, 1.1, 82, 0.095),
        StaffingRatio("Cardiology", "Cath Lab RN", 2.2, 1.8, 2.6, 108, 0.095),
        StaffingRatio("Orthopedic Surgery", "Medical Assistant", 1.5, 1.3, 1.8, 52, 0.195),
        StaffingRatio("Orthopedic Surgery", "PA / NP", 0.8, 0.5, 1.2, 135, 0.115),
        StaffingRatio("Orthopedic Surgery", "OR Tech / Surgical Scrub", 0.8, 0.6, 1.0, 72, 0.135),
        StaffingRatio("Dermatology", "Medical Assistant", 2.2, 1.8, 2.6, 48, 0.215),
        StaffingRatio("Dermatology", "PA / NP", 0.5, 0.3, 0.8, 125, 0.085),
        StaffingRatio("Oncology", "Infusion RN", 2.5, 2.2, 3.0, 108, 0.145),
        StaffingRatio("OB/GYN", "Medical Assistant", 1.8, 1.5, 2.2, 48, 0.215),
        StaffingRatio("OB/GYN", "L&D RN", 2.8, 2.4, 3.2, 108, 0.165),
        StaffingRatio("Urology", "Medical Assistant", 1.8, 1.5, 2.2, 50, 0.195),
        StaffingRatio("Psychiatry", "Behavioral Tech", 1.2, 0.8, 1.6, 55, 0.245),
    ]


def compute_specialty_benchmarks() -> BenchmarkResult:
    corpus = _load_corpus()
    benchmarks = _build_benchmarks()
    economics = _build_economics()
    new_patients = _build_new_patients()
    ancillary = _build_ancillary()
    quality = _build_quality()
    staffing = _build_staffing()

    avg_comp = sum(b.median_total_comp_k for b in benchmarks) / len(benchmarks) if benchmarks else 0
    avg_wrvu = sum(b.median_wrvu_production for b in benchmarks) / len(benchmarks) if benchmarks else 0
    avg_oh = sum(b.median_overhead_pct for b in benchmarks) / len(benchmarks) if benchmarks else 0
    avg_ebitda = sum(e.median_ebitda_margin_pct for e in economics) / len(economics) if economics else 0

    specialties_covered = 16

    return BenchmarkResult(
        total_specialties=len(benchmarks),
        specialties_with_portfolio_coverage=specialties_covered,
        avg_comp_k=round(avg_comp, 1),
        avg_wrvu=round(avg_wrvu, 0),
        avg_overhead_pct=round(avg_oh, 4),
        avg_ebitda_margin_pct=round(avg_ebitda, 4),
        benchmarks=benchmarks,
        economics=economics,
        new_patients=new_patients,
        ancillary=ancillary,
        quality=quality,
        staffing=staffing,
        corpus_deal_count=len(corpus),
    )
