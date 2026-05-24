#!/usr/bin/env python3
"""BUILD-TIME ONLY — generate vendored US-state SVG paths for the Portfolio Map.

Reads a vendored public-domain US-states GeoJSON (Census-derived boundary
polygons) and projects each state to an SVG path `d` string with an Albers
Equal-Area Conic projection (the canonical "looks like the US" projection),
placing Alaska and Hawaii as scaled insets at the bottom-left like d3's
albersUsa. Writes `rcm_mc/ui/_us_geo_paths.py` — a pure-data module the runtime
imports. **No runtime network**: this script runs by hand when the asset
changes; the app only imports the generated module.

Run:  .venv/bin/python tools/build_us_geo_paths.py

Source GeoJSON: PublicaMundi/MappingAPI (US Census cartographic boundaries,
public domain). Vendored at rcm_mc/data/us_states.geojson.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_GEOJSON = _HERE.parent / "rcm_mc" / "data" / "us_states.geojson"
_OUT = _HERE.parent / "rcm_mc" / "ui" / "_us_geo_paths.py"

_ABBR = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
    "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
    "District of Columbia": "DC", "Florida": "FL", "Georgia": "GA",
    "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL", "Indiana": "IN",
    "Iowa": "IA", "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA",
    "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA", "Michigan": "MI",
    "Minnesota": "MN", "Mississippi": "MS", "Missouri": "MO", "Montana": "MT",
    "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH", "New Jersey": "NJ",
    "New Mexico": "NM", "New York": "NY", "North Carolina": "NC",
    "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR",
    "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
    "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT",
    "Vermont": "VT", "Virginia": "VA", "Washington": "WA",
    "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
    "Puerto Rico": "PR",
}

# Albers Equal-Area Conic standard parallels / origin for the continental US.
_PHI1, _PHI2 = math.radians(29.5), math.radians(45.5)
_LON0, _LAT0 = math.radians(-96.0), math.radians(23.0)
_N = 0.5 * (math.sin(_PHI1) + math.sin(_PHI2))
_C = math.cos(_PHI1) ** 2 + 2 * _N * math.sin(_PHI1)
_RHO0 = math.sqrt(_C - 2 * _N * math.sin(_LAT0)) / _N


def _albers(lon_deg, lat_deg):
    lon, lat = math.radians(lon_deg), math.radians(lat_deg)
    theta = _N * (lon - _LON0)
    rho = math.sqrt(max(_C - 2 * _N * math.sin(lat), 0.0)) / _N
    return rho * math.sin(theta), _RHO0 - rho * math.cos(theta)


def _polys(geom):
    """Yield rings (lists of [lon,lat]) for Polygon / MultiPolygon."""
    if geom["type"] == "Polygon":
        for ring in geom["coordinates"]:
            yield ring
    else:  # MultiPolygon
        for poly in geom["coordinates"]:
            for ring in poly:
                yield ring


def main() -> None:
    g = json.loads(_GEOJSON.read_text())

    # First pass: project every state's rings, tracking which feature each
    # ring belongs to and the global bounds of the continental projection.
    feats = []  # (abbr, name, [ [(x,y),...], ... ])
    for f in g["features"]:
        name = f["properties"]["name"]
        abbr = _ABBR.get(name)
        if abbr is None:
            continue
        rings = [[_albers(lon, lat) for lon, lat in ring] for ring in _polys(f["geometry"])]
        feats.append((abbr, name, rings))

    # Inset transform for AK/HI: project, then scale+translate into the
    # bottom-left so they read as labelled insets (not part of the grid).
    def _bounds(abbrs):
        xs, ys = [], []
        for abbr, _, rings in feats:
            if abbr in abbrs:
                for r in rings:
                    for x, y in r:
                        xs.append(x); ys.append(y)
        return min(xs), min(ys), max(xs), max(ys)

    cont = {a for a, _, _ in feats} - {"AK", "HI"}
    cx0, cy0, cx1, cy1 = _bounds(cont)

    W = 960.0
    scale = W / (cx1 - cx0)
    H = (cy1 - cy0) * scale
    # SVG y grows downward but Albers y grows north, so flip: north → top.
    def _fx(x): return (x - cx0) * scale
    def _fy(y): return (cy1 - y) * scale

    def _inset(rings, frac, ox, oy):
        """Scale a region to `frac` of the canvas width and drop it at (ox,oy)
        from the BOTTOM-left, y-flipped — for the AK / HI insets."""
        ix0, iy0, ix1, iy1 = (min(p[0] for r in rings for p in r),
                              min(p[1] for r in rings for p in r),
                              max(p[0] for r in rings for p in r),
                              max(p[1] for r in rings for p in r))
        isc = (W * frac) / (ix1 - ix0)
        ih = (iy1 - iy0) * isc
        return [[((x - ix0) * isc + ox, (iy1 - y) * isc + (H - oy - ih))
                 for x, y in r] for r in rings]

    transformed = {}
    for abbr, name, rings in feats:
        if abbr == "AK":
            rr = _inset(rings, 0.17, 8, 8)          # bottom-left
        elif abbr == "HI":
            rr = _inset(rings, 0.07, 185, 8)        # right of Alaska
        else:
            rr = [[(_fx(x), _fy(y)) for x, y in r] for r in rings]
        transformed[abbr] = (name, rr)

    def _path_d(rings):
        parts = []
        for r in rings:
            pts = [f"{x:.1f} {y:.1f}" for x, y in r]
            parts.append("M" + "L".join(pts) + "Z")
        return "".join(parts)

    paths = {abbr: {"name": name, "d": _path_d(rings)}
             for abbr, (name, rings) in sorted(transformed.items())}

    body = [
        '"""Vendored US-state SVG paths for the Portfolio Map — GENERATED.',
        "",
        "Do NOT hand-edit. Regenerate with tools/build_us_geo_paths.py.",
        "Source: PublicaMundi/MappingAPI US-states GeoJSON (US Census",
        "cartographic boundaries, public domain). Albers Equal-Area Conic;",
        "Alaska & Hawaii are scaled bottom-left insets. No runtime network.",
        '"""',
        "from __future__ import annotations",
        "",
        f"US_GEO_VIEWBOX = (0, 0, {W:.0f}, {math.ceil(H)})",
        "",
        "US_STATE_PATHS = {",
    ]
    for abbr, rec in paths.items():
        body.append(f'    {abbr!r}: {{"name": {rec["name"]!r}, "d": {rec["d"]!r}}},')
    body.append("}")
    _OUT.write_text("\n".join(body) + "\n")
    print(f"wrote {_OUT} — {len(paths)} states, viewBox 0 0 {W:.0f} {math.ceil(H)}, "
          f"{_OUT.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
