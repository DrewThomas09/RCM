"""M&A pipeline — add-on acquisition pipeline tracking.

For platform / rollup deals, the M&A pipeline is the thesis. This
module tracks:

- **Pipeline inventory** by stage (sourced / outreach / LOI / DD /
  closed).
- **Conversion ratios** — stage-to-stage conversion benchmarks.
- **Aggregate deal-year** — expected closed add-ons per year given
  the pipeline and conversion.
- **Capacity check** — whether the platform can absorb the pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional


ADDON_STAGES = (
    "sourced", "outreach", "loi", "diligence", "closed", "passed",
)


@dataclass
class AddOnTarget:
    name: str
    stage: str = "sourced"
    ebitda_m: Optional[float] = None
    price_multiple: Optional[float] = None
    sector: Optional[str] = None
    last_activity_date: Optional[date] = None
    strategic_fit: Optional[str] = None         # "high" | "moderate" | "low"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "stage": self.stage,
            "ebitda_m": self.ebitda_m,
            "price_multiple": self.price_multiple,
            "sector": self.sector,
            "last_activity_date": (self.last_activity_date.isoformat()
                                    if self.last_activity_date else None),
            "strategic_fit": self.strategic_fit,
        }


@dataclass
class PipelineSummary:
    inventory: Dict[str, int] = field(default_factory=dict)
    n_active: int = 0
    total_ebitda_pipeline: float = 0.0
    weighted_ebitda_close: float = 0.0        # expected EBITDA closed
    expected_closes_per_year: float = 0.0
    capacity_ratio: Optional[float] = None    # pipeline vs platform EBITDA
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "inventory": dict(self.inventory),
            "n_active": self.n_active,
            "total_ebitda_pipeline": self.total_ebitda_pipeline,
            "weighted_ebitda_close": self.weighted_ebitda_close,
            "expected_closes_per_year": self.expected_closes_per_year,
            "capacity_ratio": self.capacity_ratio,
            "partner_note": self.partner_note,
        }


# ── Default conversion benchmarks ──────────────────────────────────

_DEFAULT_CONVERSION = {
    "sourced": 0.30,
    "outreach": 0.40,
    "loi": 0.60,
    "diligence": 0.75,
    "closed": 1.0,
}


# ── Analyzer ───────────────────────────────────────────────────────

def _stage_inventory(targets: List[AddOnTarget]) -> Dict[str, int]:
    out: Dict[str, int] = {s: 0 for s in ADDON_STAGES}
    for t in targets:
        out[t.stage] = out.get(t.stage, 0) + 1
    return out


def analyze_pipeline(
    targets: List[AddOnTarget],
    *,
    platform_ebitda_m: Optional[float] = None,
    conversion_rates: Optional[Dict[str, float]] = None,
    expected_cycle_months: float = 9.0,
) -> PipelineSummary:
    """Summarize the add-on pipeline."""
    conv = dict(_DEFAULT_CONVERSION)
    if conversion_rates:
        conv.update(conversion_rates)

    inv = _stage_inventory(targets)
    active = [t for t in targets if t.stage not in ("closed", "passed")]
    n_active = len(active)

    total_ebitda = sum(t.ebitda_m or 0.0 for t in active)

    # Weighted expected close: each active target's EBITDA × its
    # cumulative conversion probability from its stage to close.
    weighted = 0.0
    cumulative = {}
    running = 1.0
    for stage in ("sourced", "outreach", "loi", "diligence", "closed"):
        cumulative[stage] = running
        running *= conv.get(stage, 0.0)
        # Actually for forward conversion, we multiply each stage's
        # conversion to the next. So cumulative[stage] = prob(closing | stage).
    cumulative = {}
    prob = 1.0
    for stage in ("closed", "diligence", "loi", "outreach", "sourced"):
        cumulative[stage] = prob
        # next stage up
        prob *= conv.get({"sourced": "outreach", "outreach": "loi",
                          "loi": "diligence", "diligence": "closed",
                          "closed": "closed"}[stage], 1.0)
    # Actually the cleanest way: prob(close | stage=sourced) = c(sourced→outreach) × c(outreach→loi) × c(loi→diligence) × c(diligence→closed)
    prob_close = {
        "closed": 1.0,
        "diligence": conv.get("diligence", 0.0),
        "loi": conv.get("loi", 0.0) * conv.get("diligence", 0.0),
        "outreach": conv.get("outreach", 0.0) * conv.get("loi", 0.0) * conv.get("diligence", 0.0),
        "sourced": conv.get("sourced", 0.0) * conv.get("outreach", 0.0) * conv.get("loi", 0.0) * conv.get("diligence", 0.0),
    }
    for t in active:
        weighted += (t.ebitda_m or 0.0) * prob_close.get(t.stage, 0.0)

    # Expected closes/year: n_active × avg prob × (12 / cycle_months).
    avg_prob = (sum(prob_close.get(t.stage, 0.0) for t in active) /
                max(len(active), 1))
    expected_closes_per_year = (n_active * avg_prob *
                                (12.0 / max(expected_cycle_months, 1)))

    capacity_ratio: Optional[float] = None
    if platform_ebitda_m and platform_ebitda_m > 0:
        capacity_ratio = weighted / platform_ebitda_m

    # Partner note
    if n_active == 0:
        note = "No active pipeline — restart sourcing or revisit thesis."
    elif expected_closes_per_year < 1:
        note = (f"Pipeline yields <1 close/year expected. Thesis assumes "
                "more velocity — widen top of funnel.")
    elif capacity_ratio is not None and capacity_ratio > 0.40:
        note = (f"Weighted-close EBITDA is {capacity_ratio*100:.0f}% of "
                "platform — integration capacity check required.")
    else:
        note = (f"Pipeline healthy: {expected_closes_per_year:.1f} expected "
                f"closes/yr, {n_active} active targets.")

    return PipelineSummary(
        inventory=inv,
        n_active=n_active,
        total_ebitda_pipeline=round(total_ebitda, 2),
        weighted_ebitda_close=round(weighted, 2),
        expected_closes_per_year=round(expected_closes_per_year, 2),
        capacity_ratio=(round(capacity_ratio, 4)
                        if capacity_ratio is not None else None),
        partner_note=note,
    )


def render_pipeline_markdown(summary: PipelineSummary) -> str:
    lines = [
        "# M&A pipeline",
        "",
        f"_{summary.partner_note}_",
        "",
        f"- Active targets: {summary.n_active}",
        f"- Total pipeline EBITDA: ${summary.total_ebitda_pipeline:,.0f}M",
        f"- Weighted-close EBITDA: ${summary.weighted_ebitda_close:,.0f}M",
        f"- Expected closes/yr: {summary.expected_closes_per_year:.1f}",
    ]
    if summary.capacity_ratio is not None:
        lines.append(
            f"- Capacity ratio (close EBITDA / platform): "
            f"{summary.capacity_ratio*100:.1f}%")
    lines.extend(["", "## Inventory by stage", ""])
    for stage, count in summary.inventory.items():
        lines.append(f"- {stage}: {count}")
    return "\n".join(lines)
