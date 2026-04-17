"""Extra deal archetypes — additional pattern classifiers.

`deal_archetype.py` classifies 10 canonical healthcare-PE shapes.
This module adds specialized archetypes that don't fit the big ten:

- **de_novo_build** — platform doesn't exist yet; thesis is to build.
- **joint_venture** — sponsor + strategic (or sponsor + sponsor) JV.
- **distressed_restructuring** — sub-scale balance sheet with covenant
  breach; think DIP lending or chapter-11 emergence.
- **carveout_platform** — carve-out that becomes a platform, not a
  standalone. Captures the integration + rollup hybrid.
- **succession_transition** — family-founder seller, transition-
  focused buyout where team retention is the key risk.
- **public_to_private_tender** — tender offer to take a minority-
  holder company private. Procedural mechanics differ from LBO.
- **spinco_carveout** — reverse-morris-trust or similar.
- **late_stage_growth** — minority stake in a pre-IPO operator.

Each is classified via an :class:`ExtraArchetypeContext` with
explicit boolean signals, returning :class:`ExtraArchetypeHit` with
confidence, playbook, risks, and questions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class ExtraArchetypeContext:
    is_jv: Optional[bool] = None
    jv_partner_is_strategic: Optional[bool] = None
    jv_partner_is_sponsor: Optional[bool] = None
    is_pre_revenue: Optional[bool] = None
    has_ebitda: Optional[bool] = None
    covenant_in_breach: Optional[bool] = None
    in_bankruptcy: Optional[bool] = None
    is_family_owned: Optional[bool] = None
    founder_exiting: Optional[bool] = None
    tender_offer_planned: Optional[bool] = None
    rmt_structure: Optional[bool] = None            # reverse morris trust
    is_carveout: Optional[bool] = None
    has_rollup_thesis: Optional[bool] = None
    is_minority: Optional[bool] = None
    pre_ipo: Optional[bool] = None
    revenue_cagr: Optional[float] = None


@dataclass
class ExtraArchetypeHit:
    archetype: str
    confidence: float                              # 0..1
    signals: List[str] = field(default_factory=list)
    playbook: str = ""
    risks: List[str] = field(default_factory=list)
    questions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "archetype": self.archetype,
            "confidence": self.confidence,
            "signals": list(self.signals),
            "playbook": self.playbook,
            "risks": list(self.risks),
            "questions": list(self.questions),
        }


# ── Classifiers ─────────────────────────────────────────────────────

def _score_de_novo_build(ctx: ExtraArchetypeContext) -> Optional[ExtraArchetypeHit]:
    score = 0.0
    signals: List[str] = []
    if ctx.is_pre_revenue:
        score += 0.50
        signals.append("Pre-revenue target.")
    if ctx.has_ebitda is False:
        score += 0.30
        signals.append("No current EBITDA.")
    if score < 0.40:
        return None
    return ExtraArchetypeHit(
        archetype="de_novo_build",
        confidence=min(score, 1.0),
        signals=signals,
        playbook=(
            "Capital-first thesis. Stage gates at month-6 / month-12 / "
            "month-24. Board-level operating oversight; defer lever "
            "programs until the business exists."),
        risks=[
            "Build never reaches scale.",
            "Capital calls exceed plan.",
            "Team departs before revenue.",
        ],
        questions=[
            "What's the named build team and their prior scaled-asset experience?",
            "Where are the stage gates, and who decides kill-vs-continue?",
            "What's the exit multiple anchor pre-ramp?",
        ],
    )


def _score_joint_venture(ctx: ExtraArchetypeContext) -> Optional[ExtraArchetypeHit]:
    if not ctx.is_jv:
        return None
    score = 0.50
    signals = ["JV structure."]
    if ctx.jv_partner_is_strategic:
        score += 0.30
        signals.append("Partner is a strategic.")
    if ctx.jv_partner_is_sponsor:
        score += 0.20
        signals.append("Partner is another sponsor.")
    playbook = (
        "Governance document is the deal. Name decision rights, deadlock "
        "mechanics, and exit triggers before signing. Operational "
        "alignment flows from governance, not vice versa.")
    return ExtraArchetypeHit(
        archetype="joint_venture",
        confidence=min(score, 1.0),
        signals=signals,
        playbook=playbook,
        risks=[
            "Governance deadlock on major decisions.",
            "Misaligned investment horizons.",
            "Exit-mechanic disputes at year 3.",
        ],
        questions=[
            "Who has the casting vote on material matters?",
            "What triggers the buy-sell / Texas shootout?",
            "How do we get out if partner behavior changes?",
        ],
    )


def _score_distressed_restructuring(ctx: ExtraArchetypeContext) -> Optional[ExtraArchetypeHit]:
    score = 0.0
    signals: List[str] = []
    if ctx.covenant_in_breach:
        score += 0.50
        signals.append("Existing covenant breach.")
    if ctx.in_bankruptcy:
        score += 0.50
        signals.append("Target in bankruptcy process.")
    if score < 0.40:
        return None
    return ExtraArchetypeHit(
        archetype="distressed_restructuring",
        confidence=min(score, 1.0),
        signals=signals,
        playbook=(
            "DIP-level discipline: liquidity first, then plan of "
            "reorganization. Expect creditor-committee oversight; "
            "operating moves happen post-emergence."),
        risks=[
            "Emergency liquidity shortfalls.",
            "Senior-lender disagreement derails plan.",
            "Clinical staff exodus during uncertainty.",
        ],
        questions=[
            "What's the 13-week cash forecast?",
            "Who are the other classes of creditors?",
            "What's the post-emergence capital structure?",
        ],
    )


def _score_carveout_platform(ctx: ExtraArchetypeContext) -> Optional[ExtraArchetypeHit]:
    if not ctx.is_carveout or not ctx.has_rollup_thesis:
        return None
    return ExtraArchetypeHit(
        archetype="carveout_platform",
        confidence=0.80,
        signals=["Carve-out + roll-up thesis combined."],
        playbook=(
            "Two concurrent workstreams: parent-systems exit AND tuck-in "
            "integration. Do not underestimate the management bandwidth "
            "required for both."),
        risks=[
            "TSA overrun delays platform stand-up.",
            "Integration capacity absorbed by standalone build.",
            "Add-on pipeline stalls while platform integrates.",
        ],
        questions=[
            "Do we have two named integration officers — one for TSA, one for tuck-ins?",
            "Is the TSA cutover date before the first add-on closes?",
        ],
    )


def _score_succession_transition(ctx: ExtraArchetypeContext) -> Optional[ExtraArchetypeHit]:
    if not ctx.is_family_owned or not ctx.founder_exiting:
        return None
    return ExtraArchetypeHit(
        archetype="succession_transition",
        confidence=0.80,
        signals=["Family-owned + founder exiting."],
        playbook=(
            "Founder-transition plan is the deal. Retain key clinicians, "
            "preserve culture long enough to stabilize, then scale "
            "systems. 12-18 month transition period is realistic."),
        risks=[
            "Founder exit triggers clinician turnover.",
            "Culture-shift resentment erodes team.",
            "Institutional knowledge leaves with founder.",
        ],
        questions=[
            "Who succeeds the founder, and is the hire signed pre-close?",
            "What's the founder's post-close commitment / non-compete?",
            "Which key clinicians have retention agreements?",
        ],
    )


def _score_public_tender(ctx: ExtraArchetypeContext) -> Optional[ExtraArchetypeHit]:
    if not ctx.tender_offer_planned:
        return None
    return ExtraArchetypeHit(
        archetype="public_to_private_tender",
        confidence=0.80,
        signals=["Tender offer planned."],
        playbook=(
            "Tender mechanics dominate the first quarter: 20-business-day "
            "window, regulatory filings, minimum-tender conditions. "
            "Operating thesis kicks in only after close."),
        risks=[
            "Minimum-tender threshold not reached.",
            "Competing bid surfaces post-announcement.",
            "Regulatory delay extends the window.",
        ],
        questions=[
            "What's the required minimum-tender percentage?",
            "Who are the 5 largest shareholders, and are they aligned?",
            "What's the break-fee / reverse-break structure?",
        ],
    )


def _score_spinco_rmt(ctx: ExtraArchetypeContext) -> Optional[ExtraArchetypeHit]:
    if not ctx.rmt_structure:
        return None
    return ExtraArchetypeHit(
        archetype="spinco_carveout",
        confidence=0.85,
        signals=["Reverse-Morris-Trust / spin-co structure."],
        playbook=(
            "Tax-counsel-led deal. The structure is the alpha — operating "
            "integration follows 12-18 months post-closing. Do not "
            "underwrite lever-program timing inside the tax lock-up "
            "window."),
        risks=[
            "Tax ruling fails or is delayed.",
            "Post-close restrictions on operating moves.",
            "Integration bandwidth constrained by regulatory reqs.",
        ],
        questions=[
            "Is the IRS private-letter ruling in hand?",
            "What operating moves are restricted by the tax lock-up?",
            "Who's the lead tax counsel, and do they have RMT experience?",
        ],
    )


def _score_late_stage_growth(ctx: ExtraArchetypeContext) -> Optional[ExtraArchetypeHit]:
    if not ctx.is_minority or not ctx.pre_ipo:
        return None
    score = 0.70
    signals = ["Minority + pre-IPO."]
    if ctx.revenue_cagr is not None and ctx.revenue_cagr >= 0.20:
        score += 0.20
        signals.append(f"Revenue CAGR {ctx.revenue_cagr*100:.1f}%.")
    return ExtraArchetypeHit(
        archetype="late_stage_growth",
        confidence=min(score, 1.0),
        signals=signals,
        playbook=(
            "Governance-lite; IPO readiness is the focus. Registration "
            "rights, board observer seat, pro-rata participation. Value "
            "creation = supporting the company through its next 12-24 "
            "months."),
        risks=[
            "IPO market cools and exit is blocked.",
            "Lock-up period at IPO limits liquidity.",
            "Later rounds dilute at worse terms.",
        ],
        questions=[
            "What are the registration rights and drag-along terms?",
            "What's the IPO readiness timeline?",
            "Is there a secondary-sale path if IPO delays?",
        ],
    )


# ── Orchestrator ────────────────────────────────────────────────────

_CLASSIFIERS: List[Callable[[ExtraArchetypeContext], Optional[ExtraArchetypeHit]]] = [
    _score_de_novo_build,
    _score_joint_venture,
    _score_distressed_restructuring,
    _score_carveout_platform,
    _score_succession_transition,
    _score_public_tender,
    _score_spinco_rmt,
    _score_late_stage_growth,
]


def classify_extra_archetypes(
    ctx: ExtraArchetypeContext,
    *,
    min_confidence: float = 0.40,
) -> List[ExtraArchetypeHit]:
    """Classify into extra archetypes; return hits sorted by confidence
    desc."""
    hits: List[ExtraArchetypeHit] = []
    for fn in _CLASSIFIERS:
        try:
            h = fn(ctx)
        except Exception:
            h = None
        if h is not None and h.confidence >= min_confidence:
            hits.append(h)
    hits.sort(key=lambda h: -h.confidence)
    return hits
