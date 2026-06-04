#!/usr/bin/env python3
"""BUILD-TIME ONLY — generate vendored world-country SVG paths for the
international market map.

Reads a vendored public-domain world-countries GeoJSON (Natural Earth 1:110m
admin-0, public domain) and projects each country to an SVG path ``d`` string
with a simple equirectangular projection. Writes ``rcm_mc/ui/_world_geo_paths.py``
— a pure-data module the runtime imports. **No runtime network**: this script
runs by hand when the asset changes; the app only imports the generated module
(mirrors tools/build_us_geo_paths.py).

Run:  python tools/build_world_geo_paths.py

Source GeoJSON: Natural Earth 1:110m Admin-0 Countries (public domain),
slimmed to {name, iso2, continent, geometry} and vendored at
rcm_mc/data/world_countries.geojson. Antarctica is dropped; latitude is
clamped to [-60, 85] to trim the polar stretch inherent to equirectangular.
Natural Earth pre-splits antimeridian-crossing countries (Russia, Fiji) into
MultiPolygon parts, so equirectangular renders them without a horizontal
streak across the map.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_GEOJSON = _HERE.parent / "rcm_mc" / "data" / "world_countries.geojson"
_OUT = _HERE.parent / "rcm_mc" / "ui" / "_world_geo_paths.py"

_W = 960.0          # output viewBox width
_LAT_MIN, _LAT_MAX = -60.0, 85.0   # clamp polar stretch (drops most of Antarctica anyway)


def _rings(geom):
    """Yield rings (lists of [lon,lat]) for Polygon / MultiPolygon."""
    if geom["type"] == "Polygon":
        for ring in geom["coordinates"]:
            yield ring
    elif geom["type"] == "MultiPolygon":
        for poly in geom["coordinates"]:
            for ring in poly:
                yield ring


def main() -> None:
    g = json.loads(_GEOJSON.read_text())

    feats = []  # (iso2, name, continent, [ring of (lon,lat), ...])
    for f in g["features"]:
        pr = f["properties"]
        iso2 = (pr.get("iso2") or "").strip()
        continent = pr.get("continent") or ""
        if not iso2 or continent == "Antarctica":
            continue
        rings = [[(float(c[0]), float(c[1])) for c in ring]
                 for ring in _rings(f["geometry"])]
        feats.append((iso2, pr.get("name") or iso2, continent, rings))

    # Global bounds (longitude full; latitude clamped to trim polar stretch).
    xs = [p[0] for _, _, _, rs in feats for r in rs for p in r]
    ys = [p[1] for _, _, _, rs in feats for r in rs for p in r]
    x0, x1 = min(xs), max(xs)
    y0, y1 = max(min(ys), _LAT_MIN), min(max(ys), _LAT_MAX)
    scale = _W / (x1 - x0)
    H = (y1 - y0) * scale

    def _fx(x):
        return (x - x0) * scale

    def _fy(y):
        return (y1 - y) * scale  # SVG y grows down; flip so north is up.

    def _path_d(rings):
        parts = []
        for r in rings:
            if len(r) < 4:          # skip degenerate slivers
                continue
            pts = [f"{_fx(x):.1f} {_fy(y):.1f}" for x, y in r]
            parts.append("M" + "L".join(pts) + "Z")
        return "".join(parts)

    paths = {}
    for iso2, name, continent, rings in feats:
        d = _path_d(rings)
        if d:
            # Keep the first feature per ISO2 (NE is one feature per country).
            paths.setdefault(iso2, {"name": name, "continent": continent, "d": d})

    body = [
        '"""Vendored world-country SVG paths for the international map — GENERATED.',
        "",
        "Do NOT hand-edit. Regenerate with tools/build_world_geo_paths.py.",
        "Source: Natural Earth 1:110m Admin-0 Countries (public domain),",
        "equirectangular projection, Antarctica dropped, latitude clamped to",
        "[-60, 85]. No runtime network.",
        '"""',
        "from __future__ import annotations",
        "",
        f"WORLD_GEO_VIEWBOX = (0, 0, {_W:.0f}, {math.ceil(H)})",
        "",
        "WORLD_COUNTRY_PATHS = {",
    ]
    for iso2 in sorted(paths):
        rec = paths[iso2]
        body.append(
            f'    {iso2!r}: {{"name": {rec["name"]!r}, '
            f'"continent": {rec["continent"]!r}, "d": {rec["d"]!r}}},'
        )
    body.append("}")
    _OUT.write_text("\n".join(body) + "\n")
    print(f"wrote {_OUT} — {len(paths)} countries, viewBox 0 0 {_W:.0f} "
          f"{math.ceil(H)}, {_OUT.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
