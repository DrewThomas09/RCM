"""Public-operator comparables loader + comparable-finder.

Given a target's category + size, pick the public comps that
match and quote the EV/EBITDA + EV/Revenue ranges. Used for the
"your target looks like X at Y multiple" overlay on the market-
intel page.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


CONTENT_DIR = Path(__file__).parent / "content"


@dataclass
class AnalystCoverage:
    """Aggregated analyst consensus — drawn from public aggregators
    (Seeking Alpha, Yahoo Finance, CapIQ) as a directional view."""
    consensus: str = "NONE"        # BUY | HOLD | SELL | NONE
    price_target_usd: Optional[float] = None
    ratings_count: Optional[int] = None
    last_updated: Optional[str] = None  # ISO date

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class EarningsLatest:
    """Most recent earnings report surprise vs. consensus.
    Positive surprise_pct = beat; negative = miss."""
    period: Optional[str] = None
    eps_reported: Optional[float] = None
    eps_consensus: Optional[float] = None
    surprise_pct: Optional[float] = None
    reported_on: Optional[str] = None  # ISO date

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class PublicComp:
    ticker: str
    name: str
    category: str
    market_cap_usd_bn: float
    enterprise_value_usd_bn: float
    revenue_ttm_usd_bn: float
    ebitda_ttm_usd_bn: float
    ev_ebitda_multiple: float
    ev_revenue_multiple: float
    net_debt_usd_bn: float = 0.0
    debt_to_ebitda: Optional[float] = None
    operating_margin: Optional[float] = None
    hospitals: Optional[int] = None
    employed_physicians: Optional[int] = None
    payer_mix_commercial: Optional[float] = None
    payer_mix_medicare: Optional[float] = None
    payer_mix_medicaid: Optional[float] = None
    payer_mix_other: Optional[float] = None
    # Physician retention — disclosed turnover rate (10-K "human
    # capital" section when available; otherwise management
    # commentary).  Critical peer context for the P-PAM model.
    physician_turnover_disclosed: Optional[float] = None
    # Analyst coverage + earnings surprise — refreshed quarterly
    # from the content YAML.  Used by the market intel dashboard
    # sentiment overlays and the compare-to-target scatter.
    analyst_coverage: Optional[AnalystCoverage] = None
    earnings_latest: Optional[EarningsLatest] = None

    def to_dict(self) -> Dict[str, Any]:
        d = self.__dict__.copy()
        if self.analyst_coverage is not None:
            d["analyst_coverage"] = self.analyst_coverage.to_dict()
        if self.earnings_latest is not None:
            d["earnings_latest"] = self.earnings_latest.to_dict()
        return d


#: Category bands anchored by fewer than this many named public
#: constituents carry ``small_sample: True``. The p25/median/p75 in the
#: YAML are curated analyst curves, and with one or two anchoring
#: tickers there aren't enough distinct observations for the spread to
#: read as an OBSERVED distribution (you can't place three quartiles on
#: two points) — so the band is directional. This is the broader
#: sibling of ``peer_snapshot.peer_band_indicative`` (which fires only
#: at the strict single-ticker n<2); every small-sample band nests it.
SMALL_SAMPLE_CONSTITUENTS: int = 3


@dataclass
class CategoryBand:
    category: str
    median_ev_ebitda: float
    p25_ev_ebitda: float
    p75_ev_ebitda: float
    median_ev_revenue: float
    constituents: List[str] = field(default_factory=list)
    note: Optional[str] = None
    # Review date of the curated comps YAML this band was read from.
    # Carried on the band (not just the find_comparables envelope)
    # because seeking_alpha_page renders category_bands() directly and a
    # "sector median" without its as-of reads as a live quote when it is
    # a quarterly-refreshed fixture. Stamped by ``category_bands``.
    content_last_reviewed: Optional[str] = None

    @property
    def constituent_count(self) -> int:
        """How many named public constituents anchor this band.

        Disclosed because the p25/median/p75 "peer range" reads like a
        distribution, but several categories on the lattice are backed
        by one or two tickers (RURAL_ACUTE_HOSPITAL is a single CYH) —
        at that n the band is a curated analyst curve, not observed
        spread, and every consumer of the range needs the n to say so.
        """
        return len(self.constituents)

    @property
    def small_sample(self) -> bool:
        """True when too few named constituents anchor the band for its
        spread to read as an observed distribution — see
        :data:`SMALL_SAMPLE_CONSTITUENTS`. Self-describing so a consumer
        that never touches peer_snapshot (market-intel comps table,
        Seeking Alpha sector bands) still inherits the caveat."""
        return self.constituent_count < SMALL_SAMPLE_CONSTITUENTS

    def to_dict(self) -> Dict[str, Any]:
        d = self.__dict__.copy()
        d["constituent_count"] = self.constituent_count
        d["small_sample"] = self.small_sample
        return d


def _load() -> Dict[str, Any]:
    return yaml.safe_load(
        (CONTENT_DIR / "public_comps.yaml").read_text("utf-8")
    )


def list_companies() -> List[PublicComp]:
    data = _load()
    out: List[PublicComp] = []
    for row in data.get("companies") or ():
        ac_raw = row.get("analyst_coverage") or None
        ac = None
        if ac_raw:
            ac = AnalystCoverage(
                consensus=str(ac_raw.get("consensus", "NONE")).upper(),
                price_target_usd=ac_raw.get("price_target_usd"),
                ratings_count=ac_raw.get("ratings_count"),
                last_updated=(
                    str(ac_raw["last_updated"])
                    if ac_raw.get("last_updated") else None
                ),
            )
        el_raw = row.get("earnings_latest") or None
        el = None
        if el_raw:
            el = EarningsLatest(
                period=el_raw.get("period"),
                eps_reported=el_raw.get("eps_reported"),
                eps_consensus=el_raw.get("eps_consensus"),
                surprise_pct=el_raw.get("surprise_pct"),
                reported_on=(
                    str(el_raw["reported_on"])
                    if el_raw.get("reported_on") else None
                ),
            )
        out.append(PublicComp(
            ticker=row["ticker"], name=row["name"],
            category=row["category"],
            market_cap_usd_bn=float(row.get("market_cap_usd_bn", 0)),
            enterprise_value_usd_bn=float(row.get("enterprise_value_usd_bn", 0)),
            revenue_ttm_usd_bn=float(row.get("revenue_ttm_usd_bn", 0)),
            ebitda_ttm_usd_bn=float(row.get("ebitda_ttm_usd_bn", 0)),
            ev_ebitda_multiple=float(row.get("ev_ebitda_multiple", 0)),
            ev_revenue_multiple=float(row.get("ev_revenue_multiple", 0)),
            net_debt_usd_bn=float(row.get("net_debt_usd_bn", 0) or 0),
            debt_to_ebitda=row.get("debt_to_ebitda"),
            operating_margin=row.get("operating_margin"),
            hospitals=row.get("hospitals"),
            employed_physicians=row.get("employed_physicians"),
            payer_mix_commercial=row.get("payer_mix_commercial"),
            payer_mix_medicare=row.get("payer_mix_medicare"),
            payer_mix_medicaid=row.get("payer_mix_medicaid"),
            payer_mix_other=row.get("payer_mix_other"),
            physician_turnover_disclosed=row.get(
                "physician_turnover_disclosed",
            ),
            analyst_coverage=ac,
            earnings_latest=el,
        ))
    return out


#: Turnover benchmarks over fewer than this many disclosing operators
#: carry ``small_sample: True``. Only a subset of public operators
#: report a physician-turnover rate in their 10-K human-capital
#: section, so the peer median is a handful of data points, not a
#: population statistic — the flag lets the consumer soften "peer
#: median" to "few disclosures" instead of quoting a p25/median/p75
#: spread over a single-digit n as if it were market structure.
TURNOVER_SMALL_SAMPLE_N: int = 5


def peer_physician_turnover_stats() -> Dict[str, Any]:
    """Disclosed physician turnover across public operators.

    Returns ``median``, ``p25``, ``p75``, ``count``, ``small_sample``
    (count < :data:`TURNOVER_SMALL_SAMPLE_N`), and
    ``content_last_reviewed`` (the curated comps YAML's review date) for
    the subset of operators that disclose a turnover rate. Used by the
    Physician Attrition page as a peer benchmark.

    Central read is the ``median`` (interpolated), not the mean:
    disclosed turnover is right-skewed — one operator in a workforce
    crisis reports a rate several times the norm — so a mean would drag
    the benchmark toward the tail and misprice the typical peer. The
    ``small_sample`` flag and vintage travel WITH the numbers so a
    benchmark read off ``count`` single-digit disclosures, or off a
    year-old filing cycle, can't render as a live population statistic.
    On the empty path percentiles are ``0.0`` but ``small_sample`` is
    ``True`` and ``count`` is ``0`` — the honest render is "no
    disclosures", never "0% turnover".
    """
    from .content_vintage import content_vintage

    reviewed = content_vintage("public_comps")["last_reviewed"]
    rates = [
        c.physician_turnover_disclosed
        for c in list_companies()
        if c.physician_turnover_disclosed is not None
        and c.physician_turnover_disclosed > 0
    ]
    if not rates:
        return {"median": 0.0, "p25": 0.0, "p75": 0.0, "count": 0,
                "small_sample": True, "content_last_reviewed": reviewed}
    rates_sorted = sorted(rates)
    n = len(rates_sorted)

    def _pct(p: float) -> float:
        if n == 1:
            return rates_sorted[0]
        idx = p * (n - 1)
        lo = int(idx)
        hi = min(lo + 1, n - 1)
        frac = idx - lo
        return rates_sorted[lo] * (1 - frac) + rates_sorted[hi] * frac

    return {
        "median": _pct(0.50),
        "p25": _pct(0.25),
        "p75": _pct(0.75),
        "count": n,
        "small_sample": n < TURNOVER_SMALL_SAMPLE_N,
        "content_last_reviewed": reviewed,
    }


# ── Exports ────────────────────────────────────────────────────────

__all__ = [
    "AnalystCoverage",
    "CategoryBand",
    "EarningsLatest",
    "PublicComp",
    "SMALL_SAMPLE_CONSTITUENTS",
    "TURNOVER_SMALL_SAMPLE_N",
    "category_bands",
    "find_comparables",
    "list_companies",
    "peer_physician_turnover_stats",
]


def category_bands() -> Dict[str, CategoryBand]:
    from .content_vintage import content_vintage

    reviewed = content_vintage("public_comps")["last_reviewed"]
    data = _load()
    out: Dict[str, CategoryBand] = {}
    for cat, row in (data.get("category_aggregates") or {}).items():
        out[cat] = CategoryBand(
            category=cat,
            median_ev_ebitda=float(row.get("median_ev_ebitda", 0)),
            p25_ev_ebitda=float(row.get("p25_ev_ebitda", 0)),
            p75_ev_ebitda=float(row.get("p75_ev_ebitda", 0)),
            median_ev_revenue=float(row.get("median_ev_revenue", 0)),
            constituents=list(row.get("constituents") or ()),
            note=row.get("note"),
            content_last_reviewed=reviewed,
        )
    return out


def find_comparables(
    *,
    target_category: str,
    target_revenue_usd: Optional[float] = None,
    top_n: int = 5,
) -> Dict[str, Any]:
    """Pick the comps that match target_category.

    When ``target_revenue_usd`` is supplied, we also score by
    absolute-revenue-difference to surface size-proximate comps
    first; otherwise we return all same-category comps.

    The envelope carries ``content_last_reviewed`` (the curated
    YAML's review date) so every consumer inherits the vintage with
    the numbers — a comps table without its as-of date reads as live
    market data when it is a quarterly-refreshed fixture.
    """
    from .content_vintage import content_vintage

    reviewed = content_vintage("public_comps")["last_reviewed"]
    all_comps = list_companies()
    category = (target_category or "").upper()
    matches = [c for c in all_comps if c.category == category]
    if not matches:
        return {
            "category": category,
            "comps": [],
            "band": None,
            "note": (
                f"No public operator on the lattice for category "
                f"{category!r}. Refer to transaction_multiples for "
                f"private-market benchmarks."
            ),
            "content_last_reviewed": reviewed,
        }
    if target_revenue_usd and target_revenue_usd > 0:
        target_rev_bn = target_revenue_usd / 1_000_000_000
        matches.sort(
            key=lambda c: abs(c.revenue_ttm_usd_bn - target_rev_bn),
        )
    bands = category_bands()
    band = bands.get(category)
    return {
        "category": category,
        "comps": [c.to_dict() for c in matches[:top_n]],
        "band": band.to_dict() if band else None,
        "content_last_reviewed": reviewed,
    }
