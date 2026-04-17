"""Market intelligence — competitor finder & HHI analysis (Prompt 52).

Identifies competitor hospitals near a target using Haversine distance
on approximate lat/lon from state-capital centroids, then computes
market concentration (HHI) and classification.

Uses :func:`rcm_mc.data.hcris.load_hcris` for hospital locations.
Since HCRIS only provides city/state (no lat/lon), we approximate
each hospital's position using a lookup dict of ~50 state capitals
as centroids. This is intentionally coarse — partners use it for
directional screening, not GPS-level precision.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ── State capital centroids (lat, lon) ────────────────────────────
# Approximate geographic centroids for each US state, keyed by
# 2-letter state abbreviation. Used as a proxy when HCRIS has
# city/state but no coordinates.

STATE_CENTROIDS: Dict[str, tuple[float, float]] = {
    "AL": (32.3777, -86.3006), "AK": (64.2008, -152.4937),
    "AZ": (34.0489, -111.0937), "AR": (34.7465, -92.2896),
    "CA": (36.7783, -119.4179), "CO": (39.5501, -105.7821),
    "CT": (41.6032, -73.0877), "DE": (38.9108, -75.5277),
    "FL": (27.6648, -81.5158), "GA": (32.1656, -82.9001),
    "HI": (19.8968, -155.5828), "ID": (44.0682, -114.7420),
    "IL": (40.6331, -89.3985), "IN": (40.2672, -86.1349),
    "IA": (41.8780, -93.0977), "KS": (39.0119, -98.4842),
    "KY": (37.8393, -84.2700), "LA": (30.9843, -91.9623),
    "ME": (45.2538, -69.4455), "MD": (39.0458, -76.6413),
    "MA": (42.4072, -71.3824), "MI": (44.3148, -85.6024),
    "MN": (46.7296, -94.6859), "MS": (32.3547, -89.3985),
    "MO": (37.9643, -91.8318), "MT": (46.8797, -110.3626),
    "NE": (41.4925, -99.9018), "NV": (38.8026, -116.4194),
    "NH": (43.1939, -71.5724), "NJ": (40.0583, -74.4057),
    "NM": (34.5199, -105.8701), "NY": (40.7128, -74.0060),
    "NC": (35.7596, -79.0193), "ND": (47.5515, -101.0020),
    "OH": (40.4173, -82.9071), "OK": (35.4676, -97.5164),
    "OR": (43.8041, -120.5542), "PA": (41.2033, -77.1945),
    "RI": (41.5801, -71.4774), "SC": (33.8361, -81.1637),
    "SD": (43.9695, -99.9018), "TN": (35.5175, -86.5804),
    "TX": (31.9686, -99.9018), "UT": (39.3210, -111.0937),
    "VT": (44.5588, -72.5778), "VA": (37.4316, -78.6569),
    "WA": (47.7511, -120.7401), "WV": (38.5976, -80.4549),
    "WI": (43.7844, -88.7879), "WY": (43.0760, -107.2903),
    "DC": (38.9072, -77.0369), "PR": (18.2208, -66.5901),
}


# ── Haversine ─────────────────────────────────────────────────────

_EARTH_RADIUS_MILES = 3958.8


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in miles between two (lat, lon) points."""
    lat1_r, lon1_r = math.radians(lat1), math.radians(lon1)
    lat2_r, lon2_r = math.radians(lat2), math.radians(lon2)
    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return _EARTH_RADIUS_MILES * c


# ── Dataclasses ───────────────────────────────────────────────────

@dataclass
class Competitor:
    ccn: str
    name: str
    distance_miles: float
    bed_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ccn": self.ccn,
            "name": self.name,
            "distance_miles": round(self.distance_miles, 1),
            "bed_count": int(self.bed_count),
        }


@dataclass
class MarketSummary:
    total_beds: int
    market_hhi: float
    market_type: str  # "dominant" | "competitive" | "fragmented"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_beds": int(self.total_beds),
            "market_hhi": round(self.market_hhi, 1),
            "market_type": self.market_type,
        }


# ── Internal helpers ──────────────────────────────────────────────

def _get_coords_for_state(state: Optional[str]) -> Optional[tuple[float, float]]:
    """Lookup approximate lat/lon for a state abbreviation."""
    if not state:
        return None
    return STATE_CENTROIDS.get(state.strip().upper())


def _load_hospitals(store: Any = None) -> "pd.DataFrame":
    """Load the HCRIS dataset. If unavailable, return empty DataFrame."""
    try:
        from .hcris import load_hcris
        return load_hcris()
    except (FileNotFoundError, ImportError):
        import pandas as pd
        return pd.DataFrame(columns=[
            "ccn", "name", "city", "state", "beds",
        ])


# ── Public API ────────────────────────────────────────────────────

def find_competitors(
    ccn: str,
    *,
    radius_miles: float = 30.0,
    store: Any = None,
    hospitals_df: Any = None,
) -> List[Competitor]:
    """Find hospitals within ``radius_miles`` of the target CCN.

    Uses Haversine distance on state-capital centroids as a coarse
    approximation. The ``hospitals_df`` parameter allows callers to
    inject a DataFrame directly (useful for testing without the
    shipped HCRIS CSV).

    Returns a list of :class:`Competitor` sorted by distance ascending.
    """
    import pandas as pd

    if hospitals_df is not None:
        df = hospitals_df
    else:
        df = _load_hospitals(store)

    if df.empty:
        return []

    # Find the target hospital.
    target_rows = df[df["ccn"] == ccn]
    if target_rows.empty:
        logger.warning("CCN %s not found in HCRIS data", ccn)
        return []

    target = target_rows.iloc[0]
    target_state = str(target.get("state") or "").strip().upper()
    target_coords = _get_coords_for_state(target_state)
    if target_coords is None:
        logger.warning("No centroid for state %s", target_state)
        return []

    competitors: List[Competitor] = []
    for _, row in df.iterrows():
        row_ccn = str(row.get("ccn") or "").strip()
        if row_ccn == ccn:
            continue

        row_state = str(row.get("state") or "").strip().upper()
        row_coords = _get_coords_for_state(row_state)
        if row_coords is None:
            continue

        dist = haversine_miles(
            target_coords[0], target_coords[1],
            row_coords[0], row_coords[1],
        )
        if dist <= radius_miles:
            bed_count = 0
            try:
                bc = row.get("beds")
                if bc is not None and bc == bc:  # not NaN
                    bed_count = int(float(bc))
            except (TypeError, ValueError):
                pass

            competitors.append(Competitor(
                ccn=row_ccn,
                name=str(row.get("name") or ""),
                distance_miles=round(dist, 1),
                bed_count=bed_count,
            ))

    competitors.sort(key=lambda c: c.distance_miles)
    return competitors


def market_summary(
    ccn: str,
    competitors: List[Competitor],
    *,
    target_bed_count: int = 0,
) -> MarketSummary:
    """Compute market concentration metrics from competitors list.

    The HHI (Herfindahl-Hirschman Index) is computed over bed-count
    market shares. The target hospital is included in the calculation
    via ``target_bed_count``.

    Market classification:
    - HHI >= 2500 → "dominant"
    - 1500 <= HHI < 2500 → "competitive"
    - HHI < 1500 → "fragmented"
    """
    # Collect bed counts for all participants (target + competitors).
    bed_counts: List[int] = []
    if target_bed_count > 0:
        bed_counts.append(target_bed_count)
    for comp in competitors:
        if comp.bed_count > 0:
            bed_counts.append(comp.bed_count)

    total_beds = sum(bed_counts)
    if total_beds == 0:
        return MarketSummary(
            total_beds=0,
            market_hhi=0.0,
            market_type="fragmented",
        )

    # HHI = sum of squared market shares (in percentage points).
    hhi = sum(
        ((bc / total_beds) * 100) ** 2
        for bc in bed_counts
    )

    if hhi >= 2500:
        market_type = "dominant"
    elif hhi >= 1500:
        market_type = "competitive"
    else:
        market_type = "fragmented"

    return MarketSummary(
        total_beds=total_beds,
        market_hhi=round(hhi, 1),
        market_type=market_type,
    )
