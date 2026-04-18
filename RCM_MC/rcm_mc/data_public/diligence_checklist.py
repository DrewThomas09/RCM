"""Diligence Checklist Generator — sector-specific PE diligence items from corpus patterns."""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


_PRIORITY = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}

_PRIORITY_COLORS = {
    "Critical": "#ef4444",
    "High":     "#ea580c",
    "Medium":   "#f59e0b",
    "Low":      "#64748b",
}


@dataclass
class ChecklistItem:
    id: str
    category: str
    title: str
    description: str
    priority: str
    priority_color: str
    red_flag_trigger: str
    corpus_fail_rate: float
    is_red_flag: bool
    status: str = "Open"


@dataclass
class DiligenceChecklistResult:
    sector: str
    ev_mm: float
    total_items: int
    critical_items: int
    high_items: int
    items: List[ChecklistItem]
    by_category: Dict[str, List[ChecklistItem]]
    red_flags_triggered: int
    corpus_deal_count: int


# ------- item definitions -------

_ITEMS = [
    # Financial
    ("fin_001","Financial Quality","Revenue Recognition Policy Audit",
     "Verify revenue recognized on contractual vs expected net realization. Flag if AR >90 days > 20%.",
     "Critical",[],">90-day AR > 20% or denial rate >15%",0.28),
    ("fin_002","Financial Quality","Add-Back Credibility Review",
     "Scrutinize all EBITDA add-backs. Flag if total > 30% of reported EBITDA.",
     "Critical",[],"Add-backs >30% of reported EBITDA",0.22),
    ("fin_003","Financial Quality","Payer Mix Sustainability",
     "Validate payer mix stability over 3 years. Flag single-payer > 60% concentration.",
     "High",[],"Single payer >60% or mix shift >10pp in 2 yrs",0.31),
    ("fin_004","Financial Quality","EBITDA Margin Benchmarking",
     "Compare margin to corpus P25/P50/P75. Flag if below P25.",
     "High",[],"Margin below corpus P25",0.19),
    ("fin_005","Financial Quality","CapEx Normalization",
     "Confirm maintenance CapEx ≥2% revenue. Flag underinvestment.",
     "Medium",[],"CapEx <2% revenue for 2+ years",0.14),
    ("fin_006","Financial Quality","Working Capital / DSO Trend",
     "Measure DSO trend. Flag if DSO increasing >5 days YoY or >50 for commercial-heavy mix.",
     "High",[],"DSO increasing or >60 days",0.25),
    # Operations
    ("ops_001","Operations","Key Provider Dependency",
     "Flag if top 3 physicians generate >40% revenue. Assess tail covenant.",
     "Critical",["Physician Group","Dental","Dermatology","Ophthalmology"],
     "Top 3 providers >40% revenue",0.45),
    ("ops_002","Operations","Provider Attrition Rate",
     "Review trailing 24-month physician turnover. Flag if >20% annual.",
     "High",["Physician Group","Behavioral Health","Urgent Care"],
     "Turnover >20% trailing 12 months",0.33),
    ("ops_003","Operations","Payor Contract Terms & Renewal Schedule",
     "Map all commercial contract terms and renewal dates. Flag if >30% contracts expire in year 1.",
     "Critical",[],"Major contracts expiring within 12 months of close",0.38),
    ("ops_004","Operations","Denial Rate Benchmarking",
     "Initial denial rate vs. industry. Flag if >15% initial denial or >5% final write-off.",
     "High",[],"Initial denial >15% or final write-off >5%",0.29),
    ("ops_005","Operations","Clinical Quality Metrics",
     "CMS star ratings, readmission rates, HAI. Flag if below national average.",
     "High",["Home Health","Hospice","Skilled Nursing","Ambulatory Surgery"],
     "CMS star <3 or below national average",0.21),
    ("ops_006","Operations","Staffing & Agency Dependency",
     "Agency/traveler staff as % total labor. Flag if >20% clinical hours from agency.",
     "High",["Staffing","Behavioral Health","Home Health","Skilled Nursing"],
     "Agency labor >20% clinical hours",0.35),
    # Regulatory
    ("reg_001","Regulatory","CMS Survey & Certification Status",
     "Review last 3 CMS surveys. Flag IJ citations, SFF status, or pending termination.",
     "Critical",["Home Health","Hospice","Skilled Nursing","Ambulatory Surgery"],
     "IJ citation or SFF designation",0.12),
    ("reg_002","Regulatory","OIG/SAM Exclusion Screening",
     "Screen all providers, owners, management against OIG/SAM exclusion lists.",
     "Critical",[],"Any provider or owner on exclusion list",0.04),
    ("reg_003","Regulatory","Stark Law / Anti-Kickback Compliance",
     "Review all physician compensation arrangements. Flag missing or stale FMV opinions.",
     "Critical",["Physician Group","Radiology","Laboratory"],
     "Compensation without FMV opinions",0.16),
    ("reg_004","Regulatory","HIPAA / Privacy Compliance",
     "Breach notification history and BAA coverage. Flag undisclosed breaches.",
     "High",[],"Undisclosed PHI breach or missing BAA",0.08),
    ("reg_005","Regulatory","State Licensure & CON",
     "Confirm all licenses current. Flag lapsed or under-scrutiny.",
     "High",[],"Lapsed licensure or active CON challenge",0.09),
    ("reg_006","Regulatory","Medicare/Medicaid Program Integrity",
     "RAC, MAC, state audit history. Flag if >$500K pending recoupment.",
     "High",[],"Active RAC audit or recoupment >$500K",0.11),
    # Market
    ("mkt_001","Market","Geographic Market Concentration",
     "Map patient origin. Flag if >50% revenue from single MSA.",
     "Medium",[],"Single MSA >50% revenue",0.40),
    ("mkt_002","Market","Competitive Positioning",
     "Top 3 competitors, market share trend. Flag if market share declining.",
     "High",[],"Market share declining >5pp in 2 years",0.18),
    ("mkt_003","Market","Referral Source Concentration",
     "Top 5 referrals. Flag if top 2 referrers >60% of new volume.",
     "High",["Home Health","Hospice","Physical Therapy","Behavioral Health"],
     "Top 2 referrers >60% of volume",0.32),
    ("mkt_004","Market","Population Demographics",
     "Target market age, income, insurance penetration trends.",
     "Medium",[],"Population decline or aging-out of service population",0.15),
    # Leverage
    ("lev_001","Leverage","Entry Leverage vs. Benchmark",
     "Entry leverage vs. corpus P50 for sector/size. Flag if >1.5 turns above P75.",
     "High",[],"Entry leverage >1.5 turns above corpus P75",0.17),
    ("lev_002","Leverage","Covenant Headroom at Close",
     "Model covenant compliance through base case. Flag if <15% headroom.",
     "Critical",[],"Covenant headroom <15% in base case",0.13),
    ("lev_003","Leverage","Interest Coverage Stress",
     "Coverage with 15% EBITDA haircut. Flag if <1.5x.",
     "High",[],"Coverage <1.5x under 15% EBITDA stress",0.20),
    # Management
    ("mgmt_001","Management","CEO/CFO Tenure & Alignment",
     "Management incentive alignment. Flag if CEO/CFO tenure <18 months or no rollover equity.",
     "High",[],"CEO/CFO <18 months tenure or no equity rollover",0.24),
    ("mgmt_002","Management","Succession Plan",
     "Single-point-of-failure risk. Flag if no documented succession plan.",
     "Medium",[],"No succession plan for C-suite",0.41),
    ("mgmt_003","Management","Integration Track Record",
     "For platform/add-on, review prior integration success.",
     "Medium",["Physician Group","Dental","Dermatology"],
     "Prior acquisitions integration >18 months",0.28),
]


def _is_applicable(sectors_filter, sector: str) -> bool:
    if not sectors_filter:
        return True
    s = sector.lower()
    return any(f.lower() in s or s in f.lower() for f in sectors_filter)


def _is_red_flag(item_id: str, sector: str, ev_mm: float, comm_pct: float, ar_days: float) -> bool:
    if item_id == "fin_001" and ar_days > 50:
        return True
    if item_id == "fin_003" and comm_pct > 0.65:
        return True
    if item_id == "ops_001" and "physician" in sector.lower():
        return True
    if item_id == "mkt_001" and ev_mm < 100:
        return True
    if item_id == "lev_001" and ev_mm > 400:
        return True
    return False


def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 57):
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


def compute_diligence_checklist(
    sector: str,
    ev_mm: float = 200.0,
    ebitda_margin: float = 0.18,
    comm_pct: float = 0.55,
    ar_days: float = 45.0,
) -> DiligenceChecklistResult:
    corpus = _load_corpus()

    items: List[ChecklistItem] = []
    for row in _ITEMS:
        iid, cat, title, desc, prio, sectors_f, rft, cfr = row
        if not _is_applicable(sectors_f, sector):
            continue
        rf = _is_red_flag(iid, sector, ev_mm, comm_pct, ar_days)
        items.append(ChecklistItem(
            id=iid, category=cat, title=title, description=desc,
            priority=prio, priority_color=_PRIORITY_COLORS[prio],
            red_flag_trigger=rft, corpus_fail_rate=cfr,
            is_red_flag=rf, status="Open",
        ))

    items.sort(key=lambda x: (_PRIORITY[x.priority], x.category, x.id))

    by_cat: Dict[str, List[ChecklistItem]] = {}
    for item in items:
        by_cat.setdefault(item.category, []).append(item)

    critical = sum(1 for i in items if i.priority == "Critical")
    high = sum(1 for i in items if i.priority == "High")
    red_flags = sum(1 for i in items if i.is_red_flag)

    return DiligenceChecklistResult(
        sector=sector, ev_mm=ev_mm,
        total_items=len(items), critical_items=critical, high_items=high,
        items=items, by_category=by_cat,
        red_flags_triggered=red_flags, corpus_deal_count=len(corpus),
    )


# ---------------------------------------------------------------------------
# Legacy compatibility aliases (expected by data_public/__init__.py)
# ---------------------------------------------------------------------------

def build_checklist(sector: str, ev_mm: float = 200.0, **kwargs) -> DiligenceChecklistResult:
    """Alias for compute_diligence_checklist."""
    return compute_diligence_checklist(sector=sector, ev_mm=ev_mm, **kwargs)


def checklist_text(sector: str, ev_mm: float = 200.0, **kwargs) -> str:
    """Return plain-text summary of checklist."""
    result = compute_diligence_checklist(sector=sector, ev_mm=ev_mm, **kwargs)
    lines = [f"Diligence Checklist — {sector} (${ev_mm:.0f}M)",
             f"Total: {result.total_items} | Critical: {result.critical_items} | High: {result.high_items}",
             f"Red Flags Triggered: {result.red_flags_triggered}", ""]
    for cat, items in result.by_category.items():
        lines.append(f"=== {cat} ===")
        for item in items:
            flag = " [RED FLAG]" if item.is_red_flag else ""
            lines.append(f"  [{item.priority}] {item.title}{flag}")
            lines.append(f"    {item.description}")
    return "\n".join(lines)


def checklist_json(sector: str, ev_mm: float = 200.0, **kwargs) -> dict:
    """Return JSON-serializable dict of checklist."""
    result = compute_diligence_checklist(sector=sector, ev_mm=ev_mm, **kwargs)
    return {
        "sector": result.sector,
        "ev_mm": result.ev_mm,
        "total_items": result.total_items,
        "critical_items": result.critical_items,
        "high_items": result.high_items,
        "red_flags_triggered": result.red_flags_triggered,
        "items": [
            {
                "id": i.id, "category": i.category, "title": i.title,
                "priority": i.priority, "is_red_flag": i.is_red_flag,
                "corpus_fail_rate": i.corpus_fail_rate,
            }
            for i in result.items
        ],
    }
