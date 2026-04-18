"""Archetype outcome distribution — what's realistic for this shape.

Partner statement: "Before I look at the model's
projected MOIC, I want to know what archetype this is
and what the empirical distribution looks like for
that shape. Back-office consolidation plays in
healthcare median 2.0x with a top quartile of 2.6x
and a bottom quartile that loses money. Roll-up
platforms median higher but with a longer tail.
Capacity expansion is the cleanest median but the
slowest. If the deal team's model says 3.5x for a
back-office play, that's not impossible — but it's
the top decile, and the burden of proof is on us."

Distinct from:
- `vintage_return_curve` — pacing curve.
- `healthcare_thesis_archetype_recognizer` — names the
  archetype.
- `competing_deals_ranker` — ranks deals against each
  other.

This module gives **per-archetype outcome distributions**
so the partner can place the deal in the empirical
context. Distribution per archetype:

- top decile MOIC, top quartile MOIC, median, bottom
  quartile, bottom decile
- median time-to-exit
- failure rate (deals returning < 1.0×)
- typical IRR range for the archetype

### 7 archetypes with empirical distributions

These are healthcare-PE shape-level distributions —
illustrative bands drawn from public industry
discussion of buyout returns. Used as partner-mind
benchmarks, not forensic reconstructions.

1. **payer_mix_shift** — narrow median, fat right tail
   when execution lands.
2. **back_office_consolidation** — median 2.0x; needs
   integration discipline.
3. **outpatient_migration** — exposed to site-neutral;
   recent vintage means below historical.
4. **cmi_uplift** — wide distribution; RAC risk drags
   the bottom tail.
5. **rollup_platform** — longest median hold but
   highest median MOIC if multiple arb holds.
6. **cost_basis_compression** — narrow distribution;
   labor-cost reality caps upside.
7. **capacity_expansion** — slow but steady; lowest
   failure rate.

### Verdict

Place the deal team's projected MOIC in the
empirical distribution and tell the partner what
percentile that puts the underwrite in.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# Empirical outcome distributions per archetype
# (illustrative bands, not forensic reconstructions).
ARCHETYPE_DISTRIBUTIONS: Dict[str, Dict[str, Any]] = {
    "payer_mix_shift": {
        "top_decile_moic": 3.4,
        "top_quartile_moic": 2.7,
        "median_moic": 1.9,
        "bottom_quartile_moic": 1.3,
        "bottom_decile_moic": 0.7,
        "median_hold_years": 5.5,
        "failure_rate_pct": 0.20,
        "typical_irr_low": 0.10,
        "typical_irr_high": 0.22,
        "shape_note": (
            "Narrow median, fat right tail. Execution-"
            "dependent — landed in-network expansion "
            "is the differentiator."
        ),
    },
    "back_office_consolidation": {
        "top_decile_moic": 3.2,
        "top_quartile_moic": 2.6,
        "median_moic": 2.0,
        "bottom_quartile_moic": 1.4,
        "bottom_decile_moic": 0.8,
        "median_hold_years": 5.0,
        "failure_rate_pct": 0.15,
        "typical_irr_low": 0.12,
        "typical_irr_high": 0.20,
        "shape_note": (
            "Predictable when integration discipline "
            "lands; bottom tail is consolidations that "
            "stalled at site resistance."
        ),
    },
    "outpatient_migration": {
        "top_decile_moic": 3.0,
        "top_quartile_moic": 2.5,
        "median_moic": 1.8,
        "bottom_quartile_moic": 1.2,
        "bottom_decile_moic": 0.6,
        "median_hold_years": 5.0,
        "failure_rate_pct": 0.25,
        "typical_irr_low": 0.08,
        "typical_irr_high": 0.21,
        "shape_note": (
            "Recent vintages below historical due to "
            "site-neutral pressure; arbitrage compresses "
            "exit multiples."
        ),
    },
    "cmi_uplift": {
        "top_decile_moic": 3.5,
        "top_quartile_moic": 2.8,
        "median_moic": 1.9,
        "bottom_quartile_moic": 1.1,
        "bottom_decile_moic": 0.5,
        "median_hold_years": 5.0,
        "failure_rate_pct": 0.30,
        "typical_irr_low": 0.07,
        "typical_irr_high": 0.24,
        "shape_note": (
            "Wide distribution. Top tail is real "
            "documentation discipline; bottom tail is "
            "RAC recapture or aggressive coding "
            "unwinding."
        ),
    },
    "rollup_platform": {
        "top_decile_moic": 4.0,
        "top_quartile_moic": 3.0,
        "median_moic": 2.2,
        "bottom_quartile_moic": 1.4,
        "bottom_decile_moic": 0.8,
        "median_hold_years": 6.0,
        "failure_rate_pct": 0.20,
        "typical_irr_low": 0.10,
        "typical_irr_high": 0.25,
        "shape_note": (
            "Longest median hold; highest median MOIC "
            "if multiple arbitrage persists. Bottom tail "
            "is auction-fatigue compression."
        ),
    },
    "cost_basis_compression": {
        "top_decile_moic": 2.8,
        "top_quartile_moic": 2.4,
        "median_moic": 1.9,
        "bottom_quartile_moic": 1.4,
        "bottom_decile_moic": 1.0,
        "median_hold_years": 4.5,
        "failure_rate_pct": 0.10,
        "typical_irr_low": 0.13,
        "typical_irr_high": 0.19,
        "shape_note": (
            "Narrow distribution; labor cost reality "
            "caps both upside and failure rate."
        ),
    },
    "capacity_expansion": {
        "top_decile_moic": 2.6,
        "top_quartile_moic": 2.2,
        "median_moic": 1.8,
        "bottom_quartile_moic": 1.3,
        "bottom_decile_moic": 0.9,
        "median_hold_years": 6.0,
        "failure_rate_pct": 0.10,
        "typical_irr_low": 0.10,
        "typical_irr_high": 0.17,
        "shape_note": (
            "Slow but steady. De-novo ramp drags "
            "early-hold MOIC; lowest failure rate."
        ),
    },
}


@dataclass
class ArchetypeOutcomeInputs:
    archetype: str = "rollup_platform"
    deal_team_projected_moic: float = 2.5
    deal_team_projected_irr: float = 0.20
    deal_team_projected_hold_years: float = 5.0


@dataclass
class ArchetypeOutcomeReport:
    archetype: str = ""
    distribution: Dict[str, Any] = field(
        default_factory=dict)
    deal_team_projected_moic: float = 0.0
    deal_team_projected_irr: float = 0.0
    deal_team_projected_hold_years: float = 0.0
    moic_percentile_band: str = ""
    irr_in_typical_range: bool = False
    hold_years_vs_median_delta: float = 0.0
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "archetype": self.archetype,
            "distribution": self.distribution,
            "deal_team_projected_moic":
                self.deal_team_projected_moic,
            "deal_team_projected_irr":
                self.deal_team_projected_irr,
            "deal_team_projected_hold_years":
                self.deal_team_projected_hold_years,
            "moic_percentile_band":
                self.moic_percentile_band,
            "irr_in_typical_range":
                self.irr_in_typical_range,
            "hold_years_vs_median_delta":
                self.hold_years_vs_median_delta,
            "partner_note": self.partner_note,
        }


def _moic_percentile_band(
    moic: float, dist: Dict[str, Any],
) -> str:
    if moic >= dist["top_decile_moic"]:
        return "top_decile"
    if moic >= dist["top_quartile_moic"]:
        return "top_quartile"
    if moic >= dist["median_moic"]:
        return "above_median"
    if moic >= dist["bottom_quartile_moic"]:
        return "below_median"
    if moic >= dist["bottom_decile_moic"]:
        return "bottom_quartile"
    return "bottom_decile"


def predict_archetype_outcome(
    inputs: ArchetypeOutcomeInputs,
) -> ArchetypeOutcomeReport:
    dist = ARCHETYPE_DISTRIBUTIONS.get(
        inputs.archetype)
    if dist is None:
        return ArchetypeOutcomeReport(
            archetype=inputs.archetype,
            distribution={},
            deal_team_projected_moic=(
                inputs.deal_team_projected_moic),
            deal_team_projected_irr=(
                inputs.deal_team_projected_irr),
            deal_team_projected_hold_years=(
                inputs.deal_team_projected_hold_years),
            moic_percentile_band="unknown_archetype",
            irr_in_typical_range=False,
            hold_years_vs_median_delta=0.0,
            partner_note=(
                f"Archetype '{inputs.archetype}' not in "
                "catalog. Use the 7 healthcare thesis "
                "archetypes from the recognizer module."
            ),
        )

    band = _moic_percentile_band(
        inputs.deal_team_projected_moic, dist)
    irr_in_range = (
        dist["typical_irr_low"] <=
        inputs.deal_team_projected_irr <=
        dist["typical_irr_high"]
    )
    hold_delta = (
        inputs.deal_team_projected_hold_years -
        dist["median_hold_years"]
    )

    band_text = {
        "top_decile":
            "top decile (10%)",
        "top_quartile":
            "top quartile (25%)",
        "above_median":
            "above median",
        "below_median":
            "below median",
        "bottom_quartile":
            "bottom quartile (worst 25%)",
        "bottom_decile":
            "bottom decile (worst 10%)",
    }.get(band, band)

    if band == "top_decile":
        verdict = (
            f"Deal team projects "
            f"{inputs.deal_team_projected_moic:.1f}x — "
            f"top decile for {inputs.archetype}. "
            "Burden of proof is on us — what's the "
            "specific edge that puts this in the top "
            "10% of the archetype?"
        )
    elif band == "top_quartile":
        verdict = (
            f"{inputs.deal_team_projected_moic:.1f}x is "
            f"top quartile for {inputs.archetype}. "
            "Plausible if execution edges align — "
            "name them."
        )
    elif band == "above_median":
        verdict = (
            f"{inputs.deal_team_projected_moic:.1f}x is "
            f"above {inputs.archetype} median "
            f"({dist['median_moic']:.1f}x). "
            "Standard sponsor underwrite. Discuss "
            "execution differentiation."
        )
    elif band == "below_median":
        verdict = (
            f"{inputs.deal_team_projected_moic:.1f}x is "
            f"BELOW median for {inputs.archetype} — "
            "deal team's own underwrite is sub-par "
            "for the shape; either re-price or pass."
        )
    else:
        verdict = (
            f"{inputs.deal_team_projected_moic:.1f}x is "
            f"in the worst quartile/decile for "
            f"{inputs.archetype}. The archetype itself "
            "doesn't justify the equity check. Pass."
        )

    if not irr_in_range:
        verdict += (
            f" IRR {inputs.deal_team_projected_irr:.1%} "
            f"is OUTSIDE typical "
            f"{dist['typical_irr_low']:.0%}-"
            f"{dist['typical_irr_high']:.0%} range — "
            "investigate the assumption gap."
        )
    if abs(hold_delta) > 1.5:
        verdict += (
            f" Hold {inputs.deal_team_projected_hold_years:.1f}yr "
            f"vs median "
            f"{dist['median_hold_years']:.1f}yr — "
            "stress the shorter/longer assumption."
        )

    return ArchetypeOutcomeReport(
        archetype=inputs.archetype,
        distribution=dict(dist),
        deal_team_projected_moic=(
            inputs.deal_team_projected_moic),
        deal_team_projected_irr=(
            inputs.deal_team_projected_irr),
        deal_team_projected_hold_years=(
            inputs.deal_team_projected_hold_years),
        moic_percentile_band=band,
        irr_in_typical_range=irr_in_range,
        hold_years_vs_median_delta=round(
            hold_delta, 2),
        partner_note=verdict,
    )


def render_archetype_outcome_markdown(
    r: ArchetypeOutcomeReport,
) -> str:
    if not r.distribution:
        return (
            "# Archetype outcome distribution\n\n"
            f"_{r.partner_note}_\n"
        )
    d = r.distribution
    lines = [
        "# Archetype outcome distribution",
        "",
        f"_{r.partner_note}_",
        "",
        f"## {r.archetype}",
        "",
        f"_{d['shape_note']}_",
        "",
        "| Percentile | MOIC |",
        "|---|---|",
        f"| Top decile | {d['top_decile_moic']:.1f}x |",
        f"| Top quartile | {d['top_quartile_moic']:.1f}x |",
        f"| Median | {d['median_moic']:.1f}x |",
        f"| Bottom quartile | {d['bottom_quartile_moic']:.1f}x |",
        f"| Bottom decile | {d['bottom_decile_moic']:.1f}x |",
        "",
        f"- Median hold: {d['median_hold_years']:.1f} yr",
        f"- Failure rate (< 1.0×): "
        f"{d['failure_rate_pct']:.0%}",
        f"- Typical IRR range: "
        f"{d['typical_irr_low']:.0%}-{d['typical_irr_high']:.0%}",
        "",
        f"## Deal team underwrite",
        f"- MOIC: {r.deal_team_projected_moic:.2f}x → "
        f"**{r.moic_percentile_band}**",
        f"- IRR: {r.deal_team_projected_irr:.1%} → "
        f"{'in range' if r.irr_in_typical_range else 'OUTSIDE typical range'}",
        f"- Hold: {r.deal_team_projected_hold_years:.1f}yr → "
        f"{r.hold_years_vs_median_delta:+.1f}yr vs median",
    ]
    return "\n".join(lines)
