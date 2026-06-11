"""CMS Medicare Physician & Other Practitioners — by Geography and Service.

This public-use file is exactly the grain needed to put infusion J-codes
on a map: every row is

    Geo level (National / State) × Geo (state) × HCPCS × Place of Service
    × year

with ``Tot_Srvcs`` / ``Tot_Benes`` / ``Tot_Mdcr_*`` measures and an
``HCPCS_Drug_Ind`` flag that marks the J-codes. ``Place_Of_Srvc`` is the
binary **F (facility — HOPD/inpatient) vs O (office / non-facility —
physician office, freestanding AIC)** split. CMS publishes one dataset
per year (2013–2022+), so three years stack into a trend.

Caveats the caller must surface: it is **Medicare fee-for-service only**
(excludes MA — ~half of Medicare — so it understates the non-facility
shift), small cells (<11) are suppressed, and POS is binary (no granular
home/HOPD/office codes — that needs the paid PSPS Master File).

The live client resolves the per-year dataset UUID from the CMS data.json
catalog and pulls state rows for a HCPCS set. It fails **closed** (empty)
when egress is blocked; nothing here fabricates a claim count.
"""
from __future__ import annotations

import functools
import json
import urllib.parse
import urllib.request
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_CMS_DATA_API = "https://data.cms.gov/data-api/v1/dataset"
_CMS_CATALOG = "https://data.cms.gov/data.json"

# Field aliases (CMS has renamed columns across vintages).
_F_GEO_LVL = ("Rndrng_Prvdr_Geo_Lvl", "GEO_LEVEL", "geo_level")
_F_GEO_DESC = ("Rndrng_Prvdr_Geo_Desc", "GEO_DESC", "geo_desc")
_F_HCPCS = ("HCPCS_Cd", "HCPCS_CD", "hcpcs_cd")
_F_POS = ("Place_Of_Srvc", "PLACE_OF_SERVICE", "place_of_srvc")
_F_SRVCS = ("Tot_Srvcs", "TOT_SRVCS", "tot_srvcs")
_F_BENES = ("Tot_Benes", "TOT_BENES", "tot_benes")


def _pick(row: Dict[str, Any], names) -> Any:
    for n in names:
        if n in row and row[n] not in (None, ""):
            return row[n]
    return None


def _to_float(v: Any) -> Optional[float]:
    if v in (None, ""):
        return None
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return None


@functools.lru_cache(maxsize=8)
def resolve_geo_service_dataset(year: int, timeout: float = 20.0) -> str:
    """Find the 'by Geography and Service' dataset UUID for a year from
    the CMS catalog. '' on failure (caller falls back)."""
    from ._cms_download import ssl_context
    try:
        req = urllib.request.Request(
            _CMS_CATALOG, headers={"Accept": "application/json",
                                   "User-Agent": "rcm-mc/1.0"})
        with urllib.request.urlopen(
                req, timeout=timeout, context=ssl_context()) as r:
            cat = json.loads(r.read().decode())
    except Exception as exc:
        logger.warning("CMS catalog resolve failed: %s", exc)
        return ""
    for ds in cat.get("dataset", []):
        title = str(ds.get("title", ""))
        tl = title.lower()
        if ("geography and service" in tl and str(year) in title):
            for dist in ds.get("distribution", []):
                url = str(dist.get("accessURL", "")
                          or dist.get("downloadURL", ""))
                if "dataset/" in url:
                    return url.split("dataset/")[1].split("/")[0]
    return ""


def fetch_geo_service_hcpcs(
    hcpcs: str, year: int, *, dataset: str = "", timeout: float = 20.0,
) -> List[Dict[str, Any]]:
    """State-level rows for one HCPCS in one year (both POS). Returns
    ``[{state, pos, services, benes}]`` or [] on failure."""
    ds = dataset or resolve_geo_service_dataset(year)
    if not ds:
        return []
    from ._cms_download import ssl_context
    params = {
        "filter[Rndrng_Prvdr_Geo_Lvl]": "State",
        "filter[HCPCS_Cd]": hcpcs.upper(),
        "size": "300",
    }
    url = (f"{_CMS_DATA_API}/{ds}/data?"
           + urllib.parse.urlencode(params))
    try:
        req = urllib.request.Request(
            url, headers={"Accept": "application/json",
                          "User-Agent": "rcm-mc/1.0"})
        with urllib.request.urlopen(
                req, timeout=timeout, context=ssl_context()) as r:
            rows = json.loads(r.read().decode())
    except Exception as exc:
        logger.warning("CMS geo-service API unavailable: %s", exc)
        return []
    out = []
    for row in rows if isinstance(rows, list) else []:
        out.append({
            "state": str(_pick(row, _F_GEO_DESC) or "").strip(),
            "pos": str(_pick(row, _F_POS) or "").strip().upper()[:1],
            "services": _to_float(_pick(row, _F_SRVCS)) or 0.0,
            "benes": _to_float(_pick(row, _F_BENES)) or 0.0,
        })
    return out


def jcode_pos_by_state(
    hcpcs_codes: List[str], years: List[int],
) -> Dict[str, Dict[int, Dict[str, float]]]:
    """Aggregate facility vs non-facility services for a J-code basket by
    state and year: ``{state: {year: {facility, nonfacility, nonfac_pct,
    benes}}}``. Empty when the API is unreachable (fails closed)."""
    agg: Dict[str, Dict[int, Dict[str, float]]] = {}
    for yr in years:
        ds = resolve_geo_service_dataset(yr)
        if not ds:
            continue
        for code in hcpcs_codes:
            for row in fetch_geo_service_hcpcs(code, yr, dataset=ds):
                st = row["state"]
                if not st:
                    continue
                slot = agg.setdefault(st, {}).setdefault(
                    yr, {"facility": 0.0, "nonfacility": 0.0, "benes": 0.0})
                if row["pos"] == "F":
                    slot["facility"] += row["services"]
                else:
                    slot["nonfacility"] += row["services"]
                slot["benes"] += row["benes"]
    for st, byyr in agg.items():
        for yr, slot in byyr.items():
            tot = slot["facility"] + slot["nonfacility"]
            slot["nonfac_pct"] = round(slot["nonfacility"] / tot, 4) \
                if tot else 0.0
    return agg
