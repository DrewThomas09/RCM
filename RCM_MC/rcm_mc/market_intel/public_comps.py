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

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class CategoryBand:
    category: str
    median_ev_ebitda: float
    p25_ev_ebitda: float
    p75_ev_ebitda: float
    median_ev_revenue: float
    constituents: List[str] = field(default_factory=list)
    note: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


def _load() -> Dict[str, Any]:
    return yaml.safe_load(
        (CONTENT_DIR / "public_comps.yaml").read_text("utf-8")
    )


def list_companies() -> List[PublicComp]:
    data = _load()
    out: List[PublicComp] = []
    for row in data.get("companies") or ():
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
        ))
    return out


def category_bands() -> Dict[str, CategoryBand]:
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
    """
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
    }
