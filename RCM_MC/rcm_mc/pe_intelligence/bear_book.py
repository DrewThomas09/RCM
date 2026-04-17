"""Bear book — pattern-matching against things that have actually
gone wrong in healthcare PE.

A partner's most valuable asset is pattern recognition: "I've seen
this movie before." This module encodes the plotlines. When a deal
shows a combination of signals that resembles a known bad outcome,
we surface the pattern with a concrete historical/generic parallel.

These are NOT legal/confidential references. They are generic
archetypes of how deals have failed — the kind of thing a partner
says out loud at IC ("this feels like that bolt-on roll-up from 2019
that didn't integrate").

Each pattern has:
- A name and one-line summary.
- Trigger signals — a predicate over the context.
- The typical failure mode.
- The partner-voice warning.

Run against a :class:`HeuristicContext`. Returns
:class:`BearPatternHit` objects, sorted by match confidence.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .heuristics import HeuristicContext


@dataclass
class BearPatternHit:
    pattern_id: str
    name: str
    summary: str
    confidence: float                # 0.0-1.0
    failure_mode: str = ""
    partner_voice: str = ""
    signals_matched: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "name": self.name,
            "summary": self.summary,
            "confidence": self.confidence,
            "failure_mode": self.failure_mode,
            "partner_voice": self.partner_voice,
            "signals_matched": list(self.signals_matched),
        }


def _norm_mix(mix: Dict[str, float]) -> Dict[str, float]:
    if not mix:
        return {}
    low = {str(k).lower(): float(v) for k, v in mix.items() if v is not None}
    total = sum(low.values())
    if total > 1.5:
        low = {k: v / 100.0 for k, v in low.items()}
    return low


# ── Patterns ─────────────────────────────────────────────────────────

def _p_rollup_integration_failure(ctx: HeuristicContext) -> Optional[BearPatternHit]:
    """Roll-up with aggressive EBITDA growth assumption, high leverage,
    short hold. Classic shape of 2018-2020 healthcare roll-ups that
    missed integration."""
    signals: List[str] = []
    score = 0.0
    if ctx.ebitda_m is not None and ctx.ebitda_m < 50:
        score += 0.1
        signals.append("Sub-$50M platform typical of rollup start point.")
    if ctx.margin_expansion_bps_per_yr and ctx.margin_expansion_bps_per_yr >= 300:
        score += 0.3
        signals.append("Aggressive margin expansion — integration-dependent.")
    if ctx.leverage_multiple and ctx.leverage_multiple >= 5.5:
        score += 0.2
        signals.append("High leverage at close.")
    if ctx.hold_years and ctx.hold_years <= 4:
        score += 0.2
        signals.append("Short hold leaves little room for integration.")
    if score < 0.30:
        return None
    return BearPatternHit(
        pattern_id="rollup_integration_failure",
        name="Roll-up integration failure",
        summary=(
            "Platform roll-up with aggressive synergy math and a short hold. "
            "Rhymes with 2018-2020 healthcare roll-ups that underdelivered."
        ),
        confidence=min(score, 1.0),
        failure_mode=(
            "Add-ons never get integrated into one financial system. "
            "Synergies evaporate; platform CEO burns out; exit at flat "
            "multiple becomes the best case."
        ),
        partner_voice=(
            "Before we sign, show me the integration playbook with a "
            "named integration officer and a 180-day system consolidation "
            "plan. Without that, this is the same movie."
        ),
        signals_matched=signals,
    )


def _p_medicare_margin_compression(ctx: HeuristicContext) -> Optional[BearPatternHit]:
    """Medicare-heavy + margin growth plan > 150 bps/yr — history is
    that CMS rate cuts eat the plan."""
    mix = _norm_mix(ctx.payer_mix)
    medicare = mix.get("medicare", 0.0)
    if medicare < 0.50:
        return None
    if not ctx.margin_expansion_bps_per_yr or ctx.margin_expansion_bps_per_yr <= 150:
        return None
    return BearPatternHit(
        pattern_id="medicare_margin_compression",
        name="Medicare-heavy with margin expansion plan",
        summary=(
            "Medicare exposure > 50% paired with an operating-margin "
            "expansion plan. Over any 5-year window, CMS has imposed at "
            "least one unforeseen cut that compresses the plan."
        ),
        confidence=0.70,
        failure_mode=(
            "CMS rate update or add-on policy change (sequester, 340B, "
            "site-neutral) reduces reimbursement mid-hold. The margin "
            "expansion plan gets eaten before it starts."
        ),
        partner_voice=(
            "Stress the model with one unexpected CMS cut in year 2. If "
            "the lever plan still clears, we're fine. If not, we're "
            "hoping CMS is nice to us — and they rarely are."
        ),
        signals_matched=[
            f"Medicare {medicare*100:.0f}%",
            f"Margin expansion {ctx.margin_expansion_bps_per_yr:.0f} bps/yr",
        ],
    )


def _p_carveout_tsa_sprawl(ctx: HeuristicContext) -> Optional[BearPatternHit]:
    """Carve-out with missing structural signals (no case mix, low data
    coverage, high AR) — the pattern of a division pulled out of a
    parent system where standalone tooling is weak."""
    signals: List[str] = []
    score = 0.0
    if ctx.data_coverage_pct is not None and ctx.data_coverage_pct < 0.60:
        score += 0.2
        signals.append("Low data coverage — parent may hold the systems.")
    if ctx.days_in_ar and ctx.days_in_ar > 60:
        score += 0.2
        signals.append("Elevated AR days — billing workflow dependencies.")
    if not ctx.has_case_mix_data:
        score += 0.1
        signals.append("Missing CMI — parent may hold the reporting.")
    if score < 0.30:
        return None
    return BearPatternHit(
        pattern_id="carveout_tsa_sprawl",
        name="Carve-out TSA sprawl risk",
        summary=(
            "Data coverage, case-mix availability, and AR metrics all "
            "point to a target whose operating systems live at the "
            "parent. Expect a painful TSA and protracted systems build."
        ),
        confidence=min(score, 1.0),
        failure_mode=(
            "TSA fees balloon past plan; standalone systems take 18+ "
            "months to stand up; the operating thesis pushes out a "
            "full year."
        ),
        partner_voice=(
            "Get the TSA draft and a specific IT/RCM standalone timeline "
            "before LOI. If the parent can't commit to a cutover date, "
            "we can't commit to our ramp plan."
        ),
        signals_matched=signals,
    )


def _p_turnaround_without_operator(ctx: HeuristicContext) -> Optional[BearPatternHit]:
    """Below-peer margin with aggressive turnaround — works only with
    an operator CEO identified pre-close. Absent that, it's a wish."""
    signals: List[str] = []
    score = 0.0
    if ctx.ebitda_margin is not None and ctx.ebitda_margin < 0.03:
        score += 0.3
        signals.append("Margin < 3% — turnaround territory.")
    if ctx.margin_expansion_bps_per_yr and ctx.margin_expansion_bps_per_yr >= 300:
        score += 0.3
        signals.append("Aggressive margin plan.")
    if score < 0.40:
        return None
    return BearPatternHit(
        pattern_id="turnaround_without_operator",
        name="Turnaround without named operator",
        summary=(
            "Below-peer margin plus aggressive margin plan. History says "
            "this only works when an operator-CEO is hired BEFORE close."
        ),
        confidence=min(score, 1.0),
        failure_mode=(
            "Existing management can't execute; sponsor runs the "
            "business by-committee; first 12 months are lost to a "
            "CEO search; exit is a fire-sale."
        ),
        partner_voice=(
            "Who's the operator-CEO? If the answer is 'we'll hire one', "
            "we're funding a search, not a thesis. Do the search first "
            "or walk."
        ),
        signals_matched=signals,
    )


def _p_covid_tailwind_fade(ctx: HeuristicContext) -> Optional[BearPatternHit]:
    """High margin + acute-care + aggressive exit multiple — matches
    deals that priced off post-COVID earnings that didn't normalize."""
    if ctx.hospital_type != "acute_care":
        return None
    if ctx.ebitda_margin is None or ctx.ebitda_margin < 0.14:
        return None
    if not ctx.exit_multiple or ctx.exit_multiple < 10.0:
        return None
    return BearPatternHit(
        pattern_id="covid_tailwind_fade",
        name="COVID-tailwind margin and multiple",
        summary=(
            "Acute-care with elevated margin and a double-digit exit "
            "multiple. 2023-2024 priced many deals off COVID-inflated "
            "baselines that normalized lower."
        ),
        confidence=0.65,
        failure_mode=(
            "Baseline EBITDA shrinks as COVID relief and temporary rate "
            "uplifts roll off. The entry multiple is suddenly wrong and "
            "the exit plan is unreachable."
        ),
        partner_voice=(
            "Strip PRF, ERC, and temporary rate add-ons out of the "
            "baseline before we price. What's the ex-COVID EBITDA? "
            "That's the only number I care about."
        ),
        signals_matched=[
            f"Acute-care margin {ctx.ebitda_margin*100:.1f}%",
            f"Exit multiple {ctx.exit_multiple:.2f}x",
        ],
    )


def _p_high_leverage_thin_coverage(ctx: HeuristicContext) -> Optional[BearPatternHit]:
    """Levered deal with tight covenant headroom + tight interest
    coverage = pattern of distressed LBOs that went to workout in
    2022-2023 rate spike."""
    if not ctx.leverage_multiple or ctx.leverage_multiple < 6.0:
        return None
    if ctx.covenant_headroom_pct is None or ctx.covenant_headroom_pct >= 0.15:
        return None
    return BearPatternHit(
        pattern_id="high_leverage_thin_coverage",
        name="High leverage + thin covenant headroom",
        summary=(
            "Leverage ≥ 6.0x and covenant headroom < 15%. This is the "
            "structural shape of deals that went to workout when rates "
            "reset in 2022-2023."
        ),
        confidence=0.75,
        failure_mode=(
            "One miss triggers covenant renegotiation; lender demands "
            "paydown; operating plan gets truncated; sponsor puts in "
            "rescue equity."
        ),
        partner_voice=(
            "Lower leverage by a turn or negotiate a 25%+ headroom. This "
            "cap structure doesn't survive contact with a bad quarter."
        ),
        signals_matched=[
            f"Leverage {ctx.leverage_multiple:.2f}x",
            f"Headroom {ctx.covenant_headroom_pct*100:.1f}%",
        ],
    )


def _p_ffs_math_on_vbc(ctx: HeuristicContext) -> Optional[BearPatternHit]:
    """Capitation / VBC deals modeled with FFS math — the classic early
    MSO value-based bet that didn't pencil out."""
    structure = (ctx.deal_structure or "").lower()
    if structure not in ("capitation", "cap", "vbc", "value-based", "value_based_care"):
        return None
    if ctx.revenue_growth_pct_per_yr is None or ctx.revenue_growth_pct_per_yr <= 4.0:
        return None
    return BearPatternHit(
        pattern_id="vbc_priced_as_ffs",
        name="VBC / capitation priced like FFS",
        summary=(
            "Value-based / capitation structure with volume-driven "
            "revenue growth. Matches the 2020-2022 VBC mini-bust where "
            "MSO thesis was priced on FFS assumptions."
        ),
        confidence=0.70,
        failure_mode=(
            "Lives growth stalls; MLR compresses on adverse selection; "
            "revenue does not show up as modeled; rollup math fails."
        ),
        partner_voice=(
            "VBC revenue is lives × PMPM × (1 - MLR). If the model "
            "shows revenue growing without lives growing, the thesis "
            "is wrong."
        ),
        signals_matched=[
            f"Deal structure {structure}",
            f"Revenue growth {ctx.revenue_growth_pct_per_yr:.1f}%/yr",
        ],
    )


def _p_rural_single_payer_cliff(ctx: HeuristicContext) -> Optional[BearPatternHit]:
    """Critical-access / rural hospital with heavy single-payer mix.
    The pattern is a rural facility whose payer dependency moved in
    the wrong direction during the hold."""
    if ctx.hospital_type != "critical_access":
        return None
    mix = _norm_mix(ctx.payer_mix)
    if mix.get("medicare", 0.0) < 0.60 and mix.get("medicaid", 0.0) < 0.35:
        return None
    return BearPatternHit(
        pattern_id="rural_single_payer_cliff",
        name="Rural facility with dominant-payer cliff",
        summary=(
            "Critical-access or rural hospital with ≥60% Medicare or "
            "≥35% Medicaid. A single payer holds the fate of the deal."
        ),
        confidence=0.70,
        failure_mode=(
            "A state Medicaid rate freeze or a CMS CAH cost-cap change "
            "resets the baseline. The lever program can't out-run it."
        ),
        partner_voice=(
            "What's the state's Medicaid outlook? What's the CMS cost-"
            "cap methodology? If you can't answer both in a sentence, "
            "don't price this deal."
        ),
        signals_matched=[
            f"Medicare {mix.get('medicare', 0)*100:.0f}%",
            f"Medicaid {mix.get('medicaid', 0)*100:.0f}%",
        ],
    )


# ── Registry + orchestrator ──────────────────────────────────────────

BEAR_PATTERNS: List[Callable[[HeuristicContext], Optional[BearPatternHit]]] = [
    _p_rollup_integration_failure,
    _p_medicare_margin_compression,
    _p_carveout_tsa_sprawl,
    _p_turnaround_without_operator,
    _p_covid_tailwind_fade,
    _p_high_leverage_thin_coverage,
    _p_ffs_math_on_vbc,
    _p_rural_single_payer_cliff,
]


def scan_bear_book(ctx: HeuristicContext,
                   *, min_confidence: float = 0.30) -> List[BearPatternHit]:
    """Run every bear-book pattern against a context. Return matches
    at or above ``min_confidence``, sorted by confidence desc."""
    hits: List[BearPatternHit] = []
    for fn in BEAR_PATTERNS:
        try:
            hit = fn(ctx)
        except Exception:
            hit = None
        if hit is not None and hit.confidence >= min_confidence:
            hits.append(hit)
    hits.sort(key=lambda h: -h.confidence)
    return hits
