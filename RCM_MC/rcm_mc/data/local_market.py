"""Local competitive context — hospitals within a straight-line radius.

Joins the vendored geocode crosswalk (hospital_coords.csv, one-time offline
Census-geocoded CMS addresses) with the latest HCRIS filing per CCN to answer
the week-one CDD question the state-proxy screens can't: who actually
competes with this facility LOCALLY, and how big are they?

Honesty constraints baked in:
  - Straight-line (haversine) distance, not drive-time — stated wherever
    rendered. A radius is a SCREENING geography, not a relevant antitrust
    market.
  - A target or competitor absent from the geocode file simply doesn't
    appear (never an approximated location); the target missing → None.
  - Share-of-radius uses only competitors that report NPR; coverage is
    carried so the UI can say "9 of 11 report NPR".
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional

_EARTH_RADIUS_MI = 3958.8


def haversine_miles(lat1: float, lon1: float,
                    lat2: float, lon2: float) -> float:
    """Great-circle distance in miles."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = (math.sin(dp / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2)
    return 2 * _EARTH_RADIUS_MI * math.asin(math.sqrt(a))


@dataclass
class NearbyHospital:
    ccn: str
    name: str
    city: str
    state: str
    distance_mi: float
    beds: Optional[float]
    npr: Optional[float]


@dataclass
class LocalMarket:
    target_ccn: str
    radius_miles: float
    competitors: List[NearbyHospital] = field(default_factory=list)
    target_npr: Optional[float] = None

    @property
    def n_competitors(self) -> int:
        return len(self.competitors)

    @property
    def npr_reported(self) -> int:
        return sum(1 for c in self.competitors if c.npr is not None)

    @property
    def combined_competitor_npr(self) -> Optional[float]:
        vals = [c.npr for c in self.competitors if c.npr is not None]
        return float(sum(vals)) if vals else None

    @property
    def target_share_of_radius(self) -> Optional[float]:
        """Target NPR ÷ (target + reporting competitors). None when the
        target's own NPR is a gap — a share without a numerator is noise."""
        if self.target_npr is None:
            return None
        comp = self.combined_competitor_npr or 0.0
        total = self.target_npr + comp
        return (self.target_npr / total) if total > 0 else None


def local_market(ccn: str, radius_miles: float = 25.0,
                 hcris_df=None) -> Optional[LocalMarket]:
    """Hospitals within ``radius_miles`` of ``ccn``, financials attached.

    Returns None when the target isn't in the geocode file (no approximate
    fallback). Competitors sort nearest-first. ``hcris_df`` injectable for
    tests; defaults to the latest-filing-per-CCN frame.
    """
    from .hospital_coords import load_hospital_coords
    coords = load_hospital_coords()
    tgt = coords.get(str(ccn))
    if tgt is None:
        return None
    if hcris_df is None:
        from .hcris import _get_latest_per_ccn
        hcris_df = _get_latest_per_ccn()
    fin: Dict[str, dict] = {}
    if hcris_df is not None and "ccn" in getattr(hcris_df, "columns", []):
        for _, r in hcris_df.iterrows():
            fin[str(r["ccn"])] = {
                "name": str(r.get("name") or ""),
                "beds": _num(r.get("beds")),
                "npr": _num(r.get("net_patient_revenue")),
            }
    out = LocalMarket(target_ccn=str(ccn), radius_miles=float(radius_miles),
                      target_npr=(fin.get(str(ccn)) or {}).get("npr"))
    for other_ccn, c in coords.items():
        if other_ccn == str(ccn):
            continue
        d = haversine_miles(tgt.lat, tgt.lon, c.lat, c.lon)
        if d > radius_miles:
            continue
        f = fin.get(other_ccn) or {}
        out.competitors.append(NearbyHospital(
            ccn=other_ccn,
            name=f.get("name") or c.facility_name,
            city=c.city, state=c.state, distance_mi=round(d, 1),
            beds=f.get("beds"), npr=f.get("npr")))
    out.competitors.sort(key=lambda x: x.distance_mi)
    return out


def _num(v) -> Optional[float]:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f
