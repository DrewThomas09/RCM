"""TAM / SAM / SOM builder — driver-tree market sizing for CDD.

Healthcare PE diligence sizes markets the way the user described for
fertility: a CHAIN of population/utilization drivers multiplied down to
revenue (total births → % via IVF → IVF deliveries → cycles per delivery
→ cycles → price per cycle), SEGMENTED (age bands with very different
utilization + success rates), funneled TAM → SAM → SOM, and PROJECTED
forward on named growth drivers (population growth, price inflation,
benefit expansion, access-barrier mitigation, supply increase,
utilization trend).

This module is the math + the bundled templates; the page renders it and
the exporters (CSV + formatted XLSX, both stdlib) ship it to the deal
team's model. Honesty rules apply: template values carry their source
labels and are explicitly illustrative defaults to be replaced with
engagement data — nothing renders as if it were the fund's own research.

Public API:
    DriverStep, Segment, GrowthDriver, TamSamModel
    fertility_ivf_template() -> TamSamModel
    blank_template() -> TamSamModel
    compute(model) -> dict   (funnel, segments, projection, audit trail)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DriverStep:
    """One link in the TAM driver chain.

    ``op`` is how this step combines with the running value:
      · "base"  — sets the starting population/value;
      · "rate"  — multiplies by a fraction (0–1), e.g. "% via IVF";
      · "mult"  — multiplies by a count, e.g. "cycles per delivery";
      · "price" — multiplies by a $ amount (the chain becomes revenue).
    """
    name: str
    value: float
    op: str = "rate"          # base | rate | mult | price
    unit: str = ""            # display unit, e.g. "births", "$/cycle"
    source: str = ""          # where the default came from — always shown


@dataclass
class Segment:
    """A demand segment (e.g. maternal age band) with its own utilization
    economics. ``share_of_volume`` fractions should sum to ~1.0 across
    segments; ``success_rate`` is segment-specific (e.g. live-birth rate
    per cycle by age band) and drives cycles-per-outcome differences."""
    name: str
    share_of_volume: float
    success_rate: Optional[float] = None
    note: str = ""


@dataclass
class GrowthDriver:
    """A named annual growth driver, composed multiplicatively in the
    projection. Keeping them separate (not one blended CAGR) is the point
    — the IC wants to see WHICH lever carries the growth."""
    name: str
    annual_pct: float          # +2.5 means +2.5%/yr
    note: str = ""


@dataclass
class TamSamModel:
    name: str
    chain: List[DriverStep] = field(default_factory=list)
    segments: List[Segment] = field(default_factory=list)
    growth_drivers: List[GrowthDriver] = field(default_factory=list)
    sam_share: float = 1.0     # fraction of TAM that is addressable
    sam_note: str = ""
    som_share: float = 0.0     # obtainable share of SAM (0 = not set)
    som_note: str = ""
    horizon_years: int = 5
    basis_note: str = ""


def fertility_ivf_template() -> TamSamModel:
    """The fertility/IVF sizing the user described, as a worked template.

    Defaults are public-data magnitudes (CDC births, CDC/SART ART data),
    labeled per-step. They are STARTING POINTS for an engagement, not the
    fund's research — the page says so and every number is editable.
    """
    return TamSamModel(
        name="Fertility · IVF clinic market",
        chain=[
            DriverStep("Total US births / yr", 3_660_000, op="base",
                       unit="births", source="CDC NVSS 2023"),
            DriverStep("% of births via IVF", 0.023, op="rate",
                       unit="of births", source="CDC ART surveillance"),
            DriverStep("Avg cycles per IVF delivery", 2.5, op="mult",
                       unit="cycles/delivery",
                       source="SART national summary (≈1/0.40 per-cycle "
                              "live-birth rate, all ages blended)"),
            DriverStep("Avg revenue per cycle", 20_000, op="price",
                       unit="$/cycle",
                       source="ASRM-cited cash-pay range $15–25K"),
        ],
        segments=[
            Segment("<35", 0.38, success_rate=0.51,
                    note="highest per-cycle live-birth rate"),
            Segment("35–37", 0.20, success_rate=0.38),
            Segment("38–40", 0.19, success_rate=0.25),
            Segment("41–42", 0.11, success_rate=0.12),
            Segment(">42", 0.12, success_rate=0.04,
                    note="most cycles per delivery — donor-egg heavy"),
        ],
        growth_drivers=[
            GrowthDriver("Utilization growth (IVF penetration)", 6.0,
                         "US penetration ~2.3% of births vs 5–10% in "
                         "Western Europe / Israel — the structural gap"),
            GrowthDriver("Price inflation", 3.0,
                         "cash-pay pricing has outrun CPI"),
            GrowthDriver("Benefit expansion", 2.0,
                         "state mandates + employer fertility benefits "
                         "(Carrot/Progyny-style) widen coverage"),
            GrowthDriver("Access-barrier mitigation", 1.5,
                         "clinic capacity, financing products, telehealth "
                         "intake reduce drop-off"),
            GrowthDriver("Population / demographic", -0.5,
                         "births declining slowly; delayed maternal age "
                         "partially offsets for IVF specifically"),
        ],
        sam_share=0.62,
        sam_note="Cash-pay + mandated/covered metros a platform can "
                 "credibly serve (excl. academic-center-locked volume)",
        som_share=0.08,
        som_note="Obtainable share for a multi-clinic platform at entry",
        horizon_years=5,
        basis_note="Template defaults from public CDC/SART/ASRM data — "
                   "replace with engagement data before IC use.",
    )


def blank_template() -> TamSamModel:
    """Empty scaffold with one of each block so the form renders."""
    return TamSamModel(
        name="Custom market",
        chain=[
            DriverStep("Addressable population", 1_000_000, op="base",
                       unit="people", source=""),
            DriverStep("Utilization rate", 0.05, op="rate",
                       unit="of population", source=""),
            DriverStep("Avg revenue per user / yr", 1_000, op="price",
                       unit="$/yr", source=""),
        ],
        segments=[],
        growth_drivers=[
            GrowthDriver("Population growth", 0.5),
            GrowthDriver("Price inflation", 3.0),
            GrowthDriver("Utilization trend", 2.0),
        ],
        sam_share=0.5,
        som_share=0.05,
        horizon_years=5,
    )


TEMPLATES = {
    "fertility_ivf": fertility_ivf_template,
    "blank": blank_template,
}


def compute(model: TamSamModel) -> Dict[str, Any]:
    """Run the driver chain → funnel → segments → projection.

    Returns an audit-friendly dict: every chain step carries its running
    value so the page (and the export) can show the partner exactly how
    the TAM was built — the chain IS the methodology.
    """
    running = 0.0
    steps: List[Dict[str, Any]] = []
    for i, st in enumerate(model.chain):
        if i == 0 or st.op == "base":
            running = st.value
        elif st.op in ("rate", "mult", "price"):
            running = running * st.value
        steps.append({
            "name": st.name, "value": st.value, "op": st.op,
            "unit": st.unit, "source": st.source,
            "running": running,
        })
    tam = running
    sam = tam * max(0.0, min(1.0, model.sam_share))
    som = sam * max(0.0, min(1.0, model.som_share))

    seg_rows: List[Dict[str, Any]] = []
    for s in model.segments:
        seg_rows.append({
            "name": s.name,
            "share_of_volume": s.share_of_volume,
            "tam_value": tam * s.share_of_volume,
            "success_rate": s.success_rate,
            "note": s.note,
        })

    # Composite growth: drivers multiply (1+g1)(1+g2)… per year — and the
    # decomposition is preserved so the IC sees which lever carries it.
    composite = 1.0
    for g in model.growth_drivers:
        composite *= (1.0 + g.annual_pct / 100.0)
    cagr_pct = (composite - 1.0) * 100.0
    projection: List[Dict[str, Any]] = []
    for yr in range(model.horizon_years + 1):
        factor = composite ** yr
        projection.append({
            "year": yr,
            "tam": tam * factor,
            "sam": sam * factor,
            "som": som * factor,
        })

    return {
        "name": model.name,
        "steps": steps,
        "tam": tam, "sam": sam, "som": som,
        "sam_share": model.sam_share, "som_share": model.som_share,
        "sam_note": model.sam_note, "som_note": model.som_note,
        "segments": seg_rows,
        "growth_drivers": [
            {"name": g.name, "annual_pct": g.annual_pct, "note": g.note}
            for g in model.growth_drivers
        ],
        "composite_cagr_pct": cagr_pct,
        "projection": projection,
        "horizon_years": model.horizon_years,
        "basis_note": model.basis_note,
    }
