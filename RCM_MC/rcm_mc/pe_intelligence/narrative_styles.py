"""Narrative styles — alternate voices for the IC narrative.

The core `narrative.py` ships a senior-PE-partner voice. Different
audiences deserve different framings:

- **analyst_brief** — neutral, data-first, minimal editorial. Good
  for the junior-analyst pre-read.
- **skeptic** — the adversarial partner voice ("what kills this
  deal"). For a pre-mortem exercise.
- **founder_voice** — framed from the target-founder perspective,
  useful when writing outreach or setting diligence tone.
- **bullish** — the optimistic frame. For when the partner wants to
  remind the room why they're in the deal.
- **three_sentence** — compressed executive summary, three sentences
  only. For channel partners / initial screens.

Each style takes the same inputs as `compose_narrative` and returns
a `NarrativeBlock`-compatible dict so the IC-memo renderers work
without changes.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .heuristics import HeuristicHit, SEV_CRITICAL, SEV_HIGH, SEV_MEDIUM
from .narrative import NarrativeBlock, compose_narrative
from .reasonableness import (
    BandCheck,
    VERDICT_IMPLAUSIBLE,
    VERDICT_IN_BAND,
    VERDICT_OUT_OF_BAND,
    VERDICT_STRETCH,
)


def _worst_severity(hits: List[HeuristicHit]) -> str:
    order = {SEV_CRITICAL: 4, SEV_HIGH: 3, SEV_MEDIUM: 2, "LOW": 1, "INFO": 0}
    max_sev = "INFO"
    for h in hits:
        if order.get(h.severity, 0) > order.get(max_sev, 0):
            max_sev = h.severity
    return max_sev


def _worst_band(bands: List[BandCheck]) -> str:
    order = {VERDICT_IN_BAND: 0, VERDICT_STRETCH: 1,
             VERDICT_OUT_OF_BAND: 2, VERDICT_IMPLAUSIBLE: 3}
    worst = VERDICT_IN_BAND
    for b in bands:
        if order.get(b.verdict, 0) > order.get(worst, 0):
            worst = b.verdict
    return worst


def _payer_phrase(payer_mix: Optional[Dict[str, float]]) -> str:
    if not payer_mix:
        return "mixed payers"
    norm = {k: float(v) for k, v in payer_mix.items()}
    total = sum(norm.values())
    if total > 1.5:
        norm = {k: v / 100.0 for k, v in norm.items()}
    # largest payer
    name, share = max(norm.items(), key=lambda kv: kv[1])
    return f"{str(name).title()} {share*100:.0f}%"


# ── Analyst-brief style ─────────────────────────────────────────────

def compose_analyst_brief(
    *,
    bands: List[BandCheck],
    hits: List[HeuristicHit],
    hospital_type: Optional[str] = None,
    ebitda_m: Optional[float] = None,
    payer_mix: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    core = compose_narrative(
        bands=bands, hits=hits, hospital_type=hospital_type,
        ebitda_m=ebitda_m, payer_mix=payer_mix,
    )
    n_hits = len(hits)
    n_bands_off = sum(1 for b in bands
                      if b.verdict in (VERDICT_STRETCH, VERDICT_OUT_OF_BAND,
                                       VERDICT_IMPLAUSIBLE))
    headline = (
        f"Review pulled {n_hits} pattern flag(s) and "
        f"{n_bands_off} off-band reasonableness check(s). "
        f"Recommendation: {core.recommendation}."
    )
    return {
        "style": "analyst_brief",
        "headline": headline,
        "bull_case": core.bull_case,
        "bear_case": core.bear_case,
        "key_questions": list(core.key_questions),
        "recommendation": core.recommendation,
        "recommendation_rationale": core.recommendation_rationale,
    }


# ── Skeptic style ───────────────────────────────────────────────────

def compose_skeptic_view(
    *,
    bands: List[BandCheck],
    hits: List[HeuristicHit],
    hospital_type: Optional[str] = None,
    ebitda_m: Optional[float] = None,
    payer_mix: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """The adversarial voice — 'what kills this deal'."""
    # Pick the three worst items.
    severity_rank = {SEV_CRITICAL: 4, SEV_HIGH: 3, SEV_MEDIUM: 2,
                     "LOW": 1, "INFO": 0}
    worst_hits = sorted(hits, key=lambda h: -severity_rank.get(h.severity, 0))[:3]
    worst_bands = [b for b in bands
                   if b.verdict in (VERDICT_OUT_OF_BAND, VERDICT_IMPLAUSIBLE)]

    kill_statements: List[str] = []
    for h in worst_hits:
        if h.partner_voice:
            kill_statements.append(h.partner_voice)
    for b in worst_bands[:2]:
        if b.partner_note:
            kill_statements.append(b.partner_note)

    headline = "Pre-mortem: here's how this deal loses money."
    if not kill_statements:
        body = "No obvious deal-killers. The bear case is execution slippage + multiple compression."
    else:
        body = " ".join(kill_statements[:4])

    return {
        "style": "skeptic",
        "headline": headline,
        "bull_case": "(Not rendered in skeptic mode.)",
        "bear_case": body,
        "key_questions": [f"If {h.title}, how do we lose $X?" for h in worst_hits],
        "recommendation": "",
        "recommendation_rationale": "",
    }


# ── Founder-voice style ─────────────────────────────────────────────

def compose_founder_voice(
    *,
    bands: List[BandCheck],
    hits: List[HeuristicHit],
    hospital_type: Optional[str] = None,
    ebitda_m: Optional[float] = None,
    payer_mix: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """Framed from the target founder's perspective."""
    size_phrase = (f"${ebitda_m:.0f}M EBITDA" if ebitda_m else "the business")
    pay_phrase = _payer_phrase(payer_mix)
    headline = (
        f"From the founder's seat: {size_phrase}, {pay_phrase}. "
        "What changes after close?"
    )
    body = (
        "Acquirer wants to preserve the commercial franchise and invest in "
        "capacity and RCM infrastructure. Expect 100-day plan with KPI "
        "cadence, monthly operating reviews, and a seat on the board."
    )
    return {
        "style": "founder_voice",
        "headline": headline,
        "bull_case": "Capital + operating partnership to grow the asset.",
        "bear_case": body,
        "key_questions": [
            "What is the 100-day plan and who owns each line?",
            "What's preserved vs what changes?",
            "How are my key clinicians protected?",
            "What's the exit timeline?",
        ],
        "recommendation": "",
        "recommendation_rationale": "",
    }


# ── Bullish style ───────────────────────────────────────────────────

def compose_bullish_view(
    *,
    bands: List[BandCheck],
    hits: List[HeuristicHit],
    hospital_type: Optional[str] = None,
    ebitda_m: Optional[float] = None,
    payer_mix: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    core = compose_narrative(
        bands=bands, hits=hits, hospital_type=hospital_type,
        ebitda_m=ebitda_m, payer_mix=payer_mix,
    )
    in_band = [b for b in bands if b.verdict == VERDICT_IN_BAND]
    strengths_count = len(in_band)
    headline = (
        f"Why we're doing this deal: {strengths_count} band-clearing checks, "
        f"operating-lever upside, and a named exit path."
    )
    return {
        "style": "bullish",
        "headline": headline,
        "bull_case": core.bull_case,
        "bear_case": "(Not rendered in bullish mode — see main narrative.)",
        "key_questions": [
            "What accelerates the lever ramp?",
            "What are the 2-3 ways this beats the base case?",
            "Is there a dividend recap window mid-hold?",
        ],
        "recommendation": core.recommendation,
        "recommendation_rationale": core.recommendation_rationale,
    }


# ── Three-sentence summary ──────────────────────────────────────────

def compose_three_sentence(
    *,
    bands: List[BandCheck],
    hits: List[HeuristicHit],
    hospital_type: Optional[str] = None,
    ebitda_m: Optional[float] = None,
    payer_mix: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    core = compose_narrative(
        bands=bands, hits=hits, hospital_type=hospital_type,
        ebitda_m=ebitda_m, payer_mix=payer_mix,
    )
    size = (f"${ebitda_m:.0f}M EBITDA" if ebitda_m else "middle-market")
    pay = _payer_phrase(payer_mix)
    # 1. What it is. 2. The bet. 3. The answer.
    s1 = f"{size} {(hospital_type or 'healthcare')} target, {pay}."
    s2 = (f"Thesis: {core.headline}" if core.headline
          else "Thesis: operating-lever driven return.")
    s3 = f"Recommendation: {core.recommendation}."
    body = " ".join([s1, s2, s3])
    return {
        "style": "three_sentence",
        "headline": body,
        "bull_case": "",
        "bear_case": "",
        "key_questions": [],
        "recommendation": core.recommendation,
        "recommendation_rationale": core.recommendation_rationale,
    }


# ── Dispatcher ──────────────────────────────────────────────────────

_STYLE_MAP = {
    "analyst_brief": compose_analyst_brief,
    "skeptic": compose_skeptic_view,
    "founder_voice": compose_founder_voice,
    "bullish": compose_bullish_view,
    "three_sentence": compose_three_sentence,
}

ALL_NARRATIVE_STYLES = tuple(_STYLE_MAP.keys())


def compose_styled_narrative(
    style: str,
    *,
    bands: List[BandCheck],
    hits: List[HeuristicHit],
    hospital_type: Optional[str] = None,
    ebitda_m: Optional[float] = None,
    payer_mix: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """Dispatch to a named narrative style. Unknown styles fall back
    to the analyst-brief."""
    fn = _STYLE_MAP.get(style, compose_analyst_brief)
    return fn(bands=bands, hits=hits, hospital_type=hospital_type,
              ebitda_m=ebitda_m, payer_mix=payer_mix)
