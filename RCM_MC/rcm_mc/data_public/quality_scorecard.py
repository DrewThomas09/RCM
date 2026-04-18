"""Clinical Quality Scorecard — HEDIS, Stars, readmission, VBC readiness.

Measures clinical outcomes that drive reimbursement and exit value:
- HEDIS preventive care rates
- CMS Star rating proxy (Medicare Advantage)
- 30-day readmission
- Patient satisfaction (HCAHPS / CAHPS proxy)
- VBC participation (MIPS, MSSP, MA shared savings)
- Quality-adjusted EBITDA ("quality bonus" impact)
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Sector-specific quality benchmarks
# ---------------------------------------------------------------------------

_SECTOR_QUALITY_BENCHMARKS = {
    "Physician Services": {
        "hedis_overall": 74, "readmission_30d": 0.12, "satisfaction": 82,
        "vbc_participation": 0.55, "stars_median": 3.8, "quality_bonus_pct": 0.025,
    },
    "Hospital": {
        "hedis_overall": 72, "readmission_30d": 0.155, "satisfaction": 74,
        "vbc_participation": 0.80, "stars_median": 3.5, "quality_bonus_pct": 0.035,
    },
    "Home Health": {
        "hedis_overall": 78, "readmission_30d": 0.145, "satisfaction": 88,
        "vbc_participation": 0.72, "stars_median": 3.9, "quality_bonus_pct": 0.04,
    },
    "Hospice": {
        "hedis_overall": 82, "readmission_30d": 0.05, "satisfaction": 92,
        "vbc_participation": 0.28, "stars_median": 4.1, "quality_bonus_pct": 0.018,
    },
    "Skilled Nursing": {
        "hedis_overall": 68, "readmission_30d": 0.205, "satisfaction": 72,
        "vbc_participation": 0.65, "stars_median": 3.1, "quality_bonus_pct": 0.045,
    },
    "Behavioral Health": {
        "hedis_overall": 58, "readmission_30d": 0.185, "satisfaction": 78,
        "vbc_participation": 0.32, "stars_median": 3.4, "quality_bonus_pct": 0.02,
    },
    "ABA Therapy": {
        "hedis_overall": 71, "readmission_30d": 0.0, "satisfaction": 85,
        "vbc_participation": 0.15, "stars_median": 0.0, "quality_bonus_pct": 0.005,
    },
    "Dialysis": {
        "hedis_overall": 75, "readmission_30d": 0.28, "satisfaction": 78,
        "vbc_participation": 0.95, "stars_median": 3.7, "quality_bonus_pct": 0.055,
    },
    "Pharmacy": {
        "hedis_overall": 85, "readmission_30d": 0.0, "satisfaction": 89,
        "vbc_participation": 0.35, "stars_median": 0.0, "quality_bonus_pct": 0.01,
    },
    "Primary Care": {
        "hedis_overall": 76, "readmission_30d": 0.08, "satisfaction": 84,
        "vbc_participation": 0.75, "stars_median": 4.0, "quality_bonus_pct": 0.04,
    },
    "Urgent Care": {
        "hedis_overall": 62, "readmission_30d": 0.04, "satisfaction": 86,
        "vbc_participation": 0.20, "stars_median": 3.6, "quality_bonus_pct": 0.005,
    },
    "ASC": {
        "hedis_overall": 0.0, "readmission_30d": 0.025, "satisfaction": 90,
        "vbc_participation": 0.28, "stars_median": 0.0, "quality_bonus_pct": 0.008,
    },
}


# ---------------------------------------------------------------------------
# HEDIS measure set
# ---------------------------------------------------------------------------

_HEDIS_MEASURES = [
    {"code": "BCS", "name": "Breast Cancer Screening", "applicable_to": ["Primary Care", "Physician Services"]},
    {"code": "CCS", "name": "Cervical Cancer Screening", "applicable_to": ["Primary Care", "Physician Services"]},
    {"code": "COL", "name": "Colorectal Cancer Screening", "applicable_to": ["Primary Care", "Physician Services", "Gastroenterology"]},
    {"code": "CDC-HbA1c", "name": "Diabetes: HbA1c Control <8%", "applicable_to": ["Primary Care", "Physician Services"]},
    {"code": "CDC-Eye", "name": "Diabetes: Annual Eye Exam", "applicable_to": ["Primary Care", "Ophthalmology"]},
    {"code": "CBP", "name": "Controlling High Blood Pressure", "applicable_to": ["Primary Care", "Physician Services", "Cardiology"]},
    {"code": "IMA", "name": "Immunizations for Adolescents", "applicable_to": ["Pediatrics", "Primary Care"]},
    {"code": "FUH", "name": "Follow-up after Mental Health ER", "applicable_to": ["Behavioral Health", "Primary Care"]},
    {"code": "AMM", "name": "Antidepressant Medication Management", "applicable_to": ["Behavioral Health", "Primary Care"]},
    {"code": "W-30", "name": "Well-Child Visits (0-30 mo)", "applicable_to": ["Pediatrics", "Primary Care"]},
]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class QualityMetric:
    metric: str
    value: float
    unit: str
    benchmark: float
    percentile: float
    status: str            # "top_decile", "above_median", "below_median", "bottom_decile"


@dataclass
class HEDISRow:
    code: str
    name: str
    current_rate: float
    benchmark: float
    gap_pct: float
    applies: bool
    est_patients_affected: int


@dataclass
class VBCProgram:
    program: str
    participation: bool
    annual_bonus_mm: float
    downside_risk: str     # "none", "upside-only", "two-sided", "full-risk"
    notes: str


@dataclass
class QualityAdjustedValue:
    component: str
    annual_impact_mm: float
    multi_year_impact_mm: float
    ev_impact_mm: float


@dataclass
class QualityScorecardResult:
    sector: str
    overall_score: float              # 0-100
    tier: str                         # "elite", "strong", "average", "below_avg"
    metrics: List[QualityMetric]
    hedis: List[HEDISRow]
    vbc_programs: List[VBCProgram]
    value_impacts: List[QualityAdjustedValue]
    total_annual_quality_bonus_mm: float
    total_ev_uplift_from_quality_mm: float
    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 62):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    try:
        from rcm_mc.data_public.deals_corpus import _SEED_DEALS, EXTENDED_SEED_DEALS
        deals = _SEED_DEALS + EXTENDED_SEED_DEALS + deals
    except Exception:
        pass
    return deals


def _get_benchmark(sector: str) -> Dict:
    return _SECTOR_QUALITY_BENCHMARKS.get(sector, _SECTOR_QUALITY_BENCHMARKS["Physician Services"])


def _percentile_rank(actual: float, benchmark: float, higher_better: bool = True) -> float:
    """Compute rough percentile where actual sits relative to benchmark."""
    if benchmark == 0:
        return 50.0
    ratio = actual / benchmark
    if higher_better:
        if ratio >= 1.20: return 95
        if ratio >= 1.10: return 85
        if ratio >= 1.05: return 75
        if ratio >= 1.00: return 62
        if ratio >= 0.95: return 48
        if ratio >= 0.85: return 30
        return 15
    # Lower is better
    if ratio <= 0.75: return 95
    if ratio <= 0.85: return 85
    if ratio <= 0.95: return 75
    if ratio <= 1.00: return 60
    if ratio <= 1.10: return 40
    if ratio <= 1.25: return 20
    return 10


def _status(pct: float) -> str:
    if pct >= 85: return "top_decile"
    if pct >= 50: return "above_median"
    if pct >= 20: return "below_median"
    return "bottom_decile"


def _score_from_metrics(metrics: List[QualityMetric]) -> float:
    if not metrics:
        return 50.0
    return round(sum(m.percentile for m in metrics) / len(metrics), 1)


def _tier(score: float) -> str:
    if score >= 75: return "elite"
    if score >= 55: return "strong"
    if score >= 35: return "average"
    return "below_avg"


def _build_metrics(sector: str, actual: Optional[Dict] = None) -> List[QualityMetric]:
    bench = _get_benchmark(sector)
    actual = actual or {}
    rows = []

    # HEDIS overall
    hb = bench["hedis_overall"]
    h_val = actual.get("hedis_overall", hb * 0.98)
    if hb:
        pct = _percentile_rank(h_val, hb, higher_better=True)
        rows.append(QualityMetric(
            metric="HEDIS Overall (composite)", value=h_val, unit="%", benchmark=hb,
            percentile=pct, status=_status(pct),
        ))

    # Readmission
    rb = bench["readmission_30d"]
    r_val = actual.get("readmission", rb * 1.02)
    if rb > 0:
        pct = _percentile_rank(r_val, rb, higher_better=False)
        rows.append(QualityMetric(
            metric="30-Day Readmission Rate", value=r_val * 100, unit="%", benchmark=rb * 100,
            percentile=pct, status=_status(pct),
        ))

    # Patient satisfaction
    sb = bench["satisfaction"]
    s_val = actual.get("satisfaction", sb - 2)
    pct = _percentile_rank(s_val, sb, higher_better=True)
    rows.append(QualityMetric(
        metric="Patient Satisfaction (HCAHPS)", value=s_val, unit="%", benchmark=sb,
        percentile=pct, status=_status(pct),
    ))

    # VBC participation
    vb = bench["vbc_participation"]
    v_val = actual.get("vbc", vb - 0.05)
    pct = _percentile_rank(v_val, vb, higher_better=True) if vb else 50
    rows.append(QualityMetric(
        metric="VBC Contract Coverage", value=v_val * 100, unit="%", benchmark=vb * 100,
        percentile=pct, status=_status(pct),
    ))

    # Stars
    if bench["stars_median"] > 0:
        star_val = actual.get("stars", bench["stars_median"] - 0.1)
        pct = _percentile_rank(star_val, bench["stars_median"], higher_better=True)
        rows.append(QualityMetric(
            metric="Star Rating (MA proxy)", value=star_val, unit="stars",
            benchmark=bench["stars_median"], percentile=pct, status=_status(pct),
        ))

    return rows


def _build_hedis(sector: str, revenue_mm: float) -> List[HEDISRow]:
    bench = _get_benchmark(sector)
    base_rate = bench["hedis_overall"] / 100
    if not base_rate:
        return []

    # Approximate panel size: revenue / $250 per visit / 2 visits/patient
    panel_size = int(revenue_mm * 1_000_000 / 250 / 2)

    rows = []
    for m in _HEDIS_MEASURES:
        applies = sector in m["applicable_to"] or any(sector.lower() in a.lower() for a in m["applicable_to"])
        current_rate = base_rate * 0.96 + (hash(m["code"]) % 13) * 0.005     # vary per measure
        current_rate = max(0.35, min(0.95, current_rate))
        natl_benchmark = base_rate
        gap = current_rate - natl_benchmark
        affected_panel = panel_size if applies else panel_size // 20
        est_gap_patients = int(affected_panel * abs(gap))

        rows.append(HEDISRow(
            code=m["code"],
            name=m["name"],
            current_rate=round(current_rate, 3),
            benchmark=round(natl_benchmark, 3),
            gap_pct=round(gap, 3),
            applies=applies,
            est_patients_affected=est_gap_patients,
        ))
    return rows


def _build_vbc(sector: str, revenue_mm: float) -> List[VBCProgram]:
    bench = _get_benchmark(sector)
    bonus_pct = bench["quality_bonus_pct"]
    annual_total = revenue_mm * bonus_pct

    programs = [
        ("MIPS (Medicare Quality Payment Program)",
         sector in ("Primary Care", "Physician Services", "Cardiology", "Gastroenterology", "Orthopedics"),
         annual_total * 0.35, "upside-only",
         "2025 negative adjustment threshold 75 pts; max +9%/-9%"),
        ("MSSP ACO (Medicare Shared Savings)",
         sector in ("Primary Care", "Physician Services", "Physician Services", "Hospital"),
         annual_total * 0.40, "two-sided",
         "Track E mandatory downside post-2025"),
        ("MA Shared Savings (Stars)",
         sector in ("Primary Care", "Physician Services", "Skilled Nursing", "Home Health"),
         annual_total * 0.20, "upside-only",
         "Min 3.5 Stars for bonus eligibility"),
        ("Commercial Pay-for-Performance",
         True,   # almost universal
         annual_total * 0.05, "upside-only",
         "Payer-specific HEDIS + utilization targets"),
    ]
    rows = []
    for name, participating, bonus, risk, notes in programs:
        if not participating:
            bonus = 0
        rows.append(VBCProgram(
            program=name, participation=participating,
            annual_bonus_mm=round(bonus, 2), downside_risk=risk, notes=notes,
        ))
    return rows


def _build_value_impacts(
    sector: str, revenue_mm: float, ebitda_margin: float, exit_multiple: float,
    overall_score: float,
) -> List[QualityAdjustedValue]:
    bench = _get_benchmark(sector)

    # Quality-driven EBITDA accretion
    impacts = []
    for name, rev_pct in [
        ("Reduce Readmissions → Payer Bonuses", 0.012),
        ("HEDIS Gap Closure → MA Bonus", 0.008),
        ("Patient Satisfaction → Retention", 0.006),
        ("VBC Shared Savings Participation", bench["quality_bonus_pct"] * 0.6),
        ("Quality-Driven Payer Contract Uplift", 0.014),
    ]:
        annual = revenue_mm * rev_pct
        multi_year = annual * 3    # 3-year capture
        ev = annual * exit_multiple
        impacts.append(QualityAdjustedValue(
            component=name,
            annual_impact_mm=round(annual, 2),
            multi_year_impact_mm=round(multi_year, 2),
            ev_impact_mm=round(ev, 1),
        ))
    return impacts


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_quality_scorecard(
    sector: str = "Physician Services",
    revenue_mm: float = 80.0,
    ebitda_margin: float = 0.18,
    exit_multiple: float = 11.0,
) -> QualityScorecardResult:
    corpus = _load_corpus()

    metrics = _build_metrics(sector)
    hedis = _build_hedis(sector, revenue_mm)
    vbc = _build_vbc(sector, revenue_mm)

    overall = _score_from_metrics(metrics)
    tier = _tier(overall)
    impacts = _build_value_impacts(sector, revenue_mm, ebitda_margin, exit_multiple, overall)

    total_bonus = sum(v.annual_bonus_mm for v in vbc)
    total_ev_uplift = sum(i.ev_impact_mm for i in impacts) * (overall / 75)   # Scale by score

    return QualityScorecardResult(
        sector=sector,
        overall_score=overall,
        tier=tier,
        metrics=metrics,
        hedis=hedis,
        vbc_programs=vbc,
        value_impacts=impacts,
        total_annual_quality_bonus_mm=round(total_bonus, 2),
        total_ev_uplift_from_quality_mm=round(total_ev_uplift, 1),
        corpus_deal_count=len(corpus),
    )
