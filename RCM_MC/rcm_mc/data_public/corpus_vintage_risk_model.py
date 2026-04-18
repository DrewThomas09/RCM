"""Corpus vintage risk model — macro cycle risk by entry year.

Answers the IC question: "Are we entering at a historically bad time
in the cycle relative to similar vintage deals?"

Uses the corpus of realized deals to compute:
  1. Vintage MOIC distribution (P25/P50/P75) by entry year
  2. Vintage loss rate (fraction of deals with MOIC < 1.0)
  3. Cycle regime classification (expansion / peak / contraction / recovery)
  4. Entry-year risk score relative to corpus (0-100)

Macro regime heuristics (healthcare PE, 2000-2024):
  - 2000-2001: Peak/correction (dot-com, healthcare cost spike)
  - 2002-2004: Recovery (healthcare reform cycle)
  - 2005-2007: Expansion (credit boom, high leverage ratios)
  - 2008-2009: Contraction (GFC)
  - 2010-2014: Recovery → Expansion (ACA, healthcare services rally)
  - 2015-2016: Correction (healthcare multiples peak, HCA comp reset)
  - 2017-2019: Expansion (tax reform, M&A wave)
  - 2020:       Contraction/Disruption (COVID-19)
  - 2021-2022: Peak (ZIRP exit, SPAC frenzy, multiple expansion ceiling)
  - 2023-2024: Normalization (rate environment, PE denominator effect)

Public API:
    VintageStats       dataclass (year, n, moic_p25/p50/p75, loss_rate, regime)
    VintageRiskResult  dataclass (entry_year, score, signal, comparable_vintages)
    analyze_vintage(entry_year, corpus_deals) -> VintageRiskResult
    vintage_heatmap(corpus_deals) -> str
    vintage_risk_report(result, corpus_deals) -> str
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Macro regime classification
# ---------------------------------------------------------------------------

_REGIME_MAP: Dict[int, str] = {
    2000: "peak",
    2001: "contraction",
    2002: "recovery",
    2003: "recovery",
    2004: "expansion",
    2005: "expansion",
    2006: "expansion",
    2007: "peak",
    2008: "contraction",
    2009: "contraction",
    2010: "recovery",
    2011: "recovery",
    2012: "expansion",
    2013: "expansion",
    2014: "expansion",
    2015: "peak",
    2016: "correction",
    2017: "expansion",
    2018: "expansion",
    2019: "expansion",
    2020: "contraction",
    2021: "peak",
    2022: "peak",
    2023: "normalization",
    2024: "normalization",
}

# Historical base risk by regime (0-100)
_REGIME_BASE_RISK: Dict[str, float] = {
    "expansion": 25.0,
    "recovery": 20.0,
    "normalization": 35.0,
    "peak": 65.0,
    "correction": 55.0,
    "contraction": 70.0,
    "unknown": 40.0,
}

# Corpus-observed median MOIC by regime (healthcare PE, 2000-2024)
_REGIME_MOIC_BENCHMARK: Dict[str, float] = {
    "expansion": 2.8,
    "recovery": 3.1,
    "normalization": 2.5,
    "peak": 1.9,
    "correction": 2.2,
    "contraction": 1.4,
    "unknown": 2.4,
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class VintageStats:
    """Realized outcome statistics for a single entry vintage."""
    year: int
    n: int                          # deals in vintage
    moic_p25: Optional[float]
    moic_p50: Optional[float]
    moic_p75: Optional[float]
    loss_rate: float                # fraction with MOIC < 1.0
    regime: str                     # expansion / peak / contraction / recovery / normalization


@dataclass
class VintageRiskResult:
    """Vintage risk assessment for a proposed deal entry year."""
    entry_year: int
    regime: str
    regime_risk_score: float        # 0-100 base score from regime alone
    corpus_adjusted_score: float    # adjusted for actual corpus vintage outcomes
    signal: str                     # "green" / "yellow" / "red"
    comparable_vintage: Optional[VintageStats]    # closest realized vintage
    corpus_moic_p50: Optional[float]              # all-corpus median MOIC
    vintage_moic_benchmark: Optional[float]       # regime-type expected MOIC
    notes: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------

def _percentile(sorted_values: List[float], pct: float) -> Optional[float]:
    """Return pct-th percentile from a sorted list (0 <= pct <= 1)."""
    if not sorted_values:
        return None
    n = len(sorted_values)
    idx = pct * (n - 1)
    lo = int(idx)
    hi = min(lo + 1, n - 1)
    frac = idx - lo
    return sorted_values[lo] + frac * (sorted_values[hi] - sorted_values[lo])


def compute_vintage_stats(corpus_deals: List[Dict[str, Any]]) -> Dict[int, VintageStats]:
    """Compute realized outcome stats grouped by entry year."""
    by_year: Dict[int, List[float]] = {}
    for deal in corpus_deals:
        moic = deal.get("realized_moic")
        year = deal.get("entry_year") or deal.get("year")
        if moic is None or year is None:
            continue
        try:
            moic = float(moic)
            year = int(year)
        except (TypeError, ValueError):
            continue
        by_year.setdefault(year, []).append(moic)

    stats = {}
    for year, moics in by_year.items():
        moics_s = sorted(moics)
        regime = _REGIME_MAP.get(year, "unknown")
        stats[year] = VintageStats(
            year=year,
            n=len(moics_s),
            moic_p25=_percentile(moics_s, 0.25),
            moic_p50=_percentile(moics_s, 0.50),
            moic_p75=_percentile(moics_s, 0.75),
            loss_rate=sum(1 for m in moics_s if m < 1.0) / len(moics_s),
            regime=regime,
        )
    return stats


def _closest_vintage(
    entry_year: int,
    vintage_stats: Dict[int, VintageStats],
    min_n: int = 3,
) -> Optional[VintageStats]:
    """Return the vintage stats with the same regime or closest year."""
    entry_regime = _REGIME_MAP.get(entry_year, "unknown")

    # First try: same regime, sufficient n
    same_regime = [
        v for v in vintage_stats.values()
        if v.regime == entry_regime and v.n >= min_n
    ]
    if same_regime:
        return min(same_regime, key=lambda v: abs(v.year - entry_year))

    # Fallback: closest year with sufficient n
    sufficient = [v for v in vintage_stats.values() if v.n >= min_n]
    if sufficient:
        return min(sufficient, key=lambda v: abs(v.year - entry_year))

    return None


def analyze_vintage(
    entry_year: int,
    corpus_deals: List[Dict[str, Any]],
) -> VintageRiskResult:
    """Compute vintage risk for an entry year against the corpus.

    Args:
        entry_year:     Proposed deal entry year
        corpus_deals:   Raw seed dicts for benchmarking

    Returns:
        VintageRiskResult with regime, score, signal, and comparable vintage
    """
    regime = _REGIME_MAP.get(entry_year, "unknown")
    regime_score = _REGIME_BASE_RISK.get(regime, 40.0)
    vintage_benchmark_moic = _REGIME_MOIC_BENCHMARK.get(regime, 2.4)

    # Compute corpus-wide stats
    vintage_stats = compute_vintage_stats(corpus_deals)

    all_realized = [
        float(d["realized_moic"])
        for d in corpus_deals
        if d.get("realized_moic") is not None
    ]
    corpus_moic_p50 = _percentile(sorted(all_realized), 0.50) if all_realized else None

    # Find comparable vintage
    comp = _closest_vintage(entry_year, vintage_stats)

    # Adjust score using comparable vintage outcome
    corpus_adjusted = regime_score
    notes: List[str] = []

    if comp:
        # If comparable vintage had high loss rate, add risk
        if comp.loss_rate > 0.20:
            corpus_adjusted += 10.0
            notes.append(
                f"Comparable vintage {comp.year} had {comp.loss_rate:.0%} loss rate "
                f"({comp.n} deals) — elevated base rate risk"
            )
        elif comp.loss_rate < 0.08:
            corpus_adjusted -= 5.0

        # If comparable vintage median MOIC was below 2.0, add risk
        if comp.moic_p50 and comp.moic_p50 < 2.0:
            corpus_adjusted += 8.0
            notes.append(
                f"Comparable vintage {comp.year} P50 MOIC {comp.moic_p50:.2f}x — "
                "below 2.0x threshold"
            )
        elif comp.moic_p50 and comp.moic_p50 >= 3.0:
            corpus_adjusted -= 5.0

    corpus_adjusted = round(min(100.0, max(0.0, corpus_adjusted)), 1)

    # Signal thresholds
    if corpus_adjusted < 30:
        signal = "green"
    elif corpus_adjusted < 60:
        signal = "yellow"
    else:
        signal = "red"

    # Additional regime-specific notes
    if regime == "peak":
        notes.append(
            f"Entry year {entry_year} classified as 'peak' regime — "
            "historically higher multiple compression risk at exit"
        )
    elif regime == "contraction":
        notes.append(
            f"Entry year {entry_year} is a contraction year — "
            "distressed entry pricing may offset macro headwinds"
        )
    elif regime in ("correction", "normalization"):
        notes.append(
            f"Entry year {entry_year} ({regime}) — "
            "rate/multiple reset creates selective opportunity"
        )

    return VintageRiskResult(
        entry_year=entry_year,
        regime=regime,
        regime_risk_score=round(regime_score, 1),
        corpus_adjusted_score=corpus_adjusted,
        signal=signal,
        comparable_vintage=comp,
        corpus_moic_p50=round(corpus_moic_p50, 3) if corpus_moic_p50 else None,
        vintage_moic_benchmark=vintage_benchmark_moic,
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Portfolio vintage analysis
# ---------------------------------------------------------------------------

def vintage_concentration_risk(
    portfolio_deals: List[Dict[str, Any]],
    corpus_deals: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Assess vintage concentration risk in a portfolio.

    Args:
        portfolio_deals: Active or proposed portfolio deals (with entry_year)
        corpus_deals:    Full corpus for benchmarking

    Returns:
        dict with vintage_counts, dominant_vintage, concentration_hhi, risk_signal
    """
    year_counts: Dict[int, int] = {}
    for deal in portfolio_deals:
        yr = deal.get("entry_year") or deal.get("year")
        if yr:
            year_counts[int(yr)] = year_counts.get(int(yr), 0) + 1

    total = sum(year_counts.values())
    if total == 0:
        return {"vintage_counts": {}, "concentration_hhi": 0.0, "risk_signal": "green"}

    shares = {yr: cnt / total for yr, cnt in year_counts.items()}
    hhi = sum(s ** 2 for s in shares.values())

    # Score each vintage and weight by share
    weighted_risk = 0.0
    for yr, share in shares.items():
        result = analyze_vintage(yr, corpus_deals)
        weighted_risk += result.corpus_adjusted_score * share

    dominant = max(year_counts, key=lambda k: year_counts[k]) if year_counts else None
    signal = "green" if weighted_risk < 35 else ("yellow" if weighted_risk < 60 else "red")

    return {
        "vintage_counts": year_counts,
        "dominant_vintage": dominant,
        "concentration_hhi": round(hhi, 3),
        "weighted_vintage_risk": round(weighted_risk, 1),
        "risk_signal": signal,
    }


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------

def vintage_heatmap(corpus_deals: List[Dict[str, Any]]) -> str:
    """ASCII heatmap of vintage performance across years."""
    stats = compute_vintage_stats(corpus_deals)
    years = sorted(stats.keys())
    if not years:
        return "No realized vintage data available.\n"

    lines = [
        f"Vintage Performance Heatmap (Healthcare PE Corpus)",
        "=" * 70,
        f"{'Year':<6} {'N':>4} {'Regime':<14} {'P25':>6} {'P50':>6} {'P75':>6} {'Loss%':>7} {'Bar'}",
        "-" * 70,
    ]
    for yr in years:
        v = stats[yr]
        p25 = f"{v.moic_p25:.2f}x" if v.moic_p25 else "  n/a"
        p50 = f"{v.moic_p50:.2f}x" if v.moic_p50 else "  n/a"
        p75 = f"{v.moic_p75:.2f}x" if v.moic_p75 else "  n/a"
        loss_pct = f"{v.loss_rate:.0%}"
        bar_val = min(10, int((v.moic_p50 or 0) * 2))
        bar = "█" * bar_val + "░" * (10 - bar_val)
        lines.append(
            f"{yr:<6} {v.n:>4} {v.regime:<14} {p25:>6} {p50:>6} {p75:>6} {loss_pct:>7} {bar}"
        )
    return "\n".join(lines) + "\n"


def vintage_risk_report(result: VintageRiskResult, corpus_deals: List[Dict[str, Any]]) -> str:
    """Formatted vintage risk report for IC packet."""
    sig_map = {"green": "GREEN ✓", "yellow": "YELLOW ⚠", "red": "RED ✗"}
    lines = [
        f"Vintage Risk Analysis: Entry Year {result.entry_year}",
        "=" * 55,
        f"  Regime:              {result.regime.title()}",
        f"  Regime Risk Score:   {result.regime_risk_score:.1f} / 100",
        f"  Corpus-Adj Score:    {result.corpus_adjusted_score:.1f} / 100  [{sig_map.get(result.signal, '')}]",
        f"  Vintage MOIC Bench:  {result.vintage_moic_benchmark:.2f}x (regime median)",
    ]
    if result.corpus_moic_p50:
        lines.append(f"  All-Corpus P50 MOIC: {result.corpus_moic_p50:.2f}x")

    if result.comparable_vintage:
        cv = result.comparable_vintage
        lines += [
            "",
            f"Comparable Vintage ({cv.year}, n={cv.n}):",
            f"  P25: {cv.moic_p25:.2f}x  P50: {cv.moic_p50:.2f}x  P75: {cv.moic_p75:.2f}x" if cv.moic_p50 else "  No distribution data",
            f"  Loss Rate: {cv.loss_rate:.0%}",
        ]

    if result.notes:
        lines += ["", "Key Observations:"]
        for n in result.notes:
            lines.append(f"  • {n}")

    return "\n".join(lines) + "\n"
