"""Difference-in-differences + synthetic-control policy-shock estimator.

The diligence question: *what does a policy shock — the OBBBA Medicaid
changes, a CY2027 MA rate cut, the PFS conversion-factor move — do to
this asset?* The flat-haircut answer ("knock 3% off revenue") is the
one an IC picks apart. This module gives the quasi-experimental
answer: compare units exposed to the policy against units that aren't,
before and after, and let the data size the effect — with the
parallel-trends and placebo checks that make the estimate defensible.

What's here (all numpy + stdlib — numpy is already a repo runtime dep):

* :func:`did_2x2` — the canonical 2×2 difference-in-differences.
* :func:`estimate_did` — generalized two-way fixed-effects DiD (unit +
  period fixed effects) with **cluster-robust** standard errors
  clustered by unit (CR1 small-sample correction). This is the
  workhorse.
* :func:`event_study` — leads/lags around the treatment date. The
  pre-treatment leads ARE the parallel-trends test; a joint
  (Bonferroni) check is rolled into :class:`DiDResult.pretrend_pvalue`.
* :func:`placebo_test` — re-runs the estimator on a fake treatment
  date inside the pre-period; a non-null placebo effect means the
  design is picking up something other than the policy.
* :func:`synthetic_control` — the secondary identification strategy
  for a single treated unit: nonnegative donor weights (summing to 1)
  fit to the pre-period via projected gradient descent, then the
  post-period gap.
* :func:`policy_ebitda_overlay` — translate the ATT into an
  EBITDA-at-risk number for the deal, so it flows downstream into the
  Deal MC ``reg_headwind`` driver and the Bear Case like every other
  diligence finding.

Honesty about the method, surfaced in the result, not buried:
    * Normal-approximation p-values. Cluster-robust inference with few
      clusters (< ~30 units) is anti-conservative; ``small_cluster_warning``
      fires below that and the verdict is capped at SUGGESTIVE.
    * Common treatment timing (one policy date for all treated units).
      Staggered adoption needs a Callaway–Sant'Anna style estimator;
      that is a documented follow-up, not silently mis-handled here.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

CITATION_KEY = "PS1"
SOURCE_MODULE = "diligence.policy_shock"

# Below this many clusters, cluster-robust SEs are unreliable; cap the
# verdict and flag it. 30 is the conventional rule-of-thumb floor.
_MIN_CLUSTERS = 30


class PolicyVerdict(str, Enum):
    """Strength of the causal evidence that the policy moved the outcome."""
    NULL = "NULL"                 # no detectable effect
    SUGGESTIVE = "SUGGESTIVE"     # signed effect, weak/uncertain identification
    LIKELY = "LIKELY"             # significant + parallel trends hold
    STRONG = "STRONG"             # significant, clean pretrend, clean placebo


def _phi(x: float) -> float:
    """Standard-normal CDF via stdlib ``math.erf`` (no scipy)."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _two_sided_p(z: float) -> float:
    """Two-sided normal p-value for a z statistic."""
    return 2.0 * (1.0 - _phi(abs(z)))


# ────────────────────────────────────────────────────────────────────
# Panel container
# ────────────────────────────────────────────────────────────────────

@dataclass
class PanelData:
    """Long-format panel. Every list is the same length (one row per
    unit-period observation).

    unit          unit identifier (hashable) — the cluster.
    period        integer time index (e.g. year or quarter ordinal).
    outcome       the dependent variable (revenue, PMPM, margin, …).
    treated_unit  True if the unit is ever exposed to the policy.
    treatment_period  the period at which the policy takes effect;
                  post = period >= treatment_period (common timing).
    """
    unit: Sequence[Any]
    period: Sequence[int]
    outcome: Sequence[float]
    treated_unit: Sequence[bool]
    treatment_period: int

    def __post_init__(self) -> None:
        n = len(self.outcome)
        if not (len(self.unit) == len(self.period) ==
                len(self.treated_unit) == n):
            raise ValueError("PanelData columns must be equal length")
        if n == 0:
            raise ValueError("PanelData is empty")

    @property
    def n(self) -> int:
        return len(self.outcome)

    def post_mask(self) -> "np.ndarray":
        return np.asarray(self.period) >= self.treatment_period


# ────────────────────────────────────────────────────────────────────
# OLS with cluster-robust covariance
# ────────────────────────────────────────────────────────────────────

def _ols_cluster_robust(
    X: "np.ndarray", y: "np.ndarray", clusters: "np.ndarray",
) -> Tuple["np.ndarray", "np.ndarray", int]:
    """OLS via least squares with CR1 cluster-robust covariance.

    Returns (beta, cov, n_clusters). Uses the pseudo-inverse of X'X so
    that incidental dummy collinearity degrades gracefully rather than
    raising."""
    n, k = X.shape
    XtX = X.T @ X
    XtX_inv = np.linalg.pinv(XtX)
    beta = XtX_inv @ (X.T @ y)
    resid = y - X @ beta

    uniq = np.unique(clusters)
    g = len(uniq)
    meat = np.zeros((k, k))
    for c in uniq:
        idx = clusters == c
        Xg = X[idx]
        ug = resid[idx]
        s = Xg.T @ ug
        meat += np.outer(s, s)
    # CR1 small-sample correction.
    dof_c = (g / max(g - 1, 1)) * ((n - 1) / max(n - k, 1))
    cov = dof_c * (XtX_inv @ meat @ XtX_inv)
    return beta, cov, g


def _fixed_effects_design(
    panel: PanelData, interaction: "np.ndarray",
    extra_cols: Optional["np.ndarray"] = None,
) -> Tuple["np.ndarray", "np.ndarray", "np.ndarray", int]:
    """Build [intercept, unit FE, period FE, interaction(s)] design.

    Reference unit and reference period are dropped to avoid the dummy
    trap. Returns (X, y, clusters, n_interaction_cols). The interaction
    column(s) are the LAST columns of X, so callers read their
    coefficients off the tail of beta."""
    y = np.asarray(panel.outcome, dtype=float)
    units = np.asarray(panel.unit)
    periods = np.asarray(panel.period)
    clusters = units

    uniq_u = list(dict.fromkeys(units.tolist()))
    uniq_p = list(dict.fromkeys(periods.tolist()))
    n = len(y)

    cols = [np.ones(n)]  # intercept
    for u in uniq_u[1:]:                       # drop first unit
        cols.append((units == u).astype(float))
    for p in uniq_p[1:]:                       # drop first period
        cols.append((periods == p).astype(float))
    if extra_cols is not None:
        for j in range(extra_cols.shape[1]):
            cols.append(extra_cols[:, j])

    inter = np.atleast_2d(interaction)
    if inter.shape[0] == 1:
        inter = inter.T                        # (n,1)
    n_inter = inter.shape[1]
    for j in range(n_inter):
        cols.append(inter[:, j].astype(float))

    X = np.column_stack(cols)
    return X, y, clusters, n_inter


# ────────────────────────────────────────────────────────────────────
# Estimators
# ────────────────────────────────────────────────────────────────────

@dataclass
class DiDResult:
    """Average treatment effect on the treated (ATT) + diagnostics."""
    att: float
    se: float
    z_stat: float
    p_value: float
    ci_low: float
    ci_high: float
    n_obs: int
    n_clusters: int
    n_treated_units: int
    n_control_units: int
    pretrend_pvalue: Optional[float] = None
    placebo_att: Optional[float] = None
    placebo_pvalue: Optional[float] = None
    small_cluster_warning: bool = False
    verdict: PolicyVerdict = PolicyVerdict.NULL
    headline: str = ""
    method: str = "two-way fixed effects DiD (cluster-robust)"
    source_module: str = SOURCE_MODULE
    citation_key: str = CITATION_KEY

    def to_dict(self) -> Dict[str, Any]:
        return {
            "att": round(self.att, 6),
            "se": round(self.se, 6),
            "z_stat": round(self.z_stat, 4),
            "p_value": round(self.p_value, 6),
            "ci_low": round(self.ci_low, 6),
            "ci_high": round(self.ci_high, 6),
            "n_obs": self.n_obs,
            "n_clusters": self.n_clusters,
            "n_treated_units": self.n_treated_units,
            "n_control_units": self.n_control_units,
            "pretrend_pvalue": (
                None if self.pretrend_pvalue is None
                else round(self.pretrend_pvalue, 6)
            ),
            "placebo_att": (
                None if self.placebo_att is None
                else round(self.placebo_att, 6)
            ),
            "placebo_pvalue": (
                None if self.placebo_pvalue is None
                else round(self.placebo_pvalue, 6)
            ),
            "small_cluster_warning": self.small_cluster_warning,
            "verdict": self.verdict.value,
            "headline": self.headline,
            "method": self.method,
            "source_module": self.source_module,
            "citation_key": self.citation_key,
        }


def did_2x2(
    treated_pre: float, treated_post: float,
    control_pre: float, control_post: float,
) -> float:
    """Canonical 2×2 DiD point estimate:

        ATT = (treated_post − treated_pre) − (control_post − control_pre)

    The control group's change is the counterfactual for what the
    treated group would have done absent the policy."""
    return (treated_post - treated_pre) - (control_post - control_pre)


def estimate_did(
    panel: PanelData,
    confidence: float = 0.95,
    run_pretrend: bool = True,
    run_placebo: bool = True,
) -> DiDResult:
    """Two-way fixed-effects DiD with cluster-robust inference.

    The interaction term ``treated_unit × post`` is the ATT. Unit fixed
    effects absorb time-invariant level differences between markets;
    period fixed effects absorb shocks common to all units. SEs are
    clustered by unit."""
    post = panel.post_mask().astype(float)
    treated = np.asarray(panel.treated_unit).astype(float)
    interaction = treated * post

    X, y, clusters, _ = _fixed_effects_design(panel, interaction)
    beta, cov, g = _ols_cluster_robust(X, y, clusters)
    att = float(beta[-1])
    var = float(cov[-1, -1])
    se = math.sqrt(var) if var > 0 else 0.0
    z = att / se if se > 0 else 0.0
    p = _two_sided_p(z)
    zc = abs(_inv_phi((1 + confidence) / 2))
    ci_low, ci_high = att - zc * se, att + zc * se

    units = np.asarray(panel.unit)
    treated_units = set(units[np.asarray(panel.treated_unit)].tolist())
    control_units = set(units.tolist()) - treated_units

    pretrend_p: Optional[float] = None
    if run_pretrend:
        try:
            es = event_study(panel, confidence=confidence)
            pretrend_p = es.pretrend_pvalue
        except Exception:
            pretrend_p = None

    placebo_att: Optional[float] = None
    placebo_p: Optional[float] = None
    if run_placebo:
        placebo_att, placebo_p = _run_placebo(panel)

    small = g < _MIN_CLUSTERS
    verdict = _classify_policy(p, pretrend_p, placebo_p, small)
    res = DiDResult(
        att=att, se=se, z_stat=z, p_value=p,
        ci_low=ci_low, ci_high=ci_high,
        n_obs=panel.n, n_clusters=g,
        n_treated_units=len(treated_units),
        n_control_units=len(control_units),
        pretrend_pvalue=pretrend_p,
        placebo_att=placebo_att, placebo_pvalue=placebo_p,
        small_cluster_warning=small, verdict=verdict,
    )
    res.headline = _did_headline(res)
    return res


def _inv_phi(p: float) -> float:
    """Inverse standard-normal CDF (Beasley-Springer-Moro), for the
    CI critical value. Matches the repo's stdlib MC convention."""
    p = min(max(p, 1e-9), 1 - 1e-9)
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
class EventStudyResult:
    """Leads/lags coefficients relative to treatment."""
    rel_periods: List[int]
    coefs: List[float]
    ses: List[float]
    pretrend_pvalue: float        # Bonferroni joint test on pre-period leads
    source_module: str = SOURCE_MODULE
    citation_key: str = CITATION_KEY

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rel_periods": list(self.rel_periods),
            "coefs": [round(c, 6) for c in self.coefs],
            "ses": [round(s, 6) for s in self.ses],
            "pretrend_pvalue": round(self.pretrend_pvalue, 6),
            "source_module": self.source_module,
            "citation_key": self.citation_key,
        }


def event_study(
    panel: PanelData, confidence: float = 0.95,
) -> EventStudyResult:
    """Estimate treated × relative-period interactions.

    The period immediately before treatment (relative time −1) is the
    omitted base, so every coefficient is read relative to it.
    Pre-treatment coefficients should be ≈ 0 if parallel trends hold;
    the ``pretrend_pvalue`` is a Bonferroni-adjusted joint test on
    them (conservative, dependency-free)."""
    periods = np.asarray(panel.period)
    treated = np.asarray(panel.treated_unit).astype(float)
    rel = periods - panel.treatment_period
    rel_values = sorted(set(rel.tolist()))
    base = -1 if -1 in rel_values else min(
        [r for r in rel_values if r < 0], default=rel_values[0],
    )

    inter_cols = []
    rel_kept: List[int] = []
    for r in rel_values:
        if r == base:
            continue
        inter_cols.append(treated * (rel == r).astype(float))
        rel_kept.append(r)
    if not inter_cols:
        return EventStudyResult([], [], [], 1.0)
    interaction = np.column_stack(inter_cols)

    X, y, clusters, n_inter = _fixed_effects_design(panel, interaction)
    beta, cov, _ = _ols_cluster_robust(X, y, clusters)
    coefs = beta[-n_inter:]
    ses = np.sqrt(np.clip(np.diag(cov)[-n_inter:], 0, None))

    # Bonferroni joint pretrend test across pre-period leads.
    pre_idx = [i for i, r in enumerate(rel_kept) if r < 0]
    if pre_idx:
        zs = [
            abs(coefs[i] / ses[i]) if ses[i] > 0 else 0.0
            for i in pre_idx
        ]
        max_z = max(zs)
        pretrend_p = min(1.0, len(pre_idx) * _two_sided_p(max_z))
    else:
        pretrend_p = 1.0

    return EventStudyResult(
        rel_periods=rel_kept,
        coefs=[float(c) for c in coefs],
        ses=[float(s) for s in ses],
        pretrend_pvalue=float(pretrend_p),
    )


def placebo_test(
    panel: PanelData,
) -> Tuple[Optional[float], Optional[float]]:
    """Public placebo test: returns (placebo_att, placebo_pvalue).

    Re-runs DiD on a fake in-pre-period treatment date; a near-zero,
    insignificant result is the pass condition. ``(None, None)`` when
    there are too few pre-periods to construct a placebo."""
    return _run_placebo(panel)


def _run_placebo(panel: PanelData) -> Tuple[Optional[float], Optional[float]]:
    """Re-estimate DiD on a fake treatment date inside the pre-period.

    Uses only pre-policy observations and sets the placebo date to the
    median pre-period. A significant placebo ATT means the design is
    capturing a pre-existing divergence, not the policy."""
    periods = np.asarray(panel.period)
    pre_periods = sorted(set(periods[periods < panel.treatment_period].tolist()))
    if len(pre_periods) < 2:
        return None, None
    fake_period = pre_periods[len(pre_periods) // 2]
    if fake_period == pre_periods[0]:
        fake_period = pre_periods[1]

    keep = periods < panel.treatment_period
    sub = PanelData(
        unit=[u for u, k in zip(panel.unit, keep) if k],
        period=[p for p, k in zip(panel.period, keep) if k],
        outcome=[o for o, k in zip(panel.outcome, keep) if k],
        treated_unit=[t for t, k in zip(panel.treated_unit, keep) if k],
        treatment_period=fake_period,
    )
    try:
        res = estimate_did(
            sub, run_pretrend=False, run_placebo=False,
        )
        return res.att, res.p_value
    except Exception:
        return None, None


def _classify_policy(
    p: Optional[float], pretrend_p: Optional[float],
    placebo_p: Optional[float], small_cluster: bool,
) -> PolicyVerdict:
    """Combine significance, parallel-trends and placebo into a verdict.

    Significance alone is SUGGESTIVE; it only escalates to LIKELY when
    parallel trends survive, and to STRONG when the placebo is clean
    too. Few clusters caps the verdict at SUGGESTIVE regardless."""
    if p is None or p >= 0.10:
        return PolicyVerdict.NULL
    if small_cluster:
        return PolicyVerdict.SUGGESTIVE
    pretrend_ok = pretrend_p is None or pretrend_p >= 0.10
    placebo_ok = placebo_p is None or placebo_p >= 0.10
    if p < 0.05 and pretrend_ok and placebo_ok:
        return PolicyVerdict.STRONG
    if p < 0.10 and pretrend_ok:
        return PolicyVerdict.LIKELY
    return PolicyVerdict.SUGGESTIVE


def _did_headline(r: DiDResult) -> str:
    sign = "reduced" if r.att < 0 else "increased"
    base = (
        f"Policy {sign} the outcome by {abs(r.att):.3f} "
        f"(95% CI [{r.ci_low:.3f}, {r.ci_high:.3f}], p={r.p_value:.3f}); "
        f"{r.n_treated_units} treated vs {r.n_control_units} control units."
    )
    flags = []
    if r.small_cluster_warning:
        flags.append(f"only {r.n_clusters} clusters — inference cautious")
    if r.pretrend_pvalue is not None and r.pretrend_pvalue < 0.10:
        flags.append(f"parallel-trends suspect (pretrend p={r.pretrend_pvalue:.3f})")
    if r.placebo_pvalue is not None and r.placebo_pvalue < 0.10:
        flags.append(f"placebo non-null (p={r.placebo_pvalue:.3f})")
    if flags:
        base += " ⚠ " + "; ".join(flags) + "."
    base += f" Verdict: {r.verdict.value}."
    return base


# ────────────────────────────────────────────────────────────────────
# Synthetic control (secondary identification)
# ────────────────────────────────────────────────────────────────────

@dataclass
class SyntheticControlResult:
    """Single-treated-unit synthetic control."""
    donor_units: List[Any]
    weights: List[float]
    pre_rmse: float
    post_gap_mean: float          # treated − synthetic, post-period mean
    post_gaps: List[float]
    source_module: str = SOURCE_MODULE
    citation_key: str = CITATION_KEY

    def to_dict(self) -> Dict[str, Any]:
        return {
            "donor_units": [str(u) for u in self.donor_units],
            "weights": [round(w, 6) for w in self.weights],
            "pre_rmse": round(self.pre_rmse, 6),
            "post_gap_mean": round(self.post_gap_mean, 6),
            "post_gaps": [round(g, 6) for g in self.post_gaps],
            "source_module": self.source_module,
            "citation_key": self.citation_key,
        }


def synthetic_control(
    panel: PanelData,
    treated_unit: Any,
    max_iter: int = 5000,
    lr: float = 0.05,
) -> SyntheticControlResult:
    """Fit a synthetic control for a single treated unit.

    Donor weights are constrained to the simplex (nonnegative, sum to
    1) and fit by projected gradient descent to minimize pre-period
    RMSE between the treated unit and the weighted donor pool — no
    scipy/quadprog needed. The post-period gap is the estimated
    effect.

    Use when there is essentially one treated market with a clean donor
    pool; for many treated units, :func:`estimate_did` is preferred."""
    units = np.asarray(panel.unit)
    periods = np.asarray(panel.period)
    outcome = np.asarray(panel.outcome, dtype=float)

    all_periods = sorted(set(periods.tolist()))
    pre = [p for p in all_periods if p < panel.treatment_period]
    post = [p for p in all_periods if p >= panel.treatment_period]
    if not pre or not post:
        raise ValueError("need both pre and post periods")

    donors = [u for u in dict.fromkeys(units.tolist()) if u != treated_unit]
    if not donors:
        raise ValueError("no donor units available")

    def series(u: Any, prds: Sequence[int]) -> "np.ndarray":
        out = []
        for p in prds:
            mask = (units == u) & (periods == p)
            out.append(float(outcome[mask][0]) if mask.any() else np.nan)
        return np.asarray(out)

    Y1_pre = series(treated_unit, pre)
    Y0_pre = np.column_stack([series(u, pre) for u in donors])  # (T_pre, J)
    if np.isnan(Y1_pre).any() or np.isnan(Y0_pre).any():
        raise ValueError("unbalanced panel: missing pre-period observations")

    J = len(donors)
    w = np.full(J, 1.0 / J)
    for _ in range(max_iter):
        pred = Y0_pre @ w
        grad = Y0_pre.T @ (pred - Y1_pre) * (2.0 / len(pre))
        w = w - lr * grad
        w = _project_simplex(w)

    pre_pred = Y0_pre @ w
    pre_rmse = float(np.sqrt(np.mean((pre_pred - Y1_pre) ** 2)))

    Y1_post = series(treated_unit, post)
    Y0_post = np.column_stack([series(u, post) for u in donors])
    post_pred = Y0_post @ w
    gaps = (Y1_post - post_pred).tolist()
    return SyntheticControlResult(
        donor_units=donors,
        weights=[float(x) for x in w],
        pre_rmse=pre_rmse,
        post_gap_mean=float(np.mean(gaps)),
        post_gaps=[float(g) for g in gaps],
    )


def _project_simplex(v: "np.ndarray") -> "np.ndarray":
    """Euclidean projection onto the probability simplex (Duchi 2008)."""
    u = np.sort(v)[::-1]
    css = np.cumsum(u)
    rho_candidates = u - (css - 1) / (np.arange(len(u)) + 1)
    rho = np.nonzero(rho_candidates > 0)[0]
    if len(rho) == 0:
        return np.full_like(v, 1.0 / len(v))
    r = rho[-1]
    theta = (css[r] - 1) / (r + 1)
    return np.clip(v - theta, 0, None)


# ────────────────────────────────────────────────────────────────────
# Deal bridge
# ────────────────────────────────────────────────────────────────────

@dataclass
class PolicyEbitdaOverlay:
    """ATT translated into deal EBITDA-at-risk."""
    att_pct: float                # effect as a fraction of exposed revenue
    exposed_revenue_usd: float
    ebitda_impact_usd: float
    ci_low_usd: float
    ci_high_usd: float
    source_module: str = SOURCE_MODULE
    citation_key: str = CITATION_KEY

    def to_dict(self) -> Dict[str, Any]:
        return {
            "att_pct": round(self.att_pct, 6),
            "exposed_revenue_usd": round(self.exposed_revenue_usd, 2),
            "ebitda_impact_usd": round(self.ebitda_impact_usd, 2),
            "ci_low_usd": round(self.ci_low_usd, 2),
            "ci_high_usd": round(self.ci_high_usd, 2),
            "source_module": self.source_module,
            "citation_key": self.citation_key,
        }


def policy_ebitda_overlay(
    result: DiDResult,
    exposed_revenue_usd: float,
    att_is_pct: bool = True,
    flow_through: float = 1.0,
) -> PolicyEbitdaOverlay:
    """Translate a DiD ATT into an EBITDA-at-risk overlay for the deal.

    If ``att_is_pct`` the ATT is treated as a fractional change applied
    to the exposed revenue base (the dollars subject to the policy);
    otherwise the ATT is already in revenue dollars. ``flow_through``
    is the share of the revenue change that reaches EBITDA (1.0 for a
    pure rate change with no offsetting cost; lower if variable costs
    move with volume). The result flows into the Deal MC
    ``reg_headwind_usd`` driver and the Bear Case, matching the rest of
    the workbench's dollar-impact rollup."""
    if att_is_pct:
        impact = result.att * exposed_revenue_usd * flow_through
        lo = result.ci_low * exposed_revenue_usd * flow_through
        hi = result.ci_high * exposed_revenue_usd * flow_through
        att_pct = result.att
    else:
        impact = result.att * flow_through
        lo = result.ci_low * flow_through
        hi = result.ci_high * flow_through
        att_pct = (
            result.att / exposed_revenue_usd
            if exposed_revenue_usd else 0.0
        )
    return PolicyEbitdaOverlay(
        att_pct=att_pct,
        exposed_revenue_usd=exposed_revenue_usd,
        ebitda_impact_usd=impact,
        ci_low_usd=min(lo, hi),
        ci_high_usd=max(lo, hi),
    )
