"""ESG/Sustainability Dashboard — LP-facing ESG diligence for healthcare PE.

Modern LPs require ESG disclosure on:
- Environmental: energy, waste, carbon footprint of facilities
- Social: workforce diversity, patient access (dual-eligible, uninsured charity),
  clinical workforce compensation equity, community benefit
- Governance: board composition, compliance program maturity, whistleblower stats,
  audit committee independence
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# ESG factor weights
# ---------------------------------------------------------------------------

_ESG_WEIGHTS = {"E": 0.25, "S": 0.45, "G": 0.30}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ESGMetric:
    category: str              # "E", "S", "G"
    metric: str
    value: float
    unit: str
    benchmark: float
    score: float               # 0-100 contribution
    weight: float
    notes: str


@dataclass
class DiversityRow:
    dimension: str              # "Workforce Overall", "Leadership", "Board"
    pct_women: float
    pct_minority: float
    pct_women_minority: float
    benchmark_women: float
    benchmark_minority: float
    status: str


@dataclass
class AccessRow:
    population: str
    pct_patients: float
    revenue_contribution_mm: float
    community_benefit_hours: int
    notes: str


@dataclass
class LPDisclosureItem:
    framework: str              # "ILPA", "SASB", "GRESB", "UN PRI"
    category: str
    requirement: str
    status: str                 # "compliant", "partial", "gap"
    evidence: str


@dataclass
class ESGDashboardResult:
    overall_score: float        # 0-100
    tier: str                   # "Leader", "Strong", "Developing", "Lagging"
    e_score: float
    s_score: float
    g_score: float
    metrics: List[ESGMetric]
    diversity: List[DiversityRow]
    access: List[AccessRow]
    lp_disclosures: List[LPDisclosureItem]
    total_disclosure_gaps: int
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


def _score_from_ratio(actual: float, benchmark: float, higher_is_better: bool = True) -> float:
    if benchmark == 0:
        return 50.0
    ratio = actual / benchmark if higher_is_better else benchmark / actual if actual else 0.5
    if ratio >= 1.20: return 95
    if ratio >= 1.10: return 85
    if ratio >= 1.00: return 72
    if ratio >= 0.90: return 58
    if ratio >= 0.75: return 40
    if ratio >= 0.60: return 22
    return 10


def _status_from_score(score: float) -> str:
    if score >= 75: return "strong"
    if score >= 55: return "adequate"
    if score >= 35: return "gap"
    return "lagging"


def _tier_from_score(score: float) -> str:
    if score >= 75: return "Leader"
    if score >= 55: return "Strong"
    if score >= 35: return "Developing"
    return "Lagging"


def _build_metrics(sector: str, payer_mix: Dict) -> List[ESGMetric]:
    rows = []

    # Environmental
    rows.extend([
        ESGMetric(category="E", metric="Energy Intensity (kBTU/sqft)",
                  value=195, unit="kBTU/sqft", benchmark=220,
                  score=_score_from_ratio(220, 195, higher_is_better=False),
                  weight=0.10, notes="Healthcare avg ~220; hospital-grade higher"),
        ESGMetric(category="E", metric="Scope 1+2 Emissions (tCO2e / $M rev)",
                  value=42, unit="tCO2e/$M", benchmark=52,
                  score=_score_from_ratio(52, 42, higher_is_better=False),
                  weight=0.08, notes="Refrigerants, anesthetic gases major drivers"),
        ESGMetric(category="E", metric="Medical Waste (% Regulated)",
                  value=0.11, unit="%", benchmark=0.15,
                  score=_score_from_ratio(0.15, 0.11, higher_is_better=False),
                  weight=0.07, notes="Red-bag optimization is an EBITDA lever"),
    ])

    # Social — access, workforce
    comm = payer_mix.get("commercial", 0.55)
    dual_pct = max(0.12, 1 - comm - 0.25)     # proxy for Medicare+Medicaid dual
    rows.extend([
        ESGMetric(category="S", metric="Dual-Eligible Patients %",
                  value=dual_pct * 100, unit="%", benchmark=18,
                  score=_score_from_ratio(dual_pct * 100, 18, higher_is_better=True),
                  weight=0.12, notes="LP expectation: healthcare access for underserved"),
        ESGMetric(category="S", metric="Charity Care (% of revenue)",
                  value=2.8, unit="%", benchmark=2.5,
                  score=_score_from_ratio(2.8, 2.5, higher_is_better=True),
                  weight=0.08, notes="Non-profit peer: 3-5%; for-profit: 1-2%"),
        ESGMetric(category="S", metric="Workforce Diversity (Leadership)",
                  value=38, unit="%", benchmark=32,
                  score=_score_from_ratio(38, 32, higher_is_better=True),
                  weight=0.10, notes="Women/minority in director+"),
        ESGMetric(category="S", metric="Employee Turnover (Clinical)",
                  value=18.5, unit="%", benchmark=22,
                  score=_score_from_ratio(22, 18.5, higher_is_better=False),
                  weight=0.08, notes="Industry 22%; strong retention <15%"),
        ESGMetric(category="S", metric="Pay Equity Ratio (Women/Men adj.)",
                  value=0.98, unit="ratio", benchmark=0.97,
                  score=_score_from_ratio(0.98, 0.97, higher_is_better=True),
                  weight=0.07, notes="Adjusted for role/tenure"),
    ])

    # Governance
    rows.extend([
        ESGMetric(category="G", metric="Board Independence %",
                  value=55, unit="%", benchmark=60,
                  score=_score_from_ratio(55, 60, higher_is_better=True),
                  weight=0.08, notes="Target 60%+ independent for exit readiness"),
        ESGMetric(category="G", metric="Compliance Program Maturity (0-5)",
                  value=3.8, unit="tier", benchmark=4.0,
                  score=_score_from_ratio(3.8, 4.0, higher_is_better=True),
                  weight=0.10, notes="OIG 7-element effectiveness scoring"),
        ESGMetric(category="G", metric="Whistleblower Reports Closed (%)",
                  value=92, unit="%", benchmark=85,
                  score=_score_from_ratio(92, 85, higher_is_better=True),
                  weight=0.06, notes="Of reports received, % resolved < 90 days"),
        ESGMetric(category="G", metric="Audit Committee Meetings / Year",
                  value=6, unit="meetings", benchmark=4,
                  score=_score_from_ratio(6, 4, higher_is_better=True),
                  weight=0.06, notes="Industry median: 4/year"),
    ])

    return rows


def _build_diversity() -> List[DiversityRow]:
    rows = [
        ("Workforce Overall", 0.74, 0.42, 0.32, 0.75, 0.35),
        ("Mid-level Management", 0.58, 0.35, 0.22, 0.55, 0.30),
        ("Senior Leadership", 0.38, 0.18, 0.08, 0.32, 0.22),
        ("Board of Directors", 0.42, 0.14, 0.08, 0.40, 0.20),
    ]
    out = []
    for dim, w, m, wm, bw, bm in rows:
        status = "strong" if (w >= bw and m >= bm) else ("adequate" if (w >= bw * 0.9 or m >= bm * 0.9) else "gap")
        out.append(DiversityRow(
            dimension=dim, pct_women=round(w, 3), pct_minority=round(m, 3),
            pct_women_minority=round(wm, 3), benchmark_women=round(bw, 3),
            benchmark_minority=round(bm, 3), status=status,
        ))
    return out


def _build_access(revenue_mm: float, payer_mix: Dict) -> List[AccessRow]:
    rows = []
    for p, label, comm_hours_per_pct in [
        ("medicaid", "Medicaid", 5),
        ("medicare", "Medicare Dual", 3),
        ("self_pay", "Charity Care", 8),
        ("commercial", "Commercial", 1),
    ]:
        pct = payer_mix.get(p, 0.1)
        rev = revenue_mm * pct
        hours = int(pct * 100 * comm_hours_per_pct * 12)   # Monthly contribution
        notes = "Indigent care, FQHC referrals" if p == "self_pay" else "—"
        rows.append(AccessRow(
            population=label,
            pct_patients=round(pct, 3),
            revenue_contribution_mm=round(rev, 2),
            community_benefit_hours=hours,
            notes=notes,
        ))
    return rows


def _build_disclosures() -> List[LPDisclosureItem]:
    return [
        LPDisclosureItem(
            framework="ILPA ESG DDQ",
            category="Policy",
            requirement="Written ESG policy approved by board",
            status="compliant",
            evidence="ESG Policy v2.1, approved 2025-03-15",
        ),
        LPDisclosureItem(
            framework="ILPA ESG DDQ",
            category="Monitoring",
            requirement="Annual ESG metrics reporting to LP",
            status="partial",
            evidence="Quarterly ESG summary; annual full report in draft",
        ),
        LPDisclosureItem(
            framework="SASB HC-DY",
            category="Access & Affordability",
            requirement="Disclosure of charity care, patient satisfaction",
            status="compliant",
            evidence="Annual 10-K-style disclosure + trailing 12mo",
        ),
        LPDisclosureItem(
            framework="SASB HC-DR",
            category="Employee Recruitment & Turnover",
            requirement="Employee turnover by role and compensation data",
            status="compliant",
            evidence="Turnover dashboard + pay-equity audit",
        ),
        LPDisclosureItem(
            framework="UN PRI",
            category="Integration",
            requirement="ESG factors in investment decision process",
            status="compliant",
            evidence="ESG scoring in IC memos since 2024",
        ),
        LPDisclosureItem(
            framework="TCFD",
            category="Climate Governance",
            requirement="Scope 1+2 emissions quantification",
            status="partial",
            evidence="Baseline done; Scope 3 pending",
        ),
        LPDisclosureItem(
            framework="GRI 401",
            category="Employment",
            requirement="Total workforce with gender and region",
            status="compliant",
            evidence="Workforce analytics dashboard",
        ),
        LPDisclosureItem(
            framework="ILPA Diversity Metrics",
            category="Portfolio",
            requirement="Diversity stats across portfolio companies",
            status="gap",
            evidence="Portfolio-level aggregation not yet built",
        ),
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_esg_dashboard(
    sector: str = "Physician Services",
    revenue_mm: float = 80.0,
    payer_mix: Optional[Dict[str, float]] = None,
) -> ESGDashboardResult:
    corpus = _load_corpus()
    payer_mix = payer_mix or {"commercial": 0.55, "medicare": 0.25, "medicaid": 0.15, "self_pay": 0.05}

    metrics = _build_metrics(sector, payer_mix)
    diversity = _build_diversity()
    access = _build_access(revenue_mm, payer_mix)
    disclosures = _build_disclosures()

    # Category scores
    def _cat_score(cat):
        cat_metrics = [m for m in metrics if m.category == cat]
        if not cat_metrics:
            return 50
        total_w = sum(m.weight for m in cat_metrics)
        return sum(m.score * m.weight for m in cat_metrics) / total_w if total_w else 50

    e_score = _cat_score("E")
    s_score = _cat_score("S")
    g_score = _cat_score("G")
    overall = e_score * _ESG_WEIGHTS["E"] + s_score * _ESG_WEIGHTS["S"] + g_score * _ESG_WEIGHTS["G"]

    gaps = sum(1 for d in disclosures if d.status == "gap")

    return ESGDashboardResult(
        overall_score=round(overall, 1),
        tier=_tier_from_score(overall),
        e_score=round(e_score, 1),
        s_score=round(s_score, 1),
        g_score=round(g_score, 1),
        metrics=metrics,
        diversity=diversity,
        access=access,
        lp_disclosures=disclosures,
        total_disclosure_gaps=gaps,
        corpus_deal_count=len(corpus),
    )
