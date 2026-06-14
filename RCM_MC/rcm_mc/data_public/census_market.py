"""Census CBP + SAHIE — market fragmentation and payer-mix context.

Two Census endpoints the vendored ACS loader doesn't cover, answering the
PE questions ACS can't:

  * **County Business Patterns (CBP)** — establishment + employment counts by
    NAICS. The cleanest free way to ask "how fragmented is this provider
    market, and is there roll-up runway?" (e.g. NAICS 621111 = physician
    offices, 621610 = home-health agencies).
  * **Small-Area Health Insurance Estimates (SAHIE)** — uninsured rate by
    county, a payer-mix *proxy* (not contracted mix).

Design, consistent with ``public_api_clients`` and the no-egress render path:
  * Pure ``*_request`` builders return an ``ApiRequest`` you can assert on
    without a network; the shared ``HttpJsonClient`` transport handles
    retry / rate-limit / parse and **fails closed** (``PublicApiError``).
  * The opener is injectable, so normalization is fully offline-testable.
  * The Census key is **optional** — read from ``CENSUS_API_KEY`` if set
    (raises the 500/day cap), never hardcoded, never committed. Omitting it
    is a supported path.
  * Census suppression (``None`` / negative annotation codes like ``-666…``)
    is preserved as missing — never imputed.

Stdlib only (urllib + json + os). No new dependencies.
"""
from __future__ import annotations

import os
from typing import Any, Callable, Dict, List, Optional

from .public_api_clients import ApiRequest, HttpJsonClient, Opener

_CENSUS_BASE = "https://api.census.gov/data"

# NAICS codes for the provider markets PE most often rolls up (public facts).
PROVIDER_NAICS: Dict[str, str] = {
    "621111": "Offices of physicians (except mental health)",
    "621210": "Offices of dentists",
    "621310": "Offices of chiropractors",
    "621320": "Offices of optometrists",
    "621330": "Offices of mental-health practitioners",
    "621340": "Offices of PT/OT/speech/audiology",
    "621391": "Offices of podiatrists",
    "621399": "Offices of all other health practitioners",
    "621498": "All other outpatient care centers",
    "621610": "Home-health-care services",
    "623110": "Nursing-care facilities (skilled nursing)",
    "623210": "Residential intellectual/developmental-disability facilities",
}


# Postal code -> 2-digit state FIPS (public constant). Census endpoints key on
# FIPS, not the USPS code; this is the one place that mapping lives so callers
# can pass the familiar "CO" and get "08".
STATE_FIPS: Dict[str, str] = {
    "AL": "01", "AK": "02", "AZ": "04", "AR": "05", "CA": "06", "CO": "08",
    "CT": "09", "DE": "10", "DC": "11", "FL": "12", "GA": "13", "HI": "15",
    "ID": "16", "IL": "17", "IN": "18", "IA": "19", "KS": "20", "KY": "21",
    "LA": "22", "ME": "23", "MD": "24", "MA": "25", "MI": "26", "MN": "27",
    "MS": "28", "MO": "29", "MT": "30", "NE": "31", "NV": "32", "NH": "33",
    "NJ": "34", "NM": "35", "NY": "36", "NC": "37", "ND": "38", "OH": "39",
    "OK": "40", "OR": "41", "PA": "42", "RI": "44", "SC": "45", "SD": "46",
    "TN": "47", "TX": "48", "UT": "49", "VT": "50", "VA": "51", "WA": "53",
    "WV": "54", "WI": "55", "WY": "56",
}


def state_fips(postal: str) -> str:
    """2-digit state FIPS for a USPS code (case-insensitive), or ``""`` if it
    isn't a recognised state/DC — the caller treats empty as "can't scope to a
    state" rather than guessing."""
    return STATE_FIPS.get(str(postal).strip().upper(), "")


def census_api_key() -> str:
    """The optional Census API key from the environment. Empty string means
    "no key" — a supported path (subject to the 500/day cap). Never embed a
    key in source; this is the only place the value is read."""
    return os.environ.get("CENSUS_API_KEY", "").strip()


def _rows_to_dicts(payload: Any) -> List[Dict[str, str]]:
    """Census returns ``[header_row, *data_rows]``; zip into list-of-dicts.
    A short/empty payload yields ``[]`` rather than raising — an empty market
    is a legitimate answer, not an error."""
    if not isinstance(payload, list) or len(payload) < 2:
        return []
    header = payload[0]
    return [dict(zip(header, row)) for row in payload[1:]]


def _suppressed_int(value: Any) -> Optional[int]:
    """Parse a Census integer cell, mapping suppression/annotation codes
    (None, '', negative sentinels like -666666666) to ``None`` so downstream
    missingness stays explicit and a withheld count is never read as a real 0."""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        n = int(float(s))
    except (TypeError, ValueError):
        return None
    return None if n < 0 else n


def _suppressed_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        f = float(s)
    except (TypeError, ValueError):
        return None
    return None if f < 0 else f


# ── County Business Patterns ──────────────────────────────────────────────
def cbp_request(naics: str, *, state_fips: str = "", year: int = 2022,
                api_key: str = "") -> ApiRequest:
    """Establishment + employment counts for a NAICS, by county. ``state_fips``
    scopes to one state's counties; empty means all counties nationwide."""
    params: Dict[str, str] = {
        "get": "NAME,ESTAB,EMP",
        "NAICS2017": str(naics),
        "for": "county:*",
    }
    if state_fips:
        params["in"] = f"state:{state_fips}"
    if api_key:
        params["key"] = api_key
    return ApiRequest(url=f"{_CENSUS_BASE}/{int(year)}/cbp", params=params)


def fetch_cbp(naics: str, *, state_fips: str = "", year: int = 2022,
              api_key: Optional[str] = None,
              opener: Optional[Opener] = None) -> List[Dict[str, Any]]:
    """Normalized CBP rows: ``{county, fips, naics, establishments, employment}``.
    Suppressed counts come back as ``None``. Fails closed (``PublicApiError``)
    on an unreachable API rather than returning partial data."""
    key = census_api_key() if api_key is None else api_key
    req = cbp_request(naics, state_fips=state_fips, year=year, api_key=key)
    client = HttpJsonClient(base_url=_CENSUS_BASE, min_interval_s=0.1)
    payload = client.get_json(f"/{int(year)}/cbp", req.params, opener=opener)
    out: List[Dict[str, Any]] = []
    for row in _rows_to_dicts(payload):
        out.append({
            "county": row.get("NAME", ""),
            "fips": f"{row.get('state', '')}{row.get('county', '')}",
            "naics": str(naics),
            "establishments": _suppressed_int(row.get("ESTAB")),
            "employment": _suppressed_int(row.get("EMP")),
        })
    return out


def establishments_per_100k(establishments: Optional[int],
                            population: Optional[int]) -> Optional[float]:
    """Establishment density — a fragmentation / roll-up-runway indicator that
    is an honest derived count, not a synthetic concentration index (CBP has no
    per-firm shares, so a true HHI is not computable here). ``None`` when either
    input is missing or population is non-positive."""
    if establishments is None or not population or population <= 0:
        return None
    return round(establishments / population * 100_000.0, 2)


# ── SAHIE (uninsured rate by county) ──────────────────────────────────────
def sahie_request(*, state_fips: str = "", year: int = 2021,
                  api_key: str = "") -> ApiRequest:
    """Uninsured count + percent by county. SAHIE is a timeseries dataset, so
    the year is passed as ``time`` rather than in the path."""
    params: Dict[str, str] = {
        "get": "NAME,NUI_PT,PCTUI_PT",
        "for": "county:*",
        "time": str(int(year)),
    }
    if state_fips:
        params["in"] = f"state:{state_fips}"
    if api_key:
        params["key"] = api_key
    return ApiRequest(url=f"{_CENSUS_BASE}/timeseries/healthins/sahie",
                      params=params)


def fetch_sahie(*, state_fips: str = "", year: int = 2021,
                api_key: Optional[str] = None,
                opener: Optional[Opener] = None) -> List[Dict[str, Any]]:
    """Normalized SAHIE rows: ``{county, fips, uninsured, uninsured_pct}``.
    ``uninsured_pct`` is a payer-mix *proxy* — label it as such downstream;
    it is the uninsured share, not a contracted commercial/Medicaid split."""
    key = census_api_key() if api_key is None else api_key
    req = sahie_request(state_fips=state_fips, year=year, api_key=key)
    client = HttpJsonClient(base_url=_CENSUS_BASE, min_interval_s=0.1)
    payload = client.get_json("/timeseries/healthins/sahie", req.params,
                              opener=opener)
    out: List[Dict[str, Any]] = []
    for row in _rows_to_dicts(payload):
        out.append({
            "county": row.get("NAME", ""),
            "fips": f"{row.get('state', '')}{row.get('county', '')}",
            "uninsured": _suppressed_int(row.get("NUI_PT")),
            "uninsured_pct": _suppressed_float(row.get("PCTUI_PT")),
        })
    return out
