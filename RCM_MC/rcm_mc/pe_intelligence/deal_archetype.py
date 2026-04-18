"""Deal archetype classifier.

Partners recognize deals by their *shape*, not just their numbers.
A platform-plus-tuck-in roll-up has different risks than a take-
private, which has different risks than an operational turnaround.
Each archetype has its own playbook — and its own failure modes.

This module classifies a deal into one or more archetypes based on
signal patterns in the packet / context, and emits archetype-specific
commentary a partner can use directly.

Archetypes supported:

- ``platform_rollup`` — sponsor buys a platform, adds tuck-ins.
- ``take_private`` — sponsor takes a public company private.
- ``carve_out`` — sponsor buys a division out of a larger parent.
- ``turnaround`` — target is distressed / sub-peer margin, thesis is
  operating recovery.
- ``buy_and_build`` — organic + M&A growth, not a classical roll-up.
- ``continuation`` — existing sponsor rolls to a continuation fund.
- ``gp_led_secondary`` — GP-led secondary sale.
- ``pipe`` — minority investment into a public.
- ``operating_lift`` — classical LBO with RCM / ops lever as the alpha.
- ``growth_equity`` — non-control minority growth investment.

An archetype match is not binary — a deal can hit multiple archetypes
(e.g., a roll-up that is also a carve-out of a parent's health
division). :func:`classify_archetypes` returns the ranked list.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ArchetypeHit:
    archetype: str
    confidence: float               # 0.0–1.0
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


@dataclass
class ArchetypeContext:
    """Signal bag for classifying a deal.

    Most fields are optional — the classifier does the best it can
    with what's populated. Callers should populate what they know
    from the deal memo; unknown fields leave the related archetype
    at baseline confidence.
    """
    # Structural signals
    is_public_target: Optional[bool] = None
    is_carveout: Optional[bool] = None
    seller_is_strategic: Optional[bool] = None
    seller_is_sponsor: Optional[bool] = None
    platform_or_addon: Optional[str] = None    # "platform" | "addon" | "neither"
    number_of_addons_planned: Optional[int] = None
    is_continuation_vehicle: Optional[bool] = None
    is_minority: Optional[bool] = None
    ownership_pct: Optional[float] = None

    # Financial signals
    current_ebitda_margin: Optional[float] = None
    peer_median_margin: Optional[float] = None
    debt_to_ebitda: Optional[float] = None
    is_distressed: Optional[bool] = None
    revenue_growth_pct: Optional[float] = None
    ebitda_growth_pct: Optional[float] = None

    # Thesis signals
    has_rcm_thesis: Optional[bool] = None
    has_rollup_thesis: Optional[bool] = None
    has_turnaround_thesis: Optional[bool] = None
    plans_go_private: Optional[bool] = None

    # Metadata
    hospital_type: Optional[str] = None


# ── Classifiers ──────────────────────────────────────────────────────

def _score_platform_rollup(ctx: ArchetypeContext) -> ArchetypeHit:
    signals: List[str] = []
    score = 0.0
    if ctx.platform_or_addon == "platform":
        score += 0.40
        signals.append("Deal tagged as platform.")
    if ctx.number_of_addons_planned and ctx.number_of_addons_planned >= 3:
        score += 0.30
        signals.append(f"{ctx.number_of_addons_planned}+ add-ons planned.")
    if ctx.has_rollup_thesis:
        score += 0.30
        signals.append("Thesis explicitly rollup.")
    if ctx.ebitda_growth_pct and ctx.ebitda_growth_pct >= 0.20:
        score += 0.10
        signals.append("EBITDA growth plan >20%/yr (rollup-consistent).")
    return ArchetypeHit(
        archetype="platform_rollup",
        confidence=min(score, 1.0),
        signals=signals,
        playbook=(
            "Standardize back-office early, centralize RCM, hunt for "
            "tuck-ins with sub-scale overhead. Integration risk is the "
            "primary failure mode."
        ),
        risks=[
            "Integration delays eat multiple expansion.",
            "Key-person dependency at the platform level.",
            "Multiple arbitrage compression if the buy-side heats up.",
        ],
        questions=[
            "What's the tuck-in pipeline size and who's sourcing it?",
            "Who owns integration, and what's the 100-day plan?",
            "Are we paying at a multiple we can exit from, even if rollup fails?",
        ],
    )


def _score_take_private(ctx: ArchetypeContext) -> ArchetypeHit:
    signals: List[str] = []
    score = 0.0
    if ctx.is_public_target:
        score += 0.60
        signals.append("Target is a public company.")
    if ctx.plans_go_private:
        score += 0.30
        signals.append("Explicit take-private intent.")
    if ctx.debt_to_ebitda and ctx.debt_to_ebitda >= 5.0:
        score += 0.10
        signals.append("Leverage ≥ 5.0x — LBO-consistent.")
    return ArchetypeHit(
        archetype="take_private",
        confidence=min(score, 1.0),
        signals=signals,
        playbook=(
            "Delist, strip public-company cost, focus on underlying "
            "operating lever. Proxy mechanics and fiduciary-out fees "
            "are the procedural risks."
        ),
        risks=[
            "Shareholder-litigation drag on timing.",
            "Activist interference before deal closes.",
            "Break fees are sponsor-paid in a busted deal.",
        ],
        questions=[
            "What's the shareholder base concentration?",
            "Does the board support the deal — what's the fiduciary-out structure?",
            "Are there pending SEC actions that gate closing?",
        ],
    )


def _score_carveout(ctx: ArchetypeContext) -> ArchetypeHit:
    signals: List[str] = []
    score = 0.0
    if ctx.is_carveout:
        score += 0.55
        signals.append("Deal tagged as carve-out.")
    if ctx.seller_is_strategic:
        score += 0.30
        signals.append("Seller is a strategic (not a sponsor).")
    return ArchetypeHit(
        archetype="carve_out",
        confidence=min(score, 1.0),
        signals=signals,
        playbook=(
            "Rebuild standalone systems (payroll, IT, HR, RCM). TSA "
            "length is the biggest single cost driver."
        ),
        risks=[
            "Shared-services reliance creates TSA fees.",
            "Key functions (legal, compliance, payroll) may be centralized at parent.",
            "Revenue recognition mechanics can change post-close.",
        ],
        questions=[
            "What's the TSA scope and duration?",
            "How much of corporate overhead transfers at close?",
            "Are there any shared customer contracts that require consent?",
        ],
    )


def _score_turnaround(ctx: ArchetypeContext) -> ArchetypeHit:
    signals: List[str] = []
    score = 0.0
    if ctx.is_distressed:
        score += 0.50
        signals.append("Target flagged as distressed.")
    if ctx.has_turnaround_thesis:
        score += 0.30
        signals.append("Thesis is explicit turnaround.")
    if (ctx.current_ebitda_margin is not None and
            ctx.peer_median_margin is not None and
            ctx.current_ebitda_margin < ctx.peer_median_margin - 0.04):
        score += 0.30
        signals.append(
            f"Margin {ctx.current_ebitda_margin*100:.1f}% vs peer "
            f"median {ctx.peer_median_margin*100:.1f}% — substantial gap."
        )
    return ArchetypeHit(
        archetype="turnaround",
        confidence=min(score, 1.0),
        signals=signals,
        playbook=(
            "Hire an operator-CEO, cash-first plan, cut unprofitable "
            "service lines, renegotiate payer contracts. Equity upside "
            "comes from restoring to peer median, not exceeding it."
        ),
        risks=[
            "Customer/patient flight during restructuring.",
            "Labor-relations escalation under cost-cut.",
            "Regulatory scrutiny spikes when performance is weak.",
        ],
        questions=[
            "Is there a named operator-CEO identified pre-close?",
            "What's the 90-day cash plan? Will covenant waivers be needed?",
            "Which service lines are the obvious divestitures?",
        ],
    )


def _score_buy_and_build(ctx: ArchetypeContext) -> ArchetypeHit:
    signals: List[str] = []
    score = 0.0
    if (ctx.platform_or_addon == "platform" and ctx.number_of_addons_planned
            and 1 <= ctx.number_of_addons_planned <= 2):
        score += 0.40
        signals.append("Platform + 1-2 targeted add-ons (buy-and-build, not rollup).")
    if ctx.revenue_growth_pct and ctx.revenue_growth_pct >= 0.10 and not ctx.has_rollup_thesis:
        score += 0.30
        signals.append("Double-digit organic growth with selective M&A.")
    if ctx.has_rollup_thesis:
        # buy-and-build is the opposite of a rollup — penalize overlap
        score -= 0.20
    return ArchetypeHit(
        archetype="buy_and_build",
        confidence=max(min(score, 1.0), 0.0),
        signals=signals,
        playbook=(
            "Organic growth as the anchor, M&A is supplemental. "
            "Operating team must be strong enough to integrate without "
            "a dedicated integration org."
        ),
        risks=[
            "Organic growth disappoints and M&A has to carry the plan.",
            "Operating team burnt out by dual focus.",
        ],
        questions=[
            "What's the organic growth base case, ex-M&A?",
            "Who on the team has M&A experience?",
        ],
    )


def _score_continuation(ctx: ArchetypeContext) -> ArchetypeHit:
    signals: List[str] = []
    score = 0.0
    if ctx.is_continuation_vehicle:
        score += 0.70
        signals.append("Deal is a continuation-fund transaction.")
    if ctx.seller_is_sponsor:
        score += 0.20
        signals.append("Seller is an existing sponsor.")
    return ArchetypeHit(
        archetype="continuation",
        confidence=min(score, 1.0),
        signals=signals,
        playbook=(
            "LPAC approval and conflict-of-interest disclosure are the "
            "procedural gates. Focus the memo on why continuation beats "
            "a straight sale."
        ),
        risks=[
            "Conflict-of-interest optics with existing LPs.",
            "GP fee stacking on already-owned assets.",
            "Valuation scrutiny from the advisory committee.",
        ],
        questions=[
            "Has LPAC signed off on the valuation?",
            "What's the new fund's fee structure?",
            "What named upside justifies continuing vs exiting?",
        ],
    )


def _score_gp_led_secondary(ctx: ArchetypeContext) -> ArchetypeHit:
    # GP-led secondary is adjacent to continuation; share signals.
    signals: List[str] = []
    score = 0.0
    if ctx.seller_is_sponsor and not ctx.is_continuation_vehicle:
        score += 0.40
        signals.append("Sponsor-to-sponsor transaction, not a continuation.")
    return ArchetypeHit(
        archetype="gp_led_secondary",
        confidence=min(score, 1.0),
        signals=signals,
        playbook="Focus on fresh-eyes diligence — you're buying from someone who knows the asset cold.",
        risks=[
            "Adverse selection — seller knows risk you don't.",
            "Valuation anchoring to marks, not market.",
        ],
        questions=[
            "Why is the existing sponsor exiting now?",
            "What changed in the thesis since original underwriting?",
        ],
    )


def _score_operating_lift(ctx: ArchetypeContext) -> ArchetypeHit:
    signals: List[str] = []
    score = 0.0
    if ctx.has_rcm_thesis:
        score += 0.50
        signals.append("Explicit RCM / operating thesis.")
    if ctx.debt_to_ebitda and 4.0 <= ctx.debt_to_ebitda <= 6.5:
        score += 0.20
        signals.append("Classical LBO leverage range.")
    if ctx.is_minority:
        score -= 0.30
    return ArchetypeHit(
        archetype="operating_lift",
        confidence=max(min(score, 1.0), 0.0),
        signals=signals,
        playbook=(
            "Operating partner drives the lever program. Monthly "
            "operating reviews with KPI walk. Exit timed to post-ramp."
        ),
        risks=[
            "Lever ramp slips; exit EBITDA underperforms.",
            "Organic revenue flat masks the underlying progress.",
        ],
        questions=[
            "What specific operating lever is priced in? By how much?",
            "Who on the team has run this lever before, on what asset?",
        ],
    )


def _score_growth_equity(ctx: ArchetypeContext) -> ArchetypeHit:
    signals: List[str] = []
    score = 0.0
    if ctx.is_minority:
        score += 0.40
        signals.append("Minority investment.")
    if ctx.ownership_pct is not None and ctx.ownership_pct < 0.50:
        score += 0.20
        signals.append(f"Ownership {ctx.ownership_pct*100:.0f}% — below control.")
    if ctx.revenue_growth_pct and ctx.revenue_growth_pct >= 0.20:
        score += 0.20
        signals.append("Rapid revenue growth — growth-equity profile.")
    return ArchetypeHit(
        archetype="growth_equity",
        confidence=min(score, 1.0),
        signals=signals,
        playbook=(
            "Governance rights matter more than control. Focus on "
            "board composition, minority protections, and exit triggers."
        ),
        risks=[
            "Minority position limits operating influence.",
            "Exit is founder-timed, not fund-timed.",
        ],
        questions=[
            "What board rights and veto do we get?",
            "What's the drag-along / tag-along structure?",
        ],
    )


def _score_pipe(ctx: ArchetypeContext) -> ArchetypeHit:
    signals: List[str] = []
    score = 0.0
    if ctx.is_public_target and ctx.is_minority:
        score += 0.70
        signals.append("Public target, minority stake — PIPE structure.")
    return ArchetypeHit(
        archetype="pipe",
        confidence=min(score, 1.0),
        signals=signals,
        playbook="Register shares, negotiate conversion terms, monitor disclosure risk.",
        risks=[
            "Liquidity lock-up is usually 12-18 months.",
            "Negative news flow can trap the position.",
        ],
        questions=[
            "What are the registration rights?",
            "Is there a conversion ratchet if the stock drops?",
        ],
    )


# ── Orchestrator ─────────────────────────────────────────────────────

_CLASSIFIERS = [
    _score_platform_rollup,
    _score_take_private,
    _score_carveout,
    _score_turnaround,
    _score_buy_and_build,
    _score_continuation,
    _score_gp_led_secondary,
    _score_operating_lift,
    _score_growth_equity,
    _score_pipe,
]


def classify_archetypes(
    ctx: ArchetypeContext,
    *,
    min_confidence: float = 0.25,
) -> List[ArchetypeHit]:
    """Classify a deal context into zero-or-more archetypes.

    Returns archetypes with ``confidence >= min_confidence``, sorted
    descending by confidence. Lowering ``min_confidence`` surfaces
    the full ranking.
    """
    hits: List[ArchetypeHit] = []
    for fn in _CLASSIFIERS:
        hit = fn(ctx)
        if hit.confidence >= min_confidence:
            hits.append(hit)
    hits.sort(key=lambda h: -h.confidence)
    return hits


def primary_archetype(ctx: ArchetypeContext) -> Optional[str]:
    """Return the single highest-confidence archetype, or None."""
    hits = classify_archetypes(ctx, min_confidence=0.30)
    return hits[0].archetype if hits else None
