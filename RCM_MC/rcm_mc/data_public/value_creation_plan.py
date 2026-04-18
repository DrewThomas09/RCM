"""100-Day / Value Creation Plan Tracker.

Post-close operational plan with initiatives, owners, EBITDA impact, and timeline.
Tracks:
- Day 1 / 30 / 60 / 100 / 200 / 365 checkpoints
- 7 lever categories: Revenue, Cost, RCM, Labor, Procurement, Real Estate, Technology
- Initiative inventory with impact, cost, owner
- EBITDA bridge: entry → current → target → exit
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Initiative catalog
# ---------------------------------------------------------------------------

_INITIATIVE_CATALOG = [
    # (category, name, impact_pct_of_ebitda, cost_pct, target_day, owner_role, complexity)
    ("Revenue", "Pricing Optimization (payer renegotiation)", 0.12, 0.01, 365, "CRO", "medium"),
    ("Revenue", "Service Line Expansion (ancillary)", 0.08, 0.03, 200, "CEO", "medium"),
    ("Revenue", "Patient Acquisition / Marketing Uplift", 0.06, 0.02, 100, "CMO", "low"),
    ("Revenue", "Same-Store Volume Growth Program", 0.09, 0.01, 200, "COO", "medium"),
    ("Cost", "Vendor Consolidation / Procurement Savings", 0.05, 0.005, 100, "CFO", "low"),
    ("Cost", "Corporate Overhead Rightsizing", 0.04, 0.008, 100, "CHRO", "medium"),
    ("Cost", "Supplies / Implant Category Mgmt", 0.06, 0.002, 200, "COO", "medium"),
    ("RCM", "Denial Management Transformation", 0.07, 0.008, 100, "CFO", "medium"),
    ("RCM", "Charge Capture Automation", 0.04, 0.006, 200, "CFO", "low"),
    ("RCM", "Patient Collections / Self-Pay", 0.03, 0.003, 100, "CFO", "low"),
    ("Labor", "Provider Comp Restructuring", 0.05, 0.01, 200, "CEO", "high"),
    ("Labor", "Agency Labor Reduction", 0.04, 0.0, 100, "CHRO", "medium"),
    ("Labor", "MGMA Productivity Program", 0.06, 0.008, 365, "COO", "medium"),
    ("Procurement", "GPO / Group Purchasing Enrollment", 0.02, 0.001, 60, "CFO", "low"),
    ("Real Estate", "Lease Renegotiation (bulk)", 0.03, 0.0, 200, "CFO", "low"),
    ("Real Estate", "Site Rationalization (3 closures)", 0.04, 0.012, 365, "COO", "high"),
    ("Technology", "EHR Migration / Consolidation", 0.06, 0.025, 365, "CIO", "high"),
    ("Technology", "Practice Management System Upgrade", 0.03, 0.008, 200, "CIO", "medium"),
    ("Technology", "Telehealth Platform", 0.04, 0.005, 100, "CMO", "low"),
    ("M&A", "Bolt-on #1 (platform expansion)", 0.12, 0.008, 365, "CEO", "high"),
    ("M&A", "Bolt-on #2 (geographic)", 0.08, 0.006, 365, "CEO", "high"),
    ("Growth", "Payer Contract Wins (new commercial)", 0.04, 0.002, 200, "CRO", "medium"),
    ("Growth", "Referral Network Expansion", 0.05, 0.004, 200, "CRO", "medium"),
    ("Leadership", "CFO Upgrade / Exec Search", 0.0, 0.02, 100, "CEO", "medium"),
    ("Leadership", "Strategic Plan Refresh", 0.0, 0.01, 60, "CEO", "low"),
]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Initiative:
    category: str
    name: str
    impact_ebitda_mm: float
    cost_mm: float
    net_impact_mm: float
    target_day: int
    actual_status: str              # "not_started", "on_track", "at_risk", "delayed", "complete"
    progress_pct: float
    owner_role: str
    complexity: str
    priority: str


@dataclass
class MilestoneCheckpoint:
    checkpoint: str                  # "Day 30", "Day 100", etc.
    initiatives_completed: int
    initiatives_on_track: int
    initiatives_at_risk: int
    ebitda_realized_mm: float
    pct_of_plan: float


@dataclass
class CategoryRollup:
    category: str
    n_initiatives: int
    total_impact_mm: float
    total_cost_mm: float
    net_impact_mm: float
    pct_of_total_plan: float
    avg_progress: float


@dataclass
class EBITDABridge:
    stage: str                       # "Entry", "Current", "Target", "Exit Projection"
    ebitda_mm: float
    delta_from_entry_mm: float
    margin_pct: float


@dataclass
class ValueCreationPlanResult:
    sector: str
    entry_ebitda_mm: float
    target_ebitda_mm: float
    current_ebitda_mm: float
    exit_ebitda_mm: float
    hold_day: int
    initiatives: List[Initiative]
    checkpoints: List[MilestoneCheckpoint]
    category_rollups: List[CategoryRollup]
    ebitda_bridge: List[EBITDABridge]
    total_plan_impact_mm: float
    total_plan_cost_mm: float
    plan_net_value_mm: float
    execution_score: float           # 0-100
    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 68):
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


def _status_for_progress(progress: float, target_day: int, current_day: int) -> str:
    """Infer status from progress vs expected."""
    if progress >= 1.0:
        return "complete"
    expected = min(1.0, current_day / target_day) if target_day else 0
    if progress == 0 and current_day < target_day * 0.2:
        return "not_started"
    if progress >= expected - 0.10:
        return "on_track"
    if progress >= expected - 0.25:
        return "at_risk"
    return "delayed"


def _build_initiatives(entry_ebitda: float, current_day: int) -> List[Initiative]:
    rows = []
    import hashlib
    for (cat, name, impact_pct, cost_pct, target_day, owner, complexity) in _INITIATIVE_CATALOG:
        impact_mm = entry_ebitda * impact_pct
        # One-time implementation cost scales modestly with deal size
        cost_mm = entry_ebitda * 2.2 * cost_pct
        net = impact_mm - cost_mm

        # Seed deterministic progress based on name hash + current day
        h = int(hashlib.md5(name.encode()).hexdigest()[:6], 16)
        # Expected progress if on track
        expected = min(1.0, current_day / target_day) if target_day else 0
        noise = ((h % 31) / 31.0 - 0.5) * 0.30
        actual_progress = max(0, min(1.0, expected + noise))

        status = _status_for_progress(actual_progress, target_day, current_day)

        # Priority based on net impact
        if net >= entry_ebitda * 0.08:
            prio = "critical"
        elif net >= entry_ebitda * 0.04:
            prio = "high"
        elif net >= entry_ebitda * 0.02:
            prio = "medium"
        else:
            prio = "low"

        rows.append(Initiative(
            category=cat, name=name,
            impact_ebitda_mm=round(impact_mm, 2),
            cost_mm=round(cost_mm, 2),
            net_impact_mm=round(net, 2),
            target_day=target_day,
            actual_status=status,
            progress_pct=round(actual_progress, 3),
            owner_role=owner,
            complexity=complexity,
            priority=prio,
        ))
    return rows


def _build_checkpoints(initiatives: List[Initiative], current_day: int, total_impact: float) -> List[MilestoneCheckpoint]:
    checkpoints_def = [30, 60, 100, 200, 365, 730]
    rows = []
    for cp_day in checkpoints_def:
        scoped = [i for i in initiatives if i.target_day <= cp_day]
        if cp_day > current_day:
            completed = 0
            on_track = sum(1 for i in scoped if i.actual_status in ("on_track", "complete"))
            at_risk = sum(1 for i in scoped if i.actual_status in ("at_risk", "delayed"))
            ebitda_realized = total_impact * (current_day / cp_day) * 0.6
        else:
            completed = sum(1 for i in scoped if i.actual_status == "complete")
            on_track = len(scoped) - completed - sum(1 for i in scoped if i.actual_status in ("at_risk", "delayed"))
            at_risk = sum(1 for i in scoped if i.actual_status in ("at_risk", "delayed"))
            ebitda_realized = sum(i.impact_ebitda_mm * i.progress_pct for i in scoped)

        rows.append(MilestoneCheckpoint(
            checkpoint=f"Day {cp_day}",
            initiatives_completed=completed,
            initiatives_on_track=on_track,
            initiatives_at_risk=at_risk,
            ebitda_realized_mm=round(ebitda_realized, 2),
            pct_of_plan=round(ebitda_realized / total_impact if total_impact else 0, 3),
        ))
    return rows


def _build_category_rollup(initiatives: List[Initiative], total_impact: float) -> List[CategoryRollup]:
    by_cat: Dict[str, List[Initiative]] = {}
    for i in initiatives:
        by_cat.setdefault(i.category, []).append(i)

    rows = []
    for cat, inits in sorted(by_cat.items(), key=lambda x: -sum(i.net_impact_mm for i in x[1])):
        total_imp = sum(i.impact_ebitda_mm for i in inits)
        total_cost = sum(i.cost_mm for i in inits)
        net = sum(i.net_impact_mm for i in inits)
        avg_prog = sum(i.progress_pct for i in inits) / len(inits) if inits else 0
        rows.append(CategoryRollup(
            category=cat,
            n_initiatives=len(inits),
            total_impact_mm=round(total_imp, 2),
            total_cost_mm=round(total_cost, 2),
            net_impact_mm=round(net, 2),
            pct_of_total_plan=round(net / total_impact if total_impact else 0, 3),
            avg_progress=round(avg_prog, 3),
        ))
    return rows


def _build_bridge(
    entry_ebitda: float, target_ebitda: float, current_ebitda: float, exit_ebitda: float,
) -> List[EBITDABridge]:
    margin = 0.18    # assumption
    revenue = entry_ebitda / margin

    return [
        EBITDABridge("Entry", round(entry_ebitda, 2), 0, round(margin, 3)),
        EBITDABridge("Current", round(current_ebitda, 2),
                     round(current_ebitda - entry_ebitda, 2), round(current_ebitda / (revenue * 1.08), 3)),
        EBITDABridge("Target (End of Plan)", round(target_ebitda, 2),
                     round(target_ebitda - entry_ebitda, 2), round(target_ebitda / (revenue * 1.15), 3)),
        EBITDABridge("Exit Projection", round(exit_ebitda, 2),
                     round(exit_ebitda - entry_ebitda, 2), round(exit_ebitda / (revenue * 1.30), 3)),
    ]


def _execution_score(initiatives: List[Initiative]) -> float:
    """0-100 score of plan execution."""
    if not initiatives:
        return 50
    complete = sum(1 for i in initiatives if i.actual_status == "complete") / len(initiatives) * 100
    on_track_share = sum(1 for i in initiatives if i.actual_status in ("on_track", "complete")) / len(initiatives) * 100
    at_risk_pen = sum(1 for i in initiatives if i.actual_status == "delayed") / len(initiatives) * 50

    raw = on_track_share * 0.6 + complete * 0.3 - at_risk_pen * 0.1
    return round(max(0, min(100, raw)), 1)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_value_creation_plan(
    sector: str = "Physician Services",
    entry_ebitda_mm: float = 25.0,
    current_day: int = 200,
) -> ValueCreationPlanResult:
    corpus = _load_corpus()

    initiatives = _build_initiatives(entry_ebitda_mm, current_day)
    total_impact = sum(i.impact_ebitda_mm for i in initiatives)
    total_cost = sum(i.cost_mm for i in initiatives)
    plan_net = total_impact - total_cost

    # Target EBITDA at end of 2-year plan
    target_ebitda = entry_ebitda_mm + plan_net * 0.85   # net of execution haircut
    # Current EBITDA (based on initiative progress)
    current_ebitda = entry_ebitda_mm + sum(i.impact_ebitda_mm * i.progress_pct for i in initiatives) \
                     - sum(i.cost_mm * i.progress_pct for i in initiatives)
    # Exit EBITDA (target + organic growth)
    exit_ebitda = target_ebitda * 1.15

    checkpoints = _build_checkpoints(initiatives, current_day, total_impact)
    category_rollups = _build_category_rollup(initiatives, total_impact)
    bridge = _build_bridge(entry_ebitda_mm, target_ebitda, current_ebitda, exit_ebitda)
    exec_score = _execution_score(initiatives)

    return ValueCreationPlanResult(
        sector=sector,
        entry_ebitda_mm=round(entry_ebitda_mm, 2),
        target_ebitda_mm=round(target_ebitda, 2),
        current_ebitda_mm=round(current_ebitda, 2),
        exit_ebitda_mm=round(exit_ebitda, 2),
        hold_day=current_day,
        initiatives=initiatives,
        checkpoints=checkpoints,
        category_rollups=category_rollups,
        ebitda_bridge=bridge,
        total_plan_impact_mm=round(total_impact, 2),
        total_plan_cost_mm=round(total_cost, 2),
        plan_net_value_mm=round(plan_net, 2),
        execution_score=exec_score,
        corpus_deal_count=len(corpus),
    )
