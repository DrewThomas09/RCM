"""Deal timeline analytics — entry-to-exit event sequencing across the corpus.

Provides tools to reconstruct deal lifecycles, track market cycles,
and surface timing patterns useful for PE investment pacing decisions.

Public API:
    DealEvent                           dataclass
    build_deal_timeline(deal)           -> list[DealEvent]
    corpus_timeline(deals)              -> list[DealEvent]
    market_activity_by_year(deals)      -> dict[int, dict]
    holding_period_distribution(deals)  -> dict
    entry_exit_gap_analysis(deals)      -> list[dict]
    deal_cycle_phase(year)              -> str
    timeline_table(events, max_rows)    -> str
    pacing_recommendation(deals)        -> dict
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DealEvent:
    """A single event in a deal's lifecycle."""
    source_id: str
    deal_name: str
    event_type: str   # entry / exit / recap / add_on / restructuring
    year: Optional[int]
    ev_mm: Optional[float]
    moic: Optional[float]
    irr: Optional[float]
    hold_years: Optional[float]
    buyer: Optional[str]
    seller: Optional[str]
    deal_type: Optional[str]
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Deal cycle phases (rough PE market heuristics)
# ---------------------------------------------------------------------------

_CYCLE_PHASES = {
    range(1990, 1995): "early_lbo_era",
    range(1995, 2000): "growth_era",
    range(2000, 2002): "dot_com_correction",
    range(2002, 2007): "credit_expansion",
    range(2007, 2010): "financial_crisis",
    range(2010, 2015): "recovery",
    range(2015, 2020): "late_cycle_bull",
    range(2020, 2022): "covid_disruption",
    range(2022, 2024): "rate_shock",
    range(2024, 2031): "normalization",
}


def deal_cycle_phase(year: int) -> str:
    """Return the market cycle phase label for a given year."""
    for yr_range, phase in _CYCLE_PHASES.items():
        if year in yr_range:
            return phase
    return "unknown"


# ---------------------------------------------------------------------------
# Timeline builders
# ---------------------------------------------------------------------------

def build_deal_timeline(deal: Dict[str, Any]) -> List[DealEvent]:
    """Build entry (and exit if realized) events for a single deal."""
    events: List[DealEvent] = []
    year = deal.get("year")
    hold = deal.get("hold_years")
    moic = deal.get("realized_moic")
    irr = deal.get("realized_irr")

    events.append(DealEvent(
        source_id=str(deal.get("source_id") or ""),
        deal_name=str(deal.get("deal_name") or ""),
        event_type="entry",
        year=year,
        ev_mm=deal.get("ev_mm"),
        moic=None,
        irr=None,
        hold_years=hold,
        buyer=deal.get("buyer"),
        seller=deal.get("seller"),
        deal_type=deal.get("deal_type"),
        notes=deal.get("notes"),
    ))

    if moic is not None and year is not None and hold is not None:
        exit_year = int(year + hold) if hold else None
        events.append(DealEvent(
            source_id=str(deal.get("source_id") or ""),
            deal_name=str(deal.get("deal_name") or ""),
            event_type="exit",
            year=exit_year,
            ev_mm=deal.get("ev_mm"),
            moic=moic,
            irr=irr,
            hold_years=hold,
            buyer=deal.get("buyer"),
            seller=deal.get("seller"),
            deal_type=deal.get("deal_type"),
            notes=None,
        ))

    return events


def corpus_timeline(deals: List[Dict[str, Any]]) -> List[DealEvent]:
    """Build a full sorted timeline of all entry/exit events across the corpus."""
    events: List[DealEvent] = []
    for d in deals:
        events.extend(build_deal_timeline(d))
    events.sort(key=lambda e: (e.year or 9999, e.event_type))
    return events


# ---------------------------------------------------------------------------
# Market activity analysis
# ---------------------------------------------------------------------------

def market_activity_by_year(deals: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
    """Aggregate deal entry activity by year.

    Returns a dict keyed by year with:
        deal_count, total_ev_mm, median_ev_mm, avg_ev_ebitda, deal_types
    """
    from collections import defaultdict
    by_year: Dict[int, List[Dict]] = defaultdict(list)
    for d in deals:
        yr = d.get("year")
        if yr:
            by_year[int(yr)].append(d)

    result: Dict[int, Dict[str, Any]] = {}
    for yr in sorted(by_year):
        bucket = by_year[yr]
        evs = [d["ev_mm"] for d in bucket if d.get("ev_mm") is not None]
        multiples = [d["ev_ebitda"] for d in bucket if d.get("ev_ebitda") is not None]
        types = list({d.get("deal_type") or "unknown" for d in bucket})
        result[yr] = {
            "deal_count": len(bucket),
            "total_ev_mm": round(sum(evs), 1) if evs else None,
            "median_ev_mm": round(sorted(evs)[len(evs) // 2], 1) if evs else None,
            "avg_ev_ebitda": round(sum(multiples) / len(multiples), 2) if multiples else None,
            "deal_types": sorted(types),
            "cycle_phase": deal_cycle_phase(yr),
        }
    return result


# ---------------------------------------------------------------------------
# Holding period distribution
# ---------------------------------------------------------------------------

def holding_period_distribution(deals: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Summary statistics on holding periods for realized deals."""
    holds = [d["hold_years"] for d in deals
             if d.get("hold_years") is not None and d.get("realized_moic") is not None]
    if not holds:
        return {"count": 0}

    holds_s = sorted(holds)
    n = len(holds_s)
    mean = sum(holds_s) / n
    variance = sum((h - mean) ** 2 for h in holds_s) / n

    def pct(p: float) -> float:
        idx = (p / 100) * (n - 1)
        lo = int(idx)
        hi = min(lo + 1, n - 1)
        return round(holds_s[lo] + (idx - lo) * (holds_s[hi] - holds_s[lo]), 2)

    buckets = {"0-3yr": 0, "3-5yr": 0, "5-7yr": 0, "7+yr": 0}
    for h in holds_s:
        if h < 3:
            buckets["0-3yr"] += 1
        elif h < 5:
            buckets["3-5yr"] += 1
        elif h < 7:
            buckets["5-7yr"] += 1
        else:
            buckets["7+yr"] += 1

    return {
        "count": n,
        "mean": round(mean, 2),
        "stdev": round(math.sqrt(variance), 2),
        "p10": pct(10),
        "p25": pct(25),
        "p50": pct(50),
        "p75": pct(75),
        "p90": pct(90),
        "buckets": buckets,
    }


# ---------------------------------------------------------------------------
# Entry-exit gap analysis (vintage vs realization year)
# ---------------------------------------------------------------------------

def entry_exit_gap_analysis(deals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """For each realized deal, compute entry year, exit year, implied gap, and return."""
    rows = []
    for d in deals:
        yr = d.get("year")
        hold = d.get("hold_years")
        moic = d.get("realized_moic")
        if yr is None or hold is None or moic is None:
            continue
        exit_yr = int(yr + hold)
        rows.append({
            "source_id": d.get("source_id"),
            "deal_name": d.get("deal_name"),
            "entry_year": yr,
            "exit_year": exit_yr,
            "hold_years": hold,
            "realized_moic": moic,
            "realized_irr": d.get("realized_irr"),
            "entry_phase": deal_cycle_phase(yr),
            "exit_phase": deal_cycle_phase(exit_yr),
            "cross_cycle": deal_cycle_phase(yr) != deal_cycle_phase(exit_yr),
        })
    rows.sort(key=lambda r: r["entry_year"])
    return rows


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def timeline_table(events: List[DealEvent], max_rows: int = 40) -> str:
    """Formatted text table of timeline events."""
    lines = [
        f"{'Year':>4}  {'Type':<12} {'Deal':<45} {'EV $M':>8} {'MOIC':>6}",
        "-" * 85,
    ]
    for ev in events[:max_rows]:
        year = str(ev.year) if ev.year else "  —  "
        ev_s = f"${ev.ev_mm:,.0f}" if ev.ev_mm else "     —"
        moic_s = f"{ev.moic:.2f}x" if ev.moic is not None else "   —  "
        lines.append(
            f"{year:>4}  {ev.event_type:<12} {ev.deal_name[:44]:<45} {ev_s:>8} {moic_s:>6}"
        )
    if len(events) > max_rows:
        lines.append(f"  ... {len(events) - max_rows} more events")
    return "\n".join(lines) + "\n"


def pacing_recommendation(deals: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Suggest deployment pace based on corpus vintage concentration.

    Returns:
        recommended_vintages   – years with below-average deal counts (room to add)
        crowded_vintages       – years with above-average deal counts (avoid overweighting)
        avg_deals_per_year     – float
        total_active_deals     – unrealized deal count
    """
    by_year = market_activity_by_year(deals)
    if not by_year:
        return {}

    counts = [v["deal_count"] for v in by_year.values()]
    avg = sum(counts) / len(counts)
    total_active = sum(
        1 for d in deals if d.get("realized_moic") is None
    )
    crowded = [yr for yr, v in by_year.items() if v["deal_count"] > avg * 1.5]
    light = [yr for yr, v in by_year.items() if v["deal_count"] < avg * 0.5]

    return {
        "avg_deals_per_year": round(avg, 1),
        "total_active_deals": total_active,
        "crowded_vintages": sorted(crowded),
        "light_vintages": sorted(light),
        "recommendation": (
            "Corpus is vintage-concentrated — consider spreading future investments across "
            f"under-represented years: {sorted(light)}"
            if light else "Corpus has well-distributed vintages."
        ),
    }
