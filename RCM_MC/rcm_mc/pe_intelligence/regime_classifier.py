"""Regime classifier — place a deal into a performance regime.

Partners separate deals into named regimes before underwriting
because each regime has a different playbook:

- **durable_growth** — consistently positive revenue growth + stable
  margins. Priority: protect the franchise; avoid over-financial-
  engineering.
- **emerging_volatile** — growing fast but dispersion is wide. Priority:
  validate sustainability; cap downside with covenant structure.
- **steady** — modest growth, low volatility. Priority: operating
  levers carry the return; watch multiple compression.
- **stagnant** — flat/near-zero growth, stable margins. Priority: cash
  cow; don't pay for growth you won't see.
- **declining_risk** — negative growth and/or deteriorating margins.
  Priority: turnaround thesis or walk.

The classifier is deterministic and takes growth / volatility /
consistency signals directly from the packet (or from a caller-built
:class:`RegimeInputs`).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


REGIME_DURABLE_GROWTH = "durable_growth"
REGIME_EMERGING_VOLATILE = "emerging_volatile"
REGIME_STEADY = "steady"
REGIME_STAGNANT = "stagnant"
REGIME_DECLINING_RISK = "declining_risk"

ALL_REGIMES = (
    REGIME_DURABLE_GROWTH,
    REGIME_EMERGING_VOLATILE,
    REGIME_STEADY,
    REGIME_STAGNANT,
    REGIME_DECLINING_RISK,
)


@dataclass
class RegimeInputs:
    """Signal bag for regime classification.

    All fields optional — the classifier degrades gracefully.
    """
    revenue_cagr_3yr: Optional[float] = None           # fraction
    ebitda_cagr_3yr: Optional[float] = None
    revenue_growth_stddev: Optional[float] = None      # volatility of yoy growth
    margin_trend_bps: Optional[float] = None           # +/- bps per year
    positive_growth_years_out_of_5: Optional[int] = None
    current_margin: Optional[float] = None
    peer_median_margin: Optional[float] = None


@dataclass
class RegimeResult:
    regime: str
    confidence: float                              # 0.0-1.0
    signals: List[str] = field(default_factory=list)
    partner_note: str = ""
    playbook: str = ""
    key_risk: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "regime": self.regime,
            "confidence": self.confidence,
            "signals": list(self.signals),
            "partner_note": self.partner_note,
            "playbook": self.playbook,
            "key_risk": self.key_risk,
        }


# ── Scoring ─────────────────────────────────────────────────────────

def _is_declining(inputs: RegimeInputs) -> float:
    """Return confidence [0..1] that this is declining_risk."""
    score = 0.0
    if inputs.revenue_cagr_3yr is not None and inputs.revenue_cagr_3yr < -0.01:
        score += 0.35
    if inputs.ebitda_cagr_3yr is not None and inputs.ebitda_cagr_3yr < -0.02:
        score += 0.35
    if inputs.margin_trend_bps is not None and inputs.margin_trend_bps < -100:
        score += 0.20
    if (inputs.current_margin is not None and inputs.peer_median_margin is not None
            and inputs.current_margin < inputs.peer_median_margin - 0.04):
        score += 0.10
    return min(score, 1.0)


def _is_stagnant(inputs: RegimeInputs) -> float:
    score = 0.0
    if (inputs.revenue_cagr_3yr is not None
            and -0.01 <= inputs.revenue_cagr_3yr <= 0.02):
        score += 0.40
    if (inputs.ebitda_cagr_3yr is not None
            and -0.02 <= inputs.ebitda_cagr_3yr <= 0.02):
        score += 0.30
    if (inputs.margin_trend_bps is not None
            and -50 <= inputs.margin_trend_bps <= 50):
        score += 0.20
    if (inputs.positive_growth_years_out_of_5 is not None
            and 2 <= inputs.positive_growth_years_out_of_5 <= 3):
        score += 0.10
    return min(score, 1.0)


def _is_steady(inputs: RegimeInputs) -> float:
    score = 0.0
    if (inputs.revenue_cagr_3yr is not None
            and 0.02 <= inputs.revenue_cagr_3yr <= 0.06):
        score += 0.35
    if (inputs.revenue_growth_stddev is not None
            and inputs.revenue_growth_stddev <= 0.03):
        score += 0.30
    if (inputs.positive_growth_years_out_of_5 is not None
            and inputs.positive_growth_years_out_of_5 >= 4):
        score += 0.25
    if (inputs.margin_trend_bps is not None
            and -50 <= inputs.margin_trend_bps <= 150):
        score += 0.10
    return min(score, 1.0)


def _is_durable_growth(inputs: RegimeInputs) -> float:
    score = 0.0
    if inputs.revenue_cagr_3yr is not None and inputs.revenue_cagr_3yr > 0.06:
        score += 0.35
    if (inputs.revenue_growth_stddev is not None
            and inputs.revenue_growth_stddev <= 0.04):
        score += 0.30
    if (inputs.positive_growth_years_out_of_5 is not None
            and inputs.positive_growth_years_out_of_5 == 5):
        score += 0.25
    if inputs.margin_trend_bps is not None and inputs.margin_trend_bps >= 0:
        score += 0.10
    return min(score, 1.0)


def _is_emerging_volatile(inputs: RegimeInputs) -> float:
    score = 0.0
    if inputs.revenue_cagr_3yr is not None and inputs.revenue_cagr_3yr > 0.06:
        score += 0.30
    if (inputs.revenue_growth_stddev is not None
            and inputs.revenue_growth_stddev > 0.06):
        score += 0.45
    if (inputs.positive_growth_years_out_of_5 is not None
            and inputs.positive_growth_years_out_of_5 <= 3):
        score += 0.25
    return min(score, 1.0)


_REGIME_SCORERS = [
    (REGIME_DECLINING_RISK, _is_declining),
    (REGIME_STAGNANT, _is_stagnant),
    (REGIME_STEADY, _is_steady),
    (REGIME_DURABLE_GROWTH, _is_durable_growth),
    (REGIME_EMERGING_VOLATILE, _is_emerging_volatile),
]


# ── Regime metadata ─────────────────────────────────────────────────

_REGIME_PLAYBOOK = {
    REGIME_DURABLE_GROWTH: (
        "Protect the franchise. Do not financial-engineer the operating "
        "plan — the business is already working."),
    REGIME_EMERGING_VOLATILE: (
        "Validate sustainability before extrapolating growth. Cap "
        "downside with covenant structure; haircut the upside."),
    REGIME_STEADY: (
        "Operating levers are the alpha. Multiple expansion is a wish; "
        "exit discipline is a commitment."),
    REGIME_STAGNANT: (
        "Cash-cow thesis. Don't pay for growth you won't see; use "
        "leverage to amplify distributions."),
    REGIME_DECLINING_RISK: (
        "Turnaround or walk. If turnaround, named operator pre-close "
        "and a 90-day cash plan. If not, do not underwrite."),
}

_REGIME_KEY_RISK = {
    REGIME_DURABLE_GROWTH: "Multiple compression if category cools.",
    REGIME_EMERGING_VOLATILE: "Dispersion — a single bad year wipes the case.",
    REGIME_STEADY: "Rate / reimbursement cycle eats the lever plan.",
    REGIME_STAGNANT: "Deferred capex masking depreciating asset base.",
    REGIME_DECLINING_RISK: "Operating losses compound; covenant breach inside hold.",
}


def _build_signals(inputs: RegimeInputs) -> List[str]:
    sigs: List[str] = []
    if inputs.revenue_cagr_3yr is not None:
        sigs.append(f"Revenue CAGR (3yr): {inputs.revenue_cagr_3yr*100:.1f}%")
    if inputs.ebitda_cagr_3yr is not None:
        sigs.append(f"EBITDA CAGR (3yr): {inputs.ebitda_cagr_3yr*100:.1f}%")
    if inputs.revenue_growth_stddev is not None:
        sigs.append(f"Growth σ: {inputs.revenue_growth_stddev*100:.1f}%")
    if inputs.margin_trend_bps is not None:
        sigs.append(f"Margin trend: {inputs.margin_trend_bps:+.0f} bps/yr")
    if inputs.positive_growth_years_out_of_5 is not None:
        sigs.append(f"Positive-growth years out of 5: "
                    f"{inputs.positive_growth_years_out_of_5}/5")
    return sigs


# ── Orchestrator ────────────────────────────────────────────────────

def classify_regime(inputs: RegimeInputs) -> RegimeResult:
    """Classify a deal into a performance regime.

    Returns the highest-confidence regime; ties resolve in the order
    declared in ``_REGIME_SCORERS`` (declining wins over stagnant,
    etc. — conservative).
    """
    scores = [(name, fn(inputs)) for name, fn in _REGIME_SCORERS]
    best = max(scores, key=lambda kv: kv[1])
    name, conf = best
    # If every score is zero (no inputs), treat as steady w/ 0 confidence.
    if conf == 0:
        return RegimeResult(
            regime=REGIME_STEADY,
            confidence=0.0,
            signals=[],
            partner_note="Insufficient signals to classify regime.",
            playbook=_REGIME_PLAYBOOK[REGIME_STEADY],
            key_risk=_REGIME_KEY_RISK[REGIME_STEADY],
        )
    return RegimeResult(
        regime=name,
        confidence=conf,
        signals=_build_signals(inputs),
        partner_note=_partner_note_for(name, conf),
        playbook=_REGIME_PLAYBOOK.get(name, ""),
        key_risk=_REGIME_KEY_RISK.get(name, ""),
    )


def _partner_note_for(regime: str, confidence: float) -> str:
    strength = ("strong" if confidence >= 0.70
                else "moderate" if confidence >= 0.45
                else "weak")
    labels = {
        REGIME_DURABLE_GROWTH: "durable growth",
        REGIME_EMERGING_VOLATILE: "emerging / volatile",
        REGIME_STEADY: "steady",
        REGIME_STAGNANT: "stagnant",
        REGIME_DECLINING_RISK: "declining risk",
    }
    return (f"{strength.title()} signal for {labels.get(regime, regime)} "
            f"regime ({confidence*100:.0f}% confidence).")


def rank_all_regimes(inputs: RegimeInputs) -> List[RegimeResult]:
    """Return every regime scored, sorted by confidence descending.

    Useful when the primary classification is borderline and the
    partner wants to see the second-most-likely regime.
    """
    out: List[RegimeResult] = []
    for name, fn in _REGIME_SCORERS:
        conf = fn(inputs)
        out.append(RegimeResult(
            regime=name,
            confidence=conf,
            signals=_build_signals(inputs),
            partner_note=_partner_note_for(name, conf),
            playbook=_REGIME_PLAYBOOK.get(name, ""),
            key_risk=_REGIME_KEY_RISK.get(name, ""),
        ))
    out.sort(key=lambda r: -r.confidence)
    return out
