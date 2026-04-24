"""Distribution-shift check.

The PE Intelligence brain's archetype recognition, risk flags, and
named-failure libraries were calibrated on acute-hospital-dominant
public data (HCRIS / CMS). When an analyst drops a CCD for a dental
DSO or a physician roll-up in, the feature distribution sits way
outside that training corpus. The brain still produces an output; it
just isn't trustworthy.

This module scores an incoming CCD's feature distribution against the
training corpus's distribution and returns one of three verdicts:

- IN_DISTRIBUTION     — every feature is within normal bounds
- DRIFTING            — at least one feature is moving, brain output
                        degrades but is directionally useful
- OUT_OF_DISTRIBUTION — brain output is not meaningful; the packet
                        builder marks brain findings as confidence=LOW
                        and appends the scope-limits risk flag.

Metrics computed:

- **Population Stability Index (PSI)** — industry-standard for
  credit / risk-modelling. Thresholds per Siddiqi (2006):
    PSI < 0.10 stable, 0.10–0.25 drifting, ≥ 0.25 significant shift.
- **Two-sample Kolmogorov–Smirnov D** — distribution-free check for
  continuous features; complements PSI which needs binning.

Both are implemented with stdlib + numpy (numpy already a base dep).
No scipy — the KS CDF is good enough for a threshold decision and we
don't want to lean on scipy for this one feature.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np


# ── Types ───────────────────────────────────────────────────────────

class DistributionScore(str, Enum):
    IN_DISTRIBUTION = "IN_DISTRIBUTION"
    DRIFTING = "DRIFTING"
    OUT_OF_DISTRIBUTION = "OUT_OF_DISTRIBUTION"


@dataclass
class FeatureShift:
    """Per-feature shift measurement."""
    feature: str
    psi: float
    ks_d: float
    verdict: DistributionScore
    new_mean: float
    corpus_mean: float
    new_std: float
    corpus_std: float
    note: str = ""


@dataclass
class DistributionShiftReport:
    """Aggregate shift verdict + per-feature detail."""
    overall: DistributionScore
    per_feature: List[FeatureShift] = field(default_factory=list)
    worst_feature: str = ""
    worst_psi: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall": self.overall.value,
            "worst_feature": self.worst_feature,
            "worst_psi": self.worst_psi,
            "per_feature": [
                {
                    "feature": f.feature, "psi": f.psi, "ks_d": f.ks_d,
                    "verdict": f.verdict.value, "note": f.note,
                    "new_mean": f.new_mean, "corpus_mean": f.corpus_mean,
                    "new_std": f.new_std, "corpus_std": f.corpus_std,
                }
                for f in self.per_feature
            ],
        }


# ── Public API ──────────────────────────────────────────────────────

# Siddiqi (2006) thresholds — the canonical PSI banding in credit risk.
PSI_STABLE = 0.10
PSI_DRIFT = 0.25

# KS D thresholds calibrated for medium-sample claims data (n>200).
KS_STABLE = 0.10
KS_DRIFT = 0.20


def score_distribution(
    new_features: Mapping[str, Sequence[float]],
    corpus_features: Mapping[str, Sequence[float]],
    *,
    min_samples: int = 30,
) -> DistributionShiftReport:
    """Score ``new_features`` (from the uploaded CCD) against
    ``corpus_features`` (the benchmark-corpus training distribution).

    Both are ``{feature_name: [values, ...]}`` dicts. Features present
    in ``new_features`` but not ``corpus_features`` (or vice versa)
    are skipped with a note — the caller should ensure both include
    the same feature vocabulary, but we don't fail the whole audit on
    a mismatch.

    ``min_samples`` guards against tiny CCD uploads: if fewer than
    this many rows are available for a feature, we mark it OOD with a
    "insufficient_samples" note rather than trust a small-sample PSI.
    """
    per_feature: List[FeatureShift] = []
    shared = sorted(set(new_features) & set(corpus_features))

    for feat in shared:
        new_vals = _clean(new_features[feat])
        corp_vals = _clean(corpus_features[feat])
        if len(new_vals) < min_samples or len(corp_vals) < min_samples:
            per_feature.append(FeatureShift(
                feature=feat, psi=float("nan"), ks_d=float("nan"),
                verdict=DistributionScore.OUT_OF_DISTRIBUTION,
                new_mean=_safe_mean(new_vals), corpus_mean=_safe_mean(corp_vals),
                new_std=_safe_std(new_vals), corpus_std=_safe_std(corp_vals),
                note=f"insufficient_samples: new={len(new_vals)}, "
                     f"corpus={len(corp_vals)} (need ≥ {min_samples})",
            ))
            continue
        psi = _psi(new_vals, corp_vals)
        ksd = _ks_d(new_vals, corp_vals)
        verdict = classify_shift(psi=psi, ks_d=ksd)
        per_feature.append(FeatureShift(
            feature=feat, psi=psi, ks_d=ksd, verdict=verdict,
            new_mean=float(np.mean(new_vals)), corpus_mean=float(np.mean(corp_vals)),
            new_std=float(np.std(new_vals)), corpus_std=float(np.std(corp_vals)),
        ))

    # Overall verdict: worst feature wins, because one unbounded
    # feature can wreck a brain output even if the rest are stable.
    overall = DistributionScore.IN_DISTRIBUTION
    worst_feat = ""
    worst_psi = 0.0
    for f in per_feature:
        if f.verdict == DistributionScore.OUT_OF_DISTRIBUTION:
            overall = DistributionScore.OUT_OF_DISTRIBUTION
        elif (f.verdict == DistributionScore.DRIFTING
              and overall != DistributionScore.OUT_OF_DISTRIBUTION):
            overall = DistributionScore.DRIFTING
        if (not math.isnan(f.psi)) and f.psi > worst_psi:
            worst_psi = f.psi
            worst_feat = f.feature

    return DistributionShiftReport(
        overall=overall, per_feature=per_feature,
        worst_feature=worst_feat, worst_psi=worst_psi,
    )


def classify_shift(*, psi: float, ks_d: float) -> DistributionScore:
    """Given PSI and KS D for one feature, return the verdict.

    We fire OUT_OF_DISTRIBUTION if either metric exceeds its drift
    threshold — the two are complementary (PSI sensitive to tails,
    KS sensitive to shape) and we don't want one masking the other.
    """
    if math.isnan(psi) or math.isnan(ks_d):
        return DistributionScore.OUT_OF_DISTRIBUTION
    if psi >= PSI_DRIFT or ks_d >= KS_DRIFT:
        return DistributionScore.OUT_OF_DISTRIBUTION
    if psi >= PSI_STABLE or ks_d >= KS_STABLE:
        return DistributionScore.DRIFTING
    return DistributionScore.IN_DISTRIBUTION


# ── PSI + KS ────────────────────────────────────────────────────────

def _psi(new_vals: np.ndarray, corp_vals: np.ndarray, *, n_bins: int = 10) -> float:
    """Population Stability Index using equal-frequency binning on
    the corpus distribution. Epsilon smoothing avoids log(0) blowups
    for bins with no new-population rows.
    """
    edges = _equal_frequency_edges(corp_vals, n_bins)
    eps = 1e-6
    corp_hist, _ = np.histogram(corp_vals, bins=edges)
    new_hist, _ = np.histogram(new_vals, bins=edges)
    corp_frac = corp_hist / max(corp_hist.sum(), 1)
    new_frac = new_hist / max(new_hist.sum(), 1)
    corp_frac = np.where(corp_frac == 0, eps, corp_frac)
    new_frac = np.where(new_frac == 0, eps, new_frac)
    return float(np.sum((new_frac - corp_frac) * np.log(new_frac / corp_frac)))


def _equal_frequency_edges(values: np.ndarray, n_bins: int) -> np.ndarray:
    """Bin edges at equal quantiles of ``values``. Collapses ties so
    we never emit a zero-width bin (which would produce PSI=inf)."""
    quantiles = np.linspace(0.0, 1.0, n_bins + 1)
    edges = np.unique(np.quantile(values, quantiles))
    if len(edges) < 2:
        # Degenerate: all values identical. Widen by +/- 0.5 so the
        # histogram call doesn't throw.
        return np.array([values[0] - 0.5, values[0] + 0.5])
    return edges


def _ks_d(new_vals: np.ndarray, corp_vals: np.ndarray) -> float:
    """Two-sample Kolmogorov–Smirnov D statistic. No hypothesis test
    — we just use D directly against the banded thresholds.
    """
    a = np.sort(new_vals)
    b = np.sort(corp_vals)
    # Merge + evaluate both ECDFs on the pooled sorted grid.
    grid = np.concatenate([a, b])
    cdf_a = np.searchsorted(a, grid, side="right") / a.size
    cdf_b = np.searchsorted(b, grid, side="right") / b.size
    return float(np.max(np.abs(cdf_a - cdf_b)))


# ── Cleaning helpers ────────────────────────────────────────────────

def _clean(values: Sequence[float]) -> np.ndarray:
    """Drop NaN + inf from a sequence, return as float64 array."""
    arr = np.asarray(list(values), dtype=np.float64)
    return arr[np.isfinite(arr)]


def _safe_mean(arr: np.ndarray) -> float:
    return float(np.mean(arr)) if arr.size else float("nan")


def _safe_std(arr: np.ndarray) -> float:
    return float(np.std(arr)) if arr.size else float("nan")


# ── Feature extraction from a CCD ──────────────────────────────────

def check_distribution_shift(
    new_features: Mapping[str, Sequence[float]],
    corpus_features: Mapping[str, Sequence[float]],
    *,
    min_samples: int = 30,
) -> "GuardrailResult":
    """Packet-facing wrapper around :func:`score_distribution`.

    Returns PASS when IN_DISTRIBUTION, WARN when DRIFTING, and FAIL
    when OUT_OF_DISTRIBUTION. The verdict (and the worst-feature
    name) is embedded in the ``details`` dict so the packet's memo
    generator can quote it verbatim.
    """
    from .split_enforcer import GuardrailResult

    report = score_distribution(
        new_features, corpus_features, min_samples=min_samples,
    )
    mapping = {
        DistributionScore.IN_DISTRIBUTION:
            ("PASS", True,
             "feature distribution matches the brain's training corpus."),
        DistributionScore.DRIFTING:
            ("WARN", True,
             "feature distribution is drifting from the brain's training corpus."),
        DistributionScore.OUT_OF_DISTRIBUTION:
            ("FAIL", False,
             "target's feature distribution sits outside the brain's "
             "training corpus; partner memo reliability reduced."),
    }
    status, ok, reason = mapping[report.overall]
    return GuardrailResult(
        guardrail="distribution_shift", ok=ok, status=status,
        reason=reason + (
            f" worst feature: {report.worst_feature!r} "
            f"(PSI={report.worst_psi:.3f})"
            if report.worst_feature else ""
        ),
        details={"report": report.to_dict()},
    )


def features_from_ccd(ccd: Any) -> Dict[str, List[float]]:
    """Pull comparable-level features from a :class:`CanonicalClaimsDataset`.

    Features chosen to be the ones the brain's archetype scoring
    actually looks at — not an exhaustive dump. Adding a feature here
    without adding it to the corpus feature set would mask
    OUT_OF_DISTRIBUTION cases.
    """
    claims = list(getattr(ccd, "claims", ()))
    if not claims:
        return {}
    charge = [float(c.charge_amount) for c in claims if c.charge_amount is not None]
    paid = [float(c.paid_amount) for c in claims if c.paid_amount is not None]
    days_in_ar: List[float] = []
    for c in claims:
        if c.paid_date and c.service_date_from:
            delta = (c.paid_date - c.service_date_from).days
            if 0 <= delta < 365:
                days_in_ar.append(float(delta))
    # Payer-class concentration — the fraction of claims whose class
    # is MEDICARE. Dental DSOs tend toward SELF_PAY / COMMERCIAL mix,
    # so this number alone is often enough to OOD an acute-trained
    # corpus.
    medicare_frac: List[float] = [
        1.0 if c.payer_class.value == "MEDICARE" else 0.0 for c in claims
    ]
    return {
        "charge_amount": charge,
        "paid_amount": paid,
        "days_in_ar": days_in_ar,
        "medicare_share": medicare_frac,
    }
