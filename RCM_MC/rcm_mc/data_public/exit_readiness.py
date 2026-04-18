"""Exit Readiness Index — multi-dimensional IPO / sale readiness scoring.

Scores a PE portfolio company on readiness to exit across:
- Financial: audit history, forecast reliability, working capital hygiene
- Operational: system integration, org design, IT/cyber posture
- Commercial: customer concentration, pipeline quality, recurring revenue mix
- Legal/Compliance: litigation exposure, regulatory findings, D&A status
- Management: team depth, succession, independent board members

Outputs a composite 0-100 index, dimension breakdowns, outstanding gap
list, and an estimated readiness-to-close timeline.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Dimension weights
# ---------------------------------------------------------------------------

_DIMENSIONS = {
    "Financial": 0.28,
    "Operational": 0.18,
    "Commercial": 0.22,
    "Legal/Compliance": 0.16,
    "Management": 0.16,
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ReadinessCriterion:
    dimension: str
    criterion: str
    status: str                   # "ready", "in-progress", "gap"
    score_pts: float              # 0-10 points
    importance: str               # "critical", "standard", "nice-to-have"
    estimated_days_to_close: int
    owner: str


@dataclass
class DimensionScore:
    dimension: str
    weight: float
    score: float                  # 0-100
    criteria_ready: int
    criteria_gap: int
    weighted_contribution: float


@dataclass
class ExitGap:
    dimension: str
    criterion: str
    severity: str                 # "critical", "high", "medium", "low"
    days_to_close: int
    cost_estimate_mm: float


@dataclass
class ExitScenario:
    pathway: str                  # "Strategic Sale", "Sponsor-to-Sponsor", "IPO"
    readiness_bar: int            # min score needed
    current_readiness_pct: float
    months_to_ready: int
    likely_multiple: float
    notes: str


@dataclass
class ExitReadinessResult:
    overall_score: float
    tier: str                     # "Ready", "Near-Ready", "Developing", "Not Ready"
    dimensions: List[DimensionScore]
    criteria: List[ReadinessCriterion]
    gaps: List[ExitGap]
    scenarios: List[ExitScenario]
    total_gap_cost_mm: float
    est_days_to_exit_ready: int
    critical_gap_count: int
    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 63):
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


def _tier(score: float) -> str:
    if score >= 85: return "Ready"
    if score >= 68: return "Near-Ready"
    if score >= 45: return "Developing"
    return "Not Ready"


def _severity_for(criterion: "ReadinessCriterion") -> str:
    if criterion.status == "ready":
        return ""
    if criterion.importance == "critical":
        return "critical"
    if criterion.importance == "standard":
        return "high"
    return "medium"


def _build_criteria(hold_years: float, pathway: str) -> List[ReadinessCriterion]:
    """Canonical exit-readiness checklist across 5 dimensions."""
    items = [
        # Financial
        ("Financial", "3-year audited financials (Big 4 / top 10)", "ready", 10.0, "critical", 0, "CFO"),
        ("Financial", "Monthly close in 10 business days", "ready", 9.0, "critical", 0, "Controller"),
        ("Financial", "12-month rolling forecast reliability >90%", "in-progress", 6.0, "critical", 60, "FP&A"),
        ("Financial", "Working capital normalized per GAAP", "ready", 9.0, "standard", 0, "CFO"),
        ("Financial", "Debt carveout schedules prepared", "in-progress", 5.0, "standard", 45, "Treasury"),
        ("Financial", "QoE (Quality of Earnings) report ≤ 6 mo old", "gap", 0, "critical", 90, "CFO / External"),
        ("Financial", "Non-GAAP metrics reconciled & documented", "in-progress", 7.0, "standard", 30, "FP&A"),
        ("Financial", "Board-approved budget vs. actual variance <5%", "ready", 8.0, "standard", 0, "CFO"),

        # Operational
        ("Operational", "Post-acquisition IT integration complete", "in-progress", 6.0, "critical", 90, "CIO"),
        ("Operational", "ERP on single instance (not siloed)", "ready", 9.0, "standard", 0, "CIO"),
        ("Operational", "Cybersecurity: SOC 2 Type II current", "ready", 10.0, "critical", 0, "CIO / CISO"),
        ("Operational", "Cyber insurance $25M+ with stable premium", "ready", 8.0, "standard", 0, "Risk"),
        ("Operational", "Org design rationalized (no duplicate roles)", "in-progress", 6.0, "standard", 60, "CHRO"),
        ("Operational", "Standardized KPI dashboard (Tableau/Looker)", "ready", 9.0, "nice-to-have", 0, "Analytics"),

        # Commercial
        ("Commercial", "Top 10 customer concentration <35%", "ready", 10.0, "critical", 0, "CRO"),
        ("Commercial", "Net revenue retention >110%", "in-progress", 7.0, "standard", 90, "CRO"),
        ("Commercial", "Sales cycle metrics documented", "ready", 8.0, "standard", 0, "Revenue Ops"),
        ("Commercial", "Customer contract CICs scrubbed", "gap", 0, "critical", 120, "Legal"),
        ("Commercial", "ROI case studies (≥5 anchor references)", "in-progress", 6.0, "standard", 60, "Marketing"),
        ("Commercial", "Recurring revenue mix >60%", "ready", 9.0, "nice-to-have", 0, "CFO"),

        # Legal/Compliance
        ("Legal/Compliance", "Open litigation materiality <1% EV", "ready", 10.0, "critical", 0, "GC"),
        ("Legal/Compliance", "All regulatory findings remediated", "in-progress", 6.0, "critical", 90, "Compliance"),
        ("Legal/Compliance", "IP registration & ownership clean", "ready", 9.0, "standard", 0, "IP Counsel"),
        ("Legal/Compliance", "Employment agreements current", "ready", 8.0, "standard", 0, "HR / Legal"),
        ("Legal/Compliance", "HIPAA breach log clean (last 24 mo)", "in-progress", 6.0, "critical", 30, "Privacy"),
        ("Legal/Compliance", "Anti-corruption / FCPA program in place", "ready", 8.0, "nice-to-have", 0, "Compliance"),

        # Management
        ("Management", "CEO 3+ year track record post-sponsorship", "ready", 10.0, "critical", 0, "Sponsor"),
        ("Management", "Succession plan for C-suite", "in-progress", 6.0, "critical", 60, "CHRO"),
        ("Management", "CFO / VP Finance search grade", "ready", 9.0, "standard", 0, "CHRO"),
        ("Management", "Independent board member(s) seated", "in-progress", 5.0, "standard", 45, "Sponsor"),
        ("Management", "Management incentive plan vested (>50%)", "ready", 8.0, "standard", 0, "CHRO"),
        ("Management", "Key-person insurance in place", "ready", 7.0, "nice-to-have", 0, "Risk"),
    ]
    return [ReadinessCriterion(
        dimension=d, criterion=c, status=s, score_pts=p,
        importance=imp, estimated_days_to_close=days, owner=o,
    ) for d, c, s, p, imp, days, o in items]


def _build_dimensions(criteria: List[ReadinessCriterion]) -> List[DimensionScore]:
    out = []
    for dim, weight in _DIMENSIONS.items():
        group = [c for c in criteria if c.dimension == dim]
        total_pts = sum(10 for _ in group)
        earned = sum(c.score_pts for c in group)
        score = (earned / total_pts * 100) if total_pts else 0
        ready = sum(1 for c in group if c.status == "ready")
        gap = sum(1 for c in group if c.status == "gap")
        out.append(DimensionScore(
            dimension=dim,
            weight=round(weight, 3),
            score=round(score, 1),
            criteria_ready=ready,
            criteria_gap=gap,
            weighted_contribution=round(score * weight, 1),
        ))
    return out


def _build_gaps(criteria: List[ReadinessCriterion]) -> List[ExitGap]:
    rows = []
    # Cost proxies by importance
    cost_by_importance = {"critical": 0.35, "standard": 0.15, "nice-to-have": 0.05}
    for c in criteria:
        if c.status == "ready":
            continue
        sev = _severity_for(c)
        cost = cost_by_importance.get(c.importance, 0.1)
        if c.status == "in-progress":
            cost *= 0.5
        rows.append(ExitGap(
            dimension=c.dimension,
            criterion=c.criterion,
            severity=sev,
            days_to_close=c.estimated_days_to_close,
            cost_estimate_mm=round(cost, 2),
        ))
    return rows


def _build_scenarios(overall_score: float, gaps: List[ExitGap]) -> List[ExitScenario]:
    rows = []
    max_days = max((g.days_to_close for g in gaps), default=0)
    months_to_ready = max(1, max_days // 30)

    for pathway, bar, mult in [
        ("Strategic Sale", 68, 12.5),
        ("Sponsor-to-Sponsor", 75, 11.0),
        ("IPO / SPAC", 88, 14.0),
    ]:
        current_pct = min(100, overall_score / bar * 100) if bar else 100
        notes = ""
        if overall_score >= bar:
            notes = f"Meets {pathway} readiness bar"
        elif overall_score >= bar * 0.85:
            notes = f"Close to readiness (~{int((bar - overall_score) * 2)} pts gap)"
        else:
            notes = f"Significant gap; {months_to_ready}-mo build required"

        rows.append(ExitScenario(
            pathway=pathway,
            readiness_bar=bar,
            current_readiness_pct=round(current_pct, 1),
            months_to_ready=months_to_ready if overall_score < bar else 0,
            likely_multiple=round(mult, 2),
            notes=notes,
        ))
    return rows


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_exit_readiness(
    hold_years: float = 4.0,
    pathway: str = "Strategic Sale",
) -> ExitReadinessResult:
    corpus = _load_corpus()

    criteria = _build_criteria(hold_years, pathway)
    dimensions = _build_dimensions(criteria)
    overall = sum(d.weighted_contribution for d in dimensions)
    gaps = _build_gaps(criteria)
    scenarios = _build_scenarios(overall, gaps)

    total_cost = sum(g.cost_estimate_mm for g in gaps)
    est_days = max((g.days_to_close for g in gaps), default=0)
    critical_count = sum(1 for g in gaps if g.severity == "critical")

    return ExitReadinessResult(
        overall_score=round(overall, 1),
        tier=_tier(overall),
        dimensions=dimensions,
        criteria=criteria,
        gaps=gaps,
        scenarios=scenarios,
        total_gap_cost_mm=round(total_cost, 2),
        est_days_to_exit_ready=est_days,
        critical_gap_count=critical_count,
        corpus_deal_count=len(corpus),
    )
