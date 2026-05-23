"""Local CCN -> latitude/longitude crosswalk for hospital point maps.

The coordinates in ``hospital_coords.csv`` were produced by a ONE-TIME,
OFFLINE batch geocode of public CMS *Hospital General Information*
addresses through the free US Census Geocoder (Public_AR_Current). The
app reads only this vendored local file — it never geocodes at request
time, makes no external calls, and never geocodes private/deal-room data.

Each row carries its own provenance (``source`` + ``source_date`` +
``match_quality``). Hospitals whose address did not geocode are simply
absent from the file — they get no point (never a fabricated/approximate
location). See docs/PEDESK_INTERACTIVE_MAPS.md.
"""
from __future__ import annotations

import csv
import functools
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

_COORDS_CSV = Path(__file__).with_name("hospital_coords.csv")


@dataclass(frozen=True)
class HospitalCoord:
    ccn: str
    facility_name: str
    address: str
    city: str
    state: str
    zip: str
    county: str
    lat: float
    lon: float
    match_quality: str   # "Exact" | "Non_Exact"
    source: str
    source_date: str


@functools.lru_cache(maxsize=1)
def load_hospital_coords() -> Dict[str, HospitalCoord]:
    """Return ``{ccn: HospitalCoord}`` from the vendored crosswalk.

    Returns ``{}`` if the file is missing (the point map then renders
    nothing rather than failing). Never raises on a normal missing file.
    """
    out: Dict[str, HospitalCoord] = {}
    if not _COORDS_CSV.is_file():
        return out
    with _COORDS_CSV.open(newline="", encoding="utf-8", errors="replace") as fh:
        for row in csv.DictReader(fh):
            ccn = (row.get("ccn") or "").strip()
            if not ccn:
                continue
            try:
                lat = float(row["lat"])
                lon = float(row["lon"])
            except (KeyError, TypeError, ValueError):
                continue  # no usable coordinate -> skip (never invent one)
            out[ccn] = HospitalCoord(
                ccn=ccn,
                facility_name=(row.get("facility_name") or "").strip(),
                address=(row.get("address") or "").strip(),
                city=(row.get("city") or "").strip(),
                state=(row.get("state") or "").strip().upper(),
                zip=(row.get("zip") or "").strip(),
                county=(row.get("county") or "").strip(),
                lat=lat, lon=lon,
                match_quality=(row.get("match_quality") or "").strip(),
                source=(row.get("source") or "").strip(),
                source_date=(row.get("source_date") or "").strip(),
            )
    return out


def coords_for_state(state: str) -> List[HospitalCoord]:
    """Geocoded hospitals in ``state`` (postal abbr), sorted by name."""
    st = (state or "").strip().upper()
    rows = [c for c in load_hospital_coords().values() if c.state == st]
    return sorted(rows, key=lambda c: c.facility_name)


def coords_provenance() -> Optional[str]:
    """The source string shared by the crosswalk rows (or None if empty)."""
    for c in load_hospital_coords().values():
        return f"{c.source} · as of {c.source_date}"
    return None
