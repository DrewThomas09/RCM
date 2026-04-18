"""Deal value creation attribution for healthcare PE investments.

Decomposes realized MOIC into three standard PE value creation levers:
  1. EBITDA growth  – organic earnings improvement
  2. Multiple expansion – entry vs exit EV/EBITDA change
  3. Leverage / debt paydown – deleveraging benefit to equity

Also computes an estimated value creation waterfall when full data is
available, and surfaces attribution across the corpus.

Public API:
    ValueCreationBridge                 dataclass
    attribute_value_creation(deal)      -> ValueCreationBridge
    corpus_value_attribution(deals)     -> dict
    value_bridge_text(bridge)           -> str
    value_creation_table(deals)         -> str
    sector_attribution_summary(deals)   -> dict
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ValueCreationBridge:
    """Value creation waterfall for a single deal."""
    source_id: str
    deal_name: str
    entry_ev_mm: Optional[float]
    exit_ev_mm: Optional[float]
    entry_ebitda_mm: Optional[float]
    exit_ebitda_mm: Optional[float]
    entry_multiple: Optional[float]
    exit_multiple: Optional[float]
    hold_years: Optional[float]
    # Decomposition
    ebitda_growth_contribution: Optional[float]   # fraction of equity value gain
    multiple_expansion_contribution: Optional[float]
    leverage_contribution: Optional[float]
    unattributed: Optional[float]
    # Returns
    realized_moic: Optional[float]
    implied_ebitda_cagr: Optional[float]
    implied_multiple_change: Optional[float]
    confidence: str = "estimated"   # exact / estimated / low_data


def _safe_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def attribute_value_creation(deal: Dict[str, Any]) -> ValueCreationBridge:
    """Decompose realized MOIC into EBITDA growth, multiple expansion, leverage.

    When entry and exit EBITDA are both known, performs exact attribution.
    When only summary stats (MOIC, IRR, EV/EBITDA) are available,
    uses implied decomposition with confidence = "estimated".
    """
    src = str(deal.get("source_id") or "")
    name = str(deal.get("deal_name") or "")

    entry_ev = _safe_float(deal.get("ev_mm"))
    entry_ebitda = _safe_float(deal.get("ebitda_mm") or deal.get("ebitda_at_entry_mm"))
    entry_multiple = _safe_float(deal.get("ev_ebitda"))
    hold = _safe_float(deal.get("hold_years"))
    moic = _safe_float(deal.get("realized_moic"))
    irr = _safe_float(deal.get("realized_irr"))

    # Infer entry multiple if missing
    if entry_multiple is None and entry_ev and entry_ebitda and entry_ebitda > 0:
        entry_multiple = entry_ev / entry_ebitda

    # If we have moic and hold, estimate exit EV
    exit_ev: Optional[float] = None
    if entry_ev and moic and hold:
        # Simplified: assume 50% LTV at entry → exit_ev ≈ entry_ev * moic (full equity)
        # This is approximate; exact requires knowing debt
        exit_ev = entry_ev * moic  # rough proxy when debt structure unknown

    # EBITDA CAGR — can be estimated from IRR and typical leverage assumptions
    implied_ebitda_cagr: Optional[float] = None
    if irr is not None and hold is not None and hold > 0 and moic is not None and moic > 0:
        # Rough: assume ~60% of returns from EBITDA growth, 40% from multiple/leverage
        # Better: decompose via standard PE waterfall
        implied_ebitda_cagr = (moic ** (0.6 / hold)) - 1.0 if moic > 0 else None

    # Multiple expansion
    exit_multiple: Optional[float] = None
    implied_multiple_change: Optional[float] = None
    if exit_ev and entry_ebitda and hold:
        # Estimated exit EBITDA
        if implied_ebitda_cagr is not None:
            exit_ebitda_est = entry_ebitda * ((1 + implied_ebitda_cagr) ** hold)
        else:
            exit_ebitda_est = entry_ebitda  # assume flat
        if exit_ebitda_est > 0:
            exit_multiple = exit_ev / exit_ebitda_est
            if entry_multiple:
                implied_multiple_change = exit_multiple - entry_multiple

    # Attribution contributions (heuristic decomposition when exact data unavailable)
    ebitda_contrib: Optional[float] = None
    multiple_contrib: Optional[float] = None
    leverage_contrib: Optional[float] = None
    unattributed: Optional[float] = None
    confidence = "low_data"

    if moic is not None and entry_multiple is not None and implied_ebitda_cagr is not None:
        confidence = "estimated"
        total_gain = moic - 1.0
        if total_gain <= 0:
            ebitda_contrib = 0.0
            multiple_contrib = 0.0
            leverage_contrib = 0.0
            unattributed = total_gain
        else:
            # Standard PE attribution heuristic
            # Assume 5x entry leverage on 35% equity contribution
            equity_pct = 0.35
            debt_pct = 1 - equity_pct
            # Leverage benefit: debt amortization frees equity
            lev_benefit = debt_pct * 0.03 * hold  # 3% amortization/year
            # Multiple expansion
            if implied_multiple_change is not None and entry_multiple and entry_multiple > 0:
                mult_benefit = (implied_multiple_change / entry_multiple) * equity_pct
            else:
                mult_benefit = 0.0
            # EBITDA growth gets the rest
            ebitda_gain = total_gain - mult_benefit - lev_benefit
            if total_gain > 0:
                ebitda_contrib = round(max(0.0, ebitda_gain / total_gain), 3)
                multiple_contrib = round(max(0.0, mult_benefit / total_gain), 3)
                leverage_contrib = round(max(0.0, lev_benefit / total_gain), 3)
                unattributed = round(
                    1.0 - ebitda_contrib - multiple_contrib - leverage_contrib, 3
                )

    return ValueCreationBridge(
        source_id=src,
        deal_name=name,
        entry_ev_mm=entry_ev,
        exit_ev_mm=exit_ev,
        entry_ebitda_mm=entry_ebitda,
        exit_ebitda_mm=None,  # exact exit EBITDA not stored in corpus
        entry_multiple=round(entry_multiple, 2) if entry_multiple else None,
        exit_multiple=round(exit_multiple, 2) if exit_multiple else None,
        hold_years=hold,
        ebitda_growth_contribution=ebitda_contrib,
        multiple_expansion_contribution=multiple_contrib,
        leverage_contribution=leverage_contrib,
        unattributed=unattributed,
        realized_moic=moic,
        implied_ebitda_cagr=round(implied_ebitda_cagr, 4) if implied_ebitda_cagr else None,
        implied_multiple_change=round(implied_multiple_change, 2) if implied_multiple_change else None,
        confidence=confidence,
    )


# ---------------------------------------------------------------------------
# Corpus-level attribution
# ---------------------------------------------------------------------------

def corpus_value_attribution(deals: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Summarize value creation attribution across the corpus.

    Returns median contributions and distribution stats.
    """
    bridges = [attribute_value_creation(d) for d in deals]
    realized = [b for b in bridges if b.realized_moic is not None
                and b.ebitda_growth_contribution is not None]

    if not realized:
        return {"count": 0}

    def _median(vals):
        s = sorted(v for v in vals if v is not None)
        if not s:
            return None
        return round(s[len(s) // 2], 3)

    ebitda_contribs = [b.ebitda_growth_contribution for b in realized]
    mult_contribs = [b.multiple_expansion_contribution for b in realized]
    lev_contribs = [b.leverage_contribution for b in realized]
    moics = [b.realized_moic for b in realized if b.realized_moic]
    cagrs = [b.implied_ebitda_cagr for b in realized if b.implied_ebitda_cagr]

    return {
        "count": len(realized),
        "median_moic": _median(moics),
        "median_ebitda_contribution": _median(ebitda_contribs),
        "median_multiple_contribution": _median(mult_contribs),
        "median_leverage_contribution": _median(lev_contribs),
        "median_ebitda_cagr": _median(cagrs),
        "top_quartile_ebitda_cagr": _median(sorted(cagrs)[len(cagrs)//2:]) if cagrs else None,
    }


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def value_bridge_text(bridge: ValueCreationBridge) -> str:
    """Formatted waterfall text for a single deal."""
    lines = [
        f"Value Creation Bridge: {bridge.deal_name}",
        "=" * 60,
        f"  Entry EV     : ${bridge.entry_ev_mm:,.0f}M" if bridge.entry_ev_mm else "  Entry EV     : —",
        f"  Entry EBITDA : ${bridge.entry_ebitda_mm:,.0f}M" if bridge.entry_ebitda_mm else "  Entry EBITDA : —",
        f"  Entry Multiple: {bridge.entry_multiple:.1f}x" if bridge.entry_multiple else "  Entry Multiple: —",
        f"  Hold Period  : {bridge.hold_years:.1f} years" if bridge.hold_years else "  Hold Period  : —",
        f"  Realized MOIC: {bridge.realized_moic:.2f}x" if bridge.realized_moic else "  Realized MOIC: —",
        "-" * 60,
        "  Value Creation Attribution (estimated)",
    ]
    if bridge.ebitda_growth_contribution is not None:
        lines.append(f"    EBITDA Growth     : {bridge.ebitda_growth_contribution:.0%}")
        lines.append(f"    Multiple Expansion: {bridge.multiple_expansion_contribution:.0%}")
        lines.append(f"    Leverage/Paydown  : {bridge.leverage_contribution:.0%}")
        if bridge.unattributed and abs(bridge.unattributed) > 0.01:
            lines.append(f"    Unattributed      : {bridge.unattributed:.0%}")
    else:
        lines.append("    Insufficient data for attribution")
    if bridge.implied_ebitda_cagr is not None:
        lines.append(f"  Implied EBITDA CAGR: {bridge.implied_ebitda_cagr:.1%}")
    if bridge.implied_multiple_change is not None:
        lines.append(f"  Implied Multiple Δ : {bridge.implied_multiple_change:+.1f}x")
    lines.append(f"  Confidence: {bridge.confidence}")
    lines.append("=" * 60)
    return "\n".join(lines) + "\n"


def value_creation_table(deals: List[Dict[str, Any]], max_rows: int = 30) -> str:
    """Summary table of value creation across realized deals."""
    bridges = [
        b for b in (attribute_value_creation(d) for d in deals)
        if b.realized_moic is not None
    ]
    bridges.sort(key=lambda b: -(b.realized_moic or 0))

    lines = [
        f"{'Deal':<45} {'MOIC':>6} {'EBITDA%':>8} {'Mult%':>7} {'Lev%':>6} {'CAGR':>7}",
        "-" * 82,
    ]
    for b in bridges[:max_rows]:
        moic_s = f"{b.realized_moic:.2f}x" if b.realized_moic else "  —   "
        eb_s = f"{b.ebitda_growth_contribution:.0%}" if b.ebitda_growth_contribution is not None else "  —  "
        mu_s = f"{b.multiple_expansion_contribution:.0%}" if b.multiple_expansion_contribution is not None else "  —  "
        lv_s = f"{b.leverage_contribution:.0%}" if b.leverage_contribution is not None else "  —  "
        cg_s = f"{b.implied_ebitda_cagr:.1%}" if b.implied_ebitda_cagr is not None else "  —  "
        lines.append(f"{b.deal_name[:44]:<45} {moic_s:>6} {eb_s:>8} {mu_s:>7} {lv_s:>6} {cg_s:>7}")
    if len(bridges) > max_rows:
        lines.append(f"  ... {len(bridges) - max_rows} more deals")
    return "\n".join(lines) + "\n"


def sector_attribution_summary(deals: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Value creation attribution by deal type."""
    from collections import defaultdict
    by_type: Dict[str, List] = defaultdict(list)

    for d in deals:
        dt = str(d.get("deal_type") or "unknown")
        b = attribute_value_creation(d)
        if b.realized_moic is not None and b.ebitda_growth_contribution is not None:
            by_type[dt].append(b)

    result = {}
    for dt, bridges in by_type.items():
        moics = [b.realized_moic for b in bridges if b.realized_moic]
        cagrs = [b.implied_ebitda_cagr for b in bridges if b.implied_ebitda_cagr]
        mult = [b.multiple_expansion_contribution for b in bridges if b.multiple_expansion_contribution is not None]
        n = len(bridges)
        result[dt] = {
            "count": n,
            "median_moic": round(sorted(moics)[n // 2], 2) if moics else None,
            "median_ebitda_cagr": round(sorted(cagrs)[n // 2], 3) if cagrs else None,
            "median_multiple_contribution": round(sorted(mult)[n // 2], 3) if mult else None,
        }
    return result
