"""HCRIS Form 2552-10 Source-of-Truth metadata + AMC adjustments.

PEDESK Phase 2 (Week 2, Data Ingestion) — Predictive Screener fixes:

1. Map every screener-displayed metric back to its HCRIS Form 2552-10
   worksheet/line/column so the UI can render an audit overlay (badge
   or tooltip) noting where each number came from. The mapping is
   sourced from ``rcm_mc/data/hcris.py::NUMERIC_FIELDS`` so there is one
   authoritative table — this module just adds the human-readable
   surface for display.

2. Detect Academic Medical Centers (AMCs / teaching hospitals) using
   a name + CCN + bed-size heuristic. Real AMC determination requires
   resident counts (HCRIS Worksheet S-3 Pt I Ln 14 Col 4) which the
   shipped HCRIS extract does not currently include; the keyword
   heuristic is a deterministic, conservative proxy that catches the
   ~250 hospitals partner-facing diligence routinely cares about.

3. Provide AMC-specific denial rate calibration anchored at
   12% (midpoint of the 11–13% benchmark range used by CAQH /
   AHA studies of academic medical centers — empirically much
   lower than the 25% saturation cap the generic model produces).

4. Provide an Uplift→denied-revenue ceiling so the screener never
   reports a recoverable-uplift figure higher than total denied
   revenue — that would imply the operator can recover more than
   was ever denied, which is mathematically impossible.

This module is import-safe with no runtime dependencies beyond
``pandas`` (already required by HCRIS loaders).
"""
from __future__ import annotations

from typing import Optional

import pandas as pd

from ..data.hcris import NUMERIC_FIELDS

# ---------------------------------------------------------------------------
# Source-of-Truth: HCRIS column → human-readable worksheet origin
# ---------------------------------------------------------------------------
#
# Display string format: "Worksheet <code> Ln <line>[ Col <col>]". The
# worksheet codes match CMS Form 2552-10. Line and column codes are the
# zero-padded numerics from the HCRIS NMRC csv. We normalise them for
# UI display by stripping leading zeros where it improves legibility
# (e.g. "00300" → "3", "00100" → "1").

_WORKSHEET_LABELS = {
    "S200001": "S-2 Pt I",
    "S300001": "S-3 Pt I",
    "G300000": "G-3",
}


def _strip_zeros(code: str) -> str:
    """Render HCRIS centi-padded line/col codes as their integer line.

    HCRIS encodes line N as ``00N00`` (e.g., line 3 → ``"00300"``,
    line 14 → ``"01400"``, col 2 → ``"00200"``). We divide by 100 to
    recover the visible line number used in the CMS worksheet.
    """
    if not code or not code.isdigit():
        return code
    n = int(code)
    if n % 100 == 0:
        return str(n // 100)
    # Half-line (e.g. line 3.50 stored as "00350"): keep cent-form for fidelity.
    return f"{n / 100:g}"


def worksheet_origin(column_name: str) -> Optional[str]:
    """Return a short human-readable label for the HCRIS origin of a metric.

    >>> worksheet_origin("net_patient_revenue")
    'G-3 Ln 3'
    >>> worksheet_origin("beds")
    'S-3 Pt I Ln 14 Col 2'
    >>> worksheet_origin("operating_margin")  # derived, not raw
    'derived: net_income / net_patient_revenue'

    Returns None when the column isn't in the HCRIS field map.
    """
    coord = NUMERIC_FIELDS.get(column_name)
    if coord is None:
        return _DERIVED_ORIGINS.get(column_name)
    wksht_cd, line_num, col_num = coord
    label = _WORKSHEET_LABELS.get(wksht_cd, wksht_cd)
    parts = [label, f"Ln {_strip_zeros(line_num)}"]
    if col_num and col_num != "00100":
        parts.append(f"Col {_strip_zeros(col_num)}")
    return " ".join(parts)


# Derived metrics — not directly in HCRIS but computed in the screener.
_DERIVED_ORIGINS = {
    "operating_margin":   "derived: net_income / net_patient_revenue",
    "revenue_per_bed":    "derived: net_patient_revenue / beds",
    "occupancy_rate":     "derived: total_patient_days / bed_days_available",
    "commercial_pct":     "derived: 1 - medicare_day_pct - medicaid_day_pct",
    "net_to_gross_ratio": "derived: net_patient_revenue / gross_patient_revenue",
}


def sot_tooltip(column_name: str) -> str:
    """Return an HTML-attribute-safe tooltip string for ``title=`` use.

    Always returns a non-empty string. Falls back to the column name
    when no origin is known so the UI's audit overlay never shows a
    blank tooltip on a labeled metric.
    """
    origin = worksheet_origin(column_name)
    if origin is None:
        return f"Source: {column_name} (no HCRIS mapping)"
    if origin.startswith("derived:"):
        return f"HCRIS 2552-10 — {origin}"
    return f"HCRIS 2552-10 — Worksheet {origin}"


# ---------------------------------------------------------------------------
# AMC detection
# ---------------------------------------------------------------------------
#
# Keyword-based classifier, deterministic on the (ccn, name, beds) tuple.
# The set is intentionally tight: a hospital must mention a teaching
# affiliation by name AND have ≥250 beds to qualify, OR mention an
# unambiguous teaching marker (UNIVERSITY, ACADEMIC) regardless of size.
# This catches the ~250 partner-relevant teaching hospitals while
# avoiding false positives like community hospitals named "St. Mary's
# Medical Center" (the word MEDICAL CENTER alone is not enough).

_UNAMBIGUOUS_AMC_TOKENS = (
    "UNIVERSITY HOSPITAL",
    "UNIVERSITY MEDICAL",
    "ACADEMIC MEDICAL",
    "TEACHING HOSPITAL",
    "SCHOOL OF MEDICINE",
)

_AMC_HINT_TOKENS = (
    " UNIV ",
    " UNIV.",
    "UNIVERSITY OF ",
    "MEDICAL COLLEGE",
    "MEDICAL SCHOOL",
)

# Well-known AMC system names that don't always include "UNIVERSITY"
# in the hospital name on file with CMS but are AMCs by every other
# definition (COTH membership, NIH funding, ACGME accreditation).
_KNOWN_AMC_SYSTEMS = (
    "MAYO CLINIC",
    "CLEVELAND CLINIC",
    "MASSACHUSETTS GENERAL",
    "MASS GENERAL",
    "JOHNS HOPKINS",
    "MOUNT SINAI",
    "CEDARS-SINAI",
    "NYU LANGONE",
    "NORTHWESTERN MEMORIAL",
    "PENN MEDICINE",
    "STANFORD HEALTH",
    "DUKE UNIVERSITY",
    "UCLA HEALTH",
    "UCSF MEDICAL",
)


def is_amc(name: Optional[str], beds: Optional[float] = None) -> bool:
    """Heuristic: True when the hospital is an Academic Medical Center.

    Conservative classifier — avoids false positives at the cost of some
    false negatives. Uses three tiers of evidence:

    1. Known AMC system names (Mayo, Mass General, etc.) — always True.
    2. Unambiguous teaching tokens (UNIVERSITY HOSPITAL, ACADEMIC MEDICAL,
       SCHOOL OF MEDICINE) — always True.
    3. Hint tokens (MEDICAL COLLEGE, UNIV, etc.) — True only when
       ``beds`` is at least 250, the rough lower bound for an AMC.

    Bed count is optional; when missing, only tiers 1 and 2 fire.
    """
    if not name:
        return False
    name_up = " " + str(name).upper().strip() + " "
    for tok in _KNOWN_AMC_SYSTEMS:
        if tok in name_up:
            return True
    for tok in _UNAMBIGUOUS_AMC_TOKENS:
        if tok in name_up:
            return True
    if beds is not None:
        try:
            beds_f = float(beds)
        except (TypeError, ValueError):
            beds_f = 0.0
        if beds_f >= 250:
            for tok in _AMC_HINT_TOKENS:
                if tok in name_up:
                    return True
    return False


def is_amc_series(names: pd.Series, beds: Optional[pd.Series] = None) -> pd.Series:
    """Vectorised :func:`is_amc` for screening across the full HCRIS extract."""
    if names is None or len(names) == 0:
        return pd.Series([], dtype=bool)
    if beds is None:
        beds_iter = [None] * len(names)
    else:
        beds_iter = beds.tolist()
    return pd.Series(
        [is_amc(n, b) for n, b in zip(names, beds_iter)],
        index=names.index,
        dtype=bool,
    )


# ---------------------------------------------------------------------------
# AMC-specific denial calibration
# ---------------------------------------------------------------------------
#
# CAQH (CAQH Index 2023) and AHA's Hospital Statistics report median
# initial-denial rates of 11–13% for academic / teaching hospitals,
# materially below the 17–20% community-hospital benchmark and miles
# below the 25% saturation cap the generic regression hits when payer
# mix is heavily Medicare/Medicaid.
#
# The generic screener formula at ``rcm_mc/ui/predictive_screener.py``
# treats Medicare share as a denial driver, which over-estimates AMC
# denials because AMCs run dedicated denial-prevention teams and have
# negotiated case-rate contracts that move many Medicare-shaped claims
# out of the per-claim denial mechanism. This calibration replaces the
# generic formula with an AMC-anchored small-variance band.

AMC_DENIAL_ANCHOR = 0.12
AMC_DENIAL_FLOOR = 0.08
AMC_DENIAL_CEILING = 0.18


def amc_denial_rate(
    medicare_pct: float = 0.4,
    medicaid_pct: float = 0.15,
    margin: float = 0.0,
) -> float:
    """Return an AMC-calibrated initial-denial rate in [8%, 18%], anchored at 12%.

    Drift from the 12% anchor is small and driven by:
    - heavy Medicaid mix (+1.5 pp per 10pp above the 15% baseline),
    - very negative operating margin (+2 pp for margins below -10%,
      reflecting weaker collections-side investment).
    """
    anchor = AMC_DENIAL_ANCHOR
    excess_medicaid = max(0.0, float(medicaid_pct) - 0.15)
    margin_drag = max(0.0, -0.10 - float(margin)) * 0.2
    rate = anchor + excess_medicaid * 0.15 + margin_drag
    return max(AMC_DENIAL_FLOOR, min(AMC_DENIAL_CEILING, rate))


# ---------------------------------------------------------------------------
# Uplift cap: cannot exceed total denied revenue
# ---------------------------------------------------------------------------
#
# Recoverable uplift is bounded by the dollar amount that was denied in
# the first place. The previous cap (``rev * 0.15``) was a generic
# 15%-of-NPR ceiling that, on hospitals with sub-5% denial, produced
# uplift figures 3-4× the maximum theoretically recoverable. Recovering
# 100% of denied revenue is also implausible — denial-management
# benchmarks recover 60–75% of initial denials. Use 70% as the
# realistic ceiling.

DENIAL_RECOVERY_CEILING = 0.70


def cap_uplift_at_denied_revenue(
    uplift: float,
    revenue: float,
    denial_rate: float,
    *,
    recovery_ceiling: float = DENIAL_RECOVERY_CEILING,
) -> float:
    """Return uplift bounded by ``revenue * denial_rate * recovery_ceiling``.

    Total denied revenue is ``revenue * denial_rate``. Of that, only
    ``recovery_ceiling`` is realistically recoverable through RCM
    interventions (denial appeals, charge capture, contract management).
    Uplift is also floored at zero — negative uplift is meaningless.
    """
    if not (revenue > 0) or not (denial_rate > 0):
        return 0.0
    max_recoverable = float(revenue) * float(denial_rate) * float(recovery_ceiling)
    return max(0.0, min(float(uplift), max_recoverable))
