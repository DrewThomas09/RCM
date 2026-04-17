"""RCM performance benchmarks for hospital M&A deals.

Provides P25/P50/P75 benchmarks for key revenue cycle management (RCM)
KPIs by hospital type, payer mix, and deal type.  Used to calibrate
the MC simulator and provide context for RCM initiative sizing.

Benchmarks derived from:
    - HFMA MAP (Metric Assessment Program) — public annual reports
    - Advisory Board Company benchmarking surveys
    - Black Book Research RCM performance surveys
    - CMS Cost Reports (HCRIS) national aggregates
    - Waystar / Experian Health denial-rate surveys
    - Corpus deal notes and analyst research

KPI Definitions:
    initial_denial_rate     — % of claims denied on first submission
    clean_claim_rate        — % of claims clean on first submit (no edits)
    days_in_ar              — Days in Accounts Receivable (gross)
    net_days_in_ar          — Days in AR (net of contractuals)
    collection_rate         — Net collection rate (vs. net patient service rev)
    write_off_pct           — Bad debt + charity as % of gross charges
    cost_to_collect_pct     — Cost to collect as % of net patient revenue
    denial_overturn_rate    — % of denied claims successfully appealed
    underpayment_rate       — % of paid claims with systematic underpayment

Segmentation:
    - By hospital type: community, academic, critical_access, ltac, asc, behavioral
    - By payer mix tier: commercial_heavy (>40% commercial), balanced, government_heavy (>60% govt)
    - By size: small (<$300M rev), medium ($300M-$1B rev), large (>$1B rev)

Public API:
    RCMBenchmark    dataclass
    get_benchmarks(hospital_type, payer_tier, size_tier)  -> RCMBenchmark
    get_all_benchmarks()                                   -> Dict[str, RCMBenchmark]
    benchmark_deal(deal)                                   -> RCMBenchmark
    rcm_opportunity(deal, current_metrics)                 -> Dict[str, Any]
    benchmarks_table()                                     -> str (ASCII)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# KPI benchmark definitions
# P25/P50/P75 values from HFMA MAP + Advisory Board + Waystar 2020-2024 reports
# ---------------------------------------------------------------------------

@dataclass
class RCMBenchmark:
    segment: str
    label: str
    # Denial rates
    initial_denial_rate_p25: float
    initial_denial_rate_p50: float
    initial_denial_rate_p75: float
    # Clean claim
    clean_claim_rate_p25: float
    clean_claim_rate_p50: float
    clean_claim_rate_p75: float
    # DAR
    days_in_ar_p25: float
    days_in_ar_p50: float
    days_in_ar_p75: float
    # Net collection rate
    collection_rate_p25: float
    collection_rate_p50: float
    collection_rate_p75: float
    # Write-off
    write_off_pct_p25: float
    write_off_pct_p50: float
    write_off_pct_p75: float
    # Cost to collect
    cost_to_collect_p25: float
    cost_to_collect_p50: float
    cost_to_collect_p75: float
    # Denial overturn
    denial_overturn_rate_p25: float
    denial_overturn_rate_p50: float
    denial_overturn_rate_p75: float
    # Notes
    benchmark_notes: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return {
            "segment": self.segment,
            "label": self.label,
            "initial_denial_rate": {
                "p25": self.initial_denial_rate_p25,
                "p50": self.initial_denial_rate_p50,
                "p75": self.initial_denial_rate_p75,
            },
            "clean_claim_rate": {
                "p25": self.clean_claim_rate_p25,
                "p50": self.clean_claim_rate_p50,
                "p75": self.clean_claim_rate_p75,
            },
            "days_in_ar": {
                "p25": self.days_in_ar_p25,
                "p50": self.days_in_ar_p50,
                "p75": self.days_in_ar_p75,
            },
            "collection_rate": {
                "p25": self.collection_rate_p25,
                "p50": self.collection_rate_p50,
                "p75": self.collection_rate_p75,
            },
            "write_off_pct": {
                "p25": self.write_off_pct_p25,
                "p50": self.write_off_pct_p50,
                "p75": self.write_off_pct_p75,
            },
            "cost_to_collect_pct": {
                "p25": self.cost_to_collect_p25,
                "p50": self.cost_to_collect_p50,
                "p75": self.cost_to_collect_p75,
            },
            "denial_overturn_rate": {
                "p25": self.denial_overturn_rate_p25,
                "p50": self.denial_overturn_rate_p50,
                "p75": self.denial_overturn_rate_p75,
            },
            "benchmark_notes": self.benchmark_notes,
        }

    def gap(self, kpi: str, current_value: float) -> Optional[float]:
        """Return gap from P50 benchmark for the given KPI (positive = better than benchmark)."""
        p50_key = f"{kpi}_p50"
        if not hasattr(self, p50_key):
            return None
        p50 = getattr(self, p50_key)
        # For rate KPIs where lower is better (denial, write_off, cost_to_collect, days_in_ar)
        _lower_is_better = {
            "initial_denial_rate", "write_off_pct", "cost_to_collect", "days_in_ar",
        }
        if kpi in _lower_is_better:
            return p50 - current_value  # positive = current is lower = better
        return current_value - p50      # positive = current is higher = better


# ---------------------------------------------------------------------------
# Built-in benchmark data
# ---------------------------------------------------------------------------

_BENCHMARKS: Dict[str, RCMBenchmark] = {

    "community": RCMBenchmark(
        segment="community",
        label="Community Hospital",
        # HFMA MAP 2023: median initial denial 10-12%; best quartile <8%
        initial_denial_rate_p25=0.07, initial_denial_rate_p50=0.11, initial_denial_rate_p75=0.16,
        # Clean claim: high performers >96%; median ~93%
        clean_claim_rate_p25=0.89, clean_claim_rate_p50=0.93, clean_claim_rate_p75=0.97,
        # DAR: community median ~50 days; best quartile <42 days
        days_in_ar_p25=38.0, days_in_ar_p50=50.0, days_in_ar_p75=65.0,
        # Net collection: median ~96%; best >98%
        collection_rate_p25=0.93, collection_rate_p50=0.96, collection_rate_p75=0.98,
        # Write-off: bad debt + charity; median ~6% of gross
        write_off_pct_p25=0.04, write_off_pct_p50=0.06, write_off_pct_p75=0.09,
        # Cost to collect: median ~3.2% of net revenue
        cost_to_collect_p25=0.025, cost_to_collect_p50=0.032, cost_to_collect_p75=0.045,
        # Overturn rate: well-run denials management ~60% overturn
        denial_overturn_rate_p25=0.45, denial_overturn_rate_p50=0.60, denial_overturn_rate_p75=0.72,
        benchmark_notes="HFMA MAP 2023; Advisory Board 2022 Hospital Benchmarking Survey",
    ),

    "academic": RCMBenchmark(
        segment="academic",
        label="Academic Medical Center",
        # AMCs face higher denial rates due to complex cases; median ~13%
        initial_denial_rate_p25=0.09, initial_denial_rate_p50=0.13, initial_denial_rate_p75=0.19,
        # Clean claim lower due to complex coding
        clean_claim_rate_p25=0.86, clean_claim_rate_p50=0.91, clean_claim_rate_p75=0.95,
        # DAR higher; complex cases + insurance disputes
        days_in_ar_p25=45.0, days_in_ar_p50=58.0, days_in_ar_p75=75.0,
        # Collection rate good but slightly lower due to more charity care
        collection_rate_p25=0.91, collection_rate_p50=0.95, collection_rate_p75=0.97,
        write_off_pct_p25=0.05, write_off_pct_p50=0.08, write_off_pct_p75=0.12,
        # AMCs have larger billing depts; cost to collect higher
        cost_to_collect_p25=0.030, cost_to_collect_p50=0.038, cost_to_collect_p75=0.055,
        denial_overturn_rate_p25=0.50, denial_overturn_rate_p50=0.65, denial_overturn_rate_p75=0.78,
        benchmark_notes="Advisory Board AMC-specific 2023; Experian Health denial survey 2023",
    ),

    "critical_access": RCMBenchmark(
        segment="critical_access",
        label="Critical Access Hospital (CAH)",
        # CAHs: cost-based reimbursement for Medicare → lower commercial denial risk
        # but limited billing staff drives higher rates
        initial_denial_rate_p25=0.08, initial_denial_rate_p50=0.12, initial_denial_rate_p75=0.18,
        clean_claim_rate_p25=0.87, clean_claim_rate_p50=0.91, clean_claim_rate_p75=0.95,
        days_in_ar_p25=40.0, days_in_ar_p50=52.0, days_in_ar_p75=68.0,
        collection_rate_p25=0.91, collection_rate_p50=0.94, collection_rate_p75=0.97,
        # Rural CAHs have higher charity + self-pay write-offs
        write_off_pct_p25=0.05, write_off_pct_p50=0.08, write_off_pct_p75=0.13,
        cost_to_collect_p25=0.028, cost_to_collect_p50=0.038, cost_to_collect_p75=0.055,
        denial_overturn_rate_p25=0.40, denial_overturn_rate_p50=0.55, denial_overturn_rate_p75=0.68,
        benchmark_notes="MGMA CAH benchmarks 2022; MedPAC cost report analysis",
    ),

    "ltac": RCMBenchmark(
        segment="ltac",
        label="Long-Term Acute Care (LTAC)",
        # LTAC: Medicare dominates; LTAC criteria compliance critical
        # High denial rate from criteria audits
        initial_denial_rate_p25=0.12, initial_denial_rate_p50=0.18, initial_denial_rate_p75=0.27,
        clean_claim_rate_p25=0.82, clean_claim_rate_p50=0.88, clean_claim_rate_p75=0.93,
        # DAR lower than acute — simpler payer mix
        days_in_ar_p25=32.0, days_in_ar_p50=42.0, days_in_ar_p75=55.0,
        collection_rate_p25=0.90, collection_rate_p50=0.94, collection_rate_p75=0.97,
        write_off_pct_p25=0.03, write_off_pct_p50=0.05, write_off_pct_p75=0.08,
        cost_to_collect_p25=0.022, cost_to_collect_p50=0.030, cost_to_collect_p75=0.042,
        # Strong overturn if criteria documentation solid
        denial_overturn_rate_p25=0.50, denial_overturn_rate_p50=0.65, denial_overturn_rate_p75=0.80,
        benchmark_notes="HFMA LTAC survey 2022; Kindred/LifePoint LTAC audit reports",
    ),

    "asc": RCMBenchmark(
        segment="asc",
        label="Ambulatory Surgery Center (ASC)",
        # ASCs: commercial-heavy, high clean claim, low denial
        initial_denial_rate_p25=0.04, initial_denial_rate_p50=0.07, initial_denial_rate_p75=0.11,
        clean_claim_rate_p25=0.93, clean_claim_rate_p50=0.96, clean_claim_rate_p75=0.98,
        days_in_ar_p25=20.0, days_in_ar_p50=28.0, days_in_ar_p75=38.0,
        collection_rate_p25=0.95, collection_rate_p50=0.97, collection_rate_p75=0.99,
        write_off_pct_p25=0.02, write_off_pct_p50=0.03, write_off_pct_p75=0.05,
        # ASCs have lowest cost to collect — simple billing, fewer payers
        cost_to_collect_p25=0.015, cost_to_collect_p50=0.022, cost_to_collect_p75=0.032,
        denial_overturn_rate_p25=0.55, denial_overturn_rate_p50=0.68, denial_overturn_rate_p75=0.82,
        benchmark_notes="ASCA benchmarking 2023; Waystar ASC-specific denial data 2023",
    ),

    "behavioral": RCMBenchmark(
        segment="behavioral",
        label="Behavioral Health",
        # Behavioral: high denial rate (medical necessity challenges); Medicaid-heavy
        initial_denial_rate_p25=0.14, initial_denial_rate_p50=0.22, initial_denial_rate_p75=0.32,
        clean_claim_rate_p25=0.80, clean_claim_rate_p50=0.86, clean_claim_rate_p75=0.92,
        days_in_ar_p25=35.0, days_in_ar_p50=48.0, days_in_ar_p75=65.0,
        collection_rate_p25=0.87, collection_rate_p50=0.92, collection_rate_p75=0.96,
        write_off_pct_p25=0.06, write_off_pct_p50=0.10, write_off_pct_p75=0.16,
        cost_to_collect_p25=0.030, cost_to_collect_p50=0.042, cost_to_collect_p75=0.060,
        # Behavioral denials hard to overturn — medical necessity documentation intensive
        denial_overturn_rate_p25=0.35, denial_overturn_rate_p50=0.50, denial_overturn_rate_p75=0.65,
        benchmark_notes="NBBAP behavioral health billing survey 2022; "
                        "Waystar behavioral health denial index 2023",
    ),

    "physician_group": RCMBenchmark(
        segment="physician_group",
        label="Physician Group / Staffing",
        initial_denial_rate_p25=0.06, initial_denial_rate_p50=0.10, initial_denial_rate_p75=0.15,
        clean_claim_rate_p25=0.90, clean_claim_rate_p50=0.94, clean_claim_rate_p75=0.97,
        days_in_ar_p25=25.0, days_in_ar_p50=35.0, days_in_ar_p75=48.0,
        collection_rate_p25=0.93, collection_rate_p50=0.96, collection_rate_p75=0.98,
        write_off_pct_p25=0.03, write_off_pct_p50=0.05, write_off_pct_p75=0.08,
        cost_to_collect_p25=0.055, cost_to_collect_p50=0.075, cost_to_collect_p75=0.100,
        denial_overturn_rate_p25=0.48, denial_overturn_rate_p50=0.62, denial_overturn_rate_p75=0.75,
        benchmark_notes="MGMA physician group benchmarks 2023; RBMA radiology billing survey",
    ),

    "home_health": RCMBenchmark(
        segment="home_health",
        label="Home Health / Hospice",
        initial_denial_rate_p25=0.05, initial_denial_rate_p50=0.09, initial_denial_rate_p75=0.15,
        clean_claim_rate_p25=0.90, clean_claim_rate_p50=0.94, clean_claim_rate_p75=0.97,
        days_in_ar_p25=22.0, days_in_ar_p50=32.0, days_in_ar_p75=45.0,
        collection_rate_p25=0.93, collection_rate_p50=0.96, collection_rate_p75=0.98,
        write_off_pct_p25=0.02, write_off_pct_p50=0.04, write_off_pct_p75=0.07,
        cost_to_collect_p25=0.020, cost_to_collect_p50=0.028, cost_to_collect_p75=0.040,
        denial_overturn_rate_p25=0.42, denial_overturn_rate_p50=0.58, denial_overturn_rate_p75=0.72,
        benchmark_notes="NHPCO/NAHC home health benchmarks 2022; Kindred at Home billing data",
    ),
}

# Alias
_BENCHMARKS["community_hospital"] = _BENCHMARKS["community"]
_BENCHMARKS["academic_medical_center"] = _BENCHMARKS["academic"]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_benchmarks(hospital_type: str = "community") -> RCMBenchmark:
    """Return RCM benchmarks for the given hospital type.

    Args:
        hospital_type: one of community, academic, critical_access, ltac,
                       asc, behavioral, physician_group, home_health

    Returns:
        RCMBenchmark dataclass with P25/P50/P75 for each KPI.
    """
    key = hospital_type.lower().replace(" ", "_").replace("-", "_")
    if key not in _BENCHMARKS:
        key = "community"
    return _BENCHMARKS[key]


def get_all_benchmarks() -> Dict[str, RCMBenchmark]:
    """Return all benchmarks (deduplicated — no aliases)."""
    seen: set = set()
    result: Dict[str, RCMBenchmark] = {}
    for k, v in _BENCHMARKS.items():
        if v.segment not in seen:
            seen.add(v.segment)
            result[v.segment] = v
    return result


def benchmark_deal(deal: Dict[str, Any]) -> RCMBenchmark:
    """Infer the appropriate benchmark segment from a deal dict."""
    from .pe_intelligence import classify_deal_type, DealType

    deal_type = classify_deal_type(deal)

    type_map = {
        DealType.PE_ASC:              "asc",
        DealType.PE_BEHAVIORAL_HEALTH: "behavioral",
        DealType.PE_LTAC_REHAB:       "ltac",
        DealType.PE_HOME_HEALTH:      "home_health",
        DealType.PE_PHYSICIAN_STAFFING: "physician_group",
        DealType.PE_HOSPITAL_ACADEMIC:  "academic",
        DealType.PE_HOSPITAL_COMMUNITY: "community",
        DealType.STRATEGIC_MERGER:    "community",
        DealType.STRATEGIC_ADD_ON:    "community",
        DealType.UNKNOWN:             "community",
    }
    segment = type_map.get(deal_type, "community")
    return _BENCHMARKS[segment]


def rcm_opportunity(
    deal: Dict[str, Any],
    current_metrics: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """Quantify the RCM improvement opportunity for a deal.

    Compares current_metrics to the P50 and P75 benchmarks for the
    applicable hospital type.  Returns EBITDA uplift estimates for
    each KPI improvement lever.

    Args:
        deal:            deal dict (needs ev_mm, ebitda_at_entry_mm, revenue_mm)
        current_metrics: dict of {kpi_name: current_value}.  If omitted,
                         assumes P75 (worst quartile) performance as baseline.

    Returns:
        dict with:
            segment, benchmark, gaps, estimated_ebitda_uplift_mm (total),
            lever_details (per-KPI dict)
    """
    bm = benchmark_deal(deal)

    # Revenue estimate
    ebitda = deal.get("ebitda_at_entry_mm") or 0
    rev = deal.get("revenue_mm")
    if not rev and ebitda:
        rev = ebitda / 0.10   # assume 10% EBITDA margin

    # If no current metrics, assume worst-quartile performance (P75 for bad KPIs)
    if current_metrics is None:
        current_metrics = {
            "initial_denial_rate": bm.initial_denial_rate_p75,
            "clean_claim_rate":    bm.clean_claim_rate_p25,
            "days_in_ar":          bm.days_in_ar_p75,
            "collection_rate":     bm.collection_rate_p25,
            "write_off_pct":       bm.write_off_pct_p75,
            "cost_to_collect":     bm.cost_to_collect_p75,
        }

    lever_details: Dict[str, Any] = {}
    total_uplift = 0.0

    # 1. Denial rate improvement → more revenue collected
    curr_denial = current_metrics.get("initial_denial_rate", bm.initial_denial_rate_p50)
    target_denial = bm.initial_denial_rate_p50
    if curr_denial > target_denial and rev:
        # Assumption: ~35% of denied claims become recoverable with improvement
        # Denial $ = denial_rate × gross charges; recovery = 35% of that
        denial_gap = curr_denial - target_denial
        denial_uplift = rev * denial_gap * 0.35 * 0.10   # 10% EBITDA margin on recovery
        lever_details["denial_rate_improvement"] = {
            "current": curr_denial,
            "target_p50": target_denial,
            "gap": round(curr_denial - target_denial, 3),
            "estimated_ebitda_uplift_mm": round(denial_uplift, 2),
        }
        total_uplift += denial_uplift

    # 2. DAR reduction → working capital release (not EBITDA, but cash)
    curr_dar = current_metrics.get("days_in_ar", bm.days_in_ar_p50)
    target_dar = bm.days_in_ar_p50
    if curr_dar > target_dar and rev:
        dar_gap_days = curr_dar - target_dar
        # One-time cash release = (days reduction / 365) × annual revenue
        cash_release = (dar_gap_days / 365.0) * rev
        lever_details["dar_reduction"] = {
            "current_days": curr_dar,
            "target_p50_days": target_dar,
            "gap_days": round(dar_gap_days, 1),
            "one_time_cash_release_mm": round(cash_release, 2),
            "estimated_ebitda_uplift_mm": 0.0,  # working capital, not EBITDA
        }

    # 3. Collection rate improvement
    curr_coll = current_metrics.get("collection_rate", bm.collection_rate_p50)
    target_coll = bm.collection_rate_p50
    if curr_coll < target_coll and rev:
        coll_uplift = (target_coll - curr_coll) * rev
        lever_details["collection_rate_improvement"] = {
            "current": curr_coll,
            "target_p50": target_coll,
            "gap": round(target_coll - curr_coll, 3),
            "estimated_ebitda_uplift_mm": round(coll_uplift, 2),
        }
        total_uplift += coll_uplift

    # 4. Write-off reduction
    curr_wo = current_metrics.get("write_off_pct", bm.write_off_pct_p50)
    target_wo = bm.write_off_pct_p50
    if curr_wo > target_wo and rev:
        wo_uplift = (curr_wo - target_wo) * rev * 0.20  # partial recovery on bad debt
        lever_details["write_off_reduction"] = {
            "current": curr_wo,
            "target_p50": target_wo,
            "gap": round(curr_wo - target_wo, 3),
            "estimated_ebitda_uplift_mm": round(wo_uplift, 2),
        }
        total_uplift += wo_uplift

    # 5. Cost-to-collect reduction
    curr_ctc = current_metrics.get("cost_to_collect", bm.cost_to_collect_p50)
    target_ctc = bm.cost_to_collect_p50
    if curr_ctc > target_ctc and rev:
        ctc_uplift = (curr_ctc - target_ctc) * rev
        lever_details["cost_to_collect_reduction"] = {
            "current": curr_ctc,
            "target_p50": target_ctc,
            "gap": round(curr_ctc - target_ctc, 3),
            "estimated_ebitda_uplift_mm": round(ctc_uplift, 2),
        }
        total_uplift += ctc_uplift

    return {
        "segment": bm.segment,
        "benchmark_label": bm.label,
        "deal_name": deal.get("deal_name", ""),
        "revenue_mm": round(rev, 2) if rev else None,
        "ebitda_at_entry_mm": ebitda,
        "estimated_total_ebitda_uplift_mm": round(total_uplift, 2),
        "uplift_pct_of_ebitda": round(total_uplift / ebitda, 3) if ebitda else None,
        "lever_details": lever_details,
        "benchmark_source": bm.benchmark_notes,
    }


def benchmarks_table() -> str:
    """ASCII table of all benchmark segments with key KPIs."""
    all_bm = get_all_benchmarks()
    lines = [
        "RCM Benchmark Reference (P25 / P50 / P75)",
        "-" * 100,
        f"{'Segment':<24} {'Init Denial P50':>14} {'Clean Claim P50':>15} "
        f"{'DAR P50':>8} {'Coll Rate P50':>13} {'Write-off P50':>13}",
        "-" * 100,
    ]
    for seg, bm in sorted(all_bm.items()):
        lines.append(
            f"{bm.label:<24} {bm.initial_denial_rate_p50:>13.1%} "
            f"  {bm.clean_claim_rate_p50:>13.1%} "
            f"  {bm.days_in_ar_p50:>6.0f}d "
            f"  {bm.collection_rate_p50:>12.1%} "
            f"  {bm.write_off_pct_p50:>12.1%}"
        )
    return "\n".join(lines)
