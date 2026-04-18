"""Pre-IC chair brief — 4 bullets the partner walks in with.

Partner statement: "Before IC I walk the chair through 4
bullets: the thesis, where the math works, where it
doesn't, and what would change my mind. If I can't get
that on one page, the team isn't ready."

This is distinct from:

- `deal_one_liner` — the single sentence in the margin
  (too short for the chair).
- `ic_memo` — the full 60-page IC deck (too long for
  30 min before IC).
- `ic_decision_synthesizer` — the structured IC decision
  breakdown (useful but multi-dimensional).

The chair brief is exactly 4 bullets:

1. **Thesis in one sentence** — what we're buying and
   why, in plain English.
2. **Where the math works** — the 2-3 numbers that
   anchor the upside case.
3. **Where the math doesn't work** — the 2-3 numbers
   that anchor the bear case.
4. **What would change my mind** — the 3 specific things
   that, if resolved, would flip the verdict.

The brief is **verdict-bearing** — it leads with a
recommendation (invest / pass / diligence_more / reprice)
and the chair can push back on any of the 4 bullets.

The brief is synthesized from packet inputs; each bullet
pulls from the right judgment layer:

- Thesis bullet: deal_archetype + recurring EBITDA + target
  MOIC.
- Math-works bullet: in-band reasonableness checks +
  thesis chain confirmed links.
- Math-doesn't-work bullet: out-of-band checks +
  compound pattern risks + contradicted chain links.
- Change-my-mind bullet: unresolved high-risk thesis
  links + single-library pattern hits with named
  mitigants.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PreICInputs:
    deal_name: str
    thesis_sentence: str = ""
    recurring_ebitda_m: float = 0.0
    entry_multiple: float = 0.0
    target_moic: float = 0.0
    target_irr: float = 0.0
    hold_years: float = 5.0

    # From deeper judgment layers (optional; caller composes).
    recommendation: str = ""          # "invest"/"pass"/"diligence_more"/"reprice"
    math_works_numbers: List[str] = field(default_factory=list)
    math_breaks_numbers: List[str] = field(default_factory=list)
    change_my_mind_items: List[str] = field(default_factory=list)

    # Optional hooks for auto-population.
    in_band_count: int = 0
    out_of_band_count: int = 0
    compound_risks: List[str] = field(default_factory=list)
    contradicted_thesis_links: List[str] = field(default_factory=list)
    high_risk_unresolved_links: List[str] = field(default_factory=list)


@dataclass
class PreICChairBrief:
    deal_name: str
    recommendation: str
    thesis_bullet: str
    math_works_bullet: str
    math_breaks_bullet: str
    change_my_mind_bullet: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deal_name": self.deal_name,
            "recommendation": self.recommendation,
            "thesis_bullet": self.thesis_bullet,
            "math_works_bullet": self.math_works_bullet,
            "math_breaks_bullet": self.math_breaks_bullet,
            "change_my_mind_bullet": self.change_my_mind_bullet,
        }


def _default_thesis_bullet(i: PreICInputs) -> str:
    if i.thesis_sentence:
        return i.thesis_sentence
    return (
        f"{i.deal_name}: ${i.recurring_ebitda_m:,.0f}M "
        f"recurring EBITDA at {i.entry_multiple:.1f}x, "
        f"target {i.target_moic:.1f}x MOIC / "
        f"{i.target_irr*100:.0f}% IRR over "
        f"{i.hold_years:.1f}-yr hold."
    )


def _default_math_works(i: PreICInputs) -> str:
    items: List[str] = []
    if i.math_works_numbers:
        items.extend(i.math_works_numbers)
    elif i.in_band_count:
        items.append(
            f"{i.in_band_count} reasonableness check(s) "
            "in-band on peer profile."
        )
    if not items:
        items.append(
            "Seller's base case aligns with diligence — "
            "no out-of-band signals yet."
        )
    return "; ".join(items[:3]) + "."


def _default_math_breaks(i: PreICInputs) -> str:
    items: List[str] = []
    if i.math_breaks_numbers:
        items.extend(i.math_breaks_numbers)
    else:
        if i.contradicted_thesis_links:
            items.append(
                f"Thesis link(s) contradicted: "
                f"{'; '.join(i.contradicted_thesis_links[:2])}"
            )
        if i.compound_risks:
            items.append(
                f"Compound risk across {i.compound_risks[0]}"
            )
        if i.out_of_band_count:
            items.append(
                f"{i.out_of_band_count} out-of-band check(s)"
            )
    if not items:
        items.append(
            "No math-level breaks identified; bear case is "
            "execution slippage, not structural."
        )
    return "; ".join(items[:3]) + "."


def _default_change_my_mind(i: PreICInputs) -> str:
    items: List[str] = []
    if i.change_my_mind_items:
        items.extend(i.change_my_mind_items)
    else:
        # High-risk unresolved links are exactly the
        # "change my mind" set.
        for link in i.high_risk_unresolved_links[:3]:
            items.append(link)
        # Add compound-risk mitigation if present.
        for theme in i.compound_risks[:1]:
            items.append(
                f"Structural mitigation for {theme} compound risk"
            )
    if not items:
        items.append(
            "Seller indemnity or escrow that covers the "
            "top bear case"
        )
    # Cap at 3.
    trimmed = items[:3]
    return " | ".join(trimmed) + "."


def compose_chair_brief(i: PreICInputs) -> PreICChairBrief:
    # If no rec given, infer conservatively.
    rec = i.recommendation or "diligence_more"
    if not i.recommendation:
        if i.contradicted_thesis_links:
            rec = "pass"
        elif len(i.compound_risks) >= 2:
            rec = "reprice"
        elif i.in_band_count and not i.out_of_band_count \
                and not i.high_risk_unresolved_links:
            rec = "invest"
    return PreICChairBrief(
        deal_name=i.deal_name,
        recommendation=rec,
        thesis_bullet=_default_thesis_bullet(i),
        math_works_bullet=_default_math_works(i),
        math_breaks_bullet=_default_math_breaks(i),
        change_my_mind_bullet=_default_change_my_mind(i),
    )


def render_chair_brief_markdown(b: PreICChairBrief) -> str:
    lines = [
        f"# {b.deal_name} — Pre-IC chair brief",
        "",
        f"**Recommendation:** `{b.recommendation}`",
        "",
        "## 1. Thesis",
        "",
        b.thesis_bullet,
        "",
        "## 2. Where the math works",
        "",
        b.math_works_bullet,
        "",
        "## 3. Where the math doesn't work",
        "",
        b.math_breaks_bullet,
        "",
        "## 4. What would change my mind",
        "",
        b.change_my_mind_bullet,
    ]
    return "\n".join(lines)


def render_chair_brief_text(b: PreICChairBrief) -> str:
    """Plain-text one-page version for printing."""
    lines = [
        f"{b.deal_name} — Pre-IC chair brief",
        f"Recommendation: {b.recommendation.upper()}",
        "",
        f"Thesis: {b.thesis_bullet}",
        f"Math works: {b.math_works_bullet}",
        f"Math breaks: {b.math_breaks_bullet}",
        f"Change my mind: {b.change_my_mind_bullet}",
    ]
    return "\n".join(lines)
