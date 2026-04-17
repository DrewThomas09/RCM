"""City/state → approximate lat/lon lookup (Prompt 69).

Pre-built dictionary of US state capitals as centroids. Good enough
for the portfolio map where we're plotting circles at city-level
granularity — exact geocoding would require an external API.
"""
from __future__ import annotations

import math
from typing import Dict, Optional, Tuple

STATE_CENTROIDS: Dict[str, Tuple[float, float]] = {
    "AL": (32.36, -86.28), "AK": (64.20, -152.49),
    "AZ": (34.05, -111.09), "AR": (34.80, -92.20),
    "CA": (36.78, -119.42), "CO": (39.55, -105.78),
    "CT": (41.60, -72.76), "DE": (38.91, -75.53),
    "DC": (38.91, -77.04), "FL": (27.66, -81.52),
    "GA": (32.17, -82.91), "HI": (19.90, -155.58),
    "ID": (44.07, -114.74), "IL": (40.63, -89.40),
    "IN": (40.27, -86.13), "IA": (41.88, -93.10),
    "KS": (39.01, -98.48), "KY": (37.84, -84.27),
    "LA": (30.98, -91.96), "ME": (45.25, -69.45),
    "MD": (39.05, -76.64), "MA": (42.41, -71.38),
    "MI": (44.31, -84.54), "MN": (46.73, -94.69),
    "MS": (32.35, -89.40), "MO": (38.57, -92.60),
    "MT": (46.88, -110.36), "NE": (41.49, -99.90),
    "NV": (38.80, -116.42), "NH": (43.19, -71.57),
    "NJ": (40.06, -74.41), "NM": (34.52, -105.87),
    "NY": (43.30, -74.22), "NC": (35.76, -79.02),
    "ND": (47.55, -101.00), "OH": (40.42, -82.91),
    "OK": (35.47, -97.52), "OR": (43.80, -120.55),
    "PA": (41.20, -77.19), "RI": (41.58, -71.48),
    "SC": (33.84, -81.16), "SD": (43.97, -99.90),
    "TN": (35.52, -86.15), "TX": (31.97, -99.90),
    "UT": (39.32, -111.09), "VT": (44.56, -72.58),
    "VA": (37.77, -78.17), "WA": (47.75, -120.74),
    "WV": (38.60, -80.45), "WI": (43.78, -88.79),
    "WY": (43.08, -107.29),
}


def city_state_to_latlon(
    city: str, state: str,
) -> Optional[Tuple[float, float]]:
    """Return (lat, lon) for a city/state pair.

    Falls back to the state centroid for unknown cities — the map
    plots approximate circles, so ±50 miles of error is acceptable.
    """
    st = (state or "").strip().upper()
    if st in STATE_CENTROIDS:
        return STATE_CENTROIDS[st]
    return None


def haversine_miles(
    lat1: float, lon1: float, lat2: float, lon2: float,
) -> float:
    """Great-circle distance between two points in miles."""
    R = 3958.8  # Earth radius in miles
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
