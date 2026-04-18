"""Patient Experience / NPS Tracker.

Measures and monetizes patient experience for healthcare PE deals:
- HCAHPS hospital scores (10 domains)
- Press Ganey / CAHPS outpatient
- Net Promoter Score (NPS) surveys
- Online review volume & rating
- Wait time / no-show
- Retention / recall rates
- Brand equity score
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ExperienceMetric:
    category: str
    metric: str
    current_score: float
    unit: str
    benchmark: float
    percentile: int
    trend_90d: str                  # "up", "flat", "down"
    revenue_correlation: float


@dataclass
class ReviewPlatform:
    platform: str
    volume_total: int
    avg_rating: float
    volume_last_90d: int
    recent_rating_90d: float
    sentiment_positive_pct: float


@dataclass
class OperationalDriver:
    driver: str
    current_value: float
    unit: str
    benchmark: float
    impact_on_experience_pct: float


@dataclass
class ExperienceInitiative:
    initiative: str
    investment_mm: float
    expected_nps_delta: float
    expected_retention_delta_pct: float
    expected_revenue_uplift_mm: float
    timeline_months: int
    risk: str


@dataclass
class RetentionDecomposition:
    cohort: str
    current_retention_pct: float
    target_retention_pct: float
    implied_revenue_mm: float
    implied_ev_impact_mm: float


@dataclass
class PatientExperienceResult:
    composite_pex_score: int                 # 0-100
    nps_current: int
    nps_trajectory: str
    hcahps_top_box_pct: float
    google_review_rating: float
    metrics: List[ExperienceMetric]
    reviews: List[ReviewPlatform]
    drivers: List[OperationalDriver]
    initiatives: List[ExperienceInitiative]
    retention: List[RetentionDecomposition]
    total_revenue_at_risk_mm: float
    total_ev_impact_from_improvement_mm: float
    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 74):
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


def _build_metrics() -> List[ExperienceMetric]:
    return [
        ExperienceMetric("NPS", "Net Promoter Score", 48, "score", 42, 65, "up", 0.42),
        ExperienceMetric("HCAHPS", "Overall Hospital Rating (9-10)", 78, "%", 72, 68, "flat", 0.38),
        ExperienceMetric("HCAHPS", "Would Recommend Hospital", 82, "%", 78, 62, "up", 0.45),
        ExperienceMetric("HCAHPS", "Nurse Communication", 83, "%", 81, 55, "up", 0.28),
        ExperienceMetric("HCAHPS", "Doctor Communication", 85, "%", 82, 60, "flat", 0.32),
        ExperienceMetric("HCAHPS", "Pain Management", 72, "%", 76, 35, "down", 0.22),
        ExperienceMetric("HCAHPS", "Discharge Information", 88, "%", 86, 58, "up", 0.15),
        ExperienceMetric("Press Ganey", "Likelihood to Recommend", 91, "%", 88, 62, "up", 0.40),
        ExperienceMetric("Press Ganey", "Wait Time Satisfaction", 68, "%", 72, 38, "flat", 0.25),
        ExperienceMetric("Press Ganey", "Ease of Scheduling", 75, "%", 72, 58, "up", 0.18),
        ExperienceMetric("Operational", "No-Show Rate", 8.5, "%", 10.2, 60, "up", -0.12),
        ExperienceMetric("Operational", "Average Wait (minutes)", 18, "min", 22, 65, "up", -0.15),
        ExperienceMetric("Operational", "Patient Retention (12 mo)", 0.82, "%", 0.78, 65, "up", 0.68),
        ExperienceMetric("Operational", "Referral Rate", 0.42, "%", 0.35, 72, "up", 0.55),
    ]


def _build_reviews() -> List[ReviewPlatform]:
    return [
        ReviewPlatform("Google Reviews", 4250, 4.6, 420, 4.7, 0.85),
        ReviewPlatform("Healthgrades", 1850, 4.2, 180, 4.3, 0.78),
        ReviewPlatform("Yelp", 620, 3.8, 55, 3.9, 0.68),
        ReviewPlatform("Vitals", 340, 4.1, 28, 4.2, 0.75),
        ReviewPlatform("ZocDoc", 2150, 4.5, 250, 4.6, 0.88),
        ReviewPlatform("Facebook", 1420, 4.4, 110, 4.4, 0.82),
        ReviewPlatform("Internal Post-Visit Survey", 12800, 4.5, 1850, 4.55, 0.84),
    ]


def _build_drivers() -> List[OperationalDriver]:
    return [
        OperationalDriver("Average Wait Time", 18, "minutes", 15, 0.22),
        OperationalDriver("Appointment Availability (days out)", 7.5, "days", 5, 0.18),
        OperationalDriver("Provider Time with Patient", 14.2, "minutes", 15, 0.25),
        OperationalDriver("Check-in Digital Completion %", 0.62, "%", 0.80, 0.12),
        OperationalDriver("Portal Activation Rate", 0.48, "%", 0.65, 0.14),
        OperationalDriver("Follow-up Communication", 0.78, "%", 0.85, 0.15),
        OperationalDriver("Billing Transparency Score", 72, "0-100", 80, 0.18),
        OperationalDriver("Provider-to-Support Ratio", 1.8, "staff per MD", 2.2, 0.12),
        OperationalDriver("Scheduling Self-Service %", 0.35, "%", 0.60, 0.10),
        OperationalDriver("Facility Cleanliness Score", 92, "0-100", 90, 0.08),
    ]


def _build_initiatives(revenue_mm: float, exit_mult: float) -> List[ExperienceInitiative]:
    items = [
        ("Digital Check-in / Intake Automation", 0.45, 3.5, 0.015, 0.018, 6, "low"),
        ("Patient Portal + Communication Upgrade", 0.35, 4.0, 0.022, 0.025, 9, "low"),
        ("Wait-time Reduction Program (OR, clinic)", 0.68, 5.5, 0.035, 0.040, 12, "medium"),
        ("Post-Visit Survey + Recovery Workflow", 0.22, 4.5, 0.020, 0.022, 4, "low"),
        ("Online Reputation Mgmt (reviews, SEO)", 0.18, 3.0, 0.015, 0.012, 5, "low"),
        ("Provider Communication Training", 0.28, 4.0, 0.018, 0.020, 8, "medium"),
        ("Scheduling Self-Service Portal", 0.38, 5.0, 0.025, 0.028, 9, "medium"),
        ("Concierge / Premium Service Line", 0.95, 3.5, 0.020, 0.065, 18, "high"),
    ]
    rows = []
    for init, cost, nps_d, retention_d, rev_d, months, risk in items:
        rev_up = revenue_mm * rev_d
        rows.append(ExperienceInitiative(
            initiative=init,
            investment_mm=round(cost, 2),
            expected_nps_delta=round(nps_d, 2),
            expected_retention_delta_pct=round(retention_d, 3),
            expected_revenue_uplift_mm=round(rev_up, 2),
            timeline_months=months,
            risk=risk,
        ))
    return rows


def _build_retention(revenue_mm: float, exit_mult: float) -> List[RetentionDecomposition]:
    cohorts = [
        ("New Patient Y1 Retention", 0.52, 0.68, 0.15, 0.18),
        ("Chronic Care Retention", 0.78, 0.88, 0.10, 0.12),
        ("Procedure Follow-up", 0.65, 0.82, 0.17, 0.20),
        ("High-Value Commercial Patients", 0.82, 0.92, 0.08, 0.10),
        ("MA Beneficiaries", 0.88, 0.94, 0.05, 0.07),
    ]
    rows = []
    for cohort, curr, target, ret_impact, rev_share in cohorts:
        rev_mm = revenue_mm * rev_share
        ret_delta = target - curr
        impact_rev = rev_mm * ret_delta
        ev_impact = impact_rev * exit_mult * 0.18    # margin × multiple
        rows.append(RetentionDecomposition(
            cohort=cohort,
            current_retention_pct=round(curr, 3),
            target_retention_pct=round(target, 3),
            implied_revenue_mm=round(impact_rev, 2),
            implied_ev_impact_mm=round(ev_impact, 2),
        ))
    return rows


def _composite_score(metrics: List[ExperienceMetric]) -> int:
    if not metrics:
        return 50
    avg_pct = sum(m.percentile for m in metrics) / len(metrics)
    return int(avg_pct)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_patient_experience(
    sector: str = "Physician Services",
    revenue_mm: float = 80.0,
    exit_multiple: float = 11.0,
) -> PatientExperienceResult:
    corpus = _load_corpus()

    metrics = _build_metrics()
    reviews = _build_reviews()
    drivers = _build_drivers()
    initiatives = _build_initiatives(revenue_mm, exit_multiple)
    retention = _build_retention(revenue_mm, exit_multiple)

    composite = _composite_score(metrics)
    nps_metric = next((m for m in metrics if m.metric == "Net Promoter Score"), None)
    nps = int(nps_metric.current_score) if nps_metric else 45

    hcahps_overall = next((m for m in metrics if "Overall Hospital Rating" in m.metric), None)
    hcahps_pct = hcahps_overall.current_score if hcahps_overall else 75

    google_review = next((r for r in reviews if "Google" in r.platform), None)
    google_rating = google_review.avg_rating if google_review else 4.5

    # Revenue at risk = patients who wouldn't recommend × est annual value
    total_rev_at_risk = revenue_mm * (1 - nps / 100) * 0.15
    total_ev_impact = sum(r.implied_ev_impact_mm for r in retention) + \
                      sum(i.expected_revenue_uplift_mm for i in initiatives) * 0.18 * exit_multiple

    return PatientExperienceResult(
        composite_pex_score=composite,
        nps_current=nps,
        nps_trajectory="+3 vs LY",
        hcahps_top_box_pct=round(hcahps_pct, 1),
        google_review_rating=round(google_rating, 2),
        metrics=metrics,
        reviews=reviews,
        drivers=drivers,
        initiatives=initiatives,
        retention=retention,
        total_revenue_at_risk_mm=round(total_rev_at_risk, 2),
        total_ev_impact_from_improvement_mm=round(total_ev_impact, 1),
        corpus_deal_count=len(corpus),
    )
