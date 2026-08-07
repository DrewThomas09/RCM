"""CMS Care Compare facility attributes — the second name for every CCN.

Why a second name matters
-------------------------
HCRIS truncates a facility name at ~36 characters and abbreviates hard.
The same hospital that Care Compare calls "BAPTIST HEALTH MEDICAL
CENTER-CONWAY" files its cost report as "BHMC-CONWAY"; Providence
Kodiak Island files as "PROV. KODIAK ISLAND MEDICAL CENT". A registry
pattern written from the real brand cannot reach either string.

Care Compare carries the untruncated, branded name for 5,432 hospitals,
and 2,528 of them differ from what HCRIS files. Matching the system
registry against BOTH names — cost report first, Care Compare second —
recovers 379 facilities that name-matching otherwise misses, and every
one of them is a case where the cost report simply spelled the brand
too short to see.

The file also carries three attributes worth having on their own:

  - **hospital_ownership** — CMS's own classification (Proprietary /
    Voluntary non-profit - Church / Government - Local / Veterans
    Health Administration / …). This is *observed* ownership, unlike
    the registry's ``kind``, which is a judgement about the system.
    Where a facility is unmapped, this is the only ownership signal
    there is.
  - **hospital_type** — Care Compare's own type vocabulary, an
    independent check on the CCN-range classifier.
  - **countyparish** — a third county source for the FIPS chain.

Data lives in the IFT reference cache (a CMS provider-data snapshot
already vendored for another workstream). Everything degrades to empty
if the cache is absent — a missing optional file must never take the
mapping down with it.
"""
from __future__ import annotations

import gzip
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

_CACHE = (Path(__file__).resolve().parent.parent / "market_reports"
          / "reference" / "ift_v3_cache" / "pdc2_hospitals.json.gz")


@dataclass(frozen=True)
class CmsFacility:
    """One Care Compare row, keyed by CCN."""

    ccn: str
    name: str
    city: str
    state: str
    zip: str
    county: str
    hospital_type: str
    ownership: str
    emergency_services: str

    @property
    def is_government(self) -> bool:
        return self.ownership.startswith("Government") or "Veterans" in self.ownership

    @property
    def is_for_profit(self) -> bool:
        return self.ownership.startswith("Proprietary")

    @property
    def is_nonprofit(self) -> bool:
        return self.ownership.startswith("Voluntary")


@lru_cache(maxsize=1)
def load_cms_facilities() -> Dict[str, CmsFacility]:
    """CCN -> Care Compare attributes. Empty dict when the cache is absent."""
    if not _CACHE.exists():
        return {}
    try:
        with gzip.open(_CACHE, "rt", encoding="utf-8") as fh:
            rows = json.load(fh)
    except (OSError, ValueError):
        return {}
    out: Dict[str, CmsFacility] = {}
    for row in rows if isinstance(rows, list) else []:
        ccn = str(row.get("facility_id") or "").strip()
        if not ccn:
            continue
        out[ccn] = CmsFacility(
            ccn=ccn,
            name=str(row.get("facility_name") or "").strip(),
            city=str(row.get("citytown") or "").strip(),
            state=str(row.get("state") or "").strip().upper(),
            zip=str(row.get("zip_code") or "").strip(),
            county=str(row.get("countyparish") or "").strip(),
            hospital_type=str(row.get("hospital_type") or "").strip(),
            ownership=str(row.get("hospital_ownership") or "").strip(),
            emergency_services=str(row.get("emergency_services") or "").strip(),
        )
    return out


def cms_name(ccn: Any) -> str:
    """Care Compare's name for a CCN — the untruncated one."""
    rec = load_cms_facilities().get(str(ccn or "").strip())
    return rec.name if rec else ""


def cms_facility(ccn: Any) -> Optional[CmsFacility]:
    return load_cms_facilities().get(str(ccn or "").strip())


def _clear_cache() -> None:
    """Test hook."""
    load_cms_facilities.cache_clear()
