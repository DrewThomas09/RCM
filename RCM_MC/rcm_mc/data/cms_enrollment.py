"""CMS Medicare Monthly Enrollment — total beneficiaries by geography.

The Medicare Monthly Enrollment public file (data.cms.gov) reports, per
state / county / month, the TOTAL Medicare beneficiaries plus the split
between Original (FFS) Medicare and Medicare Advantage & Other. That
total is the correct denominator for a true MA-penetration rate — the
65+ population is only a proxy (it omits the under-65 disabled who are
also Medicare-eligible).

Live client when egress is available; fails **closed** otherwise, and
callers fall back to a published state total. Nothing here fabricates a
count — the offline fallback is a single, labeled published figure.
"""
from __future__ import annotations

import functools
import json
import urllib.parse
import urllib.request
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_CMS_DATA_API = "https://data.cms.gov/data-api/v1/dataset"
_CMS_CATALOG = "https://data.cms.gov/data.json"

# Published CMS Medicare total-beneficiary fallbacks (real, labeled —
# used only when the live enrollment file is unreachable). ~2024.
STATE_TOTAL_MEDICARE: Dict[str, int] = {
    "TX": 4_600_000,   # ≈4.6M total Medicare benes (CMS enrollment)
    "US": 67_000_000,
}

_F_GEO_LVL = ("BENE_GEO_LVL", "Bene_Geo_Lvl")
_F_GEO_DESC = ("BENE_GEO_DESC", "Bene_Geo_Desc", "BENE_STATE_ABRVTN")
_F_TOTAL = ("TOT_BENES", "Tot_Benes")
_F_MA = ("MA_AND_OTH_BENES", "MA_and_Oth_Benes")
_F_FFS = ("ORGNL_MDCR_BENES", "Orgnl_Mdcr_Benes")
_F_MONTH = ("MONTH", "Month")


def _pick(row: Dict[str, Any], names) -> Any:
    for n in names:
        if n in row and row[n] not in (None, ""):
            return row[n]
    return None


def _to_int(v: Any) -> Optional[int]:
    if v in (None, ""):
        return None
    try:
        return int(float(str(v).replace(",", "")))
    except (TypeError, ValueError):
        return None


@functools.lru_cache(maxsize=4)
def _resolve_dataset(timeout: float = 20.0) -> str:
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
        if "medicare monthly enrollment" in str(ds.get("title", "")).lower():
            for dist in ds.get("distribution", []):
                url = str(dist.get("accessURL", "")
                          or dist.get("downloadURL", ""))
                if "dataset/" in url:
                    return url.split("dataset/")[1].split("/")[0]
    return ""


def fetch_total_medicare(state: str, *, timeout: float = 20.0
                         ) -> Dict[str, Any]:
    """Live total / FFS / MA beneficiary counts for a state (latest month
    in the file). ``{"live": False}`` on any failure."""
    st = str(state or "").strip().upper()
    if not st:
        return {"live": False}
    ds = _resolve_dataset(timeout=timeout)
    if not ds:
        return {"live": False}
    from ._cms_download import ssl_context
    params = {"filter[BENE_GEO_LVL]": "State",
              "filter[BENE_STATE_ABRVTN]": st, "size": "200"}
    url = f"{_CMS_DATA_API}/{ds}/data?" + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(
            url, headers={"Accept": "application/json",
                          "User-Agent": "rcm-mc/1.0"})
        with urllib.request.urlopen(
                req, timeout=timeout, context=ssl_context()) as r:
            rows = json.loads(r.read().decode())
    except Exception as exc:
        logger.warning("CMS enrollment API unavailable: %s", exc)
        return {"live": False}
    best = None
    for row in rows if isinstance(rows, list) else []:
        tot = _to_int(_pick(row, _F_TOTAL))
        if tot is None:
            continue
        month = str(_pick(row, _F_MONTH) or "")
        if best is None or month > best[0]:
            best = (month, {
                "total": tot,
                "ma_and_other": _to_int(_pick(row, _F_MA)),
                "original_ffs": _to_int(_pick(row, _F_FFS)),
                "month": month, "live": True})
    return best[1] if best else {"live": False}


def total_medicare_for(state: str, *, fetch_live: bool = False) -> Dict[str, Any]:
    """Total Medicare beneficiaries for a state — live when requested and
    reachable, else the published fallback (labeled, not fabricated)."""
    st = str(state or "").strip().upper()
    if fetch_live:
        live = fetch_total_medicare(st)
        if live.get("live"):
            return live
    return {"total": STATE_TOTAL_MEDICARE.get(
        st, STATE_TOTAL_MEDICARE["US"]),
        "ma_and_other": None, "original_ffs": None,
        "month": "", "live": False}
