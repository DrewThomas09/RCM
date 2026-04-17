"""Reasonableness bands — sanity checks a senior partner would apply.

A partner's first question when they see model output is not "is this
correct" — it's "is this reasonable." A 47% IRR on a $200M acute-care
deal is not impossible, but the partner will not fund it without a
specific story about why this situation breaks the peer pattern.

The bands here are deliberately wide (they are sanity checks, not point
estimates). They are calibrated from healthcare-PE deal experience
2018-2025 and survey data on middle-market healthcare transactions.
Sources and rationale are codified in ``docs/PE_HEURISTICS.md`` —
update that doc when you move a band.

Each check returns a :class:`BandCheck` with:

- ``verdict`` in {"IN_BAND", "STRETCH", "OUT_OF_BAND", "IMPLAUSIBLE"}
- ``observed`` numeric value
- ``band`` the reference range
- ``rationale`` one-sentence partner-voice explanation

None of these checks raise. Missing inputs → ``BandCheck`` with
``verdict="UNKNOWN"`` so downstream renderers can gracefully skip.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ── Enums-as-strings (keeping JSON-roundtrip ergonomic) ───────────────

VERDICT_IN_BAND = "IN_BAND"
VERDICT_STRETCH = "STRETCH"
VERDICT_OUT_OF_BAND = "OUT_OF_BAND"
VERDICT_IMPLAUSIBLE = "IMPLAUSIBLE"
VERDICT_UNKNOWN = "UNKNOWN"

ALL_VERDICTS = (
    VERDICT_IN_BAND,
    VERDICT_STRETCH,
    VERDICT_OUT_OF_BAND,
    VERDICT_IMPLAUSIBLE,
    VERDICT_UNKNOWN,
)


# ── Dataclasses ───────────────────────────────────────────────────────

@dataclass
class Band:
    """Reference range for one metric under one peer regime.

    - ``low`` / ``high`` are the partner-comfort band (IN_BAND).
    - ``stretch_high`` extends to "defensible with a specific story"
      (STRETCH). Above that is OUT_OF_BAND.
    - ``implausible_high`` is the "I don't believe the model" ceiling.
    Symmetric fields exist for the low side.
    """
    metric: str
    regime: str
    low: Optional[float] = None
    high: Optional[float] = None
    stretch_low: Optional[float] = None
    stretch_high: Optional[float] = None
    implausible_low: Optional[float] = None
    implausible_high: Optional[float] = None
    source: str = ""

    def classify(self, value: float) -> str:
        if value is None:
            return VERDICT_UNKNOWN
        lo, hi = self.low, self.high
        if lo is not None and hi is not None and lo <= value <= hi:
            return VERDICT_IN_BAND
        # High-side escalation
        if hi is not None and value > hi:
            if self.stretch_high is not None and value <= self.stretch_high:
                return VERDICT_STRETCH
            if self.implausible_high is not None and value > self.implausible_high:
                return VERDICT_IMPLAUSIBLE
            return VERDICT_OUT_OF_BAND
        # Low-side escalation
        if lo is not None and value < lo:
            if self.stretch_low is not None and value >= self.stretch_low:
                return VERDICT_STRETCH
            if self.implausible_low is not None and value < self.implausible_low:
                return VERDICT_IMPLAUSIBLE
            return VERDICT_OUT_OF_BAND
        # Only half of the band defined.
        if lo is None and hi is not None and value <= hi:
            return VERDICT_IN_BAND
        if hi is None and lo is not None and value >= lo:
            return VERDICT_IN_BAND
        return VERDICT_UNKNOWN

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric": self.metric,
            "regime": self.regime,
            "low": self.low,
            "high": self.high,
            "stretch_low": self.stretch_low,
            "stretch_high": self.stretch_high,
            "implausible_low": self.implausible_low,
            "implausible_high": self.implausible_high,
            "source": self.source,
        }


@dataclass
class BandCheck:
    metric: str
    observed: Optional[float]
    verdict: str
    band: Optional[Band] = None
    rationale: str = ""
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric": self.metric,
            "observed": self.observed,
            "verdict": self.verdict,
            "band": self.band.to_dict() if self.band else None,
            "rationale": self.rationale,
            "partner_note": self.partner_note,
        }


# ── Size buckets (by current EBITDA, in $M) ───────────────────────────
# Middle-market healthcare deals bucket by EBITDA, not revenue. Small
# deals tolerate wider IRR ranges because of the volatility premium.

SIZE_SMALL = "small"          # <$10M EBITDA
SIZE_LOWER_MID = "lower_mid"  # $10M-$25M
SIZE_MID = "mid"              # $25M-$75M
SIZE_UPPER_MID = "upper_mid"  # $75M-$200M
SIZE_LARGE = "large"          # >$200M


def classify_size(ebitda_m: Optional[float]) -> str:
    """Bucket a deal by EBITDA (in millions).

    Negative or missing EBITDA → "small" as the conservative default.
    """
    if ebitda_m is None or ebitda_m < 10.0:
        return SIZE_SMALL
    if ebitda_m < 25.0:
        return SIZE_LOWER_MID
    if ebitda_m < 75.0:
        return SIZE_MID
    if ebitda_m < 200.0:
        return SIZE_UPPER_MID
    return SIZE_LARGE


# ── Payer-mix regimes ────────────────────────────────────────────────
# Payer mix drives *everything* — reimbursement, rate growth, denial
# rates, regulatory risk. Partners think in three regimes:

PAYER_COMMERCIAL_HEAVY = "commercial_heavy"    # Commercial >= 45%
PAYER_BALANCED = "balanced"                    # Medicare 30-50%, Commercial 25-45%
PAYER_MEDICARE_HEAVY = "medicare_heavy"        # Medicare >= 55%
PAYER_MEDICAID_HEAVY = "medicaid_heavy"        # Medicaid >= 30%
PAYER_GOVT_HEAVY = "govt_heavy"                # Medicare + Medicaid >= 70%


def classify_payer_mix(payer_mix: Optional[Dict[str, float]]) -> str:
    """Classify a hospital's payer mix into a partner-thinking regime.

    Payer-mix keys are lowercased to tolerate both "Medicare" and
    "medicare". Values are fractions (0.35) or percents (35) — we
    auto-normalize by checking the sum.
    """
    if not payer_mix:
        return PAYER_BALANCED  # unknown → neutral prior
    norm = _normalize_payer_mix(payer_mix)
    medicare = norm.get("medicare", 0.0)
    medicaid = norm.get("medicaid", 0.0)
    commercial = norm.get("commercial", 0.0)
    # Ordering matters — medicaid_heavy fires before medicare_heavy
    # because a dual-heavy deal should show the more regulatory-risky
    # regime.
    if medicare + medicaid >= 0.70:
        return PAYER_GOVT_HEAVY
    if medicaid >= 0.30:
        return PAYER_MEDICAID_HEAVY
    if medicare >= 0.55:
        return PAYER_MEDICARE_HEAVY
    if commercial >= 0.45:
        return PAYER_COMMERCIAL_HEAVY
    return PAYER_BALANCED


def _normalize_payer_mix(mix: Dict[str, float]) -> Dict[str, float]:
    """Return a {payer: fraction} dict keyed lowercase, summing ~1.0.

    Handles inputs given as percentages (sum ~100) or fractions (sum
    ~1). If the sum is implausible (0 or >200), returns as-is divided
    by 100 on a best-effort basis.
    """
    if not mix:
        return {}
    low = {str(k).lower().strip(): float(v) for k, v in mix.items()
           if v is not None}
    total = sum(low.values())
    if total <= 0:
        return low
    if total > 1.5:  # looks like percentages
        return {k: v / 100.0 for k, v in low.items()}
    return low


# ── IRR bands by (size, payer_regime) ─────────────────────────────────
# These are the partner-defensible IRR ranges for a 5-year hold under
# reasonable leverage assumptions. See docs/PE_HEURISTICS.md for the
# full derivation.

_IRR_BANDS: Dict[Tuple[str, str], Band] = {
    # Commercial-heavy deals can sustain higher IRR because of rate
    # growth and exit-multiple expansion optionality.
    (SIZE_SMALL, PAYER_COMMERCIAL_HEAVY): Band(
        metric="irr", regime="small / commercial-heavy",
        low=0.18, high=0.32, stretch_high=0.40, implausible_high=0.55,
        implausible_low=0.0,
        source="HC-PE 2019-2024 small-cap commercial deals",
    ),
    (SIZE_LOWER_MID, PAYER_COMMERCIAL_HEAVY): Band(
        metric="irr", regime="lower-mid / commercial-heavy",
        low=0.18, high=0.30, stretch_high=0.38, implausible_high=0.50,
        source="HC-PE 2019-2024",
    ),
    (SIZE_MID, PAYER_COMMERCIAL_HEAVY): Band(
        metric="irr", regime="mid / commercial-heavy",
        low=0.16, high=0.26, stretch_high=0.34, implausible_high=0.45,
        source="HC-PE 2019-2024",
    ),
    (SIZE_UPPER_MID, PAYER_COMMERCIAL_HEAVY): Band(
        metric="irr", regime="upper-mid / commercial-heavy",
        low=0.14, high=0.22, stretch_high=0.28, implausible_high=0.38,
        source="HC-PE 2019-2024",
    ),
    (SIZE_LARGE, PAYER_COMMERCIAL_HEAVY): Band(
        metric="irr", regime="large / commercial-heavy",
        low=0.12, high=0.20, stretch_high=0.25, implausible_high=0.35,
        source="HC-PE 2019-2024 large-cap",
    ),
    # Balanced — default prior.
    (SIZE_SMALL, PAYER_BALANCED): Band(
        metric="irr", regime="small / balanced payer mix",
        low=0.15, high=0.28, stretch_high=0.35, implausible_high=0.48,
        source="HC-PE middle-market balanced",
    ),
    (SIZE_LOWER_MID, PAYER_BALANCED): Band(
        metric="irr", regime="lower-mid / balanced",
        low=0.15, high=0.25, stretch_high=0.32, implausible_high=0.42,
        source="HC-PE middle-market balanced",
    ),
    (SIZE_MID, PAYER_BALANCED): Band(
        metric="irr", regime="mid / balanced",
        low=0.14, high=0.22, stretch_high=0.28, implausible_high=0.38,
        source="HC-PE middle-market balanced",
    ),
    (SIZE_UPPER_MID, PAYER_BALANCED): Band(
        metric="irr", regime="upper-mid / balanced",
        low=0.12, high=0.20, stretch_high=0.25, implausible_high=0.32,
        source="HC-PE middle-market balanced",
    ),
    (SIZE_LARGE, PAYER_BALANCED): Band(
        metric="irr", regime="large / balanced",
        low=0.10, high=0.18, stretch_high=0.22, implausible_high=0.30,
        source="HC-PE large-cap balanced",
    ),
    # Medicare-heavy — rate sensitivity compresses returns.
    (SIZE_SMALL, PAYER_MEDICARE_HEAVY): Band(
        metric="irr", regime="small / Medicare-heavy",
        low=0.10, high=0.20, stretch_high=0.26, implausible_high=0.34,
        source="HC-PE CMS-exposed deals",
    ),
    (SIZE_LOWER_MID, PAYER_MEDICARE_HEAVY): Band(
        metric="irr", regime="lower-mid / Medicare-heavy",
        low=0.10, high=0.18, stretch_high=0.24, implausible_high=0.30,
        source="HC-PE CMS-exposed deals",
    ),
    (SIZE_MID, PAYER_MEDICARE_HEAVY): Band(
        metric="irr", regime="mid / Medicare-heavy",
        low=0.09, high=0.16, stretch_high=0.21, implausible_high=0.28,
        source="HC-PE CMS-exposed deals",
    ),
    (SIZE_UPPER_MID, PAYER_MEDICARE_HEAVY): Band(
        metric="irr", regime="upper-mid / Medicare-heavy",
        low=0.08, high=0.14, stretch_high=0.18, implausible_high=0.24,
        source="HC-PE CMS-exposed deals",
    ),
    (SIZE_LARGE, PAYER_MEDICARE_HEAVY): Band(
        metric="irr", regime="large / Medicare-heavy",
        low=0.07, high=0.12, stretch_high=0.16, implausible_high=0.22,
        source="HC-PE large-cap CMS-exposed",
    ),
    # Medicaid-heavy — state-rate volatility widens dispersion.
    (SIZE_SMALL, PAYER_MEDICAID_HEAVY): Band(
        metric="irr", regime="small / Medicaid-heavy",
        low=0.10, high=0.22, stretch_high=0.28, implausible_high=0.36,
        source="HC-PE safety-net deals",
    ),
    (SIZE_LOWER_MID, PAYER_MEDICAID_HEAVY): Band(
        metric="irr", regime="lower-mid / Medicaid-heavy",
        low=0.09, high=0.20, stretch_high=0.25, implausible_high=0.32,
        source="HC-PE safety-net deals",
    ),
    (SIZE_MID, PAYER_MEDICAID_HEAVY): Band(
        metric="irr", regime="mid / Medicaid-heavy",
        low=0.08, high=0.17, stretch_high=0.22, implausible_high=0.28,
        source="HC-PE safety-net deals",
    ),
    (SIZE_UPPER_MID, PAYER_MEDICAID_HEAVY): Band(
        metric="irr", regime="upper-mid / Medicaid-heavy",
        low=0.07, high=0.14, stretch_high=0.18, implausible_high=0.24,
        source="HC-PE safety-net deals",
    ),
    (SIZE_LARGE, PAYER_MEDICAID_HEAVY): Band(
        metric="irr", regime="large / Medicaid-heavy",
        low=0.06, high=0.12, stretch_high=0.15, implausible_high=0.20,
        source="HC-PE safety-net deals",
    ),
    # Government-heavy (Medicare + Medicaid ≥ 70%) — hardest regime.
    (SIZE_SMALL, PAYER_GOVT_HEAVY): Band(
        metric="irr", regime="small / government-heavy",
        low=0.08, high=0.18, stretch_high=0.23, implausible_high=0.30,
        source="HC-PE government-heavy deals",
    ),
    (SIZE_LOWER_MID, PAYER_GOVT_HEAVY): Band(
        metric="irr", regime="lower-mid / government-heavy",
        low=0.08, high=0.16, stretch_high=0.21, implausible_high=0.27,
        source="HC-PE government-heavy deals",
    ),
    (SIZE_MID, PAYER_GOVT_HEAVY): Band(
        metric="irr", regime="mid / government-heavy",
        low=0.07, high=0.14, stretch_high=0.18, implausible_high=0.24,
        source="HC-PE government-heavy deals",
    ),
    (SIZE_UPPER_MID, PAYER_GOVT_HEAVY): Band(
        metric="irr", regime="upper-mid / government-heavy",
        low=0.06, high=0.12, stretch_high=0.16, implausible_high=0.20,
        source="HC-PE government-heavy deals",
    ),
    (SIZE_LARGE, PAYER_GOVT_HEAVY): Band(
        metric="irr", regime="large / government-heavy",
        low=0.05, high=0.10, stretch_high=0.13, implausible_high=0.18,
        source="HC-PE large-cap government-heavy",
    ),
}


def get_irr_band(size_bucket: str, payer_regime: str) -> Band:
    """Resolve the IRR band for a (size, payer) regime. Falls back to
    the balanced band for the same size if the exact pair is missing."""
    band = _IRR_BANDS.get((size_bucket, payer_regime))
    if band is not None:
        return band
    return _IRR_BANDS.get((size_bucket, PAYER_BALANCED),
                          _IRR_BANDS[(SIZE_MID, PAYER_BALANCED)])


def check_irr(
    irr: Optional[float],
    *,
    ebitda_m: Optional[float],
    payer_mix: Optional[Dict[str, float]] = None,
) -> BandCheck:
    """Classify an IRR against the (size, payer) peer band."""
    if irr is None:
        return BandCheck(
            metric="irr", observed=None, verdict=VERDICT_UNKNOWN,
            rationale="IRR not reported; cannot assess reasonableness.",
        )
    size = classify_size(ebitda_m)
    regime = classify_payer_mix(payer_mix)
    band = get_irr_band(size, regime)
    verdict = band.classify(irr)
    rationale = _irr_rationale(irr, band, verdict)
    note = _irr_partner_note(irr, band, verdict)
    return BandCheck(
        metric="irr", observed=irr, verdict=verdict,
        band=band, rationale=rationale, partner_note=note,
    )


def _irr_rationale(irr: float, band: Band, verdict: str) -> str:
    pct = f"{irr * 100:.1f}%"
    lo_pct = f"{(band.low or 0) * 100:.1f}%"
    hi_pct = f"{(band.high or 0) * 100:.1f}%"
    if verdict == VERDICT_IN_BAND:
        return (f"{pct} IRR sits inside the {lo_pct}–{hi_pct} peer band "
                f"for {band.regime} deals.")
    if verdict == VERDICT_STRETCH:
        return (f"{pct} IRR is above the {hi_pct} ceiling for "
                f"{band.regime} — defensible with a concrete alpha story.")
    if verdict == VERDICT_OUT_OF_BAND:
        if irr < (band.low or 0):
            return (f"{pct} IRR falls below the {lo_pct} floor for "
                    f"{band.regime} — most LPs pass at this level.")
        return (f"{pct} IRR exceeds the peer ceiling for "
                f"{band.regime}; assumptions likely too rosy.")
    if verdict == VERDICT_IMPLAUSIBLE:
        return (f"{pct} IRR is implausible for {band.regime}. "
                f"Re-check exit multiple, leverage, or lever timing before "
                f"taking this to IC.")
    return "IRR classification unavailable."


def _irr_partner_note(irr: float, band: Band, verdict: str) -> str:
    if verdict == VERDICT_IN_BAND:
        return "Reasonable. Move on."
    if verdict == VERDICT_STRETCH:
        return ("Tell me the alpha story in one sentence. If you can't, "
                "the model's optimism is doing the work.")
    if verdict == VERDICT_OUT_OF_BAND and irr > (band.high or 0):
        return "Either the entry is too cheap or the lever ramp is too fast. Check both."
    if verdict == VERDICT_OUT_OF_BAND:
        return "Below fund hurdle for this regime. Not fundable as modeled."
    if verdict == VERDICT_IMPLAUSIBLE:
        return "Something is wrong in the model. Do not show this number at IC."
    return ""


# ── EBITDA margin bands by hospital type ─────────────────────────────
# Healthcare subtype drives margin range. Acute care, behavioral, ASC,
# and post-acute all have different structural margins.

HTYPE_ACUTE = "acute_care"
HTYPE_ASC = "asc"                      # Ambulatory Surgery Center
HTYPE_BEHAVIORAL = "behavioral"
HTYPE_POST_ACUTE = "post_acute"
HTYPE_SPECIALTY = "specialty"          # specialty hospitals, ortho, cardio
HTYPE_OUTPATIENT = "outpatient"
HTYPE_CRITICAL_ACCESS = "critical_access"

_MARGIN_BANDS: Dict[str, Band] = {
    HTYPE_ACUTE: Band(
        metric="ebitda_margin", regime="acute-care hospital",
        low=0.04, high=0.12, stretch_high=0.15, implausible_high=0.25,
        implausible_low=-0.15,
        source="AHA + CMS cost reports, 2019-2024",
    ),
    HTYPE_ASC: Band(
        metric="ebitda_margin", regime="ambulatory surgery center",
        low=0.18, high=0.32, stretch_high=0.40, implausible_high=0.55,
        implausible_low=0.0,
        source="ASC industry surveys",
    ),
    HTYPE_BEHAVIORAL: Band(
        metric="ebitda_margin", regime="behavioral health",
        low=0.12, high=0.22, stretch_high=0.28, implausible_high=0.38,
        implausible_low=-0.05,
        source="Behavioral-health PE deal data",
    ),
    HTYPE_POST_ACUTE: Band(
        metric="ebitda_margin", regime="post-acute / SNF",
        low=0.06, high=0.14, stretch_high=0.18, implausible_high=0.25,
        implausible_low=-0.10,
        source="Post-acute sector data",
    ),
    HTYPE_SPECIALTY: Band(
        metric="ebitda_margin", regime="specialty hospital",
        low=0.10, high=0.20, stretch_high=0.28, implausible_high=0.40,
        implausible_low=-0.05,
        source="Specialty-hospital deal data",
    ),
    HTYPE_OUTPATIENT: Band(
        metric="ebitda_margin", regime="outpatient / clinic",
        low=0.10, high=0.22, stretch_high=0.30, implausible_high=0.42,
        implausible_low=-0.05,
        source="Outpatient physician-practice data",
    ),
    HTYPE_CRITICAL_ACCESS: Band(
        metric="ebitda_margin", regime="critical access hospital",
        low=0.0, high=0.06, stretch_high=0.10, implausible_high=0.15,
        implausible_low=-0.20,
        source="CAH cost-report data",
    ),
}


def get_margin_band(hospital_type: Optional[str]) -> Band:
    if not hospital_type:
        return _MARGIN_BANDS[HTYPE_ACUTE]
    key = str(hospital_type).lower().strip().replace("-", "_").replace(" ", "_")
    # tolerate a few common aliases
    alias = {
        "hospital": HTYPE_ACUTE,
        "acute": HTYPE_ACUTE,
        "acute_care_hospital": HTYPE_ACUTE,
        "surgery_center": HTYPE_ASC,
        "ambulatory": HTYPE_ASC,
        "snf": HTYPE_POST_ACUTE,
        "ltach": HTYPE_POST_ACUTE,
        "rehab": HTYPE_POST_ACUTE,
        "psych": HTYPE_BEHAVIORAL,
        "mental_health": HTYPE_BEHAVIORAL,
        "clinic": HTYPE_OUTPATIENT,
        "physician_practice": HTYPE_OUTPATIENT,
        "cah": HTYPE_CRITICAL_ACCESS,
    }
    key = alias.get(key, key)
    return _MARGIN_BANDS.get(key, _MARGIN_BANDS[HTYPE_ACUTE])


def check_ebitda_margin(
    margin: Optional[float],
    *,
    hospital_type: Optional[str],
) -> BandCheck:
    """Classify an EBITDA margin against the hospital-type band."""
    if margin is None:
        return BandCheck(
            metric="ebitda_margin", observed=None, verdict=VERDICT_UNKNOWN,
            rationale="EBITDA margin not computed.",
        )
    band = get_margin_band(hospital_type)
    verdict = band.classify(margin)
    pct = f"{margin * 100:.1f}%"
    hi_pct = f"{(band.high or 0) * 100:.1f}%"
    lo_pct = f"{(band.low or 0) * 100:.1f}%"
    if verdict == VERDICT_IN_BAND:
        rationale = f"{pct} margin is consistent with {band.regime} peers ({lo_pct}–{hi_pct})."
        note = "Normal operating profile."
    elif verdict == VERDICT_STRETCH:
        rationale = f"{pct} margin is above the {hi_pct} peer ceiling for {band.regime}."
        note = "Either best-in-class ops or a coding/payer mix that won't persist. Dig in."
    elif verdict == VERDICT_IMPLAUSIBLE and margin < (band.low or 0):
        rationale = f"{pct} margin is below the implausible floor for {band.regime}."
        note = "This is a turnaround, not an operating business. Re-underwrite accordingly."
    elif verdict == VERDICT_IMPLAUSIBLE:
        rationale = f"{pct} margin is implausibly high for {band.regime}."
        note = "Check denominator — revenue may be understated or one-time items inflating EBITDA."
    elif verdict == VERDICT_OUT_OF_BAND and margin < (band.low or 0):
        rationale = f"{pct} margin is below the {lo_pct} peer floor for {band.regime}."
        note = "Identify the structural driver before underwriting recovery."
    else:
        rationale = f"{pct} margin is above the peer ceiling for {band.regime}."
        note = "Outperformance needs a named operating advantage. If you can't name it, don't trust it."
    return BandCheck(
        metric="ebitda_margin", observed=margin, verdict=verdict,
        band=band, rationale=rationale, partner_note=note,
    )


# ── Lever realizability ──────────────────────────────────────────────
# Realizability bands: how much lift can a lever realistically deliver
# in a given timeframe. A lever that claims 300 bps of denial-rate
# improvement in 12 months is aggressive; 600 bps is implausible.

@dataclass
class LeverTimeframe:
    """How much improvement a lever can realistically deliver in N
    months. Values are in *bps* for rate metrics and in *days* for
    working-capital metrics — signalled by ``unit``.
    """
    lever: str
    unit: str                   # "bps" | "days" | "pct"
    months: int
    reasonable_max: float
    stretch_max: float
    implausible_max: float
    context: str = ""


_LEVER_TIMEFRAMES: List[LeverTimeframe] = [
    # Denial rate — in basis points (bps) reduction
    LeverTimeframe("denial_rate", "bps", 6,
                   reasonable_max=100, stretch_max=175, implausible_max=300,
                   context="6-month denial reduction — front-end edits only"),
    LeverTimeframe("denial_rate", "bps", 12,
                   reasonable_max=200, stretch_max=350, implausible_max=600,
                   context="12-month denial reduction — full program in place"),
    LeverTimeframe("denial_rate", "bps", 24,
                   reasonable_max=400, stretch_max=650, implausible_max=1000,
                   context="24-month denial reduction — matured program"),
    # Days in AR — in days reduction
    LeverTimeframe("days_in_ar", "days", 6,
                   reasonable_max=5, stretch_max=9, implausible_max=15,
                   context="6-month AR days reduction"),
    LeverTimeframe("days_in_ar", "days", 12,
                   reasonable_max=10, stretch_max=18, implausible_max=30,
                   context="12-month AR days reduction"),
    LeverTimeframe("days_in_ar", "days", 24,
                   reasonable_max=18, stretch_max=30, implausible_max=50,
                   context="24-month AR days reduction"),
    # Clean claim rate — in bps improvement
    LeverTimeframe("clean_claim_rate", "bps", 6,
                   reasonable_max=150, stretch_max=300, implausible_max=500,
                   context="6-month clean-claim improvement"),
    LeverTimeframe("clean_claim_rate", "bps", 12,
                   reasonable_max=400, stretch_max=700, implausible_max=1100,
                   context="12-month clean-claim improvement"),
    LeverTimeframe("clean_claim_rate", "bps", 24,
                   reasonable_max=750, stretch_max=1200, implausible_max=1800,
                   context="24-month clean-claim improvement"),
    # Final write-off rate — in bps reduction
    LeverTimeframe("final_writeoff_rate", "bps", 12,
                   reasonable_max=150, stretch_max=275, implausible_max=450,
                   context="12-month write-off reduction"),
    LeverTimeframe("final_writeoff_rate", "bps", 24,
                   reasonable_max=300, stretch_max=500, implausible_max=800,
                   context="24-month write-off reduction"),
    # NPSR margin expansion — in pct points
    LeverTimeframe("npsr_margin", "pct", 12,
                   reasonable_max=1.0, stretch_max=2.0, implausible_max=3.5,
                   context="12-month NPSR margin expansion"),
    LeverTimeframe("npsr_margin", "pct", 24,
                   reasonable_max=2.0, stretch_max=3.5, implausible_max=5.5,
                   context="24-month NPSR margin expansion"),
    # Net revenue growth (organic) — pct
    LeverTimeframe("organic_rev_growth", "pct", 12,
                   reasonable_max=6.0, stretch_max=10.0, implausible_max=18.0,
                   context="12-month organic revenue growth"),
]


def get_lever_timeframe(lever: str, months: int) -> Optional[LeverTimeframe]:
    """Pick the nearest timeframe entry for a lever. Returns the entry
    whose ``months`` is closest to the requested window, preferring a
    shorter window on ties (conservative)."""
    matching = [lt for lt in _LEVER_TIMEFRAMES if lt.lever == lever]
    if not matching:
        return None
    return min(matching, key=lambda lt: (abs(lt.months - months), lt.months))


def check_lever_realizability(
    lever: str,
    magnitude: float,
    months: int,
) -> BandCheck:
    """Classify a single lever's claimed improvement over a window.

    ``magnitude`` is in the unit native to the lever (bps for rates,
    days for AR, pct for margins). Callers are expected to pre-convert.
    """
    lt = get_lever_timeframe(lever, months)
    if lt is None:
        return BandCheck(
            metric=f"lever:{lever}", observed=magnitude, verdict=VERDICT_UNKNOWN,
            rationale=f"No realizability band defined for lever {lever!r}.",
        )
    # Inverse levers (days_in_ar reduction is improvement) are passed
    # in as positive magnitudes too.
    abs_mag = abs(magnitude)
    if abs_mag <= lt.reasonable_max:
        verdict = VERDICT_IN_BAND
    elif abs_mag <= lt.stretch_max:
        verdict = VERDICT_STRETCH
    elif abs_mag <= lt.implausible_max:
        verdict = VERDICT_OUT_OF_BAND
    else:
        verdict = VERDICT_IMPLAUSIBLE

    unit_label = {"bps": "bps", "days": "days", "pct": "pct points"}.get(lt.unit, lt.unit)
    rationale = (
        f"{lt.context}: claiming {abs_mag:.0f} {unit_label} in {months}mo "
        f"(reasonable ≤ {lt.reasonable_max:.0f}, stretch ≤ {lt.stretch_max:.0f}, "
        f"implausible > {lt.implausible_max:.0f})."
    )
    note = _lever_partner_note(verdict, lever)
    band = Band(
        metric=f"lever:{lever}", regime=f"{months}mo realizability",
        low=0.0, high=lt.reasonable_max, stretch_high=lt.stretch_max,
        implausible_high=lt.implausible_max,
        source="RCM-PE lever realization bands",
    )
    return BandCheck(
        metric=f"lever:{lever}", observed=abs_mag, verdict=verdict,
        band=band, rationale=rationale, partner_note=note,
    )


def _lever_partner_note(verdict: str, lever: str) -> str:
    if verdict == VERDICT_IN_BAND:
        return "Achievable with disciplined execution."
    if verdict == VERDICT_STRETCH:
        return (f"Ambitious. Confirm the {lever} program has a named owner, "
                "milestones, and a capex commitment.")
    if verdict == VERDICT_OUT_OF_BAND:
        return (f"Aggressive — I've not seen {lever} move this fast without "
                "a full platform change. Discount the projection.")
    if verdict == VERDICT_IMPLAUSIBLE:
        return ("Model says, world disagrees. Remove from the base case; keep "
                "in upside only.")
    return ""


# ── Exit multiple ceiling by payer mix ───────────────────────────────
# Medicare-heavy deals trade at a structural multiple discount to
# commercial-heavy peers.

_MULTIPLE_CEILINGS: Dict[str, Band] = {
    PAYER_COMMERCIAL_HEAVY: Band(
        metric="exit_multiple", regime="commercial-heavy",
        low=7.0, high=11.0, stretch_high=13.5, implausible_high=16.5,
        source="HC-PE exit comps",
    ),
    PAYER_BALANCED: Band(
        metric="exit_multiple", regime="balanced payer mix",
        low=6.5, high=10.0, stretch_high=12.0, implausible_high=14.5,
        source="HC-PE exit comps",
    ),
    PAYER_MEDICARE_HEAVY: Band(
        metric="exit_multiple", regime="Medicare-heavy",
        low=5.5, high=8.5, stretch_high=10.5, implausible_high=13.0,
        source="HC-PE exit comps",
    ),
    PAYER_MEDICAID_HEAVY: Band(
        metric="exit_multiple", regime="Medicaid-heavy",
        low=5.0, high=7.5, stretch_high=9.5, implausible_high=12.0,
        source="HC-PE exit comps",
    ),
    PAYER_GOVT_HEAVY: Band(
        metric="exit_multiple", regime="government-heavy",
        low=4.5, high=7.0, stretch_high=9.0, implausible_high=11.5,
        source="HC-PE exit comps",
    ),
}


def check_multiple_ceiling(
    multiple: Optional[float],
    *,
    payer_mix: Optional[Dict[str, float]] = None,
) -> BandCheck:
    """Classify an exit multiple against the payer-regime ceiling."""
    if multiple is None:
        return BandCheck(
            metric="exit_multiple", observed=None, verdict=VERDICT_UNKNOWN,
            rationale="Exit multiple not modeled.",
        )
    regime = classify_payer_mix(payer_mix)
    band = _MULTIPLE_CEILINGS.get(regime, _MULTIPLE_CEILINGS[PAYER_BALANCED])
    verdict = band.classify(multiple)
    hi = f"{band.high:.1f}x" if band.high is not None else "n/a"
    if verdict == VERDICT_IN_BAND:
        rationale = f"{multiple:.2f}x exit is within the {band.regime} ceiling (~{hi})."
        note = "Reasonable exit assumption."
    elif verdict == VERDICT_STRETCH:
        rationale = f"{multiple:.2f}x exit stretches past the {band.regime} ceiling (~{hi})."
        note = "Multiple expansion is carrying the return. If multiples compress, the deal breaks."
    elif verdict == VERDICT_OUT_OF_BAND and multiple > (band.high or 0):
        rationale = f"{multiple:.2f}x exit is above the {band.regime} peer ceiling."
        note = "Do not underwrite multiple expansion you can't defend with a comparable. This is where deals die."
    elif verdict == VERDICT_OUT_OF_BAND:
        rationale = f"{multiple:.2f}x exit is unusually low for {band.regime}."
        note = "If this is conservatism, fine. If it's a forced-sale scenario, say so explicitly."
    elif verdict == VERDICT_IMPLAUSIBLE:
        rationale = f"{multiple:.2f}x is implausible for {band.regime} — no comp supports this."
        note = "Reset the exit multiple to the peer ceiling before taking this to IC."
    else:
        rationale = f"{multiple:.2f}x exit vs {band.regime} peers."
        note = ""
    return BandCheck(
        metric="exit_multiple", observed=multiple, verdict=verdict,
        band=band, rationale=rationale, partner_note=note,
    )


# ── Orchestrator ─────────────────────────────────────────────────────

def run_reasonableness_checks(
    *,
    irr: Optional[float] = None,
    ebitda_margin: Optional[float] = None,
    ebitda_m: Optional[float] = None,
    exit_multiple: Optional[float] = None,
    hospital_type: Optional[str] = None,
    payer_mix: Optional[Dict[str, float]] = None,
    lever_claims: Optional[List[Dict[str, Any]]] = None,
) -> List[BandCheck]:
    """Run every reasonableness check that has enough input to fire.

    ``lever_claims`` is a list of ``{"lever": str, "magnitude": float,
    "months": int}`` dicts. Unknown levers produce a ``UNKNOWN``
    verdict rather than raising.
    """
    out: List[BandCheck] = []
    out.append(check_irr(irr, ebitda_m=ebitda_m, payer_mix=payer_mix))
    out.append(check_ebitda_margin(ebitda_margin, hospital_type=hospital_type))
    out.append(check_multiple_ceiling(exit_multiple, payer_mix=payer_mix))
    for claim in (lever_claims or []):
        lever = str(claim.get("lever") or "").strip()
        if not lever:
            continue
        mag = claim.get("magnitude")
        months = int(claim.get("months") or 12)
        if mag is None:
            continue
        try:
            mag_f = float(mag)
        except (TypeError, ValueError):
            continue
        out.append(check_lever_realizability(lever, mag_f, months))
    return out
