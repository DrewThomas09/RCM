"""Clinical Trial Site Economics Analyzer.

Models site-level economics for PE-backed clinical trial site networks (SMOs).
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class SiteDetail:
    site_id: str
    therapeutic_area: str
    active_trials: int
    patient_screen_volume: int
    enrollment_rate_pct: float
    annual_revenue_mm: float
    operating_margin_pct: float
    roi_per_study_k: float


@dataclass
class TherapeuticArea:
    area: str
    site_count: int
    active_trials: int
    median_revenue_per_site_mm: float
    median_enrollment_rate_pct: float
    growth_trajectory: str


@dataclass
class TrialPhaseEconomics:
    phase: str
    avg_site_payment_k: float
    avg_patients_per_site: int
    avg_trial_duration_months: int
    avg_total_revenue_k: float
    typical_margin_pct: float


@dataclass
class SponsorRelationship:
    sponsor: str
    sponsor_type: str
    active_trials: int
    trials_completed_ltm: int
    avg_per_study_fee_k: float
    on_time_delivery_pct: float
    repeat_engagement: str


@dataclass
class CostStructure:
    category: str
    pct_of_revenue: float
    annual_cost_mm: float
    trend: str


@dataclass
class TrialSiteResult:
    total_sites: int
    total_active_trials: int
    annual_revenue_mm: float
    blended_margin_pct: float
    avg_enrollment_rate_pct: float
    sites: List[SiteDetail]
    therapeutic_areas: List[TherapeuticArea]
    phase_econ: List[TrialPhaseEconomics]
    sponsors: List[SponsorRelationship]
    cost_structure: List[CostStructure]
    corpus_deal_count: int


def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 97):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    return deals


def _build_sites() -> List[SiteDetail]:
    import hashlib
    ta_mix = [
        ("Oncology", 8, 32000, 0.048, 5.85),
        ("Cardiology", 6, 18500, 0.062, 3.42),
        ("Neurology", 5, 12000, 0.052, 2.85),
        ("Dermatology", 4, 24000, 0.085, 2.20),
        ("Endocrinology / Metabolic", 4, 22000, 0.068, 2.65),
        ("Immunology / Rheum", 4, 15500, 0.058, 2.95),
        ("Ophthalmology", 3, 8500, 0.075, 1.85),
        ("Psychiatry / CNS", 3, 11000, 0.058, 1.62),
        ("Pediatrics", 2, 6800, 0.072, 1.18),
        ("Rare Disease", 2, 2200, 0.180, 2.48),
    ]
    rows = []
    site_idx = 0
    for area, site_count, screen_base, rate_base, rev_base in ta_mix:
        for i in range(site_count):
            site_idx += 1
            h = int(hashlib.md5(f"{area}{i}".encode()).hexdigest()[:6], 16)
            screens = int(screen_base / site_count * (0.8 + (h % 40) / 100))
            rate = rate_base * (0.85 + (h % 30) / 100)
            active = 4 + (h % 6)
            rev = rev_base * (0.85 + (h % 30) / 100)
            margin = 0.18 + (h % 15) / 100
            roi_per_study = rev * margin / max(active, 1) * 1000
            rows.append(SiteDetail(
                site_id=f"SITE-{site_idx:03d}",
                therapeutic_area=area,
                active_trials=active,
                patient_screen_volume=screens,
                enrollment_rate_pct=round(rate, 4),
                annual_revenue_mm=round(rev, 2),
                operating_margin_pct=round(margin, 4),
                roi_per_study_k=round(roi_per_study, 1),
            ))
    return rows


def _build_therapeutic_areas(sites: List[SiteDetail]) -> List[TherapeuticArea]:
    import statistics
    buckets: dict = {}
    for s in sites:
        buckets.setdefault(s.therapeutic_area, []).append(s)
    rows = []
    area_trends = {
        "Oncology": "accelerating", "Cardiology": "stable", "Neurology": "accelerating",
        "Dermatology": "stable", "Endocrinology / Metabolic": "accelerating (GLP-1)",
        "Immunology / Rheum": "stable", "Ophthalmology": "stable",
        "Psychiatry / CNS": "accelerating (psychedelics)", "Pediatrics": "stable",
        "Rare Disease": "accelerating",
    }
    for area, ss in buckets.items():
        revenues = [s.annual_revenue_mm for s in ss]
        rates = [s.enrollment_rate_pct for s in ss]
        rows.append(TherapeuticArea(
            area=area,
            site_count=len(ss),
            active_trials=sum(s.active_trials for s in ss),
            median_revenue_per_site_mm=round(statistics.median(revenues), 2),
            median_enrollment_rate_pct=round(statistics.median(rates), 4),
            growth_trajectory=area_trends.get(area, "stable"),
        ))
    return sorted(rows, key=lambda r: r.site_count, reverse=True)


def _build_phase_econ() -> List[TrialPhaseEconomics]:
    return [
        TrialPhaseEconomics("Phase I", 285.0, 24, 18, 685.0, 0.24),
        TrialPhaseEconomics("Phase II", 485.0, 85, 30, 1625.0, 0.22),
        TrialPhaseEconomics("Phase III", 1250.0, 325, 42, 4850.0, 0.18),
        TrialPhaseEconomics("Phase IV / PMS", 185.0, 120, 24, 525.0, 0.28),
        TrialPhaseEconomics("DCT (Decentralized)", 420.0, 180, 28, 1180.0, 0.26),
    ]


def _build_sponsors() -> List[SponsorRelationship]:
    return [
        SponsorRelationship("Pfizer", "Large Pharma", 18, 8, 725.0, 0.88, "repeat"),
        SponsorRelationship("Merck & Co", "Large Pharma", 14, 6, 685.0, 0.92, "repeat"),
        SponsorRelationship("Bristol Myers Squibb", "Large Pharma", 12, 5, 820.0, 0.85, "repeat"),
        SponsorRelationship("Eli Lilly", "Large Pharma", 15, 7, 685.0, 0.91, "repeat"),
        SponsorRelationship("AstraZeneca", "Large Pharma", 11, 4, 620.0, 0.82, "repeat"),
        SponsorRelationship("IQVIA (CRO)", "CRO", 22, 11, 485.0, 0.78, "pass-through"),
        SponsorRelationship("Parexel (CRO)", "CRO", 18, 8, 425.0, 0.80, "pass-through"),
        SponsorRelationship("Novartis", "Large Pharma", 13, 6, 725.0, 0.87, "repeat"),
        SponsorRelationship("Roche / Genentech", "Large Pharma", 16, 7, 780.0, 0.89, "repeat"),
        SponsorRelationship("Biogen", "Specialty Biotech", 6, 3, 520.0, 0.75, "repeat"),
        SponsorRelationship("Vertex", "Specialty Biotech", 5, 2, 820.0, 0.85, "repeat"),
        SponsorRelationship("Moderna", "Specialty Biotech", 8, 3, 385.0, 0.72, "growing"),
    ]


def _build_cost_structure(total_rev: float) -> List[CostStructure]:
    items = [
        ("Clinical Staff (CRC/Coordinators)", 0.32, "stable"),
        ("Physician Investigators", 0.18, "rising (wage pressure)"),
        ("Facility / Lease / Utilities", 0.08, "stable"),
        ("Lab & Imaging Pass-Through", 0.12, "stable"),
        ("Patient Stipends / Travel", 0.04, "rising (DCT shift)"),
        ("Recruitment / Patient Acquisition", 0.05, "rising"),
        ("Technology / eSource / CTMS", 0.03, "stable"),
        ("Regulatory / IRB / Compliance", 0.04, "rising"),
        ("Corporate / G&A", 0.06, "stable"),
    ]
    rows = []
    for cat, pct, trend in items:
        rows.append(CostStructure(
            category=cat,
            pct_of_revenue=pct,
            annual_cost_mm=round(total_rev * pct, 2),
            trend=trend,
        ))
    return rows


def compute_trial_site_econ() -> TrialSiteResult:
    corpus = _load_corpus()

    sites = _build_sites()
    tas = _build_therapeutic_areas(sites)
    phase = _build_phase_econ()
    sponsors = _build_sponsors()

    total_rev = sum(s.annual_revenue_mm for s in sites)
    blended_margin = sum(s.annual_revenue_mm * s.operating_margin_pct for s in sites) / total_rev if total_rev else 0
    total_trials = sum(s.active_trials for s in sites)
    avg_rate = sum(s.enrollment_rate_pct for s in sites) / len(sites) if sites else 0

    cost_structure = _build_cost_structure(total_rev)

    return TrialSiteResult(
        total_sites=len(sites),
        total_active_trials=total_trials,
        annual_revenue_mm=round(total_rev, 2),
        blended_margin_pct=round(blended_margin, 4),
        avg_enrollment_rate_pct=round(avg_rate, 4),
        sites=sites,
        therapeutic_areas=tas,
        phase_econ=phase,
        sponsors=sponsors,
        cost_structure=cost_structure,
        corpus_deal_count=len(corpus),
    )
