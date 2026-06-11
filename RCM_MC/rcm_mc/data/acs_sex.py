"""ACS sex composition — county female share via the Census API.

The vendored ``county_demographics`` table carries age / income /
insurance but not sex. Female share matters for one infusion proxy in
particular: **IV iron / anemia management**, where iron-deficiency
anemia runs materially higher in women (menstrual + peripartum loss),
so an IV-iron demand index should weight by the female population.

This pulls ACS 5-year table B01001 (Sex by Age): ``B01001_001E`` total
and ``B01001_026E`` female total, by county. Live Census API when
egress is available; otherwise callers fall back to the published
statewide female share (sex ratio is tight — county variance is a few
points — so a state constant is a defensible labeled fallback).
"""
from __future__ import annotations

import functools
import json
import urllib.parse
import urllib.request
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

_CENSUS_HOST = "api.census.gov"

# Published ACS 5-yr statewide female share fallbacks (real values;
# used only when the county-level Census call can't be reached).
STATE_FEMALE_SHARE: Dict[str, float] = {
    "TX": 0.497,   # ACS 2018-2022 5-yr, Texas
    "US": 0.505,
}


def _to_float(v) -> Optional[float]:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def fetch_acs_county_female(
    state_fips: str,
    *,
    year: int = 2022,
    api_key: str = "",
    timeout: float = 20.0,
) -> Dict[str, float]:
    """Female population share by county FIPS for a state.

    Returns ``{county_fips: female_fraction}`` (0–1). Empty dict on any
    failure — caller falls back to ``STATE_FEMALE_SHARE``.
    """
    sf = str(state_fips or "").strip().zfill(2)
    if not sf or sf == "00":
        return {}
    params = {
        "get": "B01001_001E,B01001_026E",
        "for": "county:*",
        "in": f"state:{sf}",
    }
    if api_key:
        params["key"] = api_key
    url = (f"https://{_CENSUS_HOST}/data/{year}/acs/acs5?"
           + urllib.parse.urlencode(params, safe=":*,"))
    from ._cms_download import ssl_context
    try:
        req = urllib.request.Request(
            url, headers={"Accept": "application/json",
                          "User-Agent": "rcm-mc/1.0"})
        with urllib.request.urlopen(
                req, timeout=timeout, context=ssl_context()) as r:
            rows = json.loads(r.read().decode())
    except Exception as exc:
        logger.warning("Census ACS sex API unavailable: %s", exc)
        return {}
    if not rows or len(rows) < 2:
        return {}
    header = rows[0]
    try:
        i_tot = header.index("B01001_001E")
        i_fem = header.index("B01001_026E")
        i_st = header.index("state")
        i_co = header.index("county")
    except ValueError:
        return {}
    out: Dict[str, float] = {}
    for row in rows[1:]:
        total = _to_float(row[i_tot])
        female = _to_float(row[i_fem])
        if not total or female is None or total <= 0:
            continue
        fips = f"{str(row[i_st]).zfill(2)}{str(row[i_co]).zfill(3)}"
        out[fips] = round(female / total, 4)
    return out


@functools.lru_cache(maxsize=8)
def county_female_share(state: str, state_fips: str) -> Dict[str, float]:
    """Cached county female-share map for a state, with disk cache and
    a graceful empty result when the Census API is unreachable."""
    sf = str(state_fips or "").strip().zfill(2)
    cache_path = None
    try:
        from ._cms_download import cache_dir
        cache_path = cache_dir("acs_sex") / f"female_share_{sf}.json"
        if cache_path.is_file():
            cached = json.loads(cache_path.read_text())
            if cached:
                return cached
    except Exception:
        cache_path = None
    data = fetch_acs_county_female(sf)
    if data and cache_path is not None:
        try:
            cache_path.write_text(json.dumps(data))
        except Exception:
            pass
    return data


def female_share_for(
    fips: str, state: str, by_fips: Optional[Dict[str, float]] = None,
) -> float:
    """Female share for a county FIPS — live/cached value if present,
    else the published statewide fallback."""
    if by_fips:
        v = by_fips.get(str(fips).zfill(5))
        if v:
            return v
    return STATE_FEMALE_SHARE.get(
        str(state).strip().upper(), STATE_FEMALE_SHARE["US"])
