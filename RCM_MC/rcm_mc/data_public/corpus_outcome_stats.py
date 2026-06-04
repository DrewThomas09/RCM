"""Credibility-first outcome statistics on the **real** (verified) corpus.

Why this exists
---------------
The corpus's realized-return fields are thin on the real tier: only ~6% of
verified deals carry a ``realized_moic`` (sponsors rarely disclose returns), so
a MOIC regression on real-only data would be almost all nulls. But the *outcome*
field is well populated (~83%) and 100% of real deals are sector- and
vintage-tagged. The honest, defensible statistics on the real base are therefore
**outcome-based**: how often do real PE healthcare deals reach public distress or
bankruptcy, and how does that incidence vary by sector and by vintage?

This module computes exactly that, and — unlike a naive ``k/n`` headline — reports
every rate with:

- the **known-outcome sample size** it is computed over (deals with ``outcome ==
  None`` are excluded from the denominator, never silently counted as "fine");
- a **Wilson score 95% confidence interval**, which is the statistically correct
  interval for a proportion and stays sensible at small ``n`` (where the textbook
  normal approximation produces nonsense like negative lower bounds); and
- an explicit **insufficient-sample flag** for cells below ``min_known`` so a
  partner never reads a 1-of-2 cell as a real "50% distress rate".

Outcome vocabulary (from ``verified_deals`` / the bridge):
``bankrupt`` · ``distressed`` · ``exited`` · ``active`` · ``None`` (unknown).

We define the headline metric as **distress incidence** = (bankrupt + distressed)
/ (deals with a known outcome). It is a base rate over the whole known-outcome
population (active included, because distress can strike an ongoing deal); it is
deliberately *not* labelled a realized IRR/MOIC loss rate. A stricter
**realized-loss rate** (bankrupt / closed outcomes) is also exposed for the
subset whose outcome is actually resolved.

Public API
----------
    wilson_interval(k, n, z=1.96)        -> (lo, hi)
    OutcomeStats                          dataclass
    compute_outcome_stats(deals, label)   -> OutcomeStats
    outcome_stats_by_sector(deals, ...)   -> List[OutcomeStats]
    outcome_stats_by_vintage(deals, ...)  -> List[OutcomeStats]
    corpus_outcome_summary(universe)      -> dict   (programmatic / UI)
    real_corpus_outcome_report()          -> str    (IC-ready text)

Pure standard library (``math`` only); no new runtime dependencies.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# Outcomes that count as an adverse (distress) event in the numerator.
_ADVERSE = ("bankrupt", "distressed")
# Outcomes that represent a *resolved* deal (used for the stricter realized-loss
# rate denominator); "active"/"distressed" are still in flight and excluded.
_REALIZED = ("bankrupt", "exited")

_Z_95 = 1.959963984540054  # standard normal quantile for a two-sided 95% CI


# ---------------------------------------------------------------------------
# Proportion confidence interval (Wilson score)
# ---------------------------------------------------------------------------

def wilson_interval(k: int, n: int, z: float = _Z_95) -> tuple[float, float]:
    """Wilson score confidence interval for a binomial proportion ``k/n``.

    Correct at small ``n`` where the normal approximation breaks down (it never
    leaves [0, 1] and is asymmetric near the boundaries). Returns ``(0.0, 1.0)``
    — maximal ignorance — when ``n == 0``.
    """
    if n <= 0:
        return (0.0, 1.0)
    p = k / n
    z2 = z * z
    denom = 1.0 + z2 / n
    center = (p + z2 / (2 * n)) / denom
    half = (z / denom) * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))
    lo = max(0.0, center - half)
    hi = min(1.0, center + half)
    return (lo, hi)


# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------

@dataclass
class OutcomeStats:
    """Outcome statistics for one cohort (overall, a sector, or a vintage)."""
    label: str
    n_total: int                  # all deals in the cohort
    n_known: int                  # deals with a non-null outcome (the denominator)
    n_bankrupt: int
    n_distressed: int
    n_exited: int
    n_active: int
    distress_rate: Optional[float]      # (bankrupt + distressed) / n_known
    distress_ci_lo: Optional[float]     # Wilson 95% CI lower bound
    distress_ci_hi: Optional[float]     # Wilson 95% CI upper bound
    realized_loss_rate: Optional[float]  # bankrupt / (bankrupt + exited)
    n_realized: int                     # bankrupt + exited (resolved deals)
    insufficient: bool                  # n_known < min_known -> read with caution

    @property
    def n_adverse(self) -> int:
        return self.n_bankrupt + self.n_distressed

    @property
    def coverage(self) -> Optional[float]:
        """Fraction of the cohort with a known outcome (denominator honesty)."""
        return (self.n_known / self.n_total) if self.n_total else None


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------

def _outcome(deal: Dict[str, Any]) -> Optional[str]:
    o = deal.get("outcome")
    if not o:
        return None
    o = str(o).strip().lower()
    return o or None


def compute_outcome_stats(
    deals: List[Dict[str, Any]],
    label: str = "All",
    min_known: int = 5,
) -> OutcomeStats:
    """Compute outcome statistics for a list of corpus deals.

    The distress-rate denominator is the count of deals with a *known* outcome;
    deals with ``outcome == None`` are excluded (never silently treated as
    non-distressed). ``insufficient`` is set when ``n_known < min_known``.
    """
    n_total = len(deals)
    n_b = n_d = n_e = n_a = 0
    for deal in deals:
        o = _outcome(deal)
        if o == "bankrupt":
            n_b += 1
        elif o == "distressed":
            n_d += 1
        elif o == "exited":
            n_e += 1
        elif o == "active":
            n_a += 1
    n_known = n_b + n_d + n_e + n_a
    n_adverse = n_b + n_d
    n_realized = n_b + n_e

    if n_known > 0:
        distress_rate = n_adverse / n_known
        ci_lo, ci_hi = wilson_interval(n_adverse, n_known)
    else:
        distress_rate = ci_lo = ci_hi = None

    realized_loss_rate = (n_b / n_realized) if n_realized > 0 else None

    return OutcomeStats(
        label=label,
        n_total=n_total,
        n_known=n_known,
        n_bankrupt=n_b,
        n_distressed=n_d,
        n_exited=n_e,
        n_active=n_a,
        distress_rate=distress_rate,
        distress_ci_lo=ci_lo,
        distress_ci_hi=ci_hi,
        realized_loss_rate=realized_loss_rate,
        n_realized=n_realized,
        insufficient=(n_known < min_known),
    )


def outcome_stats_by_sector(
    deals: List[Dict[str, Any]],
    min_known: int = 5,
) -> List[OutcomeStats]:
    """Per-sector outcome stats, sorted by distress rate (desc), then sample
    size (desc). Sectors below ``min_known`` are still returned but carry
    ``insufficient=True`` so callers can separate signal from noise.
    """
    by_sector: Dict[str, List[Dict[str, Any]]] = {}
    for d in deals:
        sec = d.get("sector") or "unclassified"
        by_sector.setdefault(str(sec), []).append(d)

    out = [
        compute_outcome_stats(rows, label=sec, min_known=min_known)
        for sec, rows in by_sector.items()
    ]
    out.sort(key=lambda s: (-(s.distress_rate or -1.0), -s.n_known))
    return out


def outcome_stats_by_vintage(
    deals: List[Dict[str, Any]],
    bucket: int = 3,
    min_known: int = 5,
) -> List[OutcomeStats]:
    """Outcome stats grouped into ``bucket``-year vintage windows (e.g. a value
    of 3 buckets 2004-2006, 2007-2009, ...). Buckets are labelled by their
    inclusive year range and returned in chronological order.
    """
    if bucket < 1:
        bucket = 1
    by_bucket: Dict[int, List[Dict[str, Any]]] = {}
    for d in deals:
        yr = d.get("year") or d.get("entry_year")
        if yr is None:
            continue
        try:
            yr = int(yr)
        except (TypeError, ValueError):
            continue
        start = (yr // bucket) * bucket
        by_bucket.setdefault(start, []).append(d)

    out = []
    for start in sorted(by_bucket):
        end = start + bucket - 1
        label = f"{start}-{end}" if bucket > 1 else f"{start}"
        out.append(compute_outcome_stats(by_bucket[start], label=label, min_known=min_known))
    return out


# Macro-cycle regimes in rough chronological/severity order, for stable display.
_REGIME_ORDER = (
    "recovery", "expansion", "peak", "correction", "contraction",
    "normalization", "unknown",
)


def outcome_stats_by_regime(
    deals: List[Dict[str, Any]],
    min_known: int = 5,
) -> List[OutcomeStats]:
    """Distress/outcome stats grouped by the **entry-year macro regime**
    (expansion / peak / contraction / …) from ``corpus_vintage_risk_model``.

    This tests the platform's regime-risk heuristic against realized outcomes:
    does entering in a "peak" vintage actually correlate with more distress in
    the verified corpus? **Caveat (right-censoring):** recent regimes (peak
    2021-22, normalization 2023-24) are dominated by deals too young to have
    surfaced distress, so their low observed rates reflect immaturity, not
    safety — read alongside the vintage table, not as a hazard model.
    """
    from .corpus_vintage_risk_model import regime_for_year
    by_regime: Dict[str, List[Dict[str, Any]]] = {}
    for d in deals:
        reg = regime_for_year(d.get("year") or d.get("entry_year"))
        by_regime.setdefault(reg, []).append(d)
    # Stable order: known regimes first (chronological-ish), then any extras.
    ordered = [r for r in _REGIME_ORDER if r in by_regime]
    ordered += [r for r in by_regime if r not in _REGIME_ORDER]
    return [
        compute_outcome_stats(by_regime[r], label=r, min_known=min_known)
        for r in ordered
    ]


# ---------------------------------------------------------------------------
# Corpus-level convenience (real universe by default)
# ---------------------------------------------------------------------------

def _load_real() -> List[Dict[str, Any]]:
    from .corpus_loader import load_corpus_deals
    return load_corpus_deals("real")


def corpus_outcome_summary(universe: str = "real") -> Dict[str, Any]:
    """Programmatic summary for the chosen universe (default real-only).

    Returns a JSON-friendly dict: overall stats plus sector and vintage
    breakdowns (each row already carries its CI + insufficient flag).
    """
    from .corpus_loader import load_corpus_deals
    deals = load_corpus_deals(universe if universe in ("real", "synthetic", "all") else "real")
    overall = compute_outcome_stats(deals, label=f"{universe} corpus")

    def _row(s: OutcomeStats) -> Dict[str, Any]:
        return {
            "label": s.label,
            "n_total": s.n_total,
            "n_known": s.n_known,
            "n_adverse": s.n_adverse,
            "n_bankrupt": s.n_bankrupt,
            "n_distressed": s.n_distressed,
            "n_exited": s.n_exited,
            "n_active": s.n_active,
            "distress_rate": s.distress_rate,
            "ci": [s.distress_ci_lo, s.distress_ci_hi],
            "realized_loss_rate": s.realized_loss_rate,
            "n_realized": s.n_realized,
            "insufficient": s.insufficient,
        }

    return {
        "universe": universe,
        "overall": _row(overall),
        "by_sector": [_row(s) for s in outcome_stats_by_sector(deals)],
        "by_vintage": [_row(s) for s in outcome_stats_by_vintage(deals)],
        "by_regime": [_row(s) for s in outcome_stats_by_regime(deals)],
    }


# ---------------------------------------------------------------------------
# Text report
# ---------------------------------------------------------------------------

def _pct(x: Optional[float]) -> str:
    return f"{x * 100:4.1f}%" if x is not None else "  n/a"


def _ci_str(s: OutcomeStats) -> str:
    if s.distress_ci_lo is None:
        return "       —      "
    return f"[{s.distress_ci_lo * 100:4.1f}–{s.distress_ci_hi * 100:4.1f}%]"


def real_corpus_outcome_report(min_known: int = 5) -> str:
    """IC-ready text report of distress/outcome statistics on the real corpus.

    Every rate is paired with its known-outcome n and a Wilson 95% CI; sectors
    and vintages below ``min_known`` resolved outcomes are flagged so single-
    deal noise is never read as signal.
    """
    deals = _load_real()
    overall = compute_outcome_stats(deals, label="Real corpus", min_known=min_known)

    lines: List[str] = [
        "Real-Corpus Outcome Statistics (verified, source-cited deals only)",
        "=" * 74,
        f"Deals: {overall.n_total}   Known outcome: {overall.n_known} "
        f"({_pct(overall.coverage)})   "
        f"[bankrupt {overall.n_bankrupt} · distressed {overall.n_distressed} · "
        f"exited {overall.n_exited} · active {overall.n_active}]",
        "",
        f"Distress incidence (bankrupt+distressed / known outcome): "
        f"{_pct(overall.distress_rate)}  {_ci_str(overall)}  (n={overall.n_known})",
        f"Realized-loss rate (bankrupt / resolved): "
        f"{_pct(overall.realized_loss_rate)}  (n={overall.n_realized} resolved)",
        "Rates are base rates over disclosed outcomes — not realized IRR/MOIC losses.",
        "",
        "By sector (>= %d known outcomes; others flagged *insufficient*):" % min_known,
        f"  {'Sector':<22}{'N':>4}{'Known':>7}{'Distress':>10}{'  95% CI':<16}{'Flag'}",
        "  " + "-" * 70,
    ]
    for s in outcome_stats_by_sector(deals, min_known=min_known):
        flag = "  *low n*" if s.insufficient else ""
        lines.append(
            f"  {s.label:<22}{s.n_total:>4}{s.n_known:>7}{_pct(s.distress_rate):>10}"
            f"  {_ci_str(s):<14}{flag}"
        )

    lines += ["", "By vintage (3-year windows):",
              f"  {'Vintage':<12}{'N':>4}{'Known':>7}{'Distress':>10}{'  95% CI':<16}{'Flag'}",
              "  " + "-" * 60]
    for s in outcome_stats_by_vintage(deals, bucket=3, min_known=min_known):
        flag = "  *low n*" if s.insufficient else ""
        lines.append(
            f"  {s.label:<12}{s.n_total:>4}{s.n_known:>7}{_pct(s.distress_rate):>10}"
            f"  {_ci_str(s):<14}{flag}"
        )

    lines += ["", "By entry-year macro regime (vs. the regime-risk heuristic):",
              f"  {'Regime':<14}{'N':>4}{'Known':>7}{'Distress':>10}{'  95% CI':<16}{'Flag'}",
              "  " + "-" * 62]
    for s in outcome_stats_by_regime(deals, min_known=min_known):
        flag = "  *low n*" if s.insufficient else ""
        lines.append(
            f"  {s.label:<14}{s.n_total:>4}{s.n_known:>7}{_pct(s.distress_rate):>10}"
            f"  {_ci_str(s):<14}{flag}"
        )
    lines.append(
        "  Note: recent regimes (peak '21-22, normalization '23-24) are right-censored"
    )
    lines.append(
        "  — deals too young to have surfaced distress — so low rates there reflect"
    )
    lines.append(
        "  immaturity, not safety. Realized distress concentrates in the mature"
    )
    lines.append(
        "  2016-18 expansion cohort (value-based-care / SPAC-era failures)."
    )

    return "\n".join(lines) + "\n"
