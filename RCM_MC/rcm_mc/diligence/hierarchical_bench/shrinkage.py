"""Hierarchical (partial-pooling) benchmarking — numpy + stdlib.

The small-n problem, stated: a 12-bed facility posts an O/E of 1.9 and
lands top of the "worst operators" list. But with that little volume,
1.9 is mostly noise — its confidence interval spans 0.6 to 3.2. Ranking
it against a 400-bed system measured to ±0.05 is comparing a coin-flip
to a calibrated instrument. Naive ranking systematically surfaces the
smallest units at both tails; you chase phantom outliers and miss real
ones buried in mid-size noise.

The fix is **partial pooling** (empirical-Bayes shrinkage): pull each
unit's estimate toward the group mean by an amount that depends on how
noisy that unit is. A high-volume unit barely moves (its data speaks);
a low-volume unit shrinks hard toward the mean (its data is weak). This
is the statistically correct way to benchmark small-n facilities, and
it pairs directly with the risk-adjusted O/E from
``diligence.risk_adjustment`` — feed the per-unit O/E ratios in, get
shrunken, rank-stable estimates out.

What's here:

* :func:`partial_pool` — single-level normal-normal empirical Bayes.
  Between-unit variance τ² is estimated by DerSimonian-Laird (method of
  moments); each unit's shrinkage factor B = τ²/(τ²+sᵢ²) is reported so
  the analyst sees exactly how much each estimate was trusted.
* :func:`partial_pool_nested` — two-level pooling (units within groups,
  e.g. providers within markets): units shrink toward their group's
  pooled mean, group means shrink toward the grand mean. The standard
  conditional-shrinkage composition.
* Outlier flagging is done on the **shrunken** CI vs the grand mean, so
  a unit is only called an outlier when the signal survives shrinkage.

Honesty about the method:
    * Normal-normal model (Gaussian sampling + Gaussian prior). For
      rates near 0/1 with tiny denominators, transform first (e.g.
      log-O/E) — documented, not silently mis-applied.
    * DerSimonian-Laird τ² is a moment estimator; it is mildly biased
      with very few units (< ~5). ``tau_squared`` and the unit count are
      returned so the caller can judge.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

CITATION_KEY = "HB1"
SOURCE_MODULE = "diligence.hierarchical_bench"


def _z_crit(confidence: float) -> float:
    """Two-sided normal critical value (Acklam inverse-normal)."""
    p = (1 + confidence) / 2
    a = [-3.969683028665376e+01, 2.209460984245205e+02,
         -2.759285104469687e+02, 1.383577518672690e+02,
         -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02,
         -1.556989798598866e+02, 6.680131188771972e+01,
         -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01,
         -2.400758277161838e+00, -2.549732539343734e+00,
         4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01,
         2.445134137142996e+00, 3.754408661907416e+00]
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
               ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
               ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q = p - 0.5
    r = q * q
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / \
           (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)


@dataclass
class ShrunkenUnit:
    """One unit's raw vs partially-pooled estimate."""
    unit: str
    raw: float
    raw_se: float
    shrunken: float
    shrunken_se: float
    shrinkage_factor: float        # B = τ²/(τ²+s²); 1=trust data, 0=full pool
    ci_low: float                  # shrunken CI
    ci_high: float
    rank_raw: int
    rank_shrunken: int
    is_outlier: bool               # shrunken CI excludes the grand mean
    group: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "unit": self.unit,
            "raw": round(self.raw, 6),
            "raw_se": round(self.raw_se, 6),
            "shrunken": round(self.shrunken, 6),
            "shrunken_se": round(self.shrunken_se, 6),
            "shrinkage_factor": round(self.shrinkage_factor, 6),
            "ci_low": round(self.ci_low, 6),
            "ci_high": round(self.ci_high, 6),
            "rank_raw": self.rank_raw,
            "rank_shrunken": self.rank_shrunken,
            "is_outlier": self.is_outlier,
            "group": self.group,
        }


@dataclass
class PartialPoolResult:
    grand_mean: float
    tau_squared: float             # estimated between-unit variance
    n_units: int
    units: List[ShrunkenUnit] = field(default_factory=list)
    headline: str = ""
    source_module: str = SOURCE_MODULE
    citation_key: str = CITATION_KEY

    def to_dict(self) -> Dict[str, Any]:
        return {
            "grand_mean": round(self.grand_mean, 6),
            "tau_squared": round(self.tau_squared, 8),
            "n_units": self.n_units,
            "units": [u.to_dict() for u in self.units],
            "headline": self.headline,
            "source_module": self.source_module,
            "citation_key": self.citation_key,
        }


def _dersimonian_laird_tau2(y: np.ndarray, s2: np.ndarray) -> float:
    """DerSimonian-Laird method-of-moments estimate of between-unit
    variance τ². Floored at 0 (a negative moment estimate means no
    detectable heterogeneity beyond sampling noise)."""
    w = 1.0 / s2
    sw = w.sum()
    if sw <= 0:
        return 0.0
    y_bar = float((w * y).sum() / sw)
    q = float((w * (y - y_bar) ** 2).sum())
    k = len(y)
    c = sw - float((w ** 2).sum()) / sw
    if c <= 0:
        return 0.0
    return max(0.0, (q - (k - 1)) / c)


def partial_pool(
    units: Sequence[str],
    estimates: Sequence[float],
    standard_errors: Sequence[float],
    confidence: float = 0.95,
    groups: Optional[Sequence[Optional[str]]] = None,
) -> PartialPoolResult:
    """Single-level empirical-Bayes partial pooling.

    Each unit carries a point ``estimate`` (e.g. its risk-adjusted O/E)
    and a ``standard_error`` (from its own sample size). Returns, per
    unit, the shrunken estimate, the shrinkage factor B, a shrunken CI,
    raw vs shrunken rank, and an outlier flag (shrunken CI excludes the
    precision-weighted grand mean).

    The shrinkage is the textbook normal-normal posterior mean:
        μ* = Σ y_i/(τ²+s_i²) / Σ 1/(τ²+s_i²)     (precision-weighted mean)
        B_i = τ²/(τ²+s_i²)
        ŷ_i = μ* + B_i (y_i − μ*)
        Var(ŷ_i) = B_i · s_i²  (+ posterior uncertainty in μ*)
    """
    y = np.asarray(estimates, dtype=float)
    se = np.asarray(standard_errors, dtype=float)
    s2 = se ** 2
    k = len(y)
    if k == 0:
        return PartialPoolResult(0.0, 0.0, 0)
    s2 = np.clip(s2, 1e-12, None)

    tau2 = _dersimonian_laird_tau2(y, s2)
    prec = 1.0 / (tau2 + s2)
    grand_mean = float((prec * y).sum() / prec.sum())
    grand_var = 1.0 / prec.sum()        # variance of the pooled mean

    z = _z_crit(confidence)
    B = tau2 / (tau2 + s2)
    shrunk = grand_mean + B * (y - grand_mean)
    # Posterior variance: shrinkage on sampling var + residual mean uncertainty.
    shrunk_var = B * s2 + (1 - B) ** 2 * grand_var

    raw_order = list(np.argsort(-y))            # rank 1 = highest raw
    shrunk_order = list(np.argsort(-shrunk))
    rank_raw = {int(idx): r + 1 for r, idx in enumerate(raw_order)}
    rank_shrunk = {int(idx): r + 1 for r, idx in enumerate(shrunk_order)}

    grp = list(groups) if groups is not None else [None] * k
    out: List[ShrunkenUnit] = []
    for i in range(k):
        sse = math.sqrt(max(shrunk_var[i], 0.0))
        lo, hi = shrunk[i] - z * sse, shrunk[i] + z * sse
        is_out = (lo > grand_mean) or (hi < grand_mean)
        out.append(ShrunkenUnit(
            unit=str(units[i]),
            raw=float(y[i]), raw_se=float(se[i]),
            shrunken=float(shrunk[i]), shrunken_se=sse,
            shrinkage_factor=float(B[i]),
            ci_low=lo, ci_high=hi,
            rank_raw=rank_raw[i], rank_shrunken=rank_shrunk[i],
            is_outlier=bool(is_out), group=grp[i],
        ))
    res = PartialPoolResult(
        grand_mean=grand_mean, tau_squared=tau2, n_units=k, units=out,
    )
    res.headline = _headline(res)
    return res


def partial_pool_nested(
    units: Sequence[str],
    groups: Sequence[str],
    estimates: Sequence[float],
    standard_errors: Sequence[float],
    confidence: float = 0.95,
) -> PartialPoolResult:
    """Two-level partial pooling: units within groups.

    Units shrink toward their *group's* pooled mean (estimated by
    single-level pooling within the group); the group means in turn
    shrink toward the grand mean. This is the conditional-shrinkage
    composition for a provider→market (or market→state) hierarchy.

    Returns one flat :class:`PartialPoolResult` over all units, with the
    ``group`` field populated and ranks computed across the full set, so
    it drops into the same UI/table as :func:`partial_pool`."""
    units = list(units)
    groups = list(groups)
    y = np.asarray(estimates, dtype=float)
    se = np.asarray(standard_errors, dtype=float)
    k = len(y)
    if k == 0:
        return PartialPoolResult(0.0, 0.0, 0)

    # Level 1: pool within each group to get a group mean + its SE.
    uniq_groups = list(dict.fromkeys(groups))
    group_mean: Dict[str, float] = {}
    group_se: Dict[str, float] = {}
    shrunk_within = np.zeros(k)
    B_within = np.zeros(k)
    for g in uniq_groups:
        idx = [i for i in range(k) if groups[i] == g]
        sub = partial_pool(
            [units[i] for i in idx],
            [float(y[i]) for i in idx],
            [float(se[i]) for i in idx],
            confidence=confidence,
        )
        group_mean[g] = sub.grand_mean
        # SE of the group mean = sqrt(1/Σ prec).
        s2 = np.clip(se[idx] ** 2, 1e-12, None)
        prec = 1.0 / (sub.tau_squared + s2)
        group_se[g] = math.sqrt(1.0 / prec.sum())
        for local_i, i in enumerate(idx):
            shrunk_within[i] = sub.units[local_i].shrunken
            B_within[i] = sub.units[local_i].shrinkage_factor

    # Level 2: pool the group means toward the grand mean.
    group_pool = partial_pool(
        uniq_groups,
        [group_mean[g] for g in uniq_groups],
        [group_se[g] for g in uniq_groups],
        confidence=confidence,
    )
    grand_mean = group_pool.grand_mean
    adj_group_mean = {
        u.unit: u.shrunken for u in group_pool.units
    }

    # Recompose: unit estimate = adjusted-group-mean + within shrinkage gap.
    z = _z_crit(confidence)
    s2 = np.clip(se ** 2, 1e-12, None)
    final = np.array([
        adj_group_mean[groups[i]] + B_within[i] * (y[i] - group_mean[groups[i]])
        for i in range(k)
    ])
    final_var = B_within * s2

    raw_order = list(np.argsort(-y))
    final_order = list(np.argsort(-final))
    rank_raw = {int(idx): r + 1 for r, idx in enumerate(raw_order)}
    rank_final = {int(idx): r + 1 for r, idx in enumerate(final_order)}

    out: List[ShrunkenUnit] = []
    for i in range(k):
        sse = math.sqrt(max(final_var[i], 0.0))
        lo, hi = final[i] - z * sse, final[i] + z * sse
        is_out = (lo > grand_mean) or (hi < grand_mean)
        out.append(ShrunkenUnit(
            unit=str(units[i]), raw=float(y[i]), raw_se=float(se[i]),
            shrunken=float(final[i]), shrunken_se=sse,
            shrinkage_factor=float(B_within[i]),
            ci_low=lo, ci_high=hi,
            rank_raw=rank_raw[i], rank_shrunken=rank_final[i],
            is_outlier=bool(is_out), group=groups[i],
        ))
    res = PartialPoolResult(
        grand_mean=grand_mean, tau_squared=group_pool.tau_squared,
        n_units=k, units=out,
    )
    res.headline = _headline(res)
    return res


def _headline(res: PartialPoolResult) -> str:
    movers = sorted(
        res.units, key=lambda u: abs(u.rank_raw - u.rank_shrunken),
        reverse=True,
    )
    n_out = sum(1 for u in res.units if u.is_outlier)
    base = (
        f"Partial pooling over {res.n_units} units (grand mean "
        f"{res.grand_mean:.3f}, τ²={res.tau_squared:.4f}): "
        f"{n_out} survive as outliers after shrinkage."
    )
    if movers and abs(movers[0].rank_raw - movers[0].rank_shrunken) > 0:
        m = movers[0]
        base += (
            f" Biggest rank correction: {m.unit} moved "
            f"#{m.rank_raw}→#{m.rank_shrunken} "
            f"(shrinkage {m.shrinkage_factor:.2f})."
        )
    return base
