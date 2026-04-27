"""Regional analysis for the public hospital M&A corpus.

Maps deals to US census regions and computes P25/P50/P75 return profiles
per region.  Useful for: "Is this Texas community hospital deal priced in
line with Southeast comps?" or "How do Midwest deals exit vs. Northeast?"

Region assignment:
    Derived from deal_name / buyer keywords, not a stored region field.
    Falls back to "national" for deals that cannot be classified.

    Northeast:  NY, MA, CT, RI, VT, NH, ME, NJ, PA, DE, MD
    Southeast:  FL, GA, TN, AL, MS, SC, NC, VA, WV, KY, AR
    Midwest:    OH, IN, IL, MI, WI, MN, IA, MO, ND, SD, NE, KS
    Southwest:  TX, AZ, NM, OK
    West:       CA, OR, WA, NV, ID, MT, WY, CO, UT, AK, HI
    National:   multi-state platforms or unclassifiable

Region tags are also derivable from the `notes` field.

Public API:
    RegionStats   dataclass
    RegionReport  dataclass
    classify_region(deal)                      -> str
    get_region_stats(region, corpus_db_path)   -> RegionStats
    get_all_regions(corpus_db_path)            -> Dict[str, RegionStats]
    region_report(corpus_db_path)              -> RegionReport
    region_table(corpus_db_path)               -> str (ASCII)
    find_regional_comps(deal, corpus_db_path, n) -> List[dict]
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from ..portfolio.store import PortfolioStore


# ---------------------------------------------------------------------------
# Region definitions
# ---------------------------------------------------------------------------

REGIONS = {
    "northeast": {
        "states": {"NY", "MA", "CT", "RI", "VT", "NH", "ME", "NJ", "PA", "DE", "MD"},
        "keywords": {
            "new york", "new jersey", "massachusetts", "pennsylvania",
            "connecticut", "maryland", "boston", "philadelphia",
            "nuvance", "northwell", "mount sinai", "montefiore",
            "brigham", "partners healthcare", "beth israel", "yale",
        },
        "label": "Northeast",
    },
    "southeast": {
        "states": {"FL", "GA", "TN", "AL", "MS", "SC", "NC", "VA", "WV", "KY", "AR"},
        "keywords": {
            "florida", "georgia", "tennessee", "alabama", "mississippi",
            "south carolina", "north carolina", "virginia", "kentucky",
            "nashville", "orlando", "charlotte", "atlanta", "richmond",
            "ballad", "wellmont", "mountain states", "hca", "capella",
            "sanford health", "duke", "novant",
        },
        "label": "Southeast",
    },
    "midwest": {
        "states": {"OH", "IN", "IL", "MI", "WI", "MN", "IA", "MO", "ND", "SD", "NE", "KS"},
        "keywords": {
            "ohio", "indiana", "illinois", "michigan", "wisconsin",
            "minnesota", "iowa", "missouri", "chicago", "cleveland",
            "detroit", "minneapolis", "indianapolis", "st. louis",
            "advocate", "trinity health", "allina", "ssm health",
            "fairview", "sanford",
        },
        "label": "Midwest",
    },
    "southwest": {
        "states": {"TX", "AZ", "NM", "OK"},
        "keywords": {
            "texas", "arizona", "new mexico", "oklahoma",
            "dallas", "houston", "phoenix", "san antonio", "austin",
            "tenet", "uspi", "baylor", "methodist", "iasis",
        },
        "label": "Southwest",
    },
    "west": {
        "states": {"CA", "OR", "WA", "NV", "ID", "MT", "WY", "CO", "UT", "AK", "HI"},
        "keywords": {
            "california", "oregon", "washington", "nevada", "colorado",
            "los angeles", "san francisco", "seattle", "denver",
            "dignity health", "sutter", "providence", "kaiser",
            "legacy", "adventist", "prospect medical",
        },
        "label": "West",
    },
}

_ALL_REGION_KEYS = list(REGIONS.keys()) + ["national"]


# ---------------------------------------------------------------------------
# Region classifier
# ---------------------------------------------------------------------------

def classify_region(deal: Dict[str, Any]) -> str:
    """Classify a deal into a US census region based on name + notes keywords."""
    text = " ".join(filter(None, [
        str(deal.get("deal_name", "")),
        str(deal.get("buyer", "")),
        str(deal.get("seller", "")),
        str(deal.get("notes", "")),
    ])).lower()

    for region_key, region_def in REGIONS.items():
        for kw in region_def["keywords"]:
            if kw in text:
                return region_key

    # State abbreviation scan
    words = set(text.upper().split())
    for region_key, region_def in REGIONS.items():
        if words & region_def["states"]:
            return region_key

    return "national"


# ---------------------------------------------------------------------------
# Percentile / mean helpers
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
class RegionStats:
    region: str
    label: str
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
    ev_p50: Optional[float]
    ev_ebitda_p50: Optional[float]
    deal_names: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        def _r(v):
            return round(v, 4) if v is not None else None
        return {
            "region": self.region,
            "label": self.label,
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
            "ev_ebitda_p50": _r(self.ev_ebitda_p50),
        }


@dataclass
class RegionReport:
    by_region: Dict[str, RegionStats]
    best_region_moic: Optional[str]
    worst_region_moic: Optional[str]
    overall_moic_p50: Optional[float]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "by_region": {k: v.as_dict() for k, v in self.by_region.items()},
            "best_region_moic": self.best_region_moic,
            "worst_region_moic": self.worst_region_moic,
            "overall_moic_p50": round(self.overall_moic_p50, 4) if self.overall_moic_p50 else None,
        }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_stats(deals: List[Dict[str, Any]], region: str) -> RegionStats:
    moics = [d["realized_moic"] for d in deals if d.get("realized_moic") is not None]
    irrs  = [d["realized_irr"]  for d in deals if d.get("realized_irr")  is not None]
    evs   = [d["ev_mm"]         for d in deals if d.get("ev_mm")         is not None]

    ev_ebitda_vals = []
    for d in deals:
        ev = d.get("ev_mm")
        eb = d.get("ebitda_at_entry_mm")
        if ev and eb and eb > 0:
            ev_ebitda_vals.append(ev / eb)

    label = REGIONS.get(region, {}).get("label", region.title())
    names = [d.get("deal_name", "") for d in deals]

    return RegionStats(
        region=region,
        label=label,
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
        ev_ebitda_p50=_pct(ev_ebitda_vals, 50),
        deal_names=names,
    )


def _load_corpus(corpus_db_path: str) -> List[Dict[str, Any]]:
    # Route through PortfolioStore (campaign target 4E, data_public
    # sweep): inherits busy_timeout=5000, foreign_keys=ON, and
    # row_factory=Row — replacing the prior bare-connect plus
    # manual row_factory assignment.
    with PortfolioStore(corpus_db_path).connect() as con:
        rows = con.execute("SELECT * FROM public_deals").fetchall()
    deals = []
    for row in rows:
        d = dict(row)
        pm = d.get("payer_mix")
        if pm and isinstance(pm, str):
            try:
                d["payer_mix"] = json.loads(pm)
            except Exception:
                pass
        deals.append(d)
    return deals


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_region_stats(region: str, corpus_db_path: str) -> RegionStats:
    """Return stats for all deals classified into a given region."""
    all_deals = _load_corpus(corpus_db_path)
    regional = [d for d in all_deals if classify_region(d) == region]
    return _build_stats(regional, region)


def get_all_regions(corpus_db_path: str) -> Dict[str, RegionStats]:
    """Return RegionStats for every region (including national)."""
    all_deals = _load_corpus(corpus_db_path)
    by_region: Dict[str, List[Dict[str, Any]]] = {r: [] for r in _ALL_REGION_KEYS}
    for d in all_deals:
        r = classify_region(d)
        by_region.setdefault(r, []).append(d)

    return {
        region: _build_stats(deals, region)
        for region, deals in by_region.items()
        if deals  # omit empty regions
    }


def region_report(corpus_db_path: str) -> RegionReport:
    """Full regional return report."""
    by_region = get_all_regions(corpus_db_path)

    candidates = {
        r: rs for r, rs in by_region.items()
        if rs.moic_p50 is not None and rs.n_with_moic >= 2
    }
    best = max(candidates, key=lambda r: candidates[r].moic_p50, default=None)
    worst = min(candidates, key=lambda r: candidates[r].moic_p50, default=None)

    all_moics = [
        d["realized_moic"]
        for d in _load_corpus(corpus_db_path)
        if d.get("realized_moic") is not None
    ]
    overall_p50 = _pct(all_moics, 50)

    return RegionReport(
        by_region=by_region,
        best_region_moic=best,
        worst_region_moic=worst,
        overall_moic_p50=overall_p50,
    )


def region_table(corpus_db_path: str) -> str:
    """ASCII table of return stats by region."""
    by_region = get_all_regions(corpus_db_path)
    lines = [
        "Regional Return Analysis",
        "-" * 80,
        f"{'Region':<12} {'N':>3} {'With MOIC':>9} {'MOIC P50':>8} "
        f"{'MOIC P75':>8} {'IRR P50':>8} {'EV/EBITDA P50':>13}",
        "-" * 80,
    ]
    for region_key, rs in sorted(by_region.items()):
        moic50 = f"{rs.moic_p50:.2f}x" if rs.moic_p50 else "   —   "
        moic75 = f"{rs.moic_p75:.2f}x" if rs.moic_p75 else "   —   "
        irr50  = f"{rs.irr_p50:.1%}"   if rs.irr_p50  else "    —  "
        eveb50 = f"{rs.ev_ebitda_p50:.1f}x" if rs.ev_ebitda_p50 else "   —  "
        lines.append(
            f"{rs.label:<12} {rs.n_deals:>3} {rs.n_with_moic:>9} "
            f"{moic50:>8} {moic75:>8} {irr50:>8} {eveb50:>13}"
        )
    return "\n".join(lines)


def find_regional_comps(
    deal: Dict[str, Any],
    corpus_db_path: str,
    n: int = 5,
) -> List[Dict[str, Any]]:
    """Find up to N deals from the same region as the query deal.

    Returns list of deal dicts sorted by recency (year desc), then by MOIC presence.
    """
    region = classify_region(deal)
    all_deals = _load_corpus(corpus_db_path)
    query_id = str(deal.get("source_id", ""))

    regional = [
        d for d in all_deals
        if classify_region(d) == region and str(d.get("source_id", "")) != query_id
    ]
    # Sort: prefer deals with MOIC data, then by year (most recent first)
    regional.sort(
        key=lambda d: (d.get("realized_moic") is not None, d.get("year") or 0),
        reverse=True,
    )
    return regional[:n]
