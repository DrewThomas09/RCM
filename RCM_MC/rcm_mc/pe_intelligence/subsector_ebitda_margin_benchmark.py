"""Subsector EBITDA margin benchmark — in-band / below / above vs. peer.

Partner statement: "Every subsector has a margin
band. Hospital at 15% is fine; ASC at 15% is soft;
dermatology at 15% is weak. When the deal's margin
is outside the band, either the business is
structurally different or the expense discipline is
broken. Tell me which one, before I price it."

Distinct from:
- `cost_line_decomposer_healthcare` — 7-line cost
  decomposition.
- `margin_of_safety` — stress buffer.
- `physician_specialty_economic_profiler` —
  per-specialty shape.

This module **benchmarks observed EBITDA margin**
vs. subsector peer band and outputs:
- band (low-high)
- observed vs. band
- % above/below band
- partner note on likely explanation
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


MARGIN_BANDS: Dict[str, Dict[str, Any]] = {
    "hospital_acute": {
        "low": 0.08, "high": 0.14,
        "note": (
            "Hospital EBITDA margin band 8-14%; "
            "compressed by labor, payer mix, and "
            "reg risk."
        ),
    },
    "ambulatory_surgery_center": {
        "low": 0.28, "high": 0.38,
        "note": (
            "ASC margin 28-38%; physician ownership "
            "structure drives upside; site-of-service "
            "tailwind."
        ),
    },
    "physician_practice_primary_care": {
        "low": 0.08, "high": 0.14,
        "note": (
            "Primary-care practice margin 8-14%; wRVU-"
            "driven comp caps margin."
        ),
    },
    "physician_practice_specialty": {
        "low": 0.15, "high": 0.25,
        "note": (
            "Specialty practice margin 15-25%; "
            "procedure mix drives outperformance."
        ),
    },
    "dental_dso": {
        "low": 0.18, "high": 0.26,
        "note": (
            "Dental DSO margin 18-26%; specialist "
            "attached services (ortho, endo, perio) "
            "add 2-4 pts."
        ),
    },
    "behavioral_outpatient": {
        "low": 0.12, "high": 0.20,
        "note": (
            "Behavioral outpatient margin 12-20%; "
            "clinician labor is 60%+ of cost."
        ),
    },
    "behavioral_residential": {
        "low": 0.15, "high": 0.25,
        "note": (
            "Residential behavioral 15-25%; facility-"
            "based with higher fixed cost but higher "
            "revenue density."
        ),
    },
    "home_health": {
        "low": 0.10, "high": 0.16,
        "note": (
            "Home health margin 10-16%; PDGM "
            "compression ongoing; referral flow "
            "matters."
        ),
    },
    "hospice": {
        "low": 0.14, "high": 0.22,
        "note": (
            "Hospice margin 14-22%; per-diem "
            "structure; length-of-stay is the lever."
        ),
    },
    "skilled_nursing_facility": {
        "low": 0.08, "high": 0.14,
        "note": (
            "SNF margin 8-14%; PDPM + labor + state "
            "Medicaid rates compress."
        ),
    },
    "dialysis": {
        "low": 0.16, "high": 0.22,
        "note": (
            "Dialysis margin 16-22%; Medicare-heavy "
            "payer mix; drug + supply are large."
        ),
    },
    "post_acute_ltach_irf": {
        "low": 0.10, "high": 0.17,
        "note": (
            "LTACH/IRF margin 10-17%; high fixed "
            "cost + CMS rate-setting risk."
        ),
    },
    "dermatology_dso": {
        "low": 0.22, "high": 0.32,
        "note": (
            "Dermatology DSO margin 22-32%; pathology "
            "attached service + Mohs drives upside."
        ),
    },
    "ophthalmology_platform": {
        "low": 0.25, "high": 0.35,
        "note": (
            "Ophthalmology margin 25-35%; ASC "
            "ancillary + retina drug margin."
        ),
    },
    "urgent_care": {
        "low": 0.12, "high": 0.20,
        "note": (
            "Urgent care margin 12-20%; commercial-"
            "heavy payer mix + high-volume model."
        ),
    },
}


@dataclass
class MarginBenchmarkInputs:
    subsector: str = "ambulatory_surgery_center"
    observed_ebitda_margin_pct: float = 0.25


@dataclass
class MarginBenchmarkReport:
    subsector: str = ""
    in_catalog: bool = False
    observed_margin_pct: float = 0.0
    band_low_pct: float = 0.0
    band_high_pct: float = 0.0
    gap_pct: float = 0.0
    verdict: str = "in_band"
    subsector_note: str = ""
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subsector": self.subsector,
            "in_catalog": self.in_catalog,
            "observed_margin_pct":
                self.observed_margin_pct,
            "band_low_pct": self.band_low_pct,
            "band_high_pct": self.band_high_pct,
            "gap_pct": self.gap_pct,
            "verdict": self.verdict,
            "subsector_note": self.subsector_note,
            "partner_note": self.partner_note,
        }


def benchmark_subsector_margin(
    inputs: MarginBenchmarkInputs,
) -> MarginBenchmarkReport:
    band = MARGIN_BANDS.get(inputs.subsector)
    if band is None:
        return MarginBenchmarkReport(
            subsector=inputs.subsector,
            in_catalog=False,
            observed_margin_pct=round(
                inputs.observed_ebitda_margin_pct, 4),
            partner_note=(
                f"Subsector '{inputs.subsector}' not in "
                "margin catalog."
            ),
        )

    lo = band["low"]
    hi = band["high"]
    obs = inputs.observed_ebitda_margin_pct

    if obs > hi:
        verdict = "above_band"
        gap = obs - hi
        note = (
            f"Margin {obs:.1%} above {inputs.subsector} "
            f"band ({lo:.1%}-{hi:.1%}). Either there's "
            "a genuine operating edge (probe what) or "
            "the base number includes one-time items "
            "or an unusual mix; QofE will surface it."
        )
    elif obs < lo:
        verdict = "below_band"
        gap = lo - obs
        note = (
            f"Margin {obs:.1%} below {inputs.subsector} "
            f"band ({lo:.1%}-{hi:.1%}). Either the "
            "business is structurally different "
            "(unusual payer mix, site profile) or "
            "expense discipline is broken. The latter "
            "is the operating-lift thesis."
        )
    else:
        verdict = "in_band"
        gap = 0.0
        note = (
            f"Margin {obs:.1%} in "
            f"{inputs.subsector} band "
            f"({lo:.1%}-{hi:.1%}). Standard shape; "
            "growth and exit multiple are the levers."
        )

    return MarginBenchmarkReport(
        subsector=inputs.subsector,
        in_catalog=True,
        observed_margin_pct=round(obs, 4),
        band_low_pct=round(lo, 4),
        band_high_pct=round(hi, 4),
        gap_pct=round(gap, 4),
        verdict=verdict,
        subsector_note=band["note"],
        partner_note=note,
    )


def render_subsector_margin_markdown(
    r: MarginBenchmarkReport,
) -> str:
    if not r.in_catalog:
        return (
            "# Subsector margin benchmark\n\n"
            f"_{r.partner_note}_\n"
        )
    lines = [
        "# Subsector EBITDA margin benchmark",
        "",
        f"_Verdict: **{r.verdict}**_ — {r.partner_note}",
        "",
        f"- Subsector: {r.subsector}",
        f"- Observed margin: {r.observed_margin_pct:.1%}",
        f"- Peer band: {r.band_low_pct:.1%}-"
        f"{r.band_high_pct:.1%}",
        f"- Gap from band: {r.gap_pct:+.1%}",
        "",
        f"**Subsector note:** {r.subsector_note}",
    ]
    return "\n".join(lines)
