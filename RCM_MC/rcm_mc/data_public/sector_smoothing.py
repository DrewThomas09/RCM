"""Bayesian smoothing + zero-base guards + TTV for sector aggregations.

PEDESK Phase 3 (Week 3, Model Retraining) — Sector Momentum + IRR
Dispersion fixes. The shipped pages had four credibility-destroying
defects that this module addresses centrally:

1. **Low-volume subsectors over-stated their signal.** A sector with
   3 disclosed-IRR deals could surface a 38% median IRR that was
   essentially one deal driving the central tendency. Bayesian
   smoothing pulls per-sector quantile estimates toward the corpus
   prior with a weight that decays as the sector sample grows, so
   small-N subsectors regress to the corpus mean instead of
   masquerading as alpha.

2. **Pure deal count obscured economic significance.** A sector
   going from 1 deal to 5 deals is identical to one going from
   $50M of TTV to $250M of TTV by deal count, but the second
   sector might be 100× the first by capital deployed. Track
   ``total_transaction_value`` (sum of EV) alongside count so
   the partner sees both volume signals.

3. **Zero-base percentages produced fictitious +400%/+∞ trends.**
   ``(recent - prior) / max(prior, 1) * 100`` reads "moving from 1
   dialysis deal to 5" as +400% — it isn't a macro trend, it's
   noise. Replace with two safer signals: (a) a Laplace-smoothed
   percent change that adds a prior term to both numerator and
   denominator, and (b) a "suppress and label" guard that shows
   absolute counts only when the denominator is below a partner-
   visible reliability threshold.

4. **24% median corpus IRR was survivor-biased.** Deals without
   disclosed IRR — typically failures, ongoing holds, or quietly
   written-down positions — were silently excluded from the
   distribution. Provide a ``realization_rate`` helper so every
   sector benchmark can be paired with the share of deals that
   actually realized, and a tightened-taxonomy filter that drops
   sub-thresholds out of the published table.

Pure stdlib + numpy. No new dependencies.
"""
from __future__ import annotations

from math import log
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


# ---------------------------------------------------------------------------
# Bayesian smoothing on quantile estimates
# ---------------------------------------------------------------------------
#
# Standard formula: smoothed = (n * x_observed + k * x_prior) / (n + k)
# Where:
#   n = sample size in the cell (e.g. one sector)
#   x_observed = the per-sector quantile (e.g. P50 IRR)
#   x_prior = corpus-wide quantile estimate
#   k = prior strength — interpretable as "k pseudo-deals at the corpus prior"
#
# The result is a James-Stein-style shrinkage estimator that gives
# better mean-squared-error than the raw per-sector estimate when N
# is small. The partner-visible behaviour: a 3-deal sector with raw
# P50 IRR of 38% gets smoothed to ~25% (mostly the corpus prior),
# while a 50-deal sector with raw P50 IRR of 28% stays near 28%.

DEFAULT_PRIOR_WEIGHT = 5


def bayesian_smooth(
    sector_value: Optional[float],
    n_observed: int,
    corpus_prior: Optional[float],
    *,
    prior_weight: int = DEFAULT_PRIOR_WEIGHT,
) -> Optional[float]:
    """Return a shrinkage-smoothed estimate, pulling small-N toward prior.

    Returns ``None`` when both inputs are ``None`` (no signal to
    blend). When only the corpus prior is available, returns it
    unchanged. When only the sector value is available — unusual,
    means the corpus prior couldn't be computed — returns it
    unchanged.
    """
    if sector_value is None and corpus_prior is None:
        return None
    if sector_value is None:
        return corpus_prior
    if corpus_prior is None:
        return sector_value
    if n_observed <= 0:
        return corpus_prior
    n = float(n_observed)
    k = float(prior_weight)
    return (n * float(sector_value) + k * float(corpus_prior)) / (n + k)


def shrinkage_weight(n_observed: int, *, prior_weight: int = DEFAULT_PRIOR_WEIGHT) -> float:
    """Return the prior's weight in the smoothed estimate, in [0, 1].

    Surface-level value for the partner UI: "prior contributes 62%
    of the displayed P50 because this sector only has 3 deals".
    """
    if n_observed <= 0:
        return 1.0
    n = float(n_observed)
    k = float(prior_weight)
    return k / (n + k)


# ---------------------------------------------------------------------------
# Total Transaction Value
# ---------------------------------------------------------------------------


def total_transaction_value(deals: Iterable[Dict[str, Any]]) -> float:
    """Sum of ``ev_mm`` across deals, in millions. Missing values count as 0."""
    total = 0.0
    for d in deals:
        ev = d.get("ev_mm")
        if ev is None:
            continue
        try:
            total += float(ev)
        except (TypeError, ValueError):
            continue
    return total


def fmt_ttv(ev_mm: float) -> str:
    """Compact USD formatter for TTV display: $1.2B / $450M / $25M."""
    if ev_mm is None:
        return "—"
    if ev_mm >= 1000:
        return f"${ev_mm / 1000:.2f}B"
    if ev_mm >= 1:
        return f"${ev_mm:.2f}M"
    if ev_mm > 0:
        return f"${ev_mm * 1000:.0f}K"
    return "$0"


# ---------------------------------------------------------------------------
# Zero-base percentage guard
# ---------------------------------------------------------------------------
#
# The old formula: change = (recent - prior) / max(prior, 1) * 100.
# When prior=0 → change = 100 * (recent - 0) / 1 = 100 * recent → reads
# "moving from 0 deals to 5 = +500%" which is meaningless.
#
# Two replacements:
#
# - safe_change_pct(): returns None when the denominator is below the
#   ``min_reliable`` threshold so the UI can render "—" or an absolute
#   delta instead of an inflated percent.
#
# - laplace_change_pct(): adds a prior term to both numerator and
#   denominator. With k=2: a 0→5 jump becomes (5+2-0-2)/(0+2) = +250%;
#   a 1→5 jump becomes (5+2-1-2)/(1+2) = +133%; a 50→55 jump becomes
#   (55+2-50-2)/(50+2) ≈ +9.6%. The smoothing dampens noise on
#   small-base sectors without zeroing them out entirely.

MIN_RELIABLE_BASE = 3
LAPLACE_PRIOR_COUNT = 2


def safe_change_pct(
    recent: float,
    prior: float,
    *,
    min_reliable: int = MIN_RELIABLE_BASE,
) -> Optional[float]:
    """Return percent change only when the denominator clears the
    reliability threshold; otherwise ``None`` so the UI can show an
    absolute delta instead of a meaningless percentage."""
    try:
        p = float(prior)
        r = float(recent)
    except (TypeError, ValueError):
        return None
    if p < min_reliable:
        return None
    return (r - p) / p * 100.0


def laplace_change_pct(
    recent: float,
    prior: float,
    *,
    k: int = LAPLACE_PRIOR_COUNT,
) -> float:
    """Laplace-smoothed percent change — adds ``k`` pseudo-deals to
    each end. Defined for every input including 0→N transitions."""
    try:
        p = float(prior) + k
        r = float(recent) + k
    except (TypeError, ValueError):
        return 0.0
    if p <= 0:
        return 0.0
    return (r - p) / p * 100.0


def log_ratio_change(recent: float, prior: float, *, k: int = LAPLACE_PRIOR_COUNT) -> float:
    """Log-ratio change in nats — symmetric, well-behaved at zero base.

    For partners who want a single momentum metric that's defined on
    0→N transitions and doesn't explode. ``log((recent+k) / (prior+k))``.
    A doubling of count is ~+0.69 regardless of base.
    """
    try:
        p = float(prior) + k
        r = float(recent) + k
    except (TypeError, ValueError):
        return 0.0
    if p <= 0 or r <= 0:
        return 0.0
    return log(r / p)


# ---------------------------------------------------------------------------
# Survivor-bias diagnostic
# ---------------------------------------------------------------------------


def realization_rate(deals: Sequence[Dict[str, Any]]) -> Tuple[int, int, float]:
    """Return ``(realized_count, total_count, realized_pct)`` for a sector.

    Realized = a deal carrying a non-None ``realized_moic`` field. The
    survivor-bias diagnostic: a sector showing a 38% median IRR with
    a 25% realization rate is reporting on 1-in-4 deals. Pair every
    quantile output with this tuple in the partner UI so the IRR
    figure always carries its sample-coverage context.
    """
    total = len(deals)
    realized = sum(1 for d in deals if d.get("realized_moic") is not None)
    pct = (realized / total * 100.0) if total else 0.0
    return realized, total, pct


def filter_publishable_sectors(
    sectors: Dict[str, Sequence[Dict[str, Any]]],
    *,
    min_realized: int = 5,
    min_realization_pct: float = 30.0,
) -> Dict[str, Sequence[Dict[str, Any]]]:
    """Return only sectors that clear the publishable thresholds.

    A sector is publishable when (a) at least ``min_realized`` deals
    have realized outcomes and (b) at least ``min_realization_pct`` of
    the sector's deals have realized. Below those thresholds, the
    quantile is too noisy to defend in IC and the survivor selection
    too acute — the page footer should still surface the count of
    suppressed sectors so the partner sees the filtration is
    deliberate.
    """
    out: Dict[str, Sequence[Dict[str, Any]]] = {}
    for sec, deals in sectors.items():
        realized, total, pct = realization_rate(list(deals))
        if realized >= min_realized and pct >= min_realization_pct:
            out[sec] = deals
    return out
