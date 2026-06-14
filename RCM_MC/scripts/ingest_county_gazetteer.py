#!/usr/bin/env python3
"""Ingest the Census Gazetteer county file → vendored aggregate.

Builds ``rcm_mc/data/vendor/county_gazetteer/county_gazetteer.csv`` with
one row per US county: FIPS, the Census *internal point* (the bureau's
own representative lat/lon for the county) and land area in sq mi.

Why: ``rcm_mc/diligence/texas_infusion_geo.py`` computes patient →
nearest-clinic distances. Offline it runs in *model mode* (documented
formula + a constant land-area table); when this vendored file exists it
switches to *gazetteer mode* — the cross-county leg becomes an EXACT
haversine from the county point to the nearest geocoded facility, and
every land area becomes the exact TIGER value. Run this once on a
network-enabled machine and commit the output; no runtime network.

Source (public domain, keyless):
    https://www2.census.gov/geo/docs/maps-data/data/gazetteer/
        2023_Gazetteer/2023_Gaz_counties_national.zip

Usage::

    python scripts/ingest_county_gazetteer.py [--zip PATH]

``--zip`` skips the download and reads an already-fetched archive
(for machines where only a browser can reach census.gov).
"""
from __future__ import annotations

import argparse
import csv
import io
import pathlib
import sys
import zipfile

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_DEST = _ROOT / "rcm_mc" / "data" / "vendor" / "county_gazetteer"
_URL = ("https://www2.census.gov/geo/docs/maps-data/data/gazetteer/"
        "2023_Gazetteer/2023_Gaz_counties_national.zip")
_SQM_PER_SQMI = 2_589_988.110336  # ALAND is square meters


def _fetch(url: str) -> bytes:
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "rcm-mc/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--zip", help="path to a pre-downloaded gazetteer zip")
    args = ap.parse_args()

    raw = (pathlib.Path(args.zip).read_bytes() if args.zip
           else _fetch(_URL))
    zf = zipfile.ZipFile(io.BytesIO(raw))
    name = next(n for n in zf.namelist() if n.endswith(".txt"))
    text = zf.read(name).decode("utf-8", errors="replace")

    rows = []
    reader = csv.DictReader(io.StringIO(text), delimiter="\t")
    for r in reader:
        # Gazetteer columns: GEOID, ALAND (sq m), INTPTLAT, INTPTLONG
        # (column names carry trailing whitespace in the raw file).
        r = {k.strip(): (v or "").strip() for k, v in r.items() if k}
        try:
            rows.append({
                "county_fips": r["GEOID"],
                "land_sqmi": round(float(r["ALAND"]) / _SQM_PER_SQMI, 1),
                "lat": float(r["INTPTLAT"]),
                "lon": float(r["INTPTLONG"]),
            })
        except (KeyError, ValueError):
            continue

    if len(rows) < 3_000:  # ~3,144 US counties — refuse a partial file
        print(f"refusing to write: only {len(rows)} county rows parsed",
              file=sys.stderr)
        return 1

    _DEST.mkdir(parents=True, exist_ok=True)
    out = _DEST / "county_gazetteer.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(
            fh, fieldnames=["county_fips", "land_sqmi", "lat", "lon"])
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} counties → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
