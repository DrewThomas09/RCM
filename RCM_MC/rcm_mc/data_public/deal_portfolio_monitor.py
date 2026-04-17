"""Portfolio monitoring — tracks active deals against plan and raises alerts.

Compares each unrealized deal's implied trajectory against base-rate benchmarks
and raises signals when returns are tracking below expectations.

Public API:
    PortfolioAlert                          dataclass
    MonitorConfig                           dataclass
    compute_implied_moic(deal, as_of_year)  -> Optional[float]
    deal_status(deal, config, as_of_year)   -> dict
    monitor_portfolio(deals, config)        -> list[dict]
    portfolio_dashboard_text(results)       -> str
    benchmark_gap_analysis(deals, corpus)   -> list[dict]
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PortfolioAlert:
    """An alert raised on an active portfolio position."""
    source_id: str
    deal_name: str
    alert_type: str    # on_track / watch / at_risk / critical
    message: str
    implied_moic: Optional[float] = None
    target_moic: Optional[float] = None
    years_held: Optional[float] = None
    years_remaining: Optional[float] = None


@dataclass
class MonitorConfig:
    """Configuration for portfolio monitoring thresholds."""
    target_gross_moic: float = 2.5
    target_net_moic: float = 2.0
    at_risk_moic_threshold: float = 1.5    # below target by this → at_risk
    critical_moic_threshold: float = 1.0   # below 1.0 → critical (losing money)
    typical_hold_years: float = 5.0
    as_of_year: int = 2024


def _safe_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def compute_implied_moic(deal: Dict[str, Any], as_of_year: int = 2024) -> Optional[float]:
    """Estimate the current implied MOIC for an unrealized deal.

    Uses entry EV/EBITDA and an assumed 5-7% EBITDA CAGR to estimate
    current equity value, then divides by cost basis.

    This is a rough trajectory estimate — not an exact NAV computation.
    """
    entry_year = _safe_float(deal.get("year"))
    ev = _safe_float(deal.get("ev_mm"))
    ebitda = _safe_float(deal.get("ebitda_mm") or deal.get("ebitda_at_entry_mm"))
    ev_ebitda = _safe_float(deal.get("ev_ebitda"))

    if entry_year is None or ev is None:
        return None

    years_held = as_of_year - entry_year
    if years_held <= 0:
        return None

    # Estimate current EBITDA via assumed CAGR
    assumed_cagr = 0.06  # 6% real healthcare sector median
    if ebitda and ebitda > 0:
        current_ebitda = ebitda * ((1 + assumed_cagr) ** years_held)
    elif ev and ev_ebitda and ev_ebitda > 0:
        implied_ebitda = ev / ev_ebitda
        current_ebitda = implied_ebitda * ((1 + assumed_cagr) ** years_held)
    else:
        return None

    # Estimate current EV using same entry multiple (conservative — no expansion)
    current_ev_ebitda = ev_ebitda or 11.0
    current_ev = current_ebitda * current_ev_ebitda

    # Estimate equity: assume 35% equity at entry, rest debt
    equity_pct = 0.35
    entry_equity = ev * equity_pct
    entry_debt = ev * (1 - equity_pct)
    # Debt paydown: 3%/year amortization
    current_debt = max(0.0, entry_debt * (1 - 0.03 * years_held))
    current_equity = current_ev - current_debt

    if entry_equity <= 0:
        return None

    return round(current_equity / entry_equity, 2)


def deal_status(
    deal: Dict[str, Any],
    config: Optional[MonitorConfig] = None,
    as_of_year: Optional[int] = None,
) -> Dict[str, Any]:
    """Compute current status of a single portfolio position."""
    if config is None:
        config = MonitorConfig()
    year = as_of_year or config.as_of_year

    src = str(deal.get("source_id") or "")
    name = str(deal.get("deal_name") or "")
    entry_year = _safe_float(deal.get("year"))
    hold = _safe_float(deal.get("hold_years"))
    realized_moic = _safe_float(deal.get("realized_moic"))

    # Already realized
    if realized_moic is not None:
        return {
            "source_id": src,
            "deal_name": name,
            "status": "realized",
            "realized_moic": realized_moic,
            "target_moic": config.target_gross_moic,
            "vs_target": round(realized_moic - config.target_gross_moic, 2),
        }

    years_held = (year - entry_year) if entry_year else None
    target_hold = hold or config.typical_hold_years
    years_remaining = max(0.0, target_hold - (years_held or 0)) if years_held is not None else None

    implied = compute_implied_moic(deal, year)

    # Determine alert type
    if implied is None:
        alert_type = "unknown"
        message = "Insufficient data to compute implied MOIC"
    elif implied >= config.target_gross_moic:
        alert_type = "on_track"
        message = f"Implied MOIC {implied:.2f}x tracking at/above target {config.target_gross_moic:.1f}x"
    elif implied >= config.at_risk_moic_threshold:
        alert_type = "watch"
        message = f"Implied MOIC {implied:.2f}x below target {config.target_gross_moic:.1f}x — monitoring"
    elif implied >= config.critical_moic_threshold:
        alert_type = "at_risk"
        message = f"Implied MOIC {implied:.2f}x below {config.at_risk_moic_threshold:.1f}x — at risk"
    else:
        alert_type = "critical"
        message = f"Implied MOIC {implied:.2f}x below 1.0x — potential loss"

    return {
        "source_id": src,
        "deal_name": name,
        "status": "active",
        "entry_year": int(entry_year) if entry_year else None,
        "years_held": round(years_held, 1) if years_held is not None else None,
        "years_remaining": round(years_remaining, 1) if years_remaining is not None else None,
        "implied_moic": implied,
        "target_moic": config.target_gross_moic,
        "vs_target": round(implied - config.target_gross_moic, 2) if implied is not None else None,
        "alert_type": alert_type,
        "message": message,
    }


def monitor_portfolio(
    deals: List[Dict[str, Any]],
    config: Optional[MonitorConfig] = None,
) -> List[Dict[str, Any]]:
    """Monitor all active (unrealized) portfolio positions.

    Returns list of status dicts sorted by urgency (critical first).
    """
    if config is None:
        config = MonitorConfig()

    results = [deal_status(d, config) for d in deals]

    # Sort: critical → at_risk → watch → on_track → realized → unknown
    order = {"critical": 0, "at_risk": 1, "watch": 2, "on_track": 3, "realized": 4, "unknown": 5}
    results.sort(key=lambda r: (order.get(r.get("alert_type") or r.get("status") or "unknown", 5), ))
    return results


def portfolio_dashboard_text(results: List[Dict[str, Any]]) -> str:
    """Formatted portfolio monitoring dashboard."""
    active = [r for r in results if r.get("status") == "active"]
    realized = [r for r in results if r.get("status") == "realized"]

    critical = [r for r in active if r.get("alert_type") == "critical"]
    at_risk = [r for r in active if r.get("alert_type") == "at_risk"]
    watch = [r for r in active if r.get("alert_type") == "watch"]
    on_track = [r for r in active if r.get("alert_type") == "on_track"]

    lines = [
        "Portfolio Monitor Dashboard",
        "=" * 70,
        f"  Active positions : {len(active)}",
        f"    On track       : {len(on_track)}",
        f"    Watch          : {len(watch)}",
        f"    At risk        : {len(at_risk)}",
        f"    Critical       : {len(critical)}",
        f"  Realized exits   : {len(realized)}",
        "-" * 70,
    ]

    if critical:
        lines.append("  [CRITICAL]")
        for r in critical:
            lines.append(f"    {r['deal_name'][:50]:<50} MOIC {r.get('implied_moic') or '—'}")

    if at_risk:
        lines.append("  [AT RISK]")
        for r in at_risk[:5]:
            lines.append(f"    {r['deal_name'][:50]:<50} MOIC {r.get('implied_moic') or '—'}")

    if watch:
        lines.append("  [WATCH]")
        for r in watch[:5]:
            lines.append(f"    {r['deal_name'][:50]:<50} MOIC {r.get('implied_moic') or '—'}")

    if realized:
        moics = [r["realized_moic"] for r in realized if r.get("realized_moic")]
        if moics:
            moics_s = sorted(moics)
            median = moics_s[len(moics_s) // 2]
            above = sum(1 for m in moics if m >= 2.0)
            below = sum(1 for m in moics if m < 1.0)
            lines.append(f"\n  Realized summary: median MOIC {median:.2f}x | "
                         f"above 2x: {above} | losses (<1x): {below}")

    lines.append("=" * 70)
    return "\n".join(lines) + "\n"


def benchmark_gap_analysis(
    deals: List[Dict[str, Any]],
    corpus_deals: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Compare each realized deal's MOIC against corpus median.

    Returns deals sorted by gap (worst underperformers first).
    """
    realized = [d for d in deals if d.get("realized_moic") is not None]
    if not realized:
        return []

    # Corpus median MOIC
    if corpus_deals:
        all_moics = [d["realized_moic"] for d in corpus_deals if d.get("realized_moic")]
    else:
        all_moics = [d["realized_moic"] for d in realized if d.get("realized_moic")]

    if not all_moics:
        return []

    all_moics_s = sorted(all_moics)
    corpus_median = all_moics_s[len(all_moics_s) // 2]

    rows = []
    for d in realized:
        moic = d["realized_moic"]
        gap = round(moic - corpus_median, 2)
        rows.append({
            "source_id": d.get("source_id"),
            "deal_name": d.get("deal_name"),
            "realized_moic": moic,
            "corpus_median_moic": round(corpus_median, 2),
            "moic_gap": gap,
            "relative_performance": "outperform" if gap > 0 else "underperform",
        })

    rows.sort(key=lambda r: r["moic_gap"])  # worst first
    return rows
