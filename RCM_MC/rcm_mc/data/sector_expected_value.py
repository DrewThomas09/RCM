"""Expected-vs-actual layer over the six live CMS verticals — two transparent,
*descriptive* estimators of where a provider sits relative to expectation.

This is NOT a forecast and NOT a causal/commercial claim. It answers one
descriptive question two ways: *given what is publicly known about a provider,
is its headline result higher or lower than comparable providers would lead
you to expect?* A large residual is a flag to investigate, never a verdict.

Layer 1 — **measure model** (`MeasureModel`): an ordinary-least-squares fit of
the vertical's headline measure on the provider's OTHER reported measures
(standardized; in-sample). Composite sub-ratings are excluded from the
predictors when the headline is itself a CMS composite rating, so the fit is
not mechanically tautological. We expose n, R², and every standardized
coefficient. The per-provider residual (actual − model expectation) and its
standardized form say how far the provider sits from its own measurement
profile.

Layer 2 — **profile benchmark** (`ProfileBenchmark`): the typical headline for
the provider's STRUCTURAL cohort — same state, ownership bucket, and (where a
size field exists) size band. The residual is actual − cohort mean. No model,
just a conditioned peer mean with the cohort n shown.

Hard rules (enforced in tests):
- Descriptive only — association, never causation; never a forecast; never a
  commercial-revenue, market-share, or investment recommendation.
- In-sample fit; R² and n always exposed; suppressed below a floor.
- No imputation — a provider missing any model predictor gets no model
  expectation (honest gap), not a guessed one.
- Reads only data/ loaders (via cross_sector + sector_correlations). numpy is
  an existing runtime dep; no network.
"""
from __future__ import annotations

import functools
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .cross_sector import SECTOR_BY_ID, SectorSpec
from .sector_correlations import metric_meta

_MIN_FIT_N = 50      # below this the OLS fit is not reported
_MIN_COHORT_N = 8    # below this a structural cohort mean is suppressed
_MIN_COVERAGE = 0.5  # a predictor must be reported by >= this fraction
_OUTLIER_SD = 2.0    # |std residual| beyond this is flagged "notable"


@dataclass(frozen=True)
class ModelCoefficient:
    key: str
    label: str
    std_coef: float       # standardized (comparable across predictors)


@dataclass
class MeasureModel:
    sector_id: str
    target_key: str
    target_label: str
    predictors: List[ModelCoefficient]   # sorted by |std_coef| desc
    n_fit: int
    r2: float
    composite_target: bool                # headline is a CMS composite rating


@dataclass
class MeasureResidual:
    expected: Optional[float]
    actual: Optional[float]
    residual: Optional[float]             # actual - expected
    std_residual: Optional[float]
    flag: str                             # "above" | "below" | "typical" | "n/a"


@dataclass
class ProfileBenchmark:
    cohort_label: str
    cohort_n: int
    expected: Optional[float]             # cohort mean of the headline
    actual: Optional[float]
    residual: Optional[float]
    flag: str                             # "above" | "below" | "typical" | "n/a"


@dataclass
class ExpectedVsActual:
    sector_id: str
    sector_label: str
    ccn: str
    provider_name: str
    state: str
    headline_label: str
    model: Optional[MeasureModel]
    model_residual: MeasureResidual
    profile: ProfileBenchmark
    caveats: List[str] = field(default_factory=list)


def _own_bucket(v: Any) -> str:
    s = (v or "").strip().lower()
    if not s:
        return "unknown ownership"
    if "for profit" in s or "for-profit" in s or "proprietary" in s:
        return "for-profit"
    if "non" in s and "profit" in s or "voluntary" in s:
        return "non-profit"
    if "government" in s or "gov" in s or "state" in s or "county" in s \
            or "city" in s or "federal" in s or "tribal" in s:
        return "government"
    return "other ownership"


def _size_attr(provider: Any) -> Optional[float]:
    for attr in ("certified_beds", "total_beds", "dialysis_stations"):
        v = getattr(provider, attr, None)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                return None
    return None


def _flag(std_or_resid: Optional[float], threshold: float) -> str:
    if std_or_resid is None:
        return "n/a"
    if std_or_resid >= threshold:
        return "above"
    if std_or_resid <= -threshold:
        return "below"
    return "typical"


@functools.lru_cache(maxsize=None)
def _fit_measure_model(sector_id: str) -> Optional[Tuple[MeasureModel, dict]]:
    """Fit the headline ~ other-measures OLS. Returns (MeasureModel, internals)
    where internals carry the means/sds/coefs needed to score a provider."""
    spec: Optional[SectorSpec] = SECTOR_BY_ID.get(sector_id)
    if spec is None:
        return None
    quality = spec.quality_loader()
    if not quality:
        return None
    target = spec.headline_key
    _, target_dir = metric_meta(target)
    composite = target_dir == "rating"

    # Candidate predictors: numeric keys present, != target, with enough
    # coverage. Exclude other rating-direction measures when the target is a
    # composite rating (avoids mechanical tautology with its sub-ratings).
    n_all = len(quality)
    coverage: Dict[str, int] = {}
    for row in quality.values():
        for k, v in row.items():
            if v is not None:
                coverage[k] = coverage.get(k, 0) + 1
    candidates = []
    for k, c in coverage.items():
        if k == target or c < _MIN_COVERAGE * n_all:
            continue
        if composite and metric_meta(k)[1] == "rating":
            continue
        candidates.append(k)
    candidates.sort()
    if len(candidates) < 1:
        return None

    # Complete-case design matrix.
    rows_X: List[List[float]] = []
    rows_y: List[float] = []
    for row in quality.values():
        y = row.get(target)
        if y is None:
            continue
        xs = [row.get(k) for k in candidates]
        if any(x is None for x in xs):
            continue
        rows_X.append([float(x) for x in xs])
        rows_y.append(float(y))
    if len(rows_y) < _MIN_FIT_N:
        return None

    X = np.array(rows_X, dtype=float)
    y = np.array(rows_y, dtype=float)
    mu_x = X.mean(axis=0)
    sd_x = X.std(axis=0)
    keep = sd_x > 0                       # drop zero-variance predictors
    if not keep.any():
        return None
    candidates = [k for k, kp in zip(candidates, keep) if kp]
    X, mu_x, sd_x = X[:, keep], mu_x[keep], sd_x[keep]
    mu_y, sd_y = float(y.mean()), float(y.std())
    if sd_y <= 0:
        return None

    Xs = (X - mu_x) / sd_x
    ys = (y - mu_y) / sd_y
    A = np.column_stack([np.ones(len(ys)), Xs])
    beta, *_ = np.linalg.lstsq(A, ys, rcond=None)
    pred = A @ beta
    ss_res = float(((ys - pred) ** 2).sum())
    ss_tot = float(((ys - ys.mean()) ** 2).sum())
    r2 = round(1 - ss_res / ss_tot, 3) if ss_tot > 0 else 0.0
    resid_sd = float((y - (mu_y + sd_y * pred)).std()) or 1.0

    coefs = [ModelCoefficient(k, metric_meta(k)[0], round(float(b), 3))
             for k, b in zip(candidates, beta[1:])]
    coefs.sort(key=lambda c: -abs(c.std_coef))

    model = MeasureModel(
        sector_id=sector_id, target_key=target,
        target_label=spec.headline_label, predictors=coefs,
        n_fit=len(ys), r2=r2, composite_target=composite)
    internals = dict(candidates=candidates, mu_x=mu_x, sd_x=sd_x,
                     mu_y=mu_y, sd_y=sd_y, intercept=float(beta[0]),
                     slopes=beta[1:], resid_sd=resid_sd)
    return model, internals


def _model_residual(sector_id: str, q: Dict[str, Optional[float]]
                    ) -> Tuple[Optional[MeasureModel], MeasureResidual]:
    fit = _fit_measure_model(sector_id)
    spec = SECTOR_BY_ID[sector_id]
    actual = q.get(spec.headline_key)
    if fit is None:
        return None, MeasureResidual(None, actual, None, None, "n/a")
    model, intr = fit
    xs = [q.get(k) for k in intr["candidates"]]
    if actual is None or any(x is None for x in xs):
        return model, MeasureResidual(None, actual, None, None, "n/a")
    xv = (np.array([float(x) for x in xs]) - intr["mu_x"]) / intr["sd_x"]
    pred_std = intr["intercept"] + float(xv @ intr["slopes"])
    expected = intr["mu_y"] + intr["sd_y"] * pred_std
    residual = float(actual) - expected
    std_resid = residual / intr["resid_sd"] if intr["resid_sd"] else None
    return model, MeasureResidual(
        round(expected, 3), float(actual), round(residual, 3),
        round(std_resid, 2) if std_resid is not None else None,
        _flag(std_resid, _OUTLIER_SD))


@functools.lru_cache(maxsize=None)
def _size_bands(sector_id: str) -> Optional[Tuple[float, float]]:
    """Tercile cut points for the sector's size field, or None if no size."""
    spec = SECTOR_BY_ID[sector_id]
    sizes = sorted(s for s in (_size_attr(p)
                   for p in spec.providers_loader().values()) if s is not None)
    if len(sizes) < 30:
        return None
    return sizes[len(sizes) // 3], sizes[2 * len(sizes) // 3]


def _size_band(sector_id: str, provider: Any) -> str:
    bands = _size_bands(sector_id)
    sz = _size_attr(provider)
    if bands is None or sz is None:
        return ""
    lo, hi = bands
    return "small" if sz <= lo else ("large" if sz > hi else "mid")


def _profile_benchmark(sector_id: str, provider: Any,
                       q: Dict[str, Optional[float]]) -> ProfileBenchmark:
    spec = SECTOR_BY_ID[sector_id]
    quality = spec.quality_loader()
    providers = spec.providers_loader()
    state = (getattr(provider, "state", "") or "").strip().upper()
    bucket = _own_bucket(getattr(provider, "ownership", ""))
    band = _size_band(sector_id, provider)
    actual = q.get(spec.headline_key)

    parts = [state, bucket] + ([f"{band} size"] if band else [])
    label = " · ".join(p for p in parts if p)

    peers: List[float] = []
    for ccn2, p2 in providers.items():
        if (getattr(p2, "state", "") or "").strip().upper() != state:
            continue
        if _own_bucket(getattr(p2, "ownership", "")) != bucket:
            continue
        if band and _size_band(sector_id, p2) != band:
            continue
        v = (quality.get(ccn2) or {}).get(spec.headline_key)
        if v is not None:
            peers.append(float(v))

    if len(peers) < _MIN_COHORT_N or actual is None:
        return ProfileBenchmark(label, len(peers), None,
                                float(actual) if actual is not None else None,
                                None, "n/a")
    expected = sum(peers) / len(peers)
    sd = float(np.std(peers)) or None
    residual = float(actual) - expected
    std = residual / sd if sd else None
    return ProfileBenchmark(
        label, len(peers), round(expected, 3), float(actual),
        round(residual, 3), _flag(std, 1.0))


def expected_vs_actual(sector_id: str, ccn: str) -> Optional[ExpectedVsActual]:
    """Both descriptive expected-vs-actual layers for one provider, or None if
    the sector or CCN is unknown."""
    spec: Optional[SectorSpec] = SECTOR_BY_ID.get(sector_id)
    if spec is None:
        return None
    provider = spec.providers_loader().get(ccn)
    if provider is None:
        return None
    q = spec.quality_loader().get(ccn) or {}
    model, mres = _model_residual(sector_id, q)
    profile = _profile_benchmark(sector_id, provider, q)

    caveats = [
        "Descriptive expected-vs-actual over public CMS data — association, "
        "NOT causation; NOT a forecast; NOT an investment, revenue, or "
        "market-share claim.",
        "A large residual flags a provider to investigate against its peers; "
        "it is not a verdict and may reflect case mix or unmeasured factors.",
    ]
    if model and model.composite_target:
        caveats.append(
            "The headline is a CMS composite rating; its sub-ratings are "
            "excluded from the model predictors so the fit is not mechanical.")
    if model is None:
        caveats.append("Measure model not fitted (too few complete-case "
                       "providers); only the structural benchmark is shown.")
    if profile.cohort_n < _MIN_COHORT_N:
        caveats.append(f"Structural cohort has only {profile.cohort_n} rated "
                       "peer(s) — its expectation is suppressed.")

    return ExpectedVsActual(
        sector_id=sector_id, sector_label=spec.label, ccn=ccn,
        provider_name=getattr(provider, spec.name_attr, "") or "",
        state=(getattr(provider, "state", "") or "").strip().upper(),
        headline_label=spec.headline_label, model=model,
        model_residual=mres, profile=profile, caveats=caveats)
