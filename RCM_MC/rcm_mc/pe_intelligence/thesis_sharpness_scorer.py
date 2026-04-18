"""Thesis sharpness scorer — is the thesis focused or diffuse?

Partner statement: "If I can't state the thesis in one
sentence with a number and a date, I don't understand the
deal. Diffuse theses don't get done — they get excused
when the deal fails."

Distinct from:

- `thesis_coherence_check` — internal consistency across
  pillars.
- `thesis_validator` — validation against packet.
- `thesis_implications_chain` — downstream links from
  the thesis.

This module scores a proposed thesis on **sharpness** —
how specific, quantified, and focused it is. A sharp
thesis survives IC; a diffuse one doesn't.

### Scoring dimensions (7)

1. **one_sentence_statable** — can the thesis be stated
   in a single sentence? (boolean)
2. **named_primary_lever** — is the *one* primary lever
   named? (boolean)
3. **quantified_uplift** — is the EBITDA uplift number
   specific (not a range)? (boolean)
4. **geography_specific** — state/MSA named if relevant?
   (boolean)
5. **timeline_bounded** — is the hold + milestone cadence
   defined? (boolean)
6. **secondary_pillars_lte_2** — ≤ 2 secondary pillars
   (more dilutes the thesis)? (boolean)
7. **anti_thesis_named** — has the partner explicitly
   named the *pass* signal / what would make us walk?
   (boolean)

### Sharpness ladder

- **7/7** = `razor` — IC-ready.
- **5-6/7** = `sharp` — sharpen the remaining dimension.
- **3-4/7** = `diffuse` — cannot advance to IC until
  sharpened.
- **0-2/7** = `incoherent` — back to thesis drafting.

### Why this module matters

Partners see 100 decks / yr. The ones that close have 1
primary lever quantified with geography + timeline + anti-
thesis. This module is a partner's 60-second sharpness
gate before team commits diligence dollars.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ThesisSharpnessInputs:
    thesis_statement: str = ""
    primary_lever: str = ""                # single named lever
    quantified_uplift_bps: Optional[int] = None  # e.g., 300 bps
    quantified_uplift_pct: Optional[float] = None  # e.g., 0.08
    geography_scope: str = ""              # e.g., "Texas GI practices"
    hold_years: Optional[float] = None
    milestone_cadence: str = ""            # e.g., "quarterly KPI"
    secondary_pillars: List[str] = field(default_factory=list)
    anti_thesis_pass_signal: str = ""      # what would make us walk


@dataclass
class SharpnessDimension:
    name: str
    passed: bool
    partner_comment: str


@dataclass
class ThesisSharpnessReport:
    score: int                             # 0-7
    ladder_tier: str                       # razor/sharp/diffuse/incoherent
    dimensions: List[SharpnessDimension] = field(default_factory=list)
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "ladder_tier": self.ladder_tier,
            "dimensions": [
                {"name": d.name, "passed": d.passed,
                 "partner_comment": d.partner_comment}
                for d in self.dimensions
            ],
            "partner_note": self.partner_note,
        }


def _count_sentences(s: str) -> int:
    # Simple: count terminators that break sentences.
    if not s.strip():
        return 0
    return sum(s.count(c) for c in ".!?") or 1


def score_thesis_sharpness(
    inputs: ThesisSharpnessInputs,
) -> ThesisSharpnessReport:
    dims: List[SharpnessDimension] = []

    # 1. One-sentence statable.
    sentences = _count_sentences(inputs.thesis_statement)
    one_sentence = (
        sentences <= 1
        and bool(inputs.thesis_statement.strip())
    )
    dims.append(SharpnessDimension(
        name="one_sentence_statable",
        passed=one_sentence,
        partner_comment=(
            "Thesis fits a single sentence."
            if one_sentence else
            "Thesis spans multiple sentences — partner "
            "wants one declarative line."
        ),
    ))

    # 2. Named primary lever.
    has_lever = bool(inputs.primary_lever.strip())
    dims.append(SharpnessDimension(
        name="named_primary_lever",
        passed=has_lever,
        partner_comment=(
            f"Primary lever: '{inputs.primary_lever}'."
            if has_lever else
            "No single primary lever named — partner asks "
            "'what's the ONE thing?'"
        ),
    ))

    # 3. Quantified uplift.
    has_uplift = (
        inputs.quantified_uplift_bps is not None
        or inputs.quantified_uplift_pct is not None
    )
    dims.append(SharpnessDimension(
        name="quantified_uplift",
        passed=has_uplift,
        partner_comment=(
            "Specific uplift number provided."
            if has_uplift else
            "Uplift not quantified — partner wants a number, "
            "not a range."
        ),
    ))

    # 4. Geography specific.
    has_geo = bool(inputs.geography_scope.strip())
    dims.append(SharpnessDimension(
        name="geography_specific",
        passed=has_geo,
        partner_comment=(
            f"Geography: '{inputs.geography_scope}'."
            if has_geo else
            "No geography named — vague market = vague "
            "thesis."
        ),
    ))

    # 5. Timeline bounded.
    has_timeline = (
        inputs.hold_years is not None
        and bool(inputs.milestone_cadence.strip())
    )
    dims.append(SharpnessDimension(
        name="timeline_bounded",
        passed=has_timeline,
        partner_comment=(
            f"Hold {inputs.hold_years:.1f} yrs, "
            f"{inputs.milestone_cadence}."
            if has_timeline else
            "Timeline + milestone cadence not defined."
        ),
    ))

    # 6. Secondary pillars ≤ 2.
    pillar_count = len(inputs.secondary_pillars)
    pillars_focused = pillar_count <= 2
    dims.append(SharpnessDimension(
        name="secondary_pillars_lte_2",
        passed=pillars_focused,
        partner_comment=(
            f"{pillar_count} secondary pillar(s) — focused."
            if pillars_focused else
            f"{pillar_count} secondary pillars — diluted; "
            "partner wants ≤ 2."
        ),
    ))

    # 7. Anti-thesis named.
    has_antithesis = bool(inputs.anti_thesis_pass_signal.strip())
    dims.append(SharpnessDimension(
        name="anti_thesis_named",
        passed=has_antithesis,
        partner_comment=(
            f"Anti-thesis: '{inputs.anti_thesis_pass_signal}'."
            if has_antithesis else
            "No anti-thesis / pass signal named — partner "
            "demands 'what would make us walk?'"
        ),
    ))

    score = sum(1 for d in dims if d.passed)
    if score == 7:
        tier = "razor"
        note = (
            "Thesis is razor-sharp. IC-ready on this "
            "dimension; proceed to diligence."
        )
    elif score >= 5:
        tier = "sharp"
        missing = [d.name for d in dims if not d.passed]
        note = (
            f"Thesis sharp ({score}/7). Sharpen "
            f"{', '.join(missing)} before IC."
        )
    elif score >= 3:
        tier = "diffuse"
        note = (
            f"Thesis diffuse ({score}/7). Cannot advance "
            "to IC until sharpened — team returns to "
            "drafting."
        )
    else:
        tier = "incoherent"
        note = (
            f"Thesis incoherent ({score}/7). Back to "
            "thesis-formation work; not ready for IC "
            "discussion."
        )

    return ThesisSharpnessReport(
        score=score,
        ladder_tier=tier,
        dimensions=dims,
        partner_note=note,
    )


def render_thesis_sharpness_markdown(
    r: ThesisSharpnessReport,
) -> str:
    lines = [
        "# Thesis sharpness",
        "",
        f"**Tier:** `{r.ladder_tier}` ({r.score}/7)",
        "",
        f"_{r.partner_note}_",
        "",
        "| Dimension | Passed | Partner comment |",
        "|---|---|---|",
    ]
    for d in r.dimensions:
        check = "✓" if d.passed else "✗"
        lines.append(
            f"| {d.name} | {check} | {d.partner_comment} |"
        )
    return "\n".join(lines)
