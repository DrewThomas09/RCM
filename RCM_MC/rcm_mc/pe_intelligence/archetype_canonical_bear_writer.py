"""Archetype-canonical bear case — per-shape bear that writes itself.

Partner statement: "Each archetype has its own
canonical bear case. The payer-mix shift bear is
'commercial payer says no.' The back-office
consolidation bear is 'sites refuse to migrate.' The
CMI uplift bear is 'RAC audit recovers four years.'
The bear case for an archetype isn't generic — it's
specific to the way THAT shape fails. When you hand
me a deal of archetype X, I should be able to recite
its canonical bear in 30 seconds. This module hands
me that recitation."

Distinct from:
- `bear_case_generator` — generic bear from signal set.
- `archetype_subrunners` — archetype-specific
  heuristic packs.
- `archetype_outcome_distribution_predictor` — MOIC
  band per archetype.
- `healthcare_thesis_archetype_recognizer` — names the
  archetype.

This module produces the **canonical bear** for each
of the 7 healthcare thesis archetypes:
- 3-line bear story
- specific named breakage point
- expected EBITDA hit ($M or %)
- recovery posture (recoverable / hold-extension /
  thesis-broken)
- early warning indicator (the thing to watch first)

### 7 archetype canonical bears

1. **payer_mix_shift** — commercial payer says no.
2. **back_office_consolidation** — sites refuse to
   migrate, synergies stall.
3. **outpatient_migration** — site-neutral collapses
   the arbitrage.
4. **cmi_uplift** — RAC audit recovers four years.
5. **rollup_platform** — auction fatigue compresses
   bolt-on multiples; integration debt accumulates.
6. **cost_basis_compression** — labor cuts hit
   quality metrics; payer downgrades follow.
7. **capacity_expansion** — de-novo ramp slips,
   carrying cost eats EBITDA.

### Output

Per-archetype canonical bear with:
- bear_story (3 lines)
- named_breakage_point
- expected_ebitda_hit_pct
- recovery_posture
- early_warning_indicator
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


CANONICAL_BEARS: Dict[str, Dict[str, Any]] = {
    "payer_mix_shift": {
        "bear_story": (
            "Commercial in-network strategy stalls. "
            "Payer holds out for rate concessions we "
            "can't accept. Mix stays where it is, growth "
            "thesis breaks, multiple compresses on exit."
        ),
        "named_breakage_point": (
            "Top-2 commercial payer refuses favorable "
            "in-network terms in year 2."
        ),
        "expected_ebitda_hit_pct": 0.20,
        "recovery_posture": "hold-extension",
        "early_warning_indicator": (
            "Payer correspondence frequency drops in "
            "first 6 months — silence is signal."
        ),
    },
    "back_office_consolidation": {
        "bear_story": (
            "Sites resist shared-services migration. "
            "RCM conversion stalls, denial rate climbs "
            "during transition. Synergy realization "
            "slips 12-18 months."
        ),
        "named_breakage_point": (
            "Two of the largest legacy sites insist on "
            "keeping their RCM vendor."
        ),
        "expected_ebitda_hit_pct": 0.15,
        "recovery_posture": "recoverable",
        "early_warning_indicator": (
            "Q1 site adoption rate of new RCM platform "
            "below 50% — culture not signing up."
        ),
    },
    "outpatient_migration": {
        "bear_story": (
            "OBBBA site-neutral expands faster than "
            "expected. HOPD-to-freestanding arbitrage "
            "compresses. Service-line economics flip "
            "from accretive to neutral."
        ),
        "named_breakage_point": (
            "CMS finalizes site-neutral on 4 more "
            "service lines in year 2."
        ),
        "expected_ebitda_hit_pct": 0.25,
        "recovery_posture": "thesis-broken",
        "early_warning_indicator": (
            "CMS proposed-rule comments include the "
            "exact service lines this deal depends on."
        ),
    },
    "cmi_uplift": {
        "bear_story": (
            "RAC audit retrospectively reviews 3-4 "
            "years of CMI uplift. Documentation gaps "
            "trigger recoupment + penalties. Reserve "
            "wipes out hold-period cash."
        ),
        "named_breakage_point": (
            "OIG includes the specific DRG family in "
            "audit work plan; RAC follows."
        ),
        "expected_ebitda_hit_pct": 0.30,
        "recovery_posture": "thesis-broken",
        "early_warning_indicator": (
            "Coder appeal-rate climbs without "
            "corresponding documentation improvements — "
            "aggressive coding, not real CMI lift."
        ),
    },
    "rollup_platform": {
        "bear_story": (
            "Auction fatigue raises bolt-on multiples "
            "above 8x. Multiple arbitrage compresses. "
            "Integration debt accumulates — first 4 "
            "bolt-ons land, next 6 stretch the team."
        ),
        "named_breakage_point": (
            "Bolt-on #5 closes at 9x and integration "
            "lead departs in year 2."
        ),
        "expected_ebitda_hit_pct": 0.18,
        "recovery_posture": "hold-extension",
        "early_warning_indicator": (
            "Bolt-on closing pace slips below 1 per "
            "quarter; price per bolt-on rises quarter-"
            "over-quarter."
        ),
    },
    "cost_basis_compression": {
        "bear_story": (
            "Labor reductions hit quality metrics — "
            "Star rating drops, HCAHPS scores decline. "
            "Payer quality bonuses evaporate; commercial "
            "narrows network."
        ),
        "named_breakage_point": (
            "Star rating drops 1 full point in year 2 "
            "after RIF."
        ),
        "expected_ebitda_hit_pct": 0.20,
        "recovery_posture": "recoverable",
        "early_warning_indicator": (
            "Patient-experience scores drop within 1 "
            "quarter of staffing change — quality is "
            "lagged, but PX is leading."
        ),
    },
    "capacity_expansion": {
        "bear_story": (
            "De-novo sites ramp slower than 18-month "
            "model assumption. Carrying cost (rent + "
            "labor pre-revenue) eats EBITDA. Payer "
            "credentialing delays compound the slip."
        ),
        "named_breakage_point": (
            "First 3 de-novo sites at 60% of pro-forma "
            "revenue 24 months in."
        ),
        "expected_ebitda_hit_pct": 0.15,
        "recovery_posture": "hold-extension",
        "early_warning_indicator": (
            "Patient acquisition cost (per-new-patient "
            "spend) running 2x model in first 6 months."
        ),
    },
}


@dataclass
class ArchetypeBearInputs:
    archetype: str = "rollup_platform"
    base_ebitda_m: float = 50.0


@dataclass
class CanonicalBearReport:
    archetype: str = ""
    bear_story: str = ""
    named_breakage_point: str = ""
    expected_ebitda_hit_pct: float = 0.0
    expected_ebitda_hit_m: float = 0.0
    recovery_posture: str = ""
    early_warning_indicator: str = ""
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "archetype": self.archetype,
            "bear_story": self.bear_story,
            "named_breakage_point":
                self.named_breakage_point,
            "expected_ebitda_hit_pct":
                self.expected_ebitda_hit_pct,
            "expected_ebitda_hit_m":
                self.expected_ebitda_hit_m,
            "recovery_posture": self.recovery_posture,
            "early_warning_indicator":
                self.early_warning_indicator,
            "partner_note": self.partner_note,
        }


def write_canonical_bear(
    inputs: ArchetypeBearInputs,
) -> CanonicalBearReport:
    bear = CANONICAL_BEARS.get(inputs.archetype)
    if bear is None:
        return CanonicalBearReport(
            archetype=inputs.archetype,
            partner_note=(
                f"Archetype '{inputs.archetype}' has no "
                "canonical bear in catalog. Use the 7 "
                "thesis archetypes from the recognizer."
            ),
        )

    hit_m = (
        inputs.base_ebitda_m *
        bear["expected_ebitda_hit_pct"]
    )

    if bear["recovery_posture"] == "thesis-broken":
        note = (
            f"{inputs.archetype} canonical bear: "
            f"EBITDA hit ~{bear['expected_ebitda_hit_pct']:.0%} "
            f"(${hit_m:.1f}M); thesis-broken — bear "
            "scenario is not recoverable within hold. "
            f"Watch: {bear['early_warning_indicator']}"
        )
    elif bear["recovery_posture"] == "hold-extension":
        note = (
            f"{inputs.archetype} canonical bear: "
            f"EBITDA hit ~{bear['expected_ebitda_hit_pct']:.0%} "
            f"(${hit_m:.1f}M); recoverable but extends "
            "hold by 12-18 months. Price the time-value "
            "drag into entry."
        )
    else:
        note = (
            f"{inputs.archetype} canonical bear: "
            f"EBITDA hit ~{bear['expected_ebitda_hit_pct']:.0%} "
            f"(${hit_m:.1f}M); recoverable within hold "
            "if operator addresses early. Early-warning: "
            f"{bear['early_warning_indicator']}"
        )

    return CanonicalBearReport(
        archetype=inputs.archetype,
        bear_story=bear["bear_story"],
        named_breakage_point=bear["named_breakage_point"],
        expected_ebitda_hit_pct=(
            bear["expected_ebitda_hit_pct"]),
        expected_ebitda_hit_m=round(hit_m, 2),
        recovery_posture=bear["recovery_posture"],
        early_warning_indicator=(
            bear["early_warning_indicator"]),
        partner_note=note,
    )


def render_canonical_bear_markdown(
    r: CanonicalBearReport,
) -> str:
    if not r.bear_story:
        return (
            "# Archetype canonical bear\n\n"
            f"_{r.partner_note}_\n"
        )
    lines = [
        "# Archetype canonical bear",
        "",
        f"## {r.archetype}",
        "",
        f"_{r.partner_note}_",
        "",
        f"**Bear story.** {r.bear_story}",
        "",
        f"**Named breakage point:** "
        f"{r.named_breakage_point}",
        "",
        f"**Expected EBITDA hit:** "
        f"{r.expected_ebitda_hit_pct:.0%} "
        f"(${r.expected_ebitda_hit_m:.1f}M)",
        "",
        f"**Recovery posture:** {r.recovery_posture}",
        "",
        f"**Early warning indicator:** "
        f"{r.early_warning_indicator}",
    ]
    return "\n".join(lines)
