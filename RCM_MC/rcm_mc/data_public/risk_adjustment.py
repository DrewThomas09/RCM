"""Risk Adjustment / HCC (Hierarchical Condition Category) Tracker.

Tracks risk adjustment factor (RAF) scores, HCC coding accuracy,
gap-closure programs, RADV exposure, revenue impact.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class PortfolioRAF:
    deal: str
    sector: str
    ma_lives_k: float
    avg_raf: float
    prior_year_raf: float
    raf_trend: float
    ma_revenue_m: float
    revenue_per_raf_point_m: float
    coding_intensity: str


@dataclass
class HCCGap:
    hcc: str
    hcc_description: str
    portfolio_members_k: int
    open_suspects: int
    gap_closure_rate_pct: float
    revenue_opportunity_m: float
    clinical_priority: str


@dataclass
class CodingQuality:
    deal: str
    documentation_score: float
    mra_quality_pct: float
    auto_adjudicated_pct: float
    provider_coding_training_pct: float
    chart_review_coverage_pct: float
    prospective_coding_pct: float


@dataclass
class RADVSimulation:
    deal: str
    current_raf: float
    radv_extrapolation_recovery_m: float
    audit_sample_size: int
    error_rate_pct: float
    likely_payback_m: float
    max_exposure_m: float


@dataclass
class V28Impact:
    category: str
    members_affected_k: int
    v24_raf: float
    v28_raf: float
    raf_delta: float
    revenue_impact_m: float
    mitigation: str


@dataclass
class ProgramMetric:
    program: str
    portfolio_deals: int
    members_engaged_k: int
    gaps_closed: int
    raf_uplift: float
    revenue_captured_m: float
    cost_per_gap_closed: float


@dataclass
class RAFResult:
    total_ma_lives_k: float
    weighted_avg_raf: float
    total_ma_revenue_m: float
    total_raf_gap_opportunity_m: float
    radv_total_exposure_m: float
    avg_coding_intensity_score: float
    portfolio_deals_exposed: int
    portfolios: List[PortfolioRAF]
    hcc_gaps: List[HCCGap]
    coding: List[CodingQuality]
    radv_sim: List[RADVSimulation]
    v28: List[V28Impact]
    programs: List[ProgramMetric]
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


def _build_portfolios() -> List[PortfolioRAF]:
    return [
        PortfolioRAF("Project Cypress — GI Network", "Gastroenterology", 168.0, 1.18, 1.12, 0.054, 148.0, 0.22, "disciplined"),
        PortfolioRAF("Project Magnolia — MSK Platform", "MSK / Ortho", 145.0, 1.22, 1.18, 0.034, 132.0, 0.21, "disciplined"),
        PortfolioRAF("Project Redwood — Behavioral", "Behavioral Health", 118.0, 1.85, 1.75, 0.057, 185.0, 0.30, "high intensity"),
        PortfolioRAF("Project Cedar — Cardiology", "Cardiology", 195.0, 1.28, 1.22, 0.049, 215.0, 0.25, "disciplined"),
        PortfolioRAF("Project Willow — Fertility", "Fertility / IVF", 18.0, 0.68, 0.65, 0.046, 22.0, 0.18, "standard"),
        PortfolioRAF("Project Spruce — Radiology", "Radiology", 110.0, 1.15, 1.12, 0.027, 95.0, 0.20, "standard"),
        PortfolioRAF("Project Aspen — Eye Care", "Eye Care", 85.0, 1.05, 1.02, 0.029, 72.0, 0.19, "standard"),
        PortfolioRAF("Project Maple — Urology", "Urology", 78.0, 1.12, 1.08, 0.037, 82.0, 0.19, "standard"),
        PortfolioRAF("Project Sage — Home Health", "Home Health", 128.0, 2.12, 1.98, 0.071, 245.0, 0.32, "aggressive"),
        PortfolioRAF("Project Linden — Behavioral", "Behavioral Health", 88.0, 1.78, 1.68, 0.060, 142.0, 0.30, "aggressive"),
        PortfolioRAF("Project Ash — Infusion", "Infusion", 48.0, 1.95, 1.85, 0.054, 95.0, 0.32, "high intensity"),
    ]


def _build_hcc_gaps() -> List[HCCGap]:
    return [
        HCCGap("HCC 18 — Diabetes with Chronic Complications", "Diabetes w/ CKD, retinopathy, neuropathy",
               225, 12800, 0.82, 18.5, "high"),
        HCCGap("HCC 19 — Diabetes without Complications", "Type 1/2 diabetes uncomplicated",
               385, 8500, 0.88, 8.2, "medium"),
        HCCGap("HCC 82 — Respiratory Dependence (Chronic)", "Ventilator/BiPAP/chronic O2",
               28, 485, 0.68, 12.5, "high"),
        HCCGap("HCC 85 — Congestive Heart Failure", "Systolic/diastolic CHF",
               168, 6200, 0.78, 15.8, "high"),
        HCCGap("HCC 96 — Specified Heart Arrhythmias", "AFib, ventricular tachycardia",
               145, 4800, 0.82, 10.5, "medium"),
        HCCGap("HCC 108 — Vascular Disease", "PAD, AAA, carotid stenosis",
               135, 5200, 0.72, 9.8, "medium"),
        HCCGap("HCC 111 — Chronic Obstructive Pulmonary Disease", "COPD w/ emphysema",
               175, 7800, 0.76, 14.5, "high"),
        HCCGap("HCC 135 — Acute Renal Failure", "Stage 3-5 CKD, ESRD",
               65, 2200, 0.72, 8.8, "high"),
        HCCGap("HCC 155 — Atherosclerosis of the Extremities", "PAD with complications",
               85, 3400, 0.68, 7.5, "medium"),
        HCCGap("HCC 170 — Peripheral Vascular Disease", "PAD claudication",
               120, 4200, 0.75, 8.2, "medium"),
        HCCGap("HCC 58 — Major Depression, Bipolar, Paranoid", "Major depressive, bipolar disorders",
               145, 8500, 0.65, 11.5, "high"),
        HCCGap("HCC 59 — Reactive and Unspecified Psychosis", "Psychosis NEC, schizoaffective",
               42, 1850, 0.62, 6.8, "medium"),
        HCCGap("HCC 54 — Drug/Alcohol Dependence", "SUD with complications",
               95, 5500, 0.58, 8.5, "high"),
        HCCGap("HCC 11 — Cancer (Breast, Prostate, Colorectal)", "Active cancer treatment",
               105, 3800, 0.82, 12.5, "high"),
        HCCGap("HCC 40 — Rheumatoid Arthritis & Inflammatory", "RA, Ankylosing Spondylitis",
               85, 3200, 0.78, 9.8, "medium"),
    ]


def _build_coding() -> List[CodingQuality]:
    return [
        CodingQuality("Project Cypress — GI Network", 8.8, 0.92, 0.78, 0.88, 0.85, 0.62),
        CodingQuality("Project Magnolia — MSK Platform", 8.5, 0.90, 0.75, 0.82, 0.78, 0.58),
        CodingQuality("Project Redwood — Behavioral", 8.2, 0.88, 0.65, 0.78, 0.92, 0.72),
        CodingQuality("Project Cedar — Cardiology", 9.0, 0.94, 0.82, 0.90, 0.88, 0.68),
        CodingQuality("Project Willow — Fertility", 8.5, 0.92, 0.78, 0.85, 0.72, 0.42),
        CodingQuality("Project Spruce — Radiology", 8.2, 0.88, 0.85, 0.75, 0.68, 0.48),
        CodingQuality("Project Aspen — Eye Care", 8.0, 0.86, 0.82, 0.72, 0.65, 0.45),
        CodingQuality("Project Maple — Urology", 8.2, 0.88, 0.72, 0.78, 0.72, 0.52),
        CodingQuality("Project Sage — Home Health", 8.8, 0.92, 0.48, 0.88, 0.95, 0.85),
        CodingQuality("Project Linden — Behavioral", 8.2, 0.88, 0.58, 0.82, 0.88, 0.72),
        CodingQuality("Project Ash — Infusion", 8.8, 0.92, 0.75, 0.85, 0.92, 0.78),
    ]


def _build_radv() -> List[RADVSimulation]:
    return [
        RADVSimulation("Project Cypress — GI Network", 1.18, 2.5, 200, 0.042, 1.8, 6.2),
        RADVSimulation("Project Magnolia — MSK Platform", 1.22, 2.2, 200, 0.038, 1.5, 5.5),
        RADVSimulation("Project Redwood — Behavioral", 1.85, 4.8, 200, 0.068, 4.2, 12.5),
        RADVSimulation("Project Cedar — Cardiology", 1.28, 3.2, 200, 0.048, 2.5, 8.0),
        RADVSimulation("Project Spruce — Radiology", 1.15, 1.2, 200, 0.035, 0.8, 3.0),
        RADVSimulation("Project Aspen — Eye Care", 1.05, 0.8, 200, 0.030, 0.5, 1.8),
        RADVSimulation("Project Maple — Urology", 1.12, 1.1, 200, 0.040, 0.7, 2.5),
        RADVSimulation("Project Sage — Home Health", 2.12, 8.5, 200, 0.085, 8.5, 22.0),
        RADVSimulation("Project Linden — Behavioral", 1.78, 3.5, 200, 0.072, 3.8, 10.5),
        RADVSimulation("Project Ash — Infusion", 1.95, 2.8, 200, 0.055, 2.2, 6.5),
    ]


def _build_v28() -> List[V28Impact]:
    return [
        V28Impact("Neoplasms (cancer)", 35, 0.422, 0.378, -0.044, -2.8, "enhance prospective DX capture"),
        V28Impact("Endocrine / Metabolic (DM)", 485, 0.118, 0.095, -0.023, -8.5, "DM w/ complications documentation"),
        V28Impact("Respiratory (COPD)", 145, 0.328, 0.285, -0.043, -4.2, "emphysema specificity"),
        V28Impact("Cardiovascular (CHF)", 185, 0.285, 0.242, -0.043, -5.5, "CHF class specificity + ejection fraction"),
        V28Impact("Renal (CKD)", 75, 0.445, 0.385, -0.060, -2.8, "CKD staging + comorbidity"),
        V28Impact("Behavioral / MH", 185, 0.225, 0.195, -0.030, -4.8, "DSM-5 specificity"),
        V28Impact("Musculoskeletal (RA)", 65, 0.225, 0.195, -0.030, -1.8, "RA severity"),
        V28Impact("Vascular (PAD)", 85, 0.195, 0.168, -0.027, -2.2, "PAD with chronic complications"),
        V28Impact("Substance Use Disorder", 95, 0.385, 0.325, -0.060, -4.5, "SUD with complications"),
        V28Impact("Immune / Auto-immune", 55, 0.285, 0.252, -0.033, -1.5, "systemic sclerosis, lupus"),
    ]


def _build_programs() -> List[ProgramMetric]:
    return [
        ProgramMetric("Annual Wellness Visit (AWV) program", 11, 258, 12800, 0.068, 28.5, 0.45),
        ProgramMetric("In-home HRA (Signify/VillageMD)", 8, 125, 8500, 0.085, 18.5, 0.65),
        ProgramMetric("Prospective chart review (EHR-embedded)", 11, 485, 22500, 0.088, 65.0, 0.28),
        ProgramMetric("Retrospective chart review (3rd party)", 11, 685, 18500, 0.038, 32.0, 0.42),
        ProgramMetric("Provider coding training", 11, 425, 14500, 0.052, 28.0, 0.22),
        ProgramMetric("Transitional Care Management (TCM)", 6, 85, 4200, 0.045, 8.5, 0.32),
        ProgramMetric("Chronic Care Management (CCM)", 9, 285, 12500, 0.048, 18.5, 0.35),
        ProgramMetric("Community-based HRA + screening", 4, 68, 5200, 0.075, 12.5, 0.58),
        ProgramMetric("Medication adherence / MTM", 11, 325, 8500, 0.028, 12.0, 0.48),
        ProgramMetric("RA / PFS coding specialist deployment", 8, 185, 8200, 0.062, 22.5, 0.35),
    ]


def compute_risk_adjustment() -> RAFResult:
    corpus = _load_corpus()
    portfolios = _build_portfolios()
    hcc_gaps = _build_hcc_gaps()
    coding = _build_coding()
    radv_sim = _build_radv()
    v28 = _build_v28()
    programs = _build_programs()

    total_lives = sum(p.ma_lives_k for p in portfolios)
    wtd_raf = sum(p.avg_raf * p.ma_lives_k for p in portfolios) / total_lives if total_lives > 0 else 0
    total_rev = sum(p.ma_revenue_m for p in portfolios)
    total_gap = sum(h.revenue_opportunity_m for h in hcc_gaps)
    radv_exposure = sum(r.max_exposure_m for r in radv_sim)
    ci_map = {"disciplined": 9.0, "standard": 8.0, "high intensity": 7.0, "aggressive": 6.0}
    avg_ci = sum(ci_map.get(p.coding_intensity, 8.0) for p in portfolios) / len(portfolios) if portfolios else 0

    return RAFResult(
        total_ma_lives_k=round(total_lives, 1),
        weighted_avg_raf=round(wtd_raf, 3),
        total_ma_revenue_m=round(total_rev, 1),
        total_raf_gap_opportunity_m=round(total_gap, 1),
        radv_total_exposure_m=round(radv_exposure, 1),
        avg_coding_intensity_score=round(avg_ci, 2),
        portfolio_deals_exposed=len(portfolios),
        portfolios=portfolios,
        hcc_gaps=hcc_gaps,
        coding=coding,
        radv_sim=radv_sim,
        v28=v28,
        programs=programs,
        corpus_deal_count=len(corpus),
    )
