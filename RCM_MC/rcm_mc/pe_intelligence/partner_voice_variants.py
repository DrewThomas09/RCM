"""Partner voice variants — the five narrators on IC.

A senior partner does not speak in one voice. They ask "what
would the skeptic say?" and "what would the operating partner
add?" before IC. This module produces the same deal through five
distinct partner voices:

- **Skeptic** — what breaks this thesis? numbers-first, no hedging.
- **Optimist** — where does this 10x? upside case, believer tone.
- **MD-numbers** — senior physician-investor, clinical + financial.
- **Operating partner** — post-close operator; "what do I own 100
  days in?"
- **LP-facing** — what a GP would write in the next LP update if
  this deal exits in line with thesis.

Input is a loose context dict (deal name, recurring EBITDA, target
MOIC/IRR, key risks, historical matches, etc.). Output is five
1-paragraph narratives in distinct voices.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


VOICES = ("skeptic", "optimist", "md_numbers", "operating_partner",
          "lp_facing")


@dataclass
class VoiceContext:
    deal_name: str
    subsector: str = "specialty_practice"
    recurring_ebitda_m: float = 0.0
    one_time_ebitda_m: float = 0.0
    target_moic: float = 2.5
    target_irr: float = 0.20
    entry_multiple: float = 11.0
    top_risks: List[str] = field(default_factory=list)
    historical_matches: List[str] = field(default_factory=list)
    key_thesis_pillars: List[str] = field(default_factory=list)
    management_score_0_100: int = 70
    pricing_power_score_0_100: int = 60


@dataclass
class VoiceParagraph:
    voice: str
    paragraph: str

    def to_dict(self) -> Dict[str, Any]:
        return {"voice": self.voice, "paragraph": self.paragraph}


@dataclass
class VoiceBundle:
    deal_name: str
    paragraphs: List[VoiceParagraph] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deal_name": self.deal_name,
            "paragraphs": [p.to_dict() for p in self.paragraphs],
        }


def _top_risk_or(default: str, risks: List[str]) -> str:
    return risks[0] if risks else default


def _skeptic(ctx: VoiceContext) -> VoiceParagraph:
    para = (
        f"The numbers. {ctx.deal_name} is priced at "
        f"{ctx.entry_multiple:.1f}x on ${ctx.recurring_ebitda_m:,.0f}M "
        "recurring EBITDA — fine if recurring is real and the exit "
        f"multiple holds. My concern: "
        f"{_top_risk_or('thesis depends on continued multiple expansion', ctx.top_risks)}. "
    )
    if ctx.historical_matches:
        para += (
            f"This deal pattern-matches "
            f"{', '.join(ctx.historical_matches)} — I want explicit "
            "mitigation, not optimism, for each. "
        )
    para += ("If IRR slips 400 bps, the narrative implodes. "
             "Pass unless we can cut entry 1x.")
    return VoiceParagraph("skeptic", para)


def _optimist(ctx: VoiceContext) -> VoiceParagraph:
    pillar = ctx.key_thesis_pillars[0] if ctx.key_thesis_pillars \
        else "operational lift"
    para = (
        f"Fundamentals. {ctx.deal_name} has ${ctx.recurring_ebitda_m:,.0f}M "
        f"recurring EBITDA and management capable of executing "
        f"{pillar}. Target {ctx.target_moic:.1f}x at "
        f"{ctx.target_irr*100:.0f}% is defensible; upside case is "
        f"{ctx.target_moic + 0.7:.1f}x if roll-up engine and pricing "
        "power compound. Bull case: strategic exit at premium. "
        "This is the best deal in the pipeline."
    )
    return VoiceParagraph("optimist", para)


def _md_numbers(ctx: VoiceContext) -> VoiceParagraph:
    para = (
        f"Clinically and financially. {ctx.subsector} at "
        f"${ctx.recurring_ebitda_m:,.0f}M — sub-scale relative to "
        "national footprints. "
        f"Management score {ctx.management_score_0_100}/100 indicates "
        f"{'a capable team' if ctx.management_score_0_100 >= 70 else 'gaps in senior ranks'}. "
        f"Pricing power {ctx.pricing_power_score_0_100}/100 "
        f"{'supports' if ctx.pricing_power_score_0_100 >= 60 else 'limits'} "
        "rate-growth assumptions. Clinically: verify that quality "
        "metrics and CMS survey history are current before IC. "
        "Financially: stress test covenant headroom at -10% EBITDA."
    )
    return VoiceParagraph("md_numbers", para)


def _operating_partner(ctx: VoiceContext) -> VoiceParagraph:
    para = (
        f"Post-close view. Day 100 on {ctx.deal_name}: the operating "
        "agenda writes itself — integrate the systems, clear the "
        "denials backlog, stand up the KPI cascade. "
    )
    if ctx.management_score_0_100 < 65:
        para += ("Management gaps mean I'm hiring in the first "
                 "90 days, not executing. ")
    if ctx.historical_matches:
        para += ("Historical pattern matches mean I want specific "
                 "mitigation playbooks in hand before close. ")
    para += ("If the thesis is clean and the team is ready, this is "
            "workable. If not, I'd rather pass than spend 5 years "
            "fixing what should have been caught in diligence.")
    return VoiceParagraph("operating_partner", para)


def _lp_facing(ctx: VoiceContext) -> VoiceParagraph:
    para = (
        f"Q+Y LP update framing. \"{ctx.deal_name} was acquired at "
        f"{ctx.entry_multiple:.1f}x ${ctx.recurring_ebitda_m:,.0f}M "
        f"recurring EBITDA. Thesis: "
    )
    if ctx.key_thesis_pillars:
        para += "; ".join(ctx.key_thesis_pillars[:3]) + ". "
    else:
        para += "platform growth + operational lift. "
    para += (
        f"Base case MOIC {ctx.target_moic:.1f}x / IRR "
        f"{ctx.target_irr*100:.0f}% over 5-year hold. Current "
        "holding posture: constructive; progress tracked against "
        "the 100-day plan and covenant headroom. Principal risks: "
    )
    if ctx.top_risks:
        para += "; ".join(ctx.top_risks[:2]) + ".\""
    else:
        para += "standard execution.\""
    return VoiceParagraph("lp_facing", para)


VOICE_BUILDERS = {
    "skeptic": _skeptic,
    "optimist": _optimist,
    "md_numbers": _md_numbers,
    "operating_partner": _operating_partner,
    "lp_facing": _lp_facing,
}


def compose_voice(voice: str, ctx: VoiceContext) -> VoiceParagraph:
    builder = VOICE_BUILDERS.get(voice)
    if builder is None:
        return VoiceParagraph(
            voice=voice,
            paragraph=f"Unknown voice: {voice!r}.",
        )
    return builder(ctx)


def compose_all_voices(ctx: VoiceContext) -> VoiceBundle:
    return VoiceBundle(
        deal_name=ctx.deal_name,
        paragraphs=[compose_voice(v, ctx) for v in VOICES],
    )


def render_voices_markdown(bundle: VoiceBundle) -> str:
    lines = [
        f"# {bundle.deal_name} — Partner voices",
        "",
    ]
    for p in bundle.paragraphs:
        lines.append(f"## {p.voice.replace('_', ' ').title()}")
        lines.append("")
        lines.append(p.paragraph)
        lines.append("")
    return "\n".join(lines)
