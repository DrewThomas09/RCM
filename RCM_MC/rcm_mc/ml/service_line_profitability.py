"""Service line profitability model from HCRIS cost-center data.

HCRIS Worksheet A reports direct costs by cost center; Worksheet B
allocates overhead; Worksheet C apportions to revenue centers. The
partner-relevant question is **which service lines are profitable
vs subsidized at this hospital?** — and the cross-subsidy
structure has to be visible (not just a single per-line margin).

This module:

  1. Accepts cost-center records (one per Worksheet-A line number)
     with direct cost, overhead allocation, gross charges, and
     net revenue.
  2. Maps cost centers to canonical service-line groups (Surgery,
     Imaging, ED, Cardiology, OB/Newborn, Inpatient Routine, ...).
  3. Computes contribution margin per service line and identifies
     subsidizers + subsidized lines.
  4. Surfaces the cross-subsidy total — the dollars that would
     have to be picked up by other lines if a subsidized line
     were closed (or, conversely, the dollars at risk if a
     profitable line lost volume).

The existing :mod:`rcm_mc.pe_intelligence.service_line_analysis`
analyzes already-computed margins; this module is the upstream
*compute* layer that produces those margins from HCRIS.

Public API::

    from rcm_mc.ml.service_line_profitability import (
        CostCenterRecord,
        ServiceLineMargin,
        SERVICE_LINE_GROUPS,
        compute_service_line_profitability,
        identify_cross_subsidies,
    )
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple


# Canonical service-line groups + the HCRIS Worksheet-A line
# numbers (CMS-2552-10) that map to them. Line numbers reflect
# the standard cost-center taxonomy CMS publishes.
SERVICE_LINE_GROUPS: Dict[str, List[int]] = {
    "Inpatient Routine": [30, 31, 32, 33, 34],   # M/S, ICU, CCU
    "Maternal/Newborn":  [50, 51, 62],           # Nursery, OB, L&D
    "Surgery":           [60, 61, 64],           # OR, Recovery, Anes
    "Imaging":           [65, 66, 67],           # Diagnostic, Therapy, Radioiso
    "Cardiology":        [75],                    # ECG
    "Lab & Blood":       [68, 69, 70],           # Lab, Blood, IV
    "Therapy":           [71, 72, 73, 74],        # Resp, PT, OT, Speech
    "Pharmacy":          [78],
    "Renal":             [79],
    "ED":                [89],
    "Outpatient Clinic": [88, 90, 91],
    "Behavioral Health": [40],
}


# Canonical service line for a given HCRIS line number — built
# once at import.
LINE_TO_SERVICE_LINE: Dict[int, str] = {
    line_no: group_name
    for group_name, lines in SERVICE_LINE_GROUPS.items()
    for line_no in lines
}


# Service-line subsidy archetype — partner expectation for which
# lines typically run at a loss in non-academic community
# hospitals. Used in identify_cross_subsidies() to flag results
# that look unusual ('ED is profitable here, that's atypical').
TYPICALLY_SUBSIDIZED: set = {
    "ED", "Behavioral Health", "Maternal/Newborn",
    "Outpatient Clinic",
}
TYPICALLY_PROFITABLE: set = {
    "Surgery", "Cardiology", "Imaging",
}


@dataclass
class CostCenterRecord:
    """One Worksheet-A line for a hospital × fiscal year.

    Direct costs come from Worksheet A col 7. Overhead is from
    Worksheet B Part I post-allocation. Charges from Worksheet C
    col 6. Net revenue is computed by the caller (charges ×
    cost-to-charge × payer-mix realization) — we don't reproduce
    HCRIS allocation logic here.
    """
    ccn: str
    fiscal_year: int
    line_number: int
    cost_center_name: str
    direct_cost: float = 0.0
    overhead_allocation: float = 0.0
    gross_charges: float = 0.0
    net_revenue: float = 0.0


@dataclass
class ServiceLineMargin:
    """Aggregated profitability for one service line."""
    service_line: str
    n_cost_centers: int
    direct_cost: float
    overhead_allocation: float
    total_cost: float
    gross_charges: float
    net_revenue: float
    contribution_margin: float       # net_revenue - total_cost
    contribution_margin_pct: float   # / net_revenue
    revenue_share: float             # of total hospital net revenue
    cost_center_lines: List[int] = field(default_factory=list)


@dataclass
class CrossSubsidyAnalysis:
    """The cross-subsidy picture for a hospital."""
    ccn: str
    fiscal_year: int
    profitable_lines: List[ServiceLineMargin]
    subsidized_lines: List[ServiceLineMargin]
    breakeven_lines: List[ServiceLineMargin]
    total_subsidy_dollars: float       # sum of negative margins (abs)
    total_profit_dollars: float        # sum of positive margins
    net_hospital_margin: float         # total_profit + total_subsidy(neg)
    subsidy_intensity: float           # subsidy_$ / profit_$
    flagged_atypical: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


# ── Core computation ─────────────────────────────────────────

def compute_service_line_profitability(
    records: Iterable[CostCenterRecord],
    *,
    breakeven_band: float = 0.02,
) -> List[ServiceLineMargin]:
    """Aggregate cost-center records into service-line margins.

    Args:
      records: cost-center records, typically one per HCRIS line
        number per (ccn, fiscal_year). Records with line numbers
        outside SERVICE_LINE_GROUPS are skipped.
      breakeven_band: ±2% margin on net revenue counts as
        breakeven (callers can tighten/loosen).

    Returns: list of ServiceLineMargin sorted by contribution
    margin descending (most profitable first).
    """
    by_group: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {
            "direct": 0.0, "overhead": 0.0,
            "charges": 0.0, "revenue": 0.0,
            "lines": [],
        })
    for r in records:
        group = LINE_TO_SERVICE_LINE.get(r.line_number)
        if not group:
            continue
        b = by_group[group]
        b["direct"] += float(r.direct_cost or 0.0)
        b["overhead"] += float(r.overhead_allocation or 0.0)
        b["charges"] += float(r.gross_charges or 0.0)
        b["revenue"] += float(r.net_revenue or 0.0)
        b["lines"].append(r.line_number)

    total_revenue = sum(b["revenue"]
                        for b in by_group.values())
    out: List[ServiceLineMargin] = []
    for group, b in by_group.items():
        total_cost = b["direct"] + b["overhead"]
        net_rev = b["revenue"]
        contrib = net_rev - total_cost
        contrib_pct = (contrib / net_rev
                       if net_rev > 0 else 0.0)
        share = (net_rev / total_revenue
                 if total_revenue > 0 else 0.0)
        out.append(ServiceLineMargin(
            service_line=group,
            n_cost_centers=len(b["lines"]),
            direct_cost=round(b["direct"], 2),
            overhead_allocation=round(b["overhead"], 2),
            total_cost=round(total_cost, 2),
            gross_charges=round(b["charges"], 2),
            net_revenue=round(net_rev, 2),
            contribution_margin=round(contrib, 2),
            contribution_margin_pct=round(contrib_pct, 4),
            revenue_share=round(share, 4),
            cost_center_lines=sorted(set(b["lines"])),
        ))
    out.sort(key=lambda m: -m.contribution_margin)
    return out


def identify_cross_subsidies(
    margins: List[ServiceLineMargin],
    ccn: str,
    fiscal_year: int,
    *,
    breakeven_band: float = 0.02,
) -> CrossSubsidyAnalysis:
    """Decompose margins into profitable / breakeven / subsidized
    and quantify the cross-subsidy structure.

    breakeven_band: ±2% margin on net revenue counts as breakeven.
    """
    profitable: List[ServiceLineMargin] = []
    subsidized: List[ServiceLineMargin] = []
    breakeven: List[ServiceLineMargin] = []
    for m in margins:
        if m.contribution_margin_pct > breakeven_band:
            profitable.append(m)
        elif m.contribution_margin_pct < -breakeven_band:
            subsidized.append(m)
        else:
            breakeven.append(m)

    total_subsidy = -sum(m.contribution_margin
                         for m in subsidized)
    total_profit = sum(m.contribution_margin
                       for m in profitable)
    net_margin = total_profit - total_subsidy
    intensity = (total_subsidy / total_profit
                 if total_profit > 0 else 0.0)

    flagged: List[str] = []
    for m in profitable:
        if m.service_line in TYPICALLY_SUBSIDIZED:
            flagged.append(
                f"{m.service_line} is profitable here "
                f"({m.contribution_margin_pct:+.1%}); "
                f"typically a loss-leader in community "
                f"hospitals.")
    for m in subsidized:
        if m.service_line in TYPICALLY_PROFITABLE:
            flagged.append(
                f"{m.service_line} is losing money "
                f"({m.contribution_margin_pct:+.1%}); "
                f"typically a profit driver. Investigate "
                f"reimbursement or volume issue.")

    notes: List[str] = []
    if intensity > 1.0:
        notes.append(
            f"Subsidy intensity {intensity:.2f} — "
            f"loss-leaders consume more dollars than "
            f"profit drivers generate. Hospital is at risk "
            f"if any profitable line loses volume.")
    elif intensity > 0.5:
        notes.append(
            f"Subsidy intensity {intensity:.2f} — "
            f"non-trivial cross-subsidy; one or more "
            f"profitable lines is load-bearing.")
    if not subsidized and profitable:
        notes.append(
            "All service lines profitable — unusual; verify "
            "overhead allocation methodology before trusting.")
    if subsidized and not profitable:
        notes.append(
            "Every service line is losing money — consistent "
            "with a distressed asset or measurement issue.")

    return CrossSubsidyAnalysis(
        ccn=ccn,
        fiscal_year=fiscal_year,
        profitable_lines=profitable,
        subsidized_lines=subsidized,
        breakeven_lines=breakeven,
        total_subsidy_dollars=round(total_subsidy, 2),
        total_profit_dollars=round(total_profit, 2),
        net_hospital_margin=round(net_margin, 2),
        subsidy_intensity=round(intensity, 4),
        flagged_atypical=flagged,
        notes=notes,
    )


# ── Caller-friendly composer ─────────────────────────────────

def analyze_hospital_service_lines(
    records: Iterable[CostCenterRecord],
    *,
    ccn: Optional[str] = None,
    fiscal_year: Optional[int] = None,
    breakeven_band: float = 0.02,
) -> Tuple[List[ServiceLineMargin], CrossSubsidyAnalysis]:
    """One-call wrapper: per-line margins + cross-subsidy.

    Infers ccn + fiscal_year from the first record when not given.
    Raises ValueError on empty input — refusing to fabricate.
    """
    records_list = list(records)
    if not records_list:
        raise ValueError(
            "Cannot analyze empty records list")
    if ccn is None:
        ccn = records_list[0].ccn
    if fiscal_year is None:
        fiscal_year = records_list[0].fiscal_year
    margins = compute_service_line_profitability(
        records_list, breakeven_band=breakeven_band)
    analysis = identify_cross_subsidies(
        margins, ccn, fiscal_year,
        breakeven_band=breakeven_band)
    return margins, analysis
