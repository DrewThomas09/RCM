"""OLS influence diagnostics — Phase 4B.

A handful of hospitals can shape an OLS fit out of all proportion
to their share of the data — Stanford, MD Anderson, Cleveland
Clinic, etc. They're not data errors (the Phase-1 + Phase-2 work
labelled them as Academic / Flagship Specialty), but they are
high-leverage points whose individual entries shift the
coefficients of the pooled model.

Three classical diagnostics, all computed from the same hat
matrix the in-sample fit already implies:

  * **leverage h_ii** — diagonal of X(XᵀX)⁻¹Xᵀ. Measures how
    extreme a row's feature vector is relative to the rest. h_ii
    sums to ``p + 1`` (one per coefficient including intercept),
    so 2(p+1)/n is the standard "high leverage" threshold.

  * **standardized residual** — residual / (RMSE × √(1 − h_ii)).
    Adjusts the raw residual for the leverage — a row whose
    features are far from average gets a smaller standardized
    residual for the same raw error.

  * **Cook's distance** — combines the two: row i's effect on
    the fitted coefficients if you deleted it. >1 is the classic
    "definitely influential" threshold; >4/n is a softer warning.

Plus a partner-facing classification of each high-influence row
(from Step 8 of the rebuild plan):
  * ``data_issue``  — large studentized residual + low leverage
                       (the row is an outlier in y but lives in
                       a normal part of X). Look for a data entry
                       error.
  * ``legitimate_but_different_class`` — high leverage AND high
    Cook's D, AND the row belongs to an Academic / Flagship
    Specialty / Children's segment (per Phase 1 taxonomy). These
    are real institutions following a different economic regime;
    they're influential because they're alone at the top end of
    the bed/revenue distribution. DO NOT DELETE — segment or
    isolate.
  * ``high_influence`` — high Cook's D without a clear segment
    explanation. Inspect manually.
  * ``segment_mismatch`` — high residual concentrated in a single
    segment. The model is mis-specified for that regime; the
    Phase-2 segmented-regression toggle is the fix.
  * ``possible_opportunity`` — large positive residual on a row
    in an acquisition-target segment (community / CAH / safety-
    net). The model says "should be smaller" but the row is
    bigger — could be a high-performing hospital worth a closer
    look.

This module produces the per-row diagnostics; the regression page
panel renders them with a partner-readable badge.

Uses numpy only.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


@dataclass(frozen=True)
class InfluencePoint:
    """Per-row influence record.

    ``index`` is the row's position in the cleaned dataframe (post-
    dropna + post-log-filter). Callers join back to the source df
    using this index.

    ``classification`` is the partner-facing label (see module
    docstring). ``severity`` drives the UI badge tone:
    "critical" (>1 Cook's), "warning" (>4/n), "info" (notable but
    below threshold), "ok" (in band).
    """
    index: int
    leverage: float
    studentized_residual: float
    cooks_d: float
    raw_residual: float
    classification: str
    severity: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "leverage": round(self.leverage, 6),
            "studentized_residual": round(
                self.studentized_residual, 4,
            ),
            "cooks_d": round(self.cooks_d, 6),
            "raw_residual": round(self.raw_residual, 4),
            "classification": self.classification,
            "severity": self.severity,
        }


def compute_influence(
    X: np.ndarray,
    y: np.ndarray,
    y_hat: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (leverage, studentized_residual, cooks_d) for every row.

    Inputs are the design matrix WITHOUT the intercept column, the
    target vector, and the fitted predictions. The function adds
    the intercept internally so callers don't have to remember the
    convention.

    Returns three length-n vectors. Falls back to NaN for any
    metric that can't be computed (singular hat matrix, RMSE = 0).
    """
    n, p = X.shape
    p_plus = p + 1  # +1 for the intercept
    X_aug = np.column_stack([np.ones(n), X])
    try:
        # Hat matrix H = X(XᵀX)⁻¹Xᵀ ; only need the diagonal
        XtX_inv = np.linalg.inv(X_aug.T @ X_aug)
        # h_ii = x_i (XᵀX)⁻¹ x_iᵀ — compute via einsum to avoid
        # building the full n×n hat matrix.
        leverage = np.einsum(
            "ij,jk,ik->i", X_aug, XtX_inv, X_aug,
        )
    except np.linalg.LinAlgError:
        leverage = np.full(n, np.nan)

    residuals = y - y_hat
    # MSE for unbiased σ² estimate (note: this is the standard
    # residual SE convention; some refs divide by n instead).
    dof = max(n - p_plus, 1)
    sigma2 = float(np.sum(residuals ** 2)) / dof
    rmse = float(np.sqrt(sigma2)) if sigma2 > 0 else 0.0

    if rmse > 0 and not np.any(np.isnan(leverage)):
        # Numerical-stability fix (user-reported bug: a Cook's D of
        # 4.89e18 surfaced for a row whose leverage was ≈ 1.0).
        # When 1 - leverage approaches zero, the divisor in the
        # studentized-residual and Cook's-D formulas blows up
        # exponentially. The old code clamped to 1e-9 — way too
        # permissive, produced 18-digit Cook's-D values that
        # rendered as nonsense in the UI.
        #
        # New behavior: rows with leverage > 0.99 are treated as
        # "perfect leverage" — geometrically isolated in feature
        # space, with no other rows nearby for the fit to compare
        # against. Their studentized residual and Cook's D are
        # undefined (set to NaN); the classifier surfaces them as
        # ``perfect_leverage`` so partners see why they're being
        # flagged rather than a nonsense number.
        perfect_lev = leverage > 0.99
        # For all other rows, clamp 1 - leverage to a sane minimum
        # (1e-4) so a near-perfect-leverage row that still has a
        # defined Cook's D doesn't produce 7-digit values.
        one_minus_lev = np.where(
            perfect_lev, np.nan,
            np.maximum(1.0 - leverage, 1e-4),
        )
        denom = rmse * np.sqrt(one_minus_lev)
        # studentized residual — NaN where perfect_lev
        studentized = np.where(
            perfect_lev, np.nan,
            residuals / np.where(denom > 0, denom, 1.0),
        )
        cooks_d = np.where(
            perfect_lev, np.nan,
            (studentized ** 2) / p_plus
            * (leverage / one_minus_lev),
        )
        # Defensive cap — even after the leverage clamp, a numerical
        # edge case could produce a Cook's D > 1000. Any value that
        # large is meaningless ("definitely influential" only needs
        # > 1) so cap to keep the UI readable.
        cooks_d = np.where(
            np.isfinite(cooks_d) & (cooks_d > 1000.0),
            1000.0, cooks_d,
        )
    else:
        studentized = np.full(n, np.nan)
        cooks_d = np.full(n, np.nan)

    return leverage, studentized, cooks_d


# Segment labels that count as "legitimate but different class" —
# these are real institutions that look influential because they
# live at the top end of the bed/revenue distribution, not because
# they're data errors. From Phase 1's hospital_taxonomy.
_LEGITIMATE_DIFFERENT_SEGMENTS = frozenset({
    "Flagship Specialty", "Academic", "Teaching", "Children's",
})
_ACQUISITION_TARGET_SEGMENTS = frozenset({
    "Large Community", "Small Community",
    "Safety-Net Community", "Critical Access",
})


def classify_influence_point(
    leverage: float,
    studentized_residual: float,
    cooks_d: float,
    n: int,
    p: int,
    segment: Optional[str] = None,
) -> Tuple[str, str]:
    """Return (classification, severity) for a single row.

    Thresholds:
      Cook's D > 1            → critical (definitely influential)
      Cook's D > 4/n          → warning  (notable)
      |stud_resid| > 3        → flagged as outlier in y
      leverage > 2(p+1)/n     → high-leverage
    """
    # Perfect-leverage rows: leverage > 0.99 → row sits alone in
    # feature space, Cook's D + studentized residual are undefined.
    # Surface as ``perfect_leverage`` so partners see why the row
    # is flagged rather than NaN or a nonsense 1e18 number.
    if not np.isnan(leverage) and leverage > 0.99:
        return ("perfect_leverage", "critical")
    # Other NaN inputs → genuinely can't classify
    if np.isnan(cooks_d) or np.isnan(leverage):
        return ("unknown", "info")

    high_cooks = cooks_d > 1.0
    warn_cooks = cooks_d > 4.0 / max(n, 1)
    high_leverage = leverage > 2.0 * (p + 1) / max(n, 1)
    big_resid = abs(studentized_residual) > 3.0

    if high_cooks:
        if segment in _LEGITIMATE_DIFFERENT_SEGMENTS:
            return ("legitimate_but_different_class", "critical")
        if (segment in _ACQUISITION_TARGET_SEGMENTS
                and studentized_residual > 3):
            # Positive residual = actual > predicted = "doing
            # better than the pooled model expected"
            return ("possible_opportunity", "critical")
        if big_resid and not high_leverage:
            return ("data_issue", "critical")
        return ("high_influence", "critical")

    if warn_cooks:
        if segment in _LEGITIMATE_DIFFERENT_SEGMENTS:
            return ("legitimate_but_different_class", "warning")
        if big_resid and not high_leverage:
            return ("data_issue", "warning")
        return ("high_influence", "warning")

    if big_resid:
        # In-band Cook's D, but the row is a y-outlier
        return ("data_issue", "info")

    return ("in_band", "ok")


def influence_points(
    X: np.ndarray,
    y: np.ndarray,
    y_hat: np.ndarray,
    segment_per_row: Optional[List[Optional[str]]] = None,
) -> List[InfluencePoint]:
    """Compute the full per-row diagnostics + partner classification.

    ``segment_per_row`` is the optional list of segment_labels
    (one per row, same order as X/y). Pass None to skip the
    segment-aware classification (rows just get high_influence /
    data_issue / in_band).
    """
    leverage, stud, cooks = compute_influence(X, y, y_hat)
    n, p = X.shape
    out: List[InfluencePoint] = []
    for i in range(n):
        seg = (
            segment_per_row[i] if segment_per_row is not None
            and i < len(segment_per_row)
            else None
        )
        cls, sev = classify_influence_point(
            float(leverage[i]),
            float(stud[i]),
            float(cooks[i]),
            n, p, segment=seg,
        )
        out.append(InfluencePoint(
            index=i,
            leverage=float(leverage[i]),
            studentized_residual=float(stud[i]),
            cooks_d=float(cooks[i]),
            raw_residual=float(y[i] - y_hat[i]),
            classification=cls,
            severity=sev,
        ))
    return out


def top_influential(
    points: List[InfluencePoint], limit: int = 15,
) -> List[InfluencePoint]:
    """Return the top-N rows by Cook's distance (descending).

    Skips NaN cooks_d entries. Stable sort within the same value.
    """
    valid = [p for p in points if not np.isnan(p.cooks_d)]
    valid.sort(key=lambda p: -p.cooks_d)
    return valid[:limit]
