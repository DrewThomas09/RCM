"""Vintage-year analysis for the public hospital M&A corpus.

Groups deals by entry year and computes return profiles per vintage.
Used to answer: "How have deals from a particular macro cycle performed?"
and "Is the proposed entry year a good vintage relative to historical norms?"

Macro cycle labels:
    pre_gfc       1990-2006  (pre-Global Financial Crisis)
    post_gfc      2007-2012  (GFC + ACA transition)
    aca_era       2013-2019  (ACA implementation, consolidation wave)
    covid_era     2020-2022  (COVID dislocation + remote care surge)
    post_covid    2023+      (rising rates, MA headwinds, staffing inflation)

Public API:
    VintageStats  dataclass
    VintageReport dataclass
    get_vintage_stats(year, corpus_db_path)             -> VintageStats
    get_all_vintages(corpus_db_path)                    -> Dict[int, VintageStats]
    vintage_report(corpus_db_path)                      -> VintageReport
    vintage_table(corpus_db_path)                       -> str  (ASCII)
    macro_cycle_summary(corpus_db_path)                 -> Dict[str, VintageStats]
    entry_timing_assessment(year, corpus_db_path)       -> Dict[str, Any]
"""
from __future__ import annotations

import json
import math
import sqlite3
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Macro cycle classification
# ---------------------------------------------------------------------------

_CYCLES: List[Tuple[str, int, int, str]] = [
    ("pre_gfc",    1990, 2006, "Pre-GFC consolidation"),
    ("post_gfc",   2007, 2012, "GFC + ACA transition"),
    ("aca_era",    2013, 2019, "ACA era consolidation"),
    ("covid_era",  2020, 2022, "COVID dislocation"),
    ("post_covid", 2023, 2099, "Post-COVID / rising-rate"),
]


def _classify_cycle(year: int) -> str:
    for name, lo, hi, _ in _CYCLES:
        if lo <= year <= hi:
            return name
    return "unknown"


def _cycle_label(cycle: str) -> str:
    for name, _, _, label in _CYCLES:
        if name == cycle:
            return label
    return cycle


# ---------------------------------------------------------------------------
# Percentile helper (no numpy)
# ---------------------------------------------------------------------------

def _pct(values: List[float], p: float) -> Optional[float]:
    if not values:
        return None
    s = sorted(values)
    idx = p / 100 * (len(s) - 1)
    lo, hi = int(idx), min(int(idx) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (idx - lo)


def _mean(values: List[float]) -> Optional[float]:
    return sum(values) / len(values) if values else None


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class VintageStats:
    year: Optional[int]          # None = cycle-level aggregate
    cycle: str
    n_deals: int
    n_with_moic: int
    n_with_irr: int
    moic_p25: Optional[float]
    moic_p50: Optional[float]
    moic_p75: Optional[float]
    moic_mean: Optional[float]
    irr_p25: Optional[float]
    irr_p50: Optional[float]
    irr_p75: Optional[float]
    irr_mean: Optional[float]
    ev_p50: Optional[float]      # median EV of deals in this vintage
    hold_p50: Optional[float]    # median hold years
    deal_names: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        def _r(v):
            return round(v, 4) if v is not None else None
        return {
            "year": self.year,
            "cycle": self.cycle,
            "n_deals": self.n_deals,
            "n_with_moic": self.n_with_moic,
            "n_with_irr": self.n_with_irr,
            "moic_p25": _r(self.moic_p25),
            "moic_p50": _r(self.moic_p50),
            "moic_p75": _r(self.moic_p75),
            "moic_mean": _r(self.moic_mean),
            "irr_p25": _r(self.irr_p25),
            "irr_p50": _r(self.irr_p50),
            "irr_p75": _r(self.irr_p75),
            "irr_mean": _r(self.irr_mean),
            "ev_p50": _r(self.ev_p50),
            "hold_p50": _r(self.hold_p50),
        }


@dataclass
class VintageReport:
    by_year: Dict[int, VintageStats]
    by_cycle: Dict[str, VintageStats]
    best_vintage_moic: Optional[int]    # year with highest median MOIC
    worst_vintage_moic: Optional[int]   # year with lowest median MOIC
    overall: VintageStats

    def as_dict(self) -> Dict[str, Any]:
        return {
            "by_year": {str(yr): vs.as_dict() for yr, vs in self.by_year.items()},
            "by_cycle": {k: v.as_dict() for k, v in self.by_cycle.items()},
            "best_vintage_moic": self.best_vintage_moic,
            "worst_vintage_moic": self.worst_vintage_moic,
            "overall": self.overall.as_dict(),
        }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_stats(
    deals: List[Dict[str, Any]],
    year: Optional[int],
    cycle: str,
) -> VintageStats:
    moics = [d["realized_moic"] for d in deals if d.get("realized_moic") is not None]
    irrs  = [d["realized_irr"]  for d in deals if d.get("realized_irr")  is not None]
    evs   = [d["ev_mm"]         for d in deals if d.get("ev_mm")         is not None]
    holds = [d["hold_years"]    for d in deals if d.get("hold_years")    is not None]
    names = [d.get("deal_name", "") for d in deals]

    return VintageStats(
        year=year,
        cycle=cycle,
        n_deals=len(deals),
        n_with_moic=len(moics),
        n_with_irr=len(irrs),
        moic_p25=_pct(moics, 25),
        moic_p50=_pct(moics, 50),
        moic_p75=_pct(moics, 75),
        moic_mean=_mean(moics),
        irr_p25=_pct(irrs, 25),
        irr_p50=_pct(irrs, 50),
        irr_p75=_pct(irrs, 75),
        irr_mean=_mean(irrs),
        ev_p50=_pct(evs, 50),
        hold_p50=_pct(holds, 50),
        deal_names=names,
    )


def _load_corpus(corpus_db_path: str) -> List[Dict[str, Any]]:
    con = sqlite3.connect(corpus_db_path)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT deal_name, year, ev_mm, ebitda_at_entry_mm, hold_years, "
        "realized_moic, realized_irr, buyer FROM public_deals"
    ).fetchall()
    con.close()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_vintage_stats(year: int, corpus_db_path: str) -> VintageStats:
    """Return stats for deals with the given entry year."""
    deals = [d for d in _load_corpus(corpus_db_path) if d.get("year") == year]
    return _build_stats(deals, year, _classify_cycle(year))


def get_all_vintages(corpus_db_path: str) -> Dict[int, VintageStats]:
    """Return a VintageStats per year, sorted ascending."""
    all_deals = _load_corpus(corpus_db_path)
    by_year: Dict[int, List[Dict[str, Any]]] = {}
    for d in all_deals:
        yr = d.get("year")
        if yr:
            by_year.setdefault(yr, []).append(d)
    return {
        yr: _build_stats(deals, yr, _classify_cycle(yr))
        for yr, deals in sorted(by_year.items())
    }


def macro_cycle_summary(corpus_db_path: str) -> Dict[str, VintageStats]:
    """Aggregate return stats by macro cycle."""
    all_deals = _load_corpus(corpus_db_path)
    by_cycle: Dict[str, List[Dict[str, Any]]] = {}
    for d in all_deals:
        yr = d.get("year")
        if yr:
            cycle = _classify_cycle(yr)
            by_cycle.setdefault(cycle, []).append(d)
    return {
        cycle: _build_stats(deals, None, cycle)
        for cycle, deals in by_cycle.items()
    }


def vintage_report(corpus_db_path: str) -> VintageReport:
    """Full vintage report: by year, by cycle, best/worst vintage."""
    by_year = get_all_vintages(corpus_db_path)
    by_cycle = macro_cycle_summary(corpus_db_path)

    # Best/worst vintage by median MOIC (require at least 2 deals)
    candidates = {
        yr: vs for yr, vs in by_year.items()
        if vs.moic_p50 is not None and vs.n_with_moic >= 2
    }
    best = max(candidates, key=lambda y: candidates[y].moic_p50, default=None)
    worst = min(candidates, key=lambda y: candidates[y].moic_p50, default=None)

    all_deals = _load_corpus(corpus_db_path)
    overall = _build_stats(all_deals, None, "all")

    return VintageReport(
        by_year=by_year,
        by_cycle=by_cycle,
        best_vintage_moic=best,
        worst_vintage_moic=worst,
        overall=overall,
    )


def entry_timing_assessment(year: int, corpus_db_path: str) -> Dict[str, Any]:
    """Assess entry timing for a proposed year relative to historical norms.

    Returns a dict with:
        cycle, cycle_label, cycle_moic_p50, overall_moic_p50,
        relative_performance (above/below/at par),
        timing_notes (list of plain-English observations)
    """
    report = vintage_report(corpus_db_path)
    cycle = _classify_cycle(year)
    cycle_stats = report.by_cycle.get(cycle)
    overall = report.overall

    notes: List[str] = []
    relative = "at par"

    cycle_p50 = cycle_stats.moic_p50 if cycle_stats else None
    overall_p50 = overall.moic_p50

    if cycle_p50 is not None and overall_p50 is not None:
        delta = cycle_p50 - overall_p50
        if delta > 0.3:
            relative = "above par"
            notes.append(
                f"{_cycle_label(cycle)} ({cycle}) deals averaged "
                f"{cycle_p50:.2f}x MOIC — {delta:.2f}x above corpus median."
            )
        elif delta < -0.3:
            relative = "below par"
            notes.append(
                f"{_cycle_label(cycle)} ({cycle}) deals averaged "
                f"{cycle_p50:.2f}x MOIC — {abs(delta):.2f}x below corpus median."
            )
        else:
            notes.append(
                f"{_cycle_label(cycle)} ({cycle}) deals in line with corpus median "
                f"({cycle_p50:.2f}x vs {overall_p50:.2f}x)."
            )

    # Cycle-specific contextual notes
    if cycle == "post_gfc":
        notes.append("Post-GFC entries faced ACA implementation uncertainty; "
                     "exits that cleared ACA clarity (2015+) often outperformed.")
    elif cycle == "covid_era":
        notes.append("COVID-era entries benefited from telehealth tailwinds "
                     "but face staffing inflation; hold-period returns skewed by timing of exit.")
    elif cycle == "post_covid":
        notes.append("Post-COVID entry: elevated rates increase cost of leverage; "
                     "MA headwinds and staffing inflation compress EBITDA — "
                     "underwrite conservatively.")
    elif cycle == "aca_era":
        notes.append("ACA era: consolidation wave; premium multiples for scale; "
                     "OON billing repricing risk elevated after 2017.")

    if report.best_vintage_moic == year:
        notes.append(f"{year} is the top-performing vintage in the corpus by median MOIC.")
    if report.worst_vintage_moic == year:
        notes.append(f"{year} is the lowest-performing vintage in the corpus by median MOIC.")

    yr_stats = report.by_year.get(year)

    return {
        "year": year,
        "cycle": cycle,
        "cycle_label": _cycle_label(cycle),
        "cycle_moic_p50": round(cycle_p50, 4) if cycle_p50 else None,
        "overall_moic_p50": round(overall_p50, 4) if overall_p50 else None,
        "year_n_deals": yr_stats.n_deals if yr_stats else 0,
        "year_moic_p50": round(yr_stats.moic_p50, 4) if (yr_stats and yr_stats.moic_p50) else None,
        "relative_performance": relative,
        "timing_notes": notes,
    }


def vintage_table(corpus_db_path: str) -> str:
    """Return an ASCII table of return stats by vintage year."""
    by_year = get_all_vintages(corpus_db_path)

    lines = [
        "Vintage Year Analysis",
        "-" * 80,
        f"{'Year':>4}  {'Cycle':<12} {'N':>3} {'MOIC M':>7} {'MOIC P50':>8} "
        f"{'IRR P50':>8} {'EV P50':>9}",
        "-" * 80,
    ]
    for yr, vs in by_year.items():
        moic_m = f"{vs.moic_mean:.2f}x"  if vs.moic_mean  else "   —   "
        moic50 = f"{vs.moic_p50:.2f}x"   if vs.moic_p50   else "   —   "
        irr50  = f"{vs.irr_p50:.1%}"     if vs.irr_p50    else "    —  "
        ev50   = f"${vs.ev_p50:,.0f}M"   if vs.ev_p50     else "      —"
        lines.append(
            f"{yr:>4}  {vs.cycle:<12} {vs.n_deals:>3} {moic_m:>7} "
            f"{moic50:>8} {irr50:>8} {ev50:>9}"
        )
    return "\n".join(lines)
