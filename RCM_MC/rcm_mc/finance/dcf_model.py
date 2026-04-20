"""Discounted Cash Flow model for hospital deal valuation.

Builds a 5-10 year DCF projection from deal profile data +
value creation assumptions. Outputs annual cash flows, terminal
value, enterprise value, and equity value with sensitivity tables.

Designed for PE associates running diligence — every assumption
is explicit and auditable.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class DCFAssumptions:
    """All inputs to the DCF model — nothing hidden."""
    revenue_base: float = 0.0
    revenue_growth_rates: List[float] = field(default_factory=lambda: [0.03] * 5)
    ebitda_margin_base: float = 0.15
    ebitda_margin_improvement_bps: List[float] = field(default_factory=lambda: [50, 100, 100, 50, 25])
    capex_pct_revenue: float = 0.04
    nwc_pct_revenue: float = 0.08
    tax_rate: float = 0.25
    wacc: float = 0.10
    terminal_growth: float = 0.025
    projection_years: int = 5

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DCFYear:
    """One year of the projection."""
    year: int
    revenue: float
    ebitda: float
    ebitda_margin: float
    ebit: float
    taxes: float
    nopat: float
    capex: float
    delta_nwc: float
    fcf: float
    pv_fcf: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        d = {k: round(v, 2) if isinstance(v, float) else v
             for k, v in asdict(self).items()}
        # UI templates (ui/models_page.py) read "free_cash_flow", not
        # "fcf" — expose both so existing callers that use the short
        # name keep working. Cheaper than renaming every reference.
        d["free_cash_flow"] = d["fcf"]
        return d


@dataclass
class DCFResult:
    """Full DCF output."""
    assumptions: DCFAssumptions
    projections: List[DCFYear]
    terminal_value: float
    pv_cash_flows: float
    pv_terminal: float
    enterprise_value: float
    sensitivity: Dict[str, List[Dict[str, float]]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "assumptions": self.assumptions.to_dict(),
            "projections": [y.to_dict() for y in self.projections],
            "terminal_value": round(self.terminal_value, 2),
            "pv_cash_flows": round(self.pv_cash_flows, 2),
            "pv_terminal": round(self.pv_terminal, 2),
            "enterprise_value": round(self.enterprise_value, 2),
            "sensitivity": self.sensitivity,
        }


def build_dcf(
    assumptions: Optional[DCFAssumptions] = None,
    **overrides: Any,
) -> DCFResult:
    """Build a full DCF model from assumptions.

    Pass overrides as kwargs to customize:
        build_dcf(revenue_base=400e6, wacc=0.12)
    """
    a = assumptions or DCFAssumptions()
    for k, v in overrides.items():
        if hasattr(a, k):
            setattr(a, k, v)

    n = a.projection_years
    growth = a.revenue_growth_rates[:n]
    while len(growth) < n:
        growth.append(growth[-1] if growth else 0.03)
    margin_bps = a.ebitda_margin_improvement_bps[:n]
    while len(margin_bps) < n:
        margin_bps.append(0)

    projections: List[DCFYear] = []
    prev_revenue = a.revenue_base
    prev_nwc = a.revenue_base * a.nwc_pct_revenue
    margin = a.ebitda_margin_base
    da_pct = 0.025

    for i in range(n):
        revenue = prev_revenue * (1 + growth[i])
        margin = margin + margin_bps[i] / 10000
        ebitda = revenue * margin
        da = revenue * da_pct
        ebit = ebitda - da
        taxes = max(ebit * a.tax_rate, 0)
        nopat = ebit - taxes
        capex = revenue * a.capex_pct_revenue
        nwc = revenue * a.nwc_pct_revenue
        delta_nwc = nwc - prev_nwc
        fcf = nopat + da - capex - delta_nwc

        projections.append(DCFYear(
            year=i + 1,
            revenue=revenue,
            ebitda=ebitda,
            ebitda_margin=margin,
            ebit=ebit,
            taxes=taxes,
            nopat=nopat,
            capex=capex,
            delta_nwc=delta_nwc,
            fcf=fcf,
        ))
        prev_revenue = revenue
        prev_nwc = nwc

    # Populate per-year present value so the UI can render a PV(FCF)
    # column. Aggregate pv_cash_flows below is the sum of these.
    for y in projections:
        y.pv_fcf = y.fcf / (1 + a.wacc) ** y.year

    last_fcf = projections[-1].fcf
    terminal_value = last_fcf * (1 + a.terminal_growth) / (a.wacc - a.terminal_growth)

    pv_cfs = sum(y.pv_fcf for y in projections)
    pv_tv = terminal_value / (1 + a.wacc) ** n
    ev = pv_cfs + pv_tv

    sensitivity = _build_sensitivity(a, projections, terminal_value)

    return DCFResult(
        assumptions=a,
        projections=projections,
        terminal_value=terminal_value,
        pv_cash_flows=pv_cfs,
        pv_terminal=pv_tv,
        enterprise_value=ev,
        sensitivity=sensitivity,
    )


def _build_sensitivity(
    a: DCFAssumptions,
    projections: List[DCFYear],
    terminal_value: float,
) -> Dict[str, List[Dict[str, float]]]:
    """WACC x Terminal Growth sensitivity matrix."""
    n = a.projection_years
    last_fcf = projections[-1].fcf
    results = []
    for wacc in [0.08, 0.09, 0.10, 0.11, 0.12, 0.13, 0.14]:
        for tg in [0.015, 0.020, 0.025, 0.030, 0.035]:
            if wacc <= tg:
                continue
            tv = last_fcf * (1 + tg) / (wacc - tg)
            pv_cfs = sum(y.fcf / (1 + wacc) ** y.year for y in projections)
            pv_tv = tv / (1 + wacc) ** n
            results.append({
                "wacc": round(wacc, 3),
                "terminal_growth": round(tg, 3),
                "enterprise_value": round(pv_cfs + pv_tv, 2),
            })
    return {"wacc_vs_terminal_growth": results}


def build_dcf_from_deal(profile: Dict[str, Any]) -> DCFResult:
    """Convenience: build DCF directly from a deal profile dict.

    Precedence for margin: current_ebitda/revenue > ebitda_margin field >
    industry default (12%). Negative / implausible margins (>50% or <-50%)
    are clamped so the DCF projection stays sane; callers should surface
    data-quality warnings elsewhere.
    """
    revenue = float(profile.get("net_revenue") or profile.get("revenue") or 0)
    ebitda_raw = profile.get("current_ebitda")
    ebitda = float(ebitda_raw) if ebitda_raw not in (None, "") else 0.0

    if revenue > 0 and ebitda != 0:
        margin = ebitda / revenue
    elif profile.get("ebitda_margin") not in (None, ""):
        try:
            margin = float(profile["ebitda_margin"])
        except (TypeError, ValueError):
            margin = 0.12
    else:
        margin = 0.12

    # Clamp to plausible range for a going-concern hospital
    margin = max(-0.50, min(0.50, margin))

    return build_dcf(
        revenue_base=revenue,
        ebitda_margin_base=margin,
    )
