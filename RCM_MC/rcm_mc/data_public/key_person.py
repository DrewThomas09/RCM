"""Key Person / Clinical Concentration Risk Tracker.

Healthcare PE deals often have undetected key-person risk:
- CEO/founder carrying disproportionate EBITDA
- Top-producer clinicians with outsized revenue share
- Medical directors controlling referral relationships
- IT/IP holders without documentation

Models departure scenarios, revenue-at-risk, and mitigation economics.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Sector risk profiles
# ---------------------------------------------------------------------------

_SECTOR_RISK = {
    "Physician Services": {"top_producer_share": 0.22, "ceo_share": 0.10, "med_director_share": 0.15},
    "Dermatology":        {"top_producer_share": 0.25, "ceo_share": 0.08, "med_director_share": 0.12},
    "Ophthalmology":      {"top_producer_share": 0.20, "ceo_share": 0.08, "med_director_share": 0.14},
    "Orthopedics":        {"top_producer_share": 0.28, "ceo_share": 0.06, "med_director_share": 0.18},
    "Gastroenterology":   {"top_producer_share": 0.24, "ceo_share": 0.07, "med_director_share": 0.15},
    "Cardiology":         {"top_producer_share": 0.26, "ceo_share": 0.07, "med_director_share": 0.20},
    "Fertility":          {"top_producer_share": 0.35, "ceo_share": 0.10, "med_director_share": 0.18},
    "Behavioral Health":  {"top_producer_share": 0.18, "ceo_share": 0.12, "med_director_share": 0.10},
    "ABA Therapy":        {"top_producer_share": 0.12, "ceo_share": 0.14, "med_director_share": 0.08},
    "Home Health":        {"top_producer_share": 0.10, "ceo_share": 0.15, "med_director_share": 0.08},
    "Hospice":            {"top_producer_share": 0.08, "ceo_share": 0.18, "med_director_share": 0.12},
    "Skilled Nursing":    {"top_producer_share": 0.08, "ceo_share": 0.18, "med_director_share": 0.10},
    "Oncology":           {"top_producer_share": 0.32, "ceo_share": 0.05, "med_director_share": 0.22},
    "Radiation Oncology": {"top_producer_share": 0.30, "ceo_share": 0.05, "med_director_share": 0.25},
    "Dialysis":           {"top_producer_share": 0.06, "ceo_share": 0.12, "med_director_share": 0.14},
    "Healthcare IT":      {"top_producer_share": 0.04, "ceo_share": 0.28, "med_director_share": 0.02},
    "EHR/EMR":            {"top_producer_share": 0.03, "ceo_share": 0.32, "med_director_share": 0.02},
    "ASC":                {"top_producer_share": 0.22, "ceo_share": 0.06, "med_director_share": 0.15},
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class KeyPerson:
    role: str
    name: str                        # anonymized "CEO", "Top Producer #1", etc.
    revenue_share_pct: float
    ebitda_share_pct: float
    tenure_years: float
    succession_status: str           # "identified", "developing", "gap", "critical_gap"
    departure_risk: str              # "low", "medium", "high"
    revenue_at_risk_mm: float
    cost_to_replace_mm: float


@dataclass
class DepartureScenario:
    role: str
    departure_type: str              # "planned", "unplanned", "adverse"
    revenue_drop_pct: float
    ebitda_drop_pct: float
    recovery_months: int
    one_time_cost_mm: float
    ev_impact_mm: float


@dataclass
class ConcentrationMetric:
    metric: str
    value: float
    threshold: float
    status: str
    unit: str
    notes: str


@dataclass
class MitigationPlan:
    lever: str
    cost_mm: float
    annual_cost_mm: float
    risk_reduction_pct: float
    timeline_months: int
    priority: str                    # "high", "medium", "low"


@dataclass
class KeyPersonResult:
    sector: str
    concentration_score: float       # 0-100 (higher = worse concentration)
    key_persons: List[KeyPerson]
    departure_scenarios: List[DepartureScenario]
    concentration_metrics: List[ConcentrationMetric]
    mitigation_plans: List[MitigationPlan]
    total_revenue_at_risk_mm: float
    total_ev_at_risk_mm: float
    total_mitigation_cost_mm: float
    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 65):
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


def _get_profile(sector: str) -> Dict:
    return _SECTOR_RISK.get(sector, _SECTOR_RISK["Physician Services"])


def _build_key_persons(
    sector: str, revenue_mm: float, ebitda_margin: float,
) -> List[KeyPerson]:
    profile = _get_profile(sector)
    rows = []

    # CEO
    ceo_rev = revenue_mm * profile["ceo_share"]
    rows.append(KeyPerson(
        role="CEO / Founder",
        name="Executive A",
        revenue_share_pct=round(profile["ceo_share"], 3),
        ebitda_share_pct=round(profile["ceo_share"] * 1.15, 3),
        tenure_years=9.0,
        succession_status="developing",
        departure_risk="medium",
        revenue_at_risk_mm=round(ceo_rev * 0.40, 2),
        cost_to_replace_mm=0.8,
    ))

    # Medical Director
    md_rev = revenue_mm * profile["med_director_share"]
    rows.append(KeyPerson(
        role="Chief Medical Officer / Medical Director",
        name="Clinical Leader B",
        revenue_share_pct=round(profile["med_director_share"], 3),
        ebitda_share_pct=round(profile["med_director_share"] * 0.95, 3),
        tenure_years=6.5,
        succession_status="gap",
        departure_risk="high",
        revenue_at_risk_mm=round(md_rev * 0.65, 2),
        cost_to_replace_mm=0.55,
    ))

    # Top producers
    if profile["top_producer_share"] > 0.05:
        top1_rev = revenue_mm * profile["top_producer_share"] * 0.55
        rows.append(KeyPerson(
            role="Top-Producing Physician #1",
            name="Provider C",
            revenue_share_pct=round(profile["top_producer_share"] * 0.55, 3),
            ebitda_share_pct=round(profile["top_producer_share"] * 0.60, 3),
            tenure_years=14.0,
            succession_status="critical_gap",
            departure_risk="high",
            revenue_at_risk_mm=round(top1_rev * 0.75, 2),
            cost_to_replace_mm=0.35,
        ))

        top2_rev = revenue_mm * profile["top_producer_share"] * 0.30
        rows.append(KeyPerson(
            role="Top-Producing Physician #2",
            name="Provider D",
            revenue_share_pct=round(profile["top_producer_share"] * 0.30, 3),
            ebitda_share_pct=round(profile["top_producer_share"] * 0.32, 3),
            tenure_years=8.0,
            succession_status="developing",
            departure_risk="medium",
            revenue_at_risk_mm=round(top2_rev * 0.55, 2),
            cost_to_replace_mm=0.25,
        ))

    # CFO
    rows.append(KeyPerson(
        role="CFO / VP Finance",
        name="Executive E",
        revenue_share_pct=0.02,
        ebitda_share_pct=0.03,
        tenure_years=4.0,
        succession_status="identified",
        departure_risk="low",
        revenue_at_risk_mm=round(revenue_mm * 0.02 * 0.25, 2),
        cost_to_replace_mm=0.45,
    ))

    # CIO / Head of Tech (higher in HCIT)
    if sector in ("Healthcare IT", "EHR/EMR"):
        rows.append(KeyPerson(
            role="CTO / Head of Engineering",
            name="Executive F",
            revenue_share_pct=0.05,
            ebitda_share_pct=0.06,
            tenure_years=6.0,
            succession_status="developing",
            departure_risk="medium",
            revenue_at_risk_mm=round(revenue_mm * 0.15, 2),
            cost_to_replace_mm=0.80,
        ))

    return rows


def _build_scenarios(
    key_persons: List[KeyPerson], revenue_mm: float, ebitda_margin: float,
    exit_multiple: float,
) -> List[DepartureScenario]:
    rows = []
    # 3 scenarios per key person
    for kp in key_persons[:4]:    # cap at 4
        for dep_type, recovery_multiplier, risk_multiplier in [
            ("planned", 0.50, 0.35),
            ("unplanned", 1.00, 0.75),
            ("adverse (poaching)", 1.50, 1.15),
        ]:
            rev_drop = kp.revenue_at_risk_mm / revenue_mm * risk_multiplier if revenue_mm else 0
            rev_drop = min(rev_drop, 0.60)
            ebitda_drop = rev_drop * 1.4   # higher margin fall-through on departure
            recovery = int(12 * recovery_multiplier) + int(kp.tenure_years / 2)
            one_time = kp.cost_to_replace_mm + (0.1 if dep_type == "adverse (poaching)" else 0)
            ev_impact = -rev_drop * revenue_mm * (ebitda_margin + 0.03) * exit_multiple

            rows.append(DepartureScenario(
                role=kp.role,
                departure_type=dep_type,
                revenue_drop_pct=round(rev_drop, 3),
                ebitda_drop_pct=round(ebitda_drop, 3),
                recovery_months=recovery,
                one_time_cost_mm=round(one_time, 2),
                ev_impact_mm=round(ev_impact, 1),
            ))
    return rows


def _build_metrics(key_persons: List[KeyPerson]) -> List[ConcentrationMetric]:
    total_rev_share = sum(kp.revenue_share_pct for kp in key_persons)
    top3_rev_share = sum(kp.revenue_share_pct for kp in sorted(
        key_persons, key=lambda k: -k.revenue_share_pct
    )[:3])
    succession_gaps = sum(1 for kp in key_persons if kp.succession_status in ("gap", "critical_gap"))

    # Bus factor: how many people can leave before 20% revenue is at risk
    sorted_kps = sorted(key_persons, key=lambda k: -k.revenue_share_pct)
    cum_share = 0
    bus_factor = 0
    for kp in sorted_kps:
        cum_share += kp.revenue_share_pct
        bus_factor += 1
        if cum_share >= 0.20:
            break

    hhi = int(sum((kp.revenue_share_pct * 100) ** 2 for kp in key_persons))

    return [
        ConcentrationMetric(
            metric="Top 5 Persons Revenue Share",
            value=round(total_rev_share * 100, 1),
            threshold=35.0,
            status="high" if total_rev_share > 0.35 else ("medium" if total_rev_share > 0.20 else "low"),
            unit="%",
            notes="PE diligence threshold: <35% combined"),
        ConcentrationMetric(
            metric="Top 3 Concentration",
            value=round(top3_rev_share * 100, 1),
            threshold=25.0,
            status="high" if top3_rev_share > 0.25 else ("medium" if top3_rev_share > 0.15 else "low"),
            unit="%",
            notes="Typical healthcare services: 20-25%"),
        ConcentrationMetric(
            metric="Bus Factor (to 20% rev at risk)",
            value=float(bus_factor),
            threshold=3.0,
            status="high" if bus_factor <= 2 else ("medium" if bus_factor <= 4 else "low"),
            unit="persons",
            notes="Higher is better; 3+ indicates diversified"),
        ConcentrationMetric(
            metric="Key Person HHI",
            value=float(hhi),
            threshold=1500,
            status="high" if hhi > 1500 else ("medium" if hhi > 800 else "low"),
            unit="HHI",
            notes="Herfindahl-Hirschman index of revenue concentration"),
        ConcentrationMetric(
            metric="Succession Plan Gaps",
            value=float(succession_gaps),
            threshold=1.0,
            status="high" if succession_gaps >= 2 else ("medium" if succession_gaps == 1 else "low"),
            unit="roles",
            notes="Roles without identified successor"),
    ]


def _build_mitigations(revenue_mm: float, ebitda_margin: float) -> List[MitigationPlan]:
    return [
        MitigationPlan(
            lever="CEO Succession Plan (2-year dev)",
            cost_mm=0.25,
            annual_cost_mm=0.15,
            risk_reduction_pct=0.40,
            timeline_months=24,
            priority="high",
        ),
        MitigationPlan(
            lever="Key-Person Life Insurance ($25M per exec)",
            cost_mm=0.0,
            annual_cost_mm=0.08,
            risk_reduction_pct=0.25,
            timeline_months=2,
            priority="high",
        ),
        MitigationPlan(
            lever="Expanded Non-Compete / Non-Solicit Agreements",
            cost_mm=0.05,
            annual_cost_mm=0.01,
            risk_reduction_pct=0.22,
            timeline_months=4,
            priority="high",
        ),
        MitigationPlan(
            lever="Referral Base Broadening (reduce top 3 share)",
            cost_mm=0.35,
            annual_cost_mm=0.18,
            risk_reduction_pct=0.30,
            timeline_months=12,
            priority="medium",
        ),
        MitigationPlan(
            lever="Clinical Documentation / SOP Capture",
            cost_mm=0.12,
            annual_cost_mm=0.04,
            risk_reduction_pct=0.18,
            timeline_months=6,
            priority="medium",
        ),
        MitigationPlan(
            lever="Retention Bonus Pool (top 10 producers)",
            cost_mm=revenue_mm * 0.015,
            annual_cost_mm=revenue_mm * 0.005,
            risk_reduction_pct=0.35,
            timeline_months=1,
            priority="high",
        ),
        MitigationPlan(
            lever="Equity Grant Refresh (vest 4-yr)",
            cost_mm=revenue_mm * 0.005,
            annual_cost_mm=0.0,
            risk_reduction_pct=0.20,
            timeline_months=3,
            priority="medium",
        ),
        MitigationPlan(
            lever="Board-Led Medical Director Council",
            cost_mm=0.10,
            annual_cost_mm=0.06,
            risk_reduction_pct=0.12,
            timeline_months=3,
            priority="low",
        ),
    ]


def _concentration_score(key_persons: List[KeyPerson]) -> float:
    """0-100, higher = worse concentration."""
    top3 = sum(kp.revenue_share_pct for kp in sorted(key_persons, key=lambda k: -k.revenue_share_pct)[:3])
    succession_pts = sum(
        40 if kp.succession_status == "critical_gap" else
        25 if kp.succession_status == "gap" else
        10 if kp.succession_status == "developing" else 0
        for kp in key_persons
    ) / max(len(key_persons), 1)
    risk_pts = sum(
        30 if kp.departure_risk == "high" else
        15 if kp.departure_risk == "medium" else 0
        for kp in key_persons
    ) / max(len(key_persons), 1)

    score = top3 * 100 + succession_pts + risk_pts
    return round(min(score, 100), 1)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_key_person(
    sector: str = "Physician Services",
    revenue_mm: float = 80.0,
    ebitda_margin: float = 0.18,
    exit_multiple: float = 11.0,
) -> KeyPersonResult:
    corpus = _load_corpus()

    key_persons = _build_key_persons(sector, revenue_mm, ebitda_margin)
    scenarios = _build_scenarios(key_persons, revenue_mm, ebitda_margin, exit_multiple)
    metrics = _build_metrics(key_persons)
    mitigations = _build_mitigations(revenue_mm, ebitda_margin)

    total_rev_at_risk = sum(kp.revenue_at_risk_mm for kp in key_persons)
    total_ev_at_risk = total_rev_at_risk * (ebitda_margin + 0.03) * exit_multiple
    total_mitigation = sum(m.cost_mm for m in mitigations if m.priority == "high")

    score = _concentration_score(key_persons)

    return KeyPersonResult(
        sector=sector,
        concentration_score=score,
        key_persons=key_persons,
        departure_scenarios=scenarios,
        concentration_metrics=metrics,
        mitigation_plans=mitigations,
        total_revenue_at_risk_mm=round(total_rev_at_risk, 2),
        total_ev_at_risk_mm=round(total_ev_at_risk, 1),
        total_mitigation_cost_mm=round(total_mitigation, 2),
        corpus_deal_count=len(corpus),
    )
