"""Top-level IC memo builder.

Stitches together the eight sections from the synthesis result +
the screening prediction + scenarios, then hands off to the
renderer.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .scenarios import ScenarioSet, build_scenarios


@dataclass
class ICMemo:
    """All the inputs the renderer needs."""
    deal_name: str
    deal_id: str
    sector: str
    states: List[str] = field(default_factory=list)
    revenue_mm: float = 0.0
    ebitda_mm: float = 0.0
    ebitda_margin: float = 0.0

    # Per-section payloads — all optional, all rendered defensively
    target_overview: Dict[str, Any] = field(default_factory=dict)
    thesis_bullets: List[str] = field(default_factory=list)
    comparables: Any = None
    qoe_result: Any = None
    bridge: Any = None
    scenarios: Optional[ScenarioSet] = None
    risks: List[Dict[str, Any]] = field(default_factory=list)
    regulatory_exposure: Any = None

    # Methodology references for the appendix
    methods_used: List[str] = field(default_factory=list)


def _default_thesis(
    sector: str, ebitda_mm: float, growth_rate: float,
) -> List[str]:
    """Build a baseline thesis when the partner hasn't supplied
    one. Mostly placeholder — the partner overrides in production."""
    out: List[str] = []
    if growth_rate >= 0.10:
        out.append(
            f"Above-market organic growth — "
            f"{growth_rate*100:.0f}% vs sector typical 5-7%.")
    if ebitda_mm >= 25:
        out.append(
            f"Platform-scale EBITDA (${ebitda_mm:.0f}M) opens "
            f"the secondary-PE + take-private exit windows.")
    elif ebitda_mm >= 10:
        out.append(
            f"Add-on candidate at "
            f"${ebitda_mm:.0f}M EBITDA — buy-and-build runway.")
    if sector in ("physician_group", "mso", "asc"):
        out.append(
            "Rollup sector with proven add-on multiple-arbitrage "
            "(buy at 6-7×, sell at 10-12× post-platform).")
    if not out:
        out.append(
            "Standard PE thesis: operational improvement, "
            "tuck-in M&A, multiple-expansion at exit.")
    return out


def build_ic_memo(
    *,
    deal_id: str,
    deal_name: str,
    sector: str,
    states: Optional[List[str]] = None,
    revenue_mm: float = 0.0,
    ebitda_mm: float = 0.0,
    ebitda_margin: float = 0.0,
    growth_rate: float = 0.05,
    synthesis_result: Any = None,
    screening_result: Any = None,
    custom_thesis: Optional[List[str]] = None,
    entry_multiple: float = 10.0,
    leverage_pct: float = 0.50,
    hold_years: float = 5.0,
) -> ICMemo:
    """Single-call IC memo builder.

    Pulls comparables / QoE / regulatory / bridge from the
    synthesis_result when supplied; falls back to defaults
    otherwise. Builds bull/base/bear scenarios off the
    comparable distribution if available.
    """
    states = states or []
    methods: List[str] = []

    # ── Comparables ─────────────────────────────────────────
    comps = None
    moic_p25 = moic_p50 = moic_p75 = None
    if synthesis_result and synthesis_result.comparables:
        comps = synthesis_result.comparables
        ed = comps.exit_multiple_distribution or {}
        if ed.get("p25") is not None:
            # Convert exit-multiple to MOIC by dividing by entry
            # multiple so the scenario builder gets consistent
            # input units. This matches the diligence convention.
            moic_p25 = ed.get("p25", 0) / entry_multiple
            moic_p50 = ed.get("p50", 0) / entry_multiple
            moic_p75 = ed.get("p75", 0) / entry_multiple
        methods.append(
            f"Comparable-deal selection via "
            f"{comps.method.upper()} — n={comps.n_matches}.")

    # ── QoE / Bridge ────────────────────────────────────────
    qoe_result = None
    bridge = None
    adjusted_ebitda = ebitda_mm
    if synthesis_result and synthesis_result.qoe_result:
        qoe_result = synthesis_result.qoe_result
        bridge = getattr(qoe_result, "ebitda_bridge", None)
        if bridge:
            adjusted_ebitda = bridge.adjusted_ebitda_mm
        methods.append(
            "QoE auto-flagger ran 9 detectors + isolation forest "
            "+ time-series z-score line-item anomaly detection.")

    # ── Scenarios ───────────────────────────────────────────
    scenarios = build_scenarios(
        entry_ebitda_mm=adjusted_ebitda,
        entry_multiple=entry_multiple,
        leverage_pct=leverage_pct,
        hold_years=hold_years,
        moic_p25=moic_p25,
        moic_p50=moic_p50,
        moic_p75=moic_p75,
    )
    methods.append(
        f"Bull/base/bear scenarios anchored to comparable-deal "
        f"MOIC quartiles (or healthcare-PE typical defaults).")

    # ── Risks ───────────────────────────────────────────────
    risks: List[Dict[str, Any]] = []
    if synthesis_result and synthesis_result.regulatory_exposure:
        exp = synthesis_result.regulatory_exposure.get(
            "exposure")
        if exp and exp.topic_exposures:
            for t in exp.topic_exposures[:5]:
                risks.append({
                    "title": t.label,
                    "ebitda_at_risk_mm": t.ebitda_at_risk_mm,
                    "n_documents": t.n_documents,
                    "category": "regulatory",
                })
            methods.append(
                "Regulatory exposure scored against TF-IDF + LDA "
                "topic discovery on the partner's regulatory "
                "corpus (FTC noncompete, state CON/CPOM, OPPS "
                "site-neutral, V28 cliff anchors).")

    if screening_result and screening_result.risk_factors:
        for rf in screening_result.risk_factors:
            risks.append({
                "title": rf,
                "category": "screening",
            })

    # Target overview — convert inputs into a flat dict for the
    # renderer.
    target_overview = {
        "revenue_mm": round(revenue_mm, 2),
        "ebitda_mm": round(ebitda_mm, 2),
        "adjusted_ebitda_mm": round(adjusted_ebitda, 2),
        "ebitda_margin": round(ebitda_margin, 4),
        "sector": sector,
        "states": states,
        "growth_rate": round(growth_rate, 4),
    }

    thesis = (custom_thesis
              if custom_thesis is not None
              else _default_thesis(sector, ebitda_mm, growth_rate))

    return ICMemo(
        deal_name=deal_name,
        deal_id=deal_id,
        sector=sector,
        states=states,
        revenue_mm=revenue_mm,
        ebitda_mm=ebitda_mm,
        ebitda_margin=ebitda_margin,
        target_overview=target_overview,
        thesis_bullets=thesis,
        comparables=comps,
        qoe_result=qoe_result,
        bridge=bridge,
        scenarios=scenarios,
        risks=risks,
        regulatory_exposure=(
            synthesis_result.regulatory_exposure
            if synthesis_result else None),
        methods_used=methods,
    )
