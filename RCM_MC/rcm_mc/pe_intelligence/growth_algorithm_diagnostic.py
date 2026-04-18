"""Growth algorithm diagnostic — decompose revenue growth.

Sellers pitch "20% revenue growth." Partners decompose:

- **Organic growth** = price + volume + mix.
- **Acquisition growth** = from bolt-ons closed in period.
- **Price growth** — rate/unit increases.
- **Volume growth** — unit increases (visits, admits, cases).
- **Mix shift** — shift toward higher- or lower-revenue services.

A platform with 18% total growth but only 4% organic is a very
different underwrite than one with 12% organic + 6% acquisition.

This module reconciles total growth = organic + acquisition,
and organic = price + volume + mix, and produces a partner note
on the sustainability of the growth algorithm.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class GrowthInputs:
    prior_revenue_m: float
    current_revenue_m: float
    acquisition_revenue_m: float = 0.0    # revenue from deals closed in period
    price_growth_pct: float = 0.0         # weighted avg rate/unit change
    volume_growth_pct: float = 0.0        # weighted avg volume change
    # mix shift inferred if not provided
    mix_growth_pct: Optional[float] = None


@dataclass
class GrowthComponent:
    name: str
    growth_pct: float                     # contribution in pp
    revenue_impact_m: float
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "growth_pct": self.growth_pct,
            "revenue_impact_m": self.revenue_impact_m,
            "description": self.description,
        }


@dataclass
class GrowthDiagnostic:
    total_growth_pct: float
    organic_growth_pct: float
    acquisition_growth_pct: float
    components: List[GrowthComponent] = field(default_factory=list)
    quality_score_0_100: int = 0
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_growth_pct": self.total_growth_pct,
            "organic_growth_pct": self.organic_growth_pct,
            "acquisition_growth_pct": self.acquisition_growth_pct,
            "components": [c.to_dict() for c in self.components],
            "quality_score_0_100": self.quality_score_0_100,
            "partner_note": self.partner_note,
        }


def diagnose_growth(inputs: GrowthInputs) -> GrowthDiagnostic:
    prior = max(0.01, inputs.prior_revenue_m)
    total_growth = (inputs.current_revenue_m - prior) / prior
    acquisition_pct = inputs.acquisition_revenue_m / prior
    organic_pct = total_growth - acquisition_pct

    # Reconcile mix if not provided.
    if inputs.mix_growth_pct is None:
        mix_pct = organic_pct - inputs.price_growth_pct - inputs.volume_growth_pct
    else:
        mix_pct = inputs.mix_growth_pct

    components = [
        GrowthComponent(
            name="price",
            growth_pct=round(inputs.price_growth_pct * 100, 2),
            revenue_impact_m=round(inputs.price_growth_pct * prior, 2),
            description=("Rate / price per unit changes — reimbursement "
                         "updates, chargemaster increases."),
        ),
        GrowthComponent(
            name="volume",
            growth_pct=round(inputs.volume_growth_pct * 100, 2),
            revenue_impact_m=round(inputs.volume_growth_pct * prior, 2),
            description=("Unit growth — more visits, admits, cases, "
                         "members."),
        ),
        GrowthComponent(
            name="mix",
            growth_pct=round(mix_pct * 100, 2),
            revenue_impact_m=round(mix_pct * prior, 2),
            description=("Service / payer / acuity mix shift — higher-"
                         "reimbursement services replacing lower."),
        ),
        GrowthComponent(
            name="acquisition",
            growth_pct=round(acquisition_pct * 100, 2),
            revenue_impact_m=round(inputs.acquisition_revenue_m, 2),
            description=("Inorganic — revenue added via bolt-ons closed "
                         "in period."),
        ),
    ]

    # Quality score: weight organic (especially volume) higher.
    # 1pp volume > 1pp price > 1pp mix > 1pp acquisition.
    score = 50
    score += int(round(inputs.volume_growth_pct * 100 * 4))
    score += int(round(inputs.price_growth_pct * 100 * 2.5))
    score += int(round(mix_pct * 100 * 1.5))
    score += int(round(acquisition_pct * 100 * 1.0))
    score = max(0, min(100, score))

    # Partner note.
    if organic_pct < 0:
        note = ("Organic revenue is contracting — acquisitions are "
                "masking core-business decline. Material diligence concern.")
    elif acquisition_pct > 0 and acquisition_pct / max(0.001, total_growth) >= 0.60:
        note = (f"{total_growth*100:.1f}% total growth but "
                f"{acquisition_pct/total_growth*100:.0f}% is acquisition-"
                "driven. Organic story is weak — underwrite the roll-up "
                "engine, not the asset.")
    elif organic_pct >= 0.10 and inputs.volume_growth_pct >= 0.05:
        note = (f"Strong organic profile: {organic_pct*100:.1f}% organic "
                f"with volume leading ({inputs.volume_growth_pct*100:.1f}% "
                "volume). Defensible growth algorithm.")
    elif (organic_pct >= 0.05
          and inputs.price_growth_pct >= 0.05
          and inputs.volume_growth_pct < 0.02):
        note = (f"Price-led growth: {inputs.price_growth_pct*100:.1f}% "
                "price and thin volume. Stress test pricing durability.")
    elif organic_pct < 0:
        note = ("Organic revenue is contracting — acquisitions are "
                "masking core-business decline. Material diligence concern.")
    else:
        note = (f"Standard growth mix: organic {organic_pct*100:.1f}%, "
                f"acquisition {acquisition_pct*100:.1f}%.")

    return GrowthDiagnostic(
        total_growth_pct=round(total_growth * 100, 2),
        organic_growth_pct=round(organic_pct * 100, 2),
        acquisition_growth_pct=round(acquisition_pct * 100, 2),
        components=components,
        quality_score_0_100=score,
        partner_note=note,
    )


def render_growth_markdown(diag: GrowthDiagnostic) -> str:
    lines = [
        "# Growth algorithm diagnostic",
        "",
        f"_{diag.partner_note}_",
        "",
        f"- Total growth: {diag.total_growth_pct:.1f}%",
        f"- Organic: {diag.organic_growth_pct:.1f}%",
        f"- Acquisition: {diag.acquisition_growth_pct:.1f}%",
        f"- Quality score: {diag.quality_score_0_100}/100",
        "",
        "| Component | Growth % | Revenue $M |",
        "|---|---:|---:|",
    ]
    for c in diag.components:
        lines.append(f"| {c.name} | {c.growth_pct:+.1f}% | "
                     f"${c.revenue_impact_m:,.2f}M |")
    return "\n".join(lines)
