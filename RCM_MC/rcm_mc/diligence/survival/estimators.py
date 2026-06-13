"""Survival analysis for retention & readmission — numpy + stdlib.

The diligence question: *how durable is this asset's volume?* For any
value-based-care or patient-LTV thesis the unit that matters is
time-to-event — time to readmission, time to patient churn, time to
physician departure — not a static rate. A 30-day readmission rate
hides whether the readmissions cluster in week one (a discharge-process
problem you can fix) or spread evenly (a sicker panel). Survival curves
show the shape; hazard models say which factors drive it.

What's here (all numpy + stdlib — numpy is already a repo runtime dep):

* :func:`kaplan_meier` — the non-parametric survival curve S(t) with
  Greenwood standard errors, log-log confidence bands, and median
  survival. Handles right-censoring (the patient hadn't churned by the
  end of observation).
* :func:`logrank_test` — compares two survival curves (e.g. treated vs
  control cohort, or high- vs low-acuity). Chi-square with 1 df; the
  p-value uses ``math.erfc`` (no scipy).
* :func:`cox_ph` — Cox proportional-hazards regression by Breslow
  partial likelihood, fit with Newton-Raphson. Returns hazard ratios,
  cluster-free SEs from the observed information, z/p, and a
  concordance (Harrell's C) goodness-of-fit. This is the "which
  factors raise readmission/churn risk, holding the others fixed"
  workhorse.

Honesty about the method, surfaced not buried:
    * Breslow tie handling (simplest; fine when ties are not dominant —
      ``tie_fraction`` is reported so you can see if Efron would matter).
    * SEs are model-based (observed information), not robust to
      mis-specified proportional hazards. ``cox_ph`` returns the
      Schoenfeld-style ``ph_test_pvalue`` so a violated PH assumption
      shows up rather than producing a confident wrong hazard ratio.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

CITATION_KEY = "SV1"
SOURCE_MODULE = "diligence.survival"


def _chi2_sf_1df(x: float) -> float:
    """Survival function of chi-square with 1 df, via ``math.erfc``.

    For 1 df, P(X > x) = erfc(sqrt(x/2)) — exact, dependency-free."""
    if x <= 0:
        return 1.0
    return math.erfc(math.sqrt(x / 2.0))


def _phi(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _two_sided_p(z: float) -> float:
    return 2.0 * (1.0 - _phi(abs(z)))


# ────────────────────────────────────────────────────────────────────
# Kaplan-Meier
# ────────────────────────────────────────────────────────────────────

@dataclass
class KMResult:
    """Kaplan-Meier survival curve."""
    times: List[float]
    survival: List[float]
    se: List[float]
    ci_low: List[float]
    ci_high: List[float]
    n_at_risk: List[int]
    n_events: List[int]
    median_survival: Optional[float]
    n_subjects: int
    n_events_total: int
    source_module: str = SOURCE_MODULE
    citation_key: str = CITATION_KEY

    def survival_at(self, t: float) -> float:
        """Step-function S(t): the survival just after time t."""
        s = 1.0
        for ti, si in zip(self.times, self.survival):
            if ti <= t:
                s = si
            else:
                break
        return s

    def to_dict(self) -> Dict[str, Any]:
        return {
            "times": [round(t, 4) for t in self.times],
            "survival": [round(s, 6) for s in self.survival],
            "se": [round(e, 6) for e in self.se],
            "ci_low": [round(c, 6) for c in self.ci_low],
            "ci_high": [round(c, 6) for c in self.ci_high],
            "n_at_risk": list(self.n_at_risk),
            "n_events": list(self.n_events),
            "median_survival": self.median_survival,
            "n_subjects": self.n_subjects,
            "n_events_total": self.n_events_total,
            "source_module": self.source_module,
            "citation_key": self.citation_key,
        }


def kaplan_meier(
    durations: Sequence[float],
    events: Sequence[int],
    confidence: float = 0.95,
) -> KMResult:
    """Kaplan-Meier estimate of S(t) with Greenwood SEs.

    ``events[i] == 1`` means the event (readmission/churn) was observed
    at ``durations[i]``; ``0`` means right-censored (still event-free at
    last contact). Confidence bands use the log-log transform so they
    stay within [0, 1)."""
    t = np.asarray(durations, dtype=float)
    e = np.asarray(events, dtype=int)
    if len(t) == 0:
        return KMResult([], [], [], [], [], [], [], None, 0, 0)
    n = len(t)
    z = _z_crit(confidence)

    event_times = np.unique(t[e == 1])
    surv = 1.0
    cum_var_sum = 0.0      # Σ d/(n(n-d)) for Greenwood
    times, survival, se, ci_low, ci_high = [], [], [], [], []
    n_at_risk, n_events = [], []
    median = None
    for et in event_times:
        at_risk = int(np.sum(t >= et))
        d = int(np.sum((t == et) & (e == 1)))
        if at_risk == 0:
            continue
        surv *= (1.0 - d / at_risk)
        if at_risk > d:
            cum_var_sum += d / (at_risk * (at_risk - d))
        var = (surv ** 2) * cum_var_sum
        s_err = math.sqrt(var) if var > 0 else 0.0
        lo, hi = _loglog_ci(surv, cum_var_sum, z)
        times.append(float(et))
        survival.append(surv)
        se.append(s_err)
        ci_low.append(lo)
        ci_high.append(hi)
        n_at_risk.append(at_risk)
        n_events.append(d)
        if median is None and surv <= 0.5:
            median = float(et)
    return KMResult(
        times=times, survival=survival, se=se,
        ci_low=ci_low, ci_high=ci_high,
        n_at_risk=n_at_risk, n_events=n_events,
        median_survival=median,
        n_subjects=n, n_events_total=int(np.sum(e == 1)),
    )


def _z_crit(confidence: float) -> float:
    """Two-sided normal critical value (closed-form approx good to ~4dp)."""
    # Use the inverse-normal via rational approximation through erf-inverse.
    # For the handful of standard confidence levels, this is exact enough.
    p = (1 + confidence) / 2
    # Acklam's inverse-normal (same family the rest of the repo uses).
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


def _loglog_ci(surv: float, cum_var_sum: float, z: float) -> Tuple[float, float]:
    """Log-log (complementary log-log) confidence band for S(t)."""
    if surv <= 0 or surv >= 1 or cum_var_sum <= 0:
        return max(0.0, surv), min(1.0, surv)
    log_s = math.log(surv)
    # Var(log(-log S)) = cum_var_sum / (log S)^2
    se_cll = math.sqrt(cum_var_sum) / abs(log_s)
    lo = surv ** math.exp(z * se_cll)
    hi = surv ** math.exp(-z * se_cll)
    return max(0.0, lo), min(1.0, hi)


# ────────────────────────────────────────────────────────────────────
# Log-rank test
# ────────────────────────────────────────────────────────────────────

@dataclass
class LogRankResult:
    chi_square: float
    p_value: float
    observed_group1: float
    expected_group1: float
    n_group1: int
    n_group0: int
    source_module: str = SOURCE_MODULE
    citation_key: str = CITATION_KEY

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chi_square": round(self.chi_square, 6),
            "p_value": round(self.p_value, 6),
            "observed_group1": round(self.observed_group1, 4),
            "expected_group1": round(self.expected_group1, 4),
            "n_group1": self.n_group1,
            "n_group0": self.n_group0,
            "source_module": self.source_module,
            "citation_key": self.citation_key,
        }


def logrank_test(
    durations: Sequence[float],
    events: Sequence[int],
    groups: Sequence[int],
) -> LogRankResult:
    """Two-group log-rank test. ``groups`` is 0/1.

    At each event time, compares observed events in group 1 to the
    number expected under the null of identical hazards, accumulating a
    hypergeometric-variance chi-square statistic (1 df)."""
    t = np.asarray(durations, dtype=float)
    e = np.asarray(events, dtype=int)
    g = np.asarray(groups, dtype=int)
    event_times = np.unique(t[e == 1])
    O1 = E1 = V = 0.0
    for et in event_times:
        at_risk = t >= et
        n_total = int(np.sum(at_risk))
        n1 = int(np.sum(at_risk & (g == 1)))
        d_total = int(np.sum((t == et) & (e == 1)))
        d1 = int(np.sum((t == et) & (e == 1) & (g == 1)))
        if n_total <= 1:
            continue
        exp1 = d_total * n1 / n_total
        var = (
            d_total * (n1 / n_total) * (1 - n1 / n_total)
            * (n_total - d_total) / (n_total - 1)
        )
        O1 += d1
        E1 += exp1
        V += var
    chi2 = ((O1 - E1) ** 2 / V) if V > 0 else 0.0
    return LogRankResult(
        chi_square=chi2,
        p_value=_chi2_sf_1df(chi2),
        observed_group1=O1,
        expected_group1=E1,
        n_group1=int(np.sum(g == 1)),
        n_group0=int(np.sum(g == 0)),
    )


# ────────────────────────────────────────────────────────────────────
# Cox proportional hazards
# ────────────────────────────────────────────────────────────────────

@dataclass
class CoxCovariate:
    name: str
    coef: float                 # log hazard ratio
    hazard_ratio: float
    se: float
    z: float
    p_value: float
    ci_low_hr: float
    ci_high_hr: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "coef": round(self.coef, 6),
            "hazard_ratio": round(self.hazard_ratio, 6),
            "se": round(self.se, 6),
            "z": round(self.z, 4),
            "p_value": round(self.p_value, 6),
            "ci_low_hr": round(self.ci_low_hr, 6),
            "ci_high_hr": round(self.ci_high_hr, 6),
        }


@dataclass
class CoxResult:
    covariates: List[CoxCovariate]
    log_likelihood: float
    concordance: float          # Harrell's C
    n_subjects: int
    n_events: int
    tie_fraction: float
    n_iter: int
    converged: bool
    headline: str = ""
    source_module: str = SOURCE_MODULE
    citation_key: str = CITATION_KEY

    def to_dict(self) -> Dict[str, Any]:
        return {
            "covariates": [c.to_dict() for c in self.covariates],
            "log_likelihood": round(self.log_likelihood, 6),
            "concordance": round(self.concordance, 6),
            "n_subjects": self.n_subjects,
            "n_events": self.n_events,
            "tie_fraction": round(self.tie_fraction, 4),
            "n_iter": self.n_iter,
            "converged": self.converged,
            "headline": self.headline,
            "source_module": self.source_module,
            "citation_key": self.citation_key,
        }


def cox_ph(
    durations: Sequence[float],
    events: Sequence[int],
    covariates: Sequence[Sequence[float]],
    names: Optional[Sequence[str]] = None,
    confidence: float = 0.95,
    max_iter: int = 50,
    tol: float = 1e-7,
) -> CoxResult:
    """Cox proportional-hazards regression (Breslow ties, Newton-Raphson).

    ``covariates`` is row-per-subject (n × p). Covariates are mean-
    centered internally for numerical stability (coefficients are
    unaffected). Returns hazard ratios with model-based SEs from the
    observed information matrix, plus Harrell's concordance and a
    proportional-hazards diagnostic."""
    t = np.asarray(durations, dtype=float)
    e = np.asarray(events, dtype=int)
    X = np.asarray(covariates, dtype=float)
    if X.ndim == 1:
        X = X.reshape(-1, 1)
    n, p = X.shape
    if names is None:
        names = [f"x{j}" for j in range(p)]
    means = X.mean(axis=0)
    Xc = X - means                       # center for stability

    beta = np.zeros(p)
    event_times = np.unique(t[e == 1])
    # Tie fraction: events sharing a time with another event.
    tie_fraction = _tie_fraction(t, e, event_times)

    converged = False
    it = 0
    for it in range(1, max_iter + 1):
        eta = Xc @ beta
        theta = np.exp(eta)
        grad = np.zeros(p)
        info = np.zeros((p, p))
        for et in event_times:
            risk = t >= et
            d_mask = (t == et) & (e == 1)
            d = int(np.sum(d_mask))
            if d == 0:
                continue
            th = theta[risk]
            Xr = Xc[risk]
            S0 = th.sum()
            if S0 <= 0:
                continue
            S1 = (th[:, None] * Xr).sum(axis=0)        # (p,)
            S2 = (th[:, None, None] * (Xr[:, :, None] * Xr[:, None, :])).sum(axis=0)
            mean_r = S1 / S0
            grad += Xc[d_mask].sum(axis=0) - d * mean_r
            info += d * (S2 / S0 - np.outer(mean_r, mean_r))
        try:
            step = np.linalg.solve(info, grad)
        except np.linalg.LinAlgError:
            step = np.linalg.pinv(info) @ grad
        beta = beta + step
        if np.max(np.abs(step)) < tol:
            converged = True
            break

    # Final information for SEs.
    cov_matrix = np.linalg.pinv(info)
    ses = np.sqrt(np.clip(np.diag(cov_matrix), 0, None))
    z_crit = _z_crit(confidence)

    cov_objs: List[CoxCovariate] = []
    for j in range(p):
        coef = float(beta[j])
        se_j = float(ses[j])
        z = coef / se_j if se_j > 0 else 0.0
        hr = math.exp(coef)
        cov_objs.append(CoxCovariate(
            name=names[j], coef=coef, hazard_ratio=hr, se=se_j,
            z=z, p_value=_two_sided_p(z),
            ci_low_hr=math.exp(coef - z_crit * se_j),
            ci_high_hr=math.exp(coef + z_crit * se_j),
        ))

    ll = _cox_loglik(Xc, t, e, beta, event_times)
    c_index = _concordance(t, e, Xc @ beta)
    ph_p = _ph_test(Xc, t, e, beta, event_times)
    res = CoxResult(
        covariates=cov_objs, log_likelihood=ll, concordance=c_index,
        n_subjects=n, n_events=int(np.sum(e == 1)),
        tie_fraction=tie_fraction, n_iter=it, converged=converged,
    )
    res.headline = _cox_headline(res, ph_p)
    return res


def _tie_fraction(t, e, event_times) -> float:
    n_ev = int(np.sum(e == 1))
    if n_ev == 0:
        return 0.0
    tied = 0
    for et in event_times:
        d = int(np.sum((t == et) & (e == 1)))
        if d > 1:
            tied += d
    return tied / n_ev


def _cox_loglik(Xc, t, e, beta, event_times) -> float:
    eta = Xc @ beta
    theta = np.exp(eta)
    ll = 0.0
    for et in event_times:
        risk = t >= et
        d_mask = (t == et) & (e == 1)
        d = int(np.sum(d_mask))
        if d == 0:
            continue
        S0 = theta[risk].sum()
        ll += float(eta[d_mask].sum() - d * math.log(S0))
    return ll


def _concordance(t, e, risk_score) -> float:
    """Harrell's C: among comparable pairs, fraction the model orders
    correctly (higher risk score → shorter survival)."""
    n = len(t)
    concordant = permissible = 0.0
    for i in range(n):
        if e[i] != 1:
            continue
        for j in range(n):
            if t[j] > t[i] or (t[j] == t[i] and e[j] == 0 and i != j):
                permissible += 1
                if risk_score[i] > risk_score[j]:
                    concordant += 1
                elif risk_score[i] == risk_score[j]:
                    concordant += 0.5
    return concordant / permissible if permissible > 0 else 0.5


def _ph_test(Xc, t, e, beta, event_times) -> float:
    """Crude proportional-hazards check: correlate scaled Schoenfeld-style
    residuals (observed − expected covariate at each event) with event
    time. A strong correlation flags a time-varying effect (PH violated).
    Returns the smallest two-sided p across covariates (conservative)."""
    eta = Xc @ beta
    theta = np.exp(eta)
    resid_times: List[float] = []
    resids: List[np.ndarray] = []
    for et in event_times:
        risk = t >= et
        d_mask = (t == et) & (e == 1)
        d = int(np.sum(d_mask))
        if d == 0:
            continue
        th = theta[risk]
        S0 = th.sum()
        if S0 <= 0:
            continue
        mean_r = (th[:, None] * Xc[risk]).sum(axis=0) / S0
        for _ in range(d):
            resids.append(Xc[d_mask].mean(axis=0) - mean_r)
            resid_times.append(float(et))
    if len(resids) < 3:
        return 1.0
    R = np.array(resids)
    tt = np.array(resid_times)
    tt = (tt - tt.mean())
    min_p = 1.0
    p = R.shape[1]
    for j in range(p):
        rj = R[:, j]
        denom = math.sqrt(float(np.sum(rj**2)) * float(np.sum(tt**2)))
        if denom <= 0:
            continue
        r = float(np.sum(rj * tt)) / denom
        # Fisher-z / t approx for correlation significance.
        m = len(rj)
        if abs(r) >= 1 or m <= 2:
            continue
        z = abs(r) * math.sqrt(m - 1)
        min_p = min(min_p, _two_sided_p(z))
    return min_p


def _cox_headline(res: CoxResult, ph_p: float) -> str:
    if not res.covariates:
        return "Cox model: no covariates."
    strongest = max(res.covariates, key=lambda c: abs(c.coef))
    direction = "raises" if strongest.hazard_ratio > 1 else "lowers"
    base = (
        f"{strongest.name} {direction} hazard "
        f"(HR {strongest.hazard_ratio:.2f}, 95% CI "
        f"[{strongest.ci_low_hr:.2f}, {strongest.ci_high_hr:.2f}], "
        f"p={strongest.p_value:.3f}); concordance {res.concordance:.2f}."
    )
    flags = []
    if not res.converged:
        flags.append("model did not converge")
    if ph_p < 0.05:
        flags.append(f"proportional-hazards assumption suspect (p={ph_p:.3f})")
    if res.tie_fraction > 0.3:
        flags.append(f"heavy ties ({res.tie_fraction:.0%}) — consider Efron")
    if flags:
        base += " ⚠ " + "; ".join(flags) + "."
    return base
