"""CMS Medicare Monthly Enrollment — total benes by state/county.

Public source: ``data.cms.gov`` "Medicare Monthly Enrollment". One row
per (geo level × geo × year × month) with the enrollment splits the
infusion analysis actually needs as a denominator:

  • ``TOT_BENES``            — all Medicare beneficiaries
  • ``ORGNL_MDCR_BENES``     — Original Medicare (FFS) — the Part B
                               buy-and-bill (ASP+6) addressable book
  • ``MA_AND_OTH_BENES``     — Medicare Advantage + other — the
                               steered / prior-auth'd book
  • ``AGED_TOT_BENES`` / ``DSBLD_TOT_BENES`` — 65+ vs <65 disabled

``MONTH`` carries calendar months plus a ``"Year"`` row (the annual
average) — we use the annual row so a single year filter returns one
row per geo.

The live client resolves the dataset UUID from the CMS data.json
catalog and walks the year back from today until rows appear (CMS
publishes with a lag). It fails **closed** (empty) when egress is
blocked; nothing here fabricates an enrollment count — the Texas page
labels its offline fallback MODELED and replaces it with these rows
when the API is reachable.
"""
from __future__ import annotations

import functools
import json
import urllib.parse
import urllib.request
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_CMS_DATA_API = "https://data.cms.gov/data-api/v1/dataset"
_CMS_CATALOG = "https://data.cms.gov/data.json"

# Field aliases (CMS has renamed columns across vintages).
_F_GEO_LVL = ("BENE_GEO_LVL", "Bene_Geo_Lvl", "bene_geo_lvl")
_F_STATE = ("BENE_STATE_ABRVTN", "Bene_State_Abrvtn", "bene_state_abrvtn")
_F_COUNTY = ("BENE_COUNTY_DESC", "Bene_County_Desc", "bene_county_desc")
_F_FIPS = ("BENE_FIPS_CD", "Bene_Fips_Cd", "bene_fips_cd")
_F_YEAR = ("YEAR", "Year", "year")
_F_MONTH = ("MONTH", "Month", "month")
_F_TOTAL = ("TOT_BENES", "Tot_Benes", "tot_benes")
_F_FFS = ("ORGNL_MDCR_BENES", "Orgnl_Mdcr_Benes", "orgnl_mdcr_benes")
_F_MA = ("MA_AND_OTH_BENES", "Ma_And_Oth_Benes", "ma_and_oth_benes")
_F_AGED = ("AGED_TOT_BENES", "Aged_Tot_Benes", "aged_tot_benes")
_F_DSBLD = ("DSBLD_TOT_BENES", "Dsbld_Tot_Benes", "dsbld_tot_benes")
_F_DUAL = ("DUAL_TOT_BENES", "Dual_Tot_Benes", "dual_tot_benes")


def _pick(row: Dict[str, Any], names) -> Any:
    for n in names:
        if n in row and row[n] not in (None, ""):
            return row[n]
    return None


def _to_int(v: Any) -> Optional[int]:
    """Parse a count; suppressed cells ('*', '', N/A) → None — never 0,
    so suppression is distinguishable from an actual zero."""
    if v in (None, ""):
        return None
    s = str(v).strip().replace(",", "")
    if s in ("*", ".", "N/A", "NA", "n/a"):
        return None
    try:
        return int(float(s))
    except (TypeError, ValueError):
        return None


@functools.lru_cache(maxsize=2)
def resolve_monthly_enrollment_dataset(timeout: float = 20.0) -> str:
    """Find the Medicare Monthly Enrollment dataset UUID from the CMS
    catalog. '' on failure (caller fails closed)."""
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
        title = str(ds.get("title", "")).lower()
        if "medicare monthly enrollment" in title:
            for dist in ds.get("distribution", []):
                url = str(dist.get("accessURL", "")
                          or dist.get("downloadURL", ""))
                if "dataset/" in url:
                    return url.split("dataset/")[1].split("/")[0]
    return ""


def _parse_row(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "geo_level": str(_pick(row, _F_GEO_LVL) or "").strip(),
        "state": str(_pick(row, _F_STATE) or "").strip().upper(),
        "county": str(_pick(row, _F_COUNTY) or "").strip(),
        "fips": str(_pick(row, _F_FIPS) or "").strip(),
        "year": _to_int(_pick(row, _F_YEAR)) or 0,
        "month": str(_pick(row, _F_MONTH) or "").strip(),
        "total_benes": _to_int(_pick(row, _F_TOTAL)),
        "ffs_benes": _to_int(_pick(row, _F_FFS)),
        "ma_benes": _to_int(_pick(row, _F_MA)),
        "aged_benes": _to_int(_pick(row, _F_AGED)),
        "disabled_benes": _to_int(_pick(row, _F_DSBLD)),
        "dual_benes": _to_int(_pick(row, _F_DUAL)),
    }


def fetch_enrollment_rows(
    state: str, geo_level: str, year: int, *,
    month: str = "Year", dataset: str = "", timeout: float = 20.0,
) -> List[Dict[str, Any]]:
    """Annual-average enrollment rows for one state at one geo level
    (``State`` → 1 row, ``County`` → one per county). [] on failure."""
    ds = dataset or resolve_monthly_enrollment_dataset()
    if not ds:
        return []
    from ._cms_download import ssl_context
    params = {
        "filter[BENE_GEO_LVL]": geo_level,
        "filter[BENE_STATE_ABRVTN]": str(state).upper(),
        "filter[YEAR]": str(year),
        "filter[MONTH]": month,
        "size": "500",
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
        logger.warning("CMS monthly-enrollment API unavailable: %s", exc)
        return []
    return [_parse_row(r) for r in rows if isinstance(r, dict)] \
        if isinstance(rows, list) else []


def fetch_state_medicare_base(
    state: str, *, lookback_years: int = 3, timeout: float = 20.0,
) -> Dict[str, Any]:
    """The state total + per-county enrollment splits for the most
    recent published year (CMS publishes with a lag, so walk back from
    the current year). ``{}`` when the API is unreachable — the caller
    keeps its labeled MODELED fallback."""
    ds = resolve_monthly_enrollment_dataset(timeout=timeout)
    if not ds:
        return {}
    this_year = datetime.now(timezone.utc).year
    for year in range(this_year, this_year - 1 - lookback_years, -1):
        st = fetch_enrollment_rows(
            state, "State", year, dataset=ds, timeout=timeout)
        st = [r for r in st if r["total_benes"]]
        if not st:
            continue
        counties = [
            r for r in fetch_enrollment_rows(
                state, "County", year, dataset=ds, timeout=timeout)
            if r["total_benes"]]
        return {
            "state": st[0],
            "counties": counties,
            "year": year,
            "period": f"{year} annual average",
        }
    return {}
