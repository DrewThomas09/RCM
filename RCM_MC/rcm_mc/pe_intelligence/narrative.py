"""Partner-voice narrative composer.

Given a list of :class:`BandCheck` results and :class:`HeuristicHit`
findings, write the commentary a senior partner would put in an IC memo.

Voice guide:
- **Direct** — no hedging like "it might be possible to consider". If
  there's a bear case, name it. If the deal doesn't clear, say so.
- **Opinionated** — partner commentary picks a side. "This is a buy at
  the right multiple, not at this one."
- **Concrete** — every claim gets a number. "200 bps of denial
  improvement is plausible; 400 is not" beats "denial assumptions look
  aggressive."
- **Plain English** — partners write like humans, not consultants. No
  bullet soup, no "leveraging synergies". Full sentences.

Output structure:

1. ``headline`` — one sentence, the partner's bottom line.
2. ``bull_case`` — 2-3 sentences, what has to be true for the deal
   to clear.
3. ``bear_case`` — 2-3 sentences, what breaks the deal.
4. ``key_questions`` — 3-5 questions the partner wants the team to
   answer before the next IC.
5. ``recommendation`` — one of "PASS", "PROCEED_WITH_CAVEATS",
   "PROCEED", "STRONG_PROCEED", plus a one-sentence why.

Nothing here talks to the DB or a network; everything is derived from
the inputs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .reasonableness import (
    BandCheck,
    VERDICT_IMPLAUSIBLE,
    VERDICT_IN_BAND,
    VERDICT_OUT_OF_BAND,
    VERDICT_STRETCH,
    VERDICT_UNKNOWN,
)
from .heuristics import (
    HeuristicHit,
    SEV_CRITICAL,
    SEV_HIGH,
    SEV_MEDIUM,
    SEV_LOW,
    SEV_INFO,
)


# ── Recommendation ───────────────────────────────────────────────────

REC_PASS = "PASS"
REC_PROCEED_CAVEATS = "PROCEED_WITH_CAVEATS"
REC_PROCEED = "PROCEED"
REC_STRONG_PROCEED = "STRONG_PROCEED"

_REC_ORDER = {
    REC_PASS: 0, REC_PROCEED_CAVEATS: 1,
    REC_PROCEED: 2, REC_STRONG_PROCEED: 3,
}


@dataclass
class NarrativeBlock:
    headline: str = ""
    bull_case: str = ""
    bear_case: str = ""
    key_questions: List[str] = field(default_factory=list)
    recommendation: str = REC_PROCEED_CAVEATS
    recommendation_rationale: str = ""
    ic_memo_paragraph: str = ""        # one prose paragraph, partner-voice

    def to_dict(self) -> Dict[str, Any]:
        return {
            "headline": self.headline,
            "bull_case": self.bull_case,
            "bear_case": self.bear_case,
            "key_questions": list(self.key_questions),
            "recommendation": self.recommendation,
            "recommendation_rationale": self.recommendation_rationale,
            "ic_memo_paragraph": self.ic_memo_paragraph,
        }


# ── Phrasing helpers ─────────────────────────────────────────────────

def _deal_type_phrase(hospital_type: Optional[str]) -> str:
    key = (hospital_type or "").lower()
    phrases = {
        "acute_care": "acute-care hospital",
        "acute": "acute-care hospital",
        "asc": "ambulatory surgery",
        "behavioral": "behavioral-health",
        "post_acute": "post-acute",
        "specialty": "specialty hospital",
        "outpatient": "outpatient",
        "critical_access": "critical-access hospital",
    }
    return phrases.get(key, "healthcare")


def _size_phrase(ebitda_m: Optional[float]) -> str:
    if ebitda_m is None:
        return "middle-market"
    if ebitda_m < 10:
        return "small-cap"
    if ebitda_m < 25:
        return "lower-middle-market"
    if ebitda_m < 75:
        return "middle-market"
    if ebitda_m < 200:
        return "upper-middle-market"
    return "large-cap"


def _payer_phrase(payer_mix: Optional[Dict[str, float]]) -> str:
    if not payer_mix:
        return "unspecified payer mix"
    norm = {str(k).lower(): float(v) for k, v in payer_mix.items()}
    total = sum(norm.values())
    if total > 1.5:
        norm = {k: v / 100.0 for k, v in norm.items()}
    medicare = norm.get("medicare", 0.0)
    medicaid = norm.get("medicaid", 0.0)
    commercial = norm.get("commercial", 0.0)
    if medicare >= 0.55:
        return f"Medicare-heavy ({medicare*100:.0f}%)"
    if medicaid >= 0.30:
        return f"Medicaid-heavy ({medicaid*100:.0f}%)"
    if commercial >= 0.45:
        return f"commercial-heavy ({commercial*100:.0f}%)"
    return "balanced payer mix"


def _worst_band_verdict(bands: List[BandCheck]) -> str:
    order = {VERDICT_IN_BAND: 0, VERDICT_UNKNOWN: 1, VERDICT_STRETCH: 2,
             VERDICT_OUT_OF_BAND: 3, VERDICT_IMPLAUSIBLE: 4}
    worst = VERDICT_IN_BAND
    for b in bands:
        if order.get(b.verdict, 0) > order.get(worst, 0):
            worst = b.verdict
    return worst


def _worst_heuristic_severity(hits: List[HeuristicHit]) -> str:
    order = {SEV_INFO: 0, SEV_LOW: 1, SEV_MEDIUM: 2, SEV_HIGH: 3, SEV_CRITICAL: 4}
    worst = SEV_INFO
    for h in hits:
        if order.get(h.severity, 0) > order.get(worst, 0):
            worst = h.severity
    return worst


# ── Headline ─────────────────────────────────────────────────────────

def _compose_headline(
    *,
    deal_phrase: str,
    irr_check: Optional[BandCheck],
    multiple_check: Optional[BandCheck],
    worst_heuristic: str,
) -> str:
    # Dead-deal cases first.
    if worst_heuristic == SEV_CRITICAL:
        return f"Critical-risk flag on this {deal_phrase} — the deal does not clear as modeled."
    if irr_check and irr_check.verdict == VERDICT_IMPLAUSIBLE:
        return f"The modeled IRR on this {deal_phrase} is implausible; rework before IC."
    if multiple_check and multiple_check.verdict == VERDICT_IMPLAUSIBLE:
        return f"The exit multiple on this {deal_phrase} is not supported by any live comp."
    # Stretch / out-of-band
    if irr_check and irr_check.verdict == VERDICT_OUT_OF_BAND:
        return f"Returns are outside the peer band for this {deal_phrase} — assumptions need a harder look."
    if worst_heuristic == SEV_HIGH:
        return f"High-severity PE flags on this {deal_phrase} — proceed only with specific remediation."
    if irr_check and irr_check.verdict == VERDICT_STRETCH:
        return f"Returns sit at the top of the peer band for this {deal_phrase} — defensible only with a named alpha story."
    if worst_heuristic == SEV_MEDIUM:
        return f"A credible {deal_phrase} deal with medium-severity items to close out."
    if irr_check and irr_check.verdict == VERDICT_IN_BAND:
        return f"A clean {deal_phrase} underwrite that sits inside peer bands."
    return f"A {deal_phrase} underwrite with the usual diligence items to close."


# ── Bull / bear case ─────────────────────────────────────────────────

def _compose_bull_case(
    bands: List[BandCheck],
    hits: List[HeuristicHit],
) -> str:
    strengths: List[str] = []
    # In-band IRR is a positive.
    for b in bands:
        if b.metric == "irr" and b.verdict == VERDICT_IN_BAND:
            strengths.append(
                f"IRR of {b.observed*100:.1f}% sits cleanly inside the peer "
                f"band for {b.band.regime if b.band else 'this regime'}."
            )
        if b.metric == "ebitda_margin" and b.verdict == VERDICT_IN_BAND:
            strengths.append(
                f"EBITDA margin of {b.observed*100:.1f}% is consistent with "
                "peer operations — no red flag on operating quality."
            )
        if b.metric == "exit_multiple" and b.verdict == VERDICT_IN_BAND:
            strengths.append(
                f"Exit multiple of {b.observed:.2f}x is defensible against "
                "recent comps."
            )
    # In-band levers are a positive signal.
    lever_ok = [b for b in bands
                if b.metric.startswith("lever:") and b.verdict == VERDICT_IN_BAND]
    if lever_ok:
        names = ", ".join(b.metric.split(":", 1)[1] for b in lever_ok[:3])
        strengths.append(
            f"Lever ramps on {names} sit inside realistic timeframes."
        )
    # Fewer than 3 heuristic hits is itself a positive.
    if len(hits) <= 2:
        strengths.append("The underwrite triggers very few PE pattern flags.")

    if not strengths:
        return ("The model clears on its face, but nothing about this deal "
                "stands out as obviously de-risked.")
    return " ".join(strengths)


def _compose_bear_case(
    bands: List[BandCheck],
    hits: List[HeuristicHit],
) -> str:
    concerns: List[str] = []
    # Out-of-band / implausible band checks
    for b in bands:
        if b.verdict in (VERDICT_OUT_OF_BAND, VERDICT_IMPLAUSIBLE) and b.partner_note:
            concerns.append(b.partner_note)
        elif b.verdict == VERDICT_STRETCH and b.partner_note:
            concerns.append(b.partner_note)
    # Top heuristics
    for h in hits[:3]:
        if h.severity in (SEV_HIGH, SEV_CRITICAL) and h.partner_voice:
            concerns.append(h.partner_voice)
    # Dedup while preserving order
    seen = set()
    uniq: List[str] = []
    for c in concerns:
        key = c.strip()
        if key and key not in seen:
            seen.add(key)
            uniq.append(key)
    if not uniq:
        return ("No obvious deal-killers. The bear case here is the usual "
                "one: lever execution slips and exit multiples compress.")
    return " ".join(uniq[:3])


def _compose_key_questions(
    bands: List[BandCheck],
    hits: List[HeuristicHit],
    ctx_summary: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """Build a focused 3-5 question list, highest signal first."""
    questions: List[str] = []
    seen: set = set()

    def _add(q: str) -> None:
        key = q.strip()
        if key and key not in seen:
            seen.add(key)
            questions.append(key)

    # Band-driven questions
    for b in bands:
        if b.metric == "irr" and b.verdict in (VERDICT_STRETCH, VERDICT_OUT_OF_BAND, VERDICT_IMPLAUSIBLE):
            _add("What is the single operating advantage that produces the modeled IRR, "
                 "and has it been validated by a comparable deal?")
        if b.metric == "exit_multiple" and b.verdict in (VERDICT_STRETCH, VERDICT_OUT_OF_BAND, VERDICT_IMPLAUSIBLE):
            _add("Which closed comp supports the exit multiple, and what was the payer mix on that comp?")
        if b.metric == "ebitda_margin" and b.verdict in (VERDICT_OUT_OF_BAND, VERDICT_IMPLAUSIBLE):
            if b.observed is not None and b.band and b.band.high is not None and b.observed > b.band.high:
                _add("What structural feature of this business explains margins above the peer ceiling?")
            else:
                _add("Is the below-peer margin temporary (integration, one-time) or structural?")
        if b.metric.startswith("lever:") and b.verdict in (VERDICT_OUT_OF_BAND, VERDICT_IMPLAUSIBLE):
            name = b.metric.split(":", 1)[1]
            _add(f"Who owns the {name} program, what's the milestone plan, and what capex does it require?")

    # Heuristic-driven questions
    for h in hits:
        if h.severity in (SEV_HIGH, SEV_CRITICAL):
            # Pull the remediation or synthesize from finding
            q = _heuristic_to_question(h)
            if q:
                _add(q)

    # Default fallbacks to ensure 3-5 items
    if len(questions) < 3:
        _add("What's the single data point the seller refuses to share, and why?")
    if len(questions) < 3:
        _add("If you lose 100 bps of blended rate, does the deal still clear the fund hurdle?")
    if len(questions) < 3:
        _add("Where does this deal sit in the sponsor's portfolio sector concentration?")

    return questions[:5]


def _heuristic_to_question(h: HeuristicHit) -> str:
    mapping = {
        "medicare_heavy_multiple_ceiling":
            "Name a closed comp with a Medicare mix this high that cleared the modeled exit multiple.",
        "aggressive_denial_improvement":
            "What evidence supports >200 bps/yr of denial-rate improvement — capex, vendor, or staffing change?",
        "capitation_vbc_uses_ffs_growth":
            "Rebuild the revenue stack as lives × PMPM × (1-MLR) + shared savings; does it still produce the modeled growth?",
        "multiple_expansion_carrying_return":
            "What does the return look like at a flat entry/exit multiple?",
        "margin_expansion_too_fast":
            "Break margin expansion into labor, RCM, service-line mix, and pricing — are any double-counted?",
        "leverage_too_high_govt_mix":
            "If CMS cuts the rate update by 100 bps, does covenant headroom survive?",
        "covenant_headroom_tight":
            "Can we negotiate covenant-lite terms or an equity cure right to widen the headroom?",
        "insufficient_data_coverage":
            "Which specific data artifacts can the seller provide to raise coverage above 70%?",
        "case_mix_missing":
            "Can we pull CMI from HCRIS Worksheet S-3 before the next model iteration?",
        "ar_days_above_peer":
            "Is the AR drag a billing problem (fixable) or a payer problem (structural)?",
        "denial_rate_elevated":
            "Do the top 10 denial reason codes account for ≥60% of denied volume?",
        "small_deal_mega_irr":
            "At a +1 turn on entry multiple, what does the IRR distribution look like?",
        "hold_too_short_for_rcm":
            "Can the hold extend to 4-5 years, or do we discount RCM value by 30-40%?",
        "writeoff_rate_high":
            "What's the reason-code breakdown of write-offs, and which buckets are addressable?",
        "critical_access_reimbursement":
            "If cost takeout hits revenue 1:1, where does margin come from — mix, volume, or scale?",
        "moic_cagr_too_high":
            "Shock any one driver 15%; does MOIC stay above 2.0x?",
        "teaching_hospital_complexity":
            "Can GME/IME be carved out of the bridge and forecast separately?",
        "ar_reduction_aggressive":
            "What capex is committed to deliver the AR days reduction — if zero, haircut the plan.",
        "state_medicaid_volatility":
            "Is Medicaid rate growth flat-lined at 0% in base case for this state?",
    }
    return mapping.get(h.id, "")


# ── Recommendation ───────────────────────────────────────────────────

def _compose_recommendation(
    bands: List[BandCheck],
    hits: List[HeuristicHit],
) -> (str, str):
    worst_band = _worst_band_verdict(bands)
    worst_sev = _worst_heuristic_severity(hits)
    n_high_plus = sum(1 for h in hits if h.severity in (SEV_HIGH, SEV_CRITICAL))
    n_critical = sum(1 for h in hits if h.severity == SEV_CRITICAL)

    # Hard PASS conditions
    if worst_band == VERDICT_IMPLAUSIBLE or n_critical >= 1:
        return (
            REC_PASS,
            "Implausible model output or critical structural flag — do not bring to IC as constructed.",
        )
    # PROCEED_WITH_CAVEATS — stretch or high flags
    if worst_band == VERDICT_OUT_OF_BAND or n_high_plus >= 2:
        return (
            REC_PROCEED_CAVEATS,
            "Multiple high-severity items or band breaches — proceed only after specific remediations.",
        )
    if worst_band == VERDICT_STRETCH or worst_sev == SEV_HIGH:
        return (
            REC_PROCEED_CAVEATS,
            "Deal clears on the surface but assumptions sit at the aggressive end of the peer band.",
        )
    # Clean
    if worst_band == VERDICT_IN_BAND and worst_sev in (SEV_INFO, SEV_LOW):
        return (
            REC_STRONG_PROCEED,
            "Assumptions sit inside peer bands and no high-severity PE pattern flags fired.",
        )
    if worst_sev == SEV_MEDIUM:
        return (
            REC_PROCEED,
            "Credible underwrite with medium-severity items to close out in diligence.",
        )
    return (REC_PROCEED, "No blocking issues identified.")


# ── IC memo paragraph ────────────────────────────────────────────────

def _compose_ic_paragraph(
    *,
    headline: str,
    bull_case: str,
    bear_case: str,
    recommendation: str,
    recommendation_rationale: str,
    deal_phrase: str,
    size_phrase: str,
    payer_phrase: str,
) -> str:
    """Write a single prose paragraph — the kind a partner dictates to
    IC minutes after reading the deck."""
    rec_word = {
        REC_PASS: "pass",
        REC_PROCEED_CAVEATS: "proceed with caveats",
        REC_PROCEED: "proceed",
        REC_STRONG_PROCEED: "strong proceed",
    }.get(recommendation, "proceed with caveats")

    pieces = [
        f"This is a {size_phrase} {deal_phrase} with a {payer_phrase}.",
        headline,
        f"Bull case: {bull_case}",
        f"Bear case: {bear_case}",
        f"My read: {rec_word} — {recommendation_rationale}",
    ]
    return " ".join(p.strip() for p in pieces if p).strip()


# ── Entry point ──────────────────────────────────────────────────────

def compose_narrative(
    *,
    bands: List[BandCheck],
    hits: List[HeuristicHit],
    hospital_type: Optional[str] = None,
    ebitda_m: Optional[float] = None,
    payer_mix: Optional[Dict[str, float]] = None,
    deal_name: Optional[str] = None,
) -> NarrativeBlock:
    """Compose the partner-voice narrative from checks + hits."""
    deal_phrase = _deal_type_phrase(hospital_type)
    size_phrase = _size_phrase(ebitda_m)
    payer_phrase = _payer_phrase(payer_mix)

    irr_check = next((b for b in bands if b.metric == "irr"), None)
    multiple_check = next((b for b in bands if b.metric == "exit_multiple"), None)
    worst_heuristic = _worst_heuristic_severity(hits)

    headline = _compose_headline(
        deal_phrase=deal_phrase,
        irr_check=irr_check,
        multiple_check=multiple_check,
        worst_heuristic=worst_heuristic,
    )
    bull = _compose_bull_case(bands, hits)
    bear = _compose_bear_case(bands, hits)
    questions = _compose_key_questions(bands, hits)
    rec, rec_rationale = _compose_recommendation(bands, hits)
    paragraph = _compose_ic_paragraph(
        headline=headline,
        bull_case=bull,
        bear_case=bear,
        recommendation=rec,
        recommendation_rationale=rec_rationale,
        deal_phrase=deal_phrase,
        size_phrase=size_phrase,
        payer_phrase=payer_phrase,
    )

    return NarrativeBlock(
        headline=headline,
        bull_case=bull,
        bear_case=bear,
        key_questions=questions,
        recommendation=rec,
        recommendation_rationale=rec_rationale,
        ic_memo_paragraph=paragraph,
    )
