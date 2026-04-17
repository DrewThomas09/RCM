"""Portfolio-level analytics over the public deals corpus.

Computes return distributions, outlier detection, vintage-cohort summaries,
and deal-quality screening across the full 135-deal corpus.  All functions
accept a list of deal dicts (as returned by DealsCorpus.list()) and return
plain Python structures or DataFrames.

Public API:
    return_distribution(deals)          -> dict   (P10/P25/P50/P75/P90 for moic/irr)
    deals_by_sponsor(deals)             -> dict   (sponsor → {count, median_moic, ...})
    deals_by_type(deals)                -> dict   (deal_type → stats)
    deals_by_region(deals)              -> dict   (region proxy from notes)
    loss_rate(deals)                    -> float  (fraction with moic < 1)
    home_run_rate(deals)                -> float  (fraction with moic >= 3)
    vintage_cohort_summary(deals)       -> list[dict]  (per-year stats)
    payer_mix_sensitivity(deals)        -> dict   (moic by dominant payer bucket)
    outlier_deals(deals, z=2.0)         -> list[dict]  (deals with extreme moic)
    corpus_scorecard(deals)             -> dict   (one-page portfolio summary)
    scorecard_text(scorecard)           -> str    (formatted text report)
"""
from __future__ import annotations

import math
import statistics
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _floats(deals: List[Dict], key: str) -> List[float]:
    """Extract non-None floats for a key from a list of deal dicts."""
    out = []
    for d in deals:
        v = d.get(key)
        if v is not None:
            try:
                out.append(float(v))
            except (TypeError, ValueError):
                pass
    return out


def _percentile(data: List[float], p: float) -> Optional[float]:
    """p-th percentile (0-100) via linear interpolation."""
    if not data:
        return None
    s = sorted(data)
    n = len(s)
    if n == 1:
        return s[0]
    rank = p / 100.0 * (n - 1)
    lo = int(rank)
    hi = min(lo + 1, n - 1)
    frac = rank - lo
    return s[lo] + frac * (s[hi] - s[lo])


def _safe_median(data: List[float]) -> Optional[float]:
    if not data:
        return None
    return statistics.median(data)


def _safe_mean(data: List[float]) -> Optional[float]:
    if not data:
        return None
    return statistics.mean(data)


def _safe_stdev(data: List[float]) -> Optional[float]:
    if len(data) < 2:
        return None
    return statistics.stdev(data)


# ---------------------------------------------------------------------------
# Return distribution
# ---------------------------------------------------------------------------

def return_distribution(deals: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Percentile distribution of realized MOIC and IRR across the corpus.

    Only includes deals with non-null realized_moic / realized_irr.
    Returns a dict with keys: moic_*, irr_*, moic_count, irr_count.
    """
    moics = _floats(deals, "realized_moic")
    irrs = _floats(deals, "realized_irr")

    result: Dict[str, Any] = {
        "moic_count": len(moics),
        "irr_count": len(irrs),
    }
    for pct in [10, 25, 50, 75, 90]:
        result[f"moic_p{pct}"] = _percentile(moics, pct)
        result[f"irr_p{pct}"] = _percentile(irrs, pct)

    result["moic_mean"] = _safe_mean(moics)
    result["moic_stdev"] = _safe_stdev(moics)
    result["irr_mean"] = _safe_mean(irrs)
    result["irr_stdev"] = _safe_stdev(irrs)
    return result


# ---------------------------------------------------------------------------
# Loss / home-run rates
# ---------------------------------------------------------------------------

def loss_rate(deals: List[Dict[str, Any]]) -> float:
    """Fraction of realized deals where moic < 1.0 (capital impairment)."""
    moics = _floats(deals, "realized_moic")
    if not moics:
        return 0.0
    return sum(1 for m in moics if m < 1.0) / len(moics)


def home_run_rate(deals: List[Dict[str, Any]]) -> float:
    """Fraction of realized deals where moic >= 3.0."""
    moics = _floats(deals, "realized_moic")
    if not moics:
        return 0.0
    return sum(1 for m in moics if m >= 3.0) / len(moics)


# ---------------------------------------------------------------------------
# Deal groupings
# ---------------------------------------------------------------------------

def deals_by_sponsor(deals: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Aggregate return stats by buyer (sponsor).

    Returns dict keyed by buyer name with: count, realized_count,
    median_moic, mean_moic, loss_rate, home_run_rate.
    """
    groups: Dict[str, List[Dict]] = {}
    for d in deals:
        key = str(d.get("buyer") or "Unknown")
        groups.setdefault(key, []).append(d)

    out: Dict[str, Dict[str, Any]] = {}
    for sponsor, group in sorted(groups.items()):
        moics = _floats(group, "realized_moic")
        out[sponsor] = {
            "count": len(group),
            "realized_count": len(moics),
            "median_moic": _safe_median(moics),
            "mean_moic": _safe_mean(moics),
            "loss_rate": loss_rate(group),
            "home_run_rate": home_run_rate(group),
        }
    return out


def deals_by_type(deals: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Aggregate return stats by deal_name keyword heuristic.

    Buckets: lbo, carve_out, ipo, spac, merger, add_on, growth_equity,
    distressed, platform, other.
    """
    _TYPE_KEYWORDS = {
        "lbo": ["lbo", "buyout"],
        "carve_out": ["carve-out", "carve_out", "carve out"],
        "ipo": ["ipo", "initial public"],
        "spac": ["spac", "acquisition corp"],
        "merger": ["merger", "combination"],
        "add_on": ["add-on", "add_on", "add on", "cluster"],
        "growth_equity": ["growth", "series"],
        "distressed": ["distressed", "post-reorg", "chapter 11", "reorgan"],
        "platform": ["platform"],
    }

    def _classify(deal: Dict) -> str:
        name = (deal.get("deal_name") or "").lower()
        notes = (deal.get("notes") or "").lower()
        combined = name + " " + notes
        for bucket, keywords in _TYPE_KEYWORDS.items():
            if any(kw in combined for kw in keywords):
                return bucket
        return "other"

    groups: Dict[str, List[Dict]] = {}
    for d in deals:
        key = _classify(d)
        groups.setdefault(key, []).append(d)

    out: Dict[str, Dict[str, Any]] = {}
    for deal_type, group in sorted(groups.items()):
        moics = _floats(group, "realized_moic")
        out[deal_type] = {
            "count": len(group),
            "realized_count": len(moics),
            "median_moic": _safe_median(moics),
            "mean_moic": _safe_mean(moics),
            "loss_rate": loss_rate(group),
        }
    return out


def deals_by_year(deals: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
    """Aggregate stats by close year."""
    groups: Dict[int, List[Dict]] = {}
    for d in deals:
        yr = d.get("year")
        if yr is not None:
            groups.setdefault(int(yr), []).append(d)

    out: Dict[int, Dict[str, Any]] = {}
    for yr in sorted(groups.keys()):
        group = groups[yr]
        moics = _floats(group, "realized_moic")
        out[yr] = {
            "count": len(group),
            "realized_count": len(moics),
            "median_moic": _safe_median(moics),
            "total_ev_mm": sum(_floats(group, "ev_mm")),
        }
    return out


# ---------------------------------------------------------------------------
# Vintage cohort
# ---------------------------------------------------------------------------

def vintage_cohort_summary(deals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Per-vintage-year summary with count, median MOIC, loss rate, total EV.

    Returns list of dicts sorted by year ascending.
    """
    by_year = deals_by_year(deals)
    rows = []
    for yr, stats in sorted(by_year.items()):
        year_deals = [d for d in deals if d.get("year") == yr]
        rows.append({
            "year": yr,
            "count": stats["count"],
            "realized_count": stats["realized_count"],
            "median_moic": stats["median_moic"],
            "total_ev_mm": stats["total_ev_mm"],
            "loss_rate": loss_rate(year_deals),
            "home_run_rate": home_run_rate(year_deals),
        })
    return rows


# ---------------------------------------------------------------------------
# Payer mix sensitivity
# ---------------------------------------------------------------------------

def payer_mix_sensitivity(deals: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """MOIC stats bucketed by dominant payer type.

    Buckets a deal into its highest-share payer category
    (medicare / medicaid / commercial / mixed).
    Only deals with non-null payer_mix dict participate.
    """
    import json as _json

    def _dominant(deal: Dict) -> str:
        pm = deal.get("payer_mix")
        if isinstance(pm, str):
            try:
                pm = _json.loads(pm)
            except Exception:
                return "unknown"
        if not isinstance(pm, dict):
            return "unknown"
        valid = {k: v for k, v in pm.items() if isinstance(v, (int, float)) and v is not None}
        if not valid:
            return "unknown"
        top_key = max(valid, key=lambda k: valid[k])
        top_val = valid[top_key]
        if top_val >= 0.50:
            return top_key
        return "mixed"

    groups: Dict[str, List[Dict]] = {}
    for d in deals:
        key = _dominant(d)
        groups.setdefault(key, []).append(d)

    out: Dict[str, Dict[str, Any]] = {}
    for bucket, group in sorted(groups.items()):
        moics = _floats(group, "realized_moic")
        out[bucket] = {
            "count": len(group),
            "realized_count": len(moics),
            "median_moic": _safe_median(moics),
            "mean_moic": _safe_mean(moics),
            "loss_rate": loss_rate(group),
        }
    return out


# ---------------------------------------------------------------------------
# Outlier detection
# ---------------------------------------------------------------------------

def outlier_deals(
    deals: List[Dict[str, Any]],
    z: float = 2.0,
) -> List[Dict[str, Any]]:
    """Deals where |moic - mean| > z * stdev (Z-score outlier detection).

    Returns list of dicts with original deal fields plus 'moic_zscore'.
    """
    moics = _floats(deals, "realized_moic")
    if len(moics) < 3:
        return []
    mean = statistics.mean(moics)
    sd = statistics.stdev(moics)
    if sd == 0:
        return []

    result = []
    for d in deals:
        v = d.get("realized_moic")
        if v is None:
            continue
        try:
            fv = float(v)
        except (TypeError, ValueError):
            continue
        zscore = (fv - mean) / sd
        if abs(zscore) > z:
            row = dict(d)
            row["moic_zscore"] = round(zscore, 3)
            result.append(row)
    return sorted(result, key=lambda r: abs(r["moic_zscore"]), reverse=True)


# ---------------------------------------------------------------------------
# Corpus scorecard
# ---------------------------------------------------------------------------

def corpus_scorecard(deals: List[Dict[str, Any]]) -> Dict[str, Any]:
    """One-page portfolio-level summary across all deals in the corpus.

    Suitable for LP reporting or quick calibration sanity checks.
    """
    dist = return_distribution(deals)
    moics = _floats(deals, "realized_moic")
    irrs = _floats(deals, "realized_irr")
    evs = _floats(deals, "ev_mm")

    return {
        "total_deals": len(deals),
        "realized_deals": len(moics),
        "total_ev_mm": round(sum(evs), 1) if evs else None,
        "median_ev_mm": round(_safe_median(evs), 1) if evs else None,
        "moic_p25": dist.get("moic_p25"),
        "moic_p50": dist.get("moic_p50"),
        "moic_p75": dist.get("moic_p75"),
        "moic_mean": dist.get("moic_mean"),
        "irr_p25": dist.get("irr_p25"),
        "irr_p50": dist.get("irr_p50"),
        "irr_p75": dist.get("irr_p75"),
        "loss_rate": round(loss_rate(deals), 3),
        "home_run_rate": round(home_run_rate(deals), 3),
        "outlier_count": len(outlier_deals(deals)),
        "vintage_years": sorted({d.get("year") for d in deals if d.get("year")}),
    }


# ---------------------------------------------------------------------------
# Text output
# ---------------------------------------------------------------------------

def scorecard_text(scorecard: Dict[str, Any]) -> str:
    """Formatted text table of the corpus scorecard."""
    def _fmt(v: Any, fmt: str = ".2f") -> str:
        if v is None:
            return "N/A"
        try:
            return format(float(v), fmt)
        except (TypeError, ValueError):
            return str(v)

    lines = [
        "Portfolio Corpus Scorecard",
        "=" * 56,
        f"  Total deals            : {scorecard.get('total_deals', 0)}",
        f"  Realized deals         : {scorecard.get('realized_deals', 0)}",
        f"  Total EV ($M)          : {_fmt(scorecard.get('total_ev_mm'), ',.1f')}",
        f"  Median deal EV ($M)    : {_fmt(scorecard.get('median_ev_mm'), ',.1f')}",
        "-" * 56,
        f"  MOIC  P25 / P50 / P75  : "
        f"{_fmt(scorecard.get('moic_p25'))}x / "
        f"{_fmt(scorecard.get('moic_p50'))}x / "
        f"{_fmt(scorecard.get('moic_p75'))}x",
        f"  MOIC  mean             : {_fmt(scorecard.get('moic_mean'))}x",
        f"  IRR   P25 / P50 / P75  : "
        f"{_fmt(scorecard.get('irr_p25'), '.1%')} / "
        f"{_fmt(scorecard.get('irr_p50'), '.1%')} / "
        f"{_fmt(scorecard.get('irr_p75'), '.1%')}",
        "-" * 56,
        f"  Loss rate (moic < 1)   : {_fmt(scorecard.get('loss_rate'), '.1%')}",
        f"  Home-run rate (≥3x)    : {_fmt(scorecard.get('home_run_rate'), '.1%')}",
        f"  Statistical outliers   : {scorecard.get('outlier_count', 0)}",
        "=" * 56,
    ]
    vintages = scorecard.get("vintage_years", [])
    if vintages:
        lines.append(f"  Vintages               : {min(vintages)}–{max(vintages)}")
    return "\n".join(lines) + "\n"
