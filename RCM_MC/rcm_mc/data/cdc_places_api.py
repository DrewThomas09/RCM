"""CDC PLACES — county-level prevalence via the Socrata API.

PLACES (chronicdata.cdc.gov / data.cdc.gov) publishes model-based,
**full-population** small-area estimates of chronic-disease prevalence
and health-risk / access measures at county and census-tract level.
The vendored aggregate in ``cdc_places_agg.py`` is the *state* roll-up;
this module pulls the **county** rows live so a market analysis can
break demand down geographically.

Design for an airgapped CI / sandbox:

  • ``fetch_places_counties`` hits the Socrata "GIS Friendly Format"
    county dataset (default ``i46a-9kgh`` — the same release the
    vendored aggregate was built from) with a ``$where`` state filter,
    paginates, and returns one dict per county keyed by FIPS.
  • Results are cached to the shared data-cache dir, so a single live
    fetch (in an egress-enabled environment) is reused thereafter.
  • Every network path fails *closed* — on any error the caller gets an
    empty result and is expected to fall back to the vendored state
    rate. Nothing here fabricates a county value.

The measure column names are PLACES ``*_crudeprev`` fields; see
``MEASURES`` for the friendly→column map covering the infusion-relevant
clinical proxies (arthritis, CKD, cancer, diabetes, obesity, poor
physical/general health) plus payer-access measures (uninsured,
routine checkup).
"""
from __future__ import annotations

import functools
import json
import urllib.parse
import urllib.request
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Default Socrata dataset: CDC PLACES County Data (GIS Friendly Format).
# Matches places_equity_summary.json ("dataset_id": "i46a-9kgh").
PLACES_COUNTY_DATASET = "i46a-9kgh"
_SOCRATA_HOST = "data.cdc.gov"

# Friendly measure name → PLACES crude-prevalence column.
MEASURES: Dict[str, str] = {
    "arthritis": "arthritis_crudeprev",
    "kidney_disease": "kidney_crudeprev",
    "cancer": "cancer_crudeprev",
    "diabetes": "diabetes_crudeprev",
    "obesity": "obesity_crudeprev",
    "poor_physical_health": "phlth_crudeprev",
    "fair_poor_health": "ghlth_crudeprev",
    "high_bp": "bphigh_crudeprev",
    "depression": "depression_crudeprev",
    "uninsured_18_64": "access2_crudeprev",
    "routine_checkup": "checkup_crudeprev",
}

# Reverse map for parsing API rows back to friendly keys.
_COL_TO_KEY = {v: k for k, v in MEASURES.items()}


def _to_float(v: Any) -> Optional[float]:
    if v in (None, ""):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _pad_fips(s: Any) -> str:
    return str(s or "").strip().zfill(5)


def fetch_places_counties(
    state: str,
    measures: Optional[List[str]] = None,
    *,
    dataset: str = PLACES_COUNTY_DATASET,
    app_token: str = "",
    timeout: float = 20.0,
    page_size: int = 1000,
) -> List[Dict[str, Any]]:
    """Fetch county PLACES rows for a state from the Socrata API.

    Returns a list of dicts (one per county) with the requested
    friendly measure keys plus ``county_fips``, ``county_name``,
    ``state``, ``population``. Returns ``[]`` on any failure (the
    caller is expected to fall back to the vendored state rate).
    """
    st = str(state or "").strip().upper()
    if not st:
        return []
    keys = measures or list(MEASURES)
    cols = ["countyfips", "countyname", "stateabbr", "totalpopulation"]
    cols += [MEASURES[k] for k in keys if k in MEASURES]
    select = ",".join(cols)

    out: List[Dict[str, Any]] = []
    offset = 0
    from ._cms_download import ssl_context
    while True:
        params = {
            "$select": select,
            "$where": f"stateabbr='{st}'",
            "$limit": str(page_size),
            "$offset": str(offset),
        }
        url = (f"https://{_SOCRATA_HOST}/resource/{dataset}.json?"
               + urllib.parse.urlencode(params, safe="$,='"))
        headers = {"Accept": "application/json",
                   "User-Agent": "rcm-mc/1.0"}
        if app_token:
            headers["X-App-Token"] = app_token
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(
                    req, timeout=timeout, context=ssl_context()) as r:
                rows = json.loads(r.read().decode())
        except Exception as exc:  # network / parse — fail closed
            logger.warning("CDC PLACES county API unavailable: %s", exc)
            return out  # whatever we paged so far (usually [])
        if not rows:
            break
        for r in rows:
            rec: Dict[str, Any] = {
                "county_fips": _pad_fips(r.get("countyfips")),
                "county_name": str(r.get("countyname") or "").strip(),
                "state": str(r.get("stateabbr") or "").strip().upper(),
                "population": _to_float(r.get("totalpopulation")),
            }
            for col, key in _COL_TO_KEY.items():
                if col in r:
                    rec[key] = _to_float(r.get(col))
            out.append(rec)
        if len(rows) < page_size:
            break
        offset += page_size
    return out


@functools.lru_cache(maxsize=8)
def places_counties_by_fips(
    state: str,
    *,
    dataset: str = PLACES_COUNTY_DATASET,
) -> Dict[str, Dict[str, Any]]:
    """County PLACES rows for a state keyed by 5-digit FIPS, cached.

    Tries the on-disk cache first, then the live API (whose result is
    written back to cache). Returns ``{}`` when neither is available —
    the airgapped path — so callers fall back to vendored state rates.
    """
    st = str(state or "").strip().upper()
    if not st:
        return {}
    cache_path = None
    try:
        from ._cms_download import cache_dir
        cache_path = cache_dir("cdc_places") / f"places_county_{st}.json"
        if cache_path.is_file():
            cached = json.loads(cache_path.read_text())
            if cached:
                return {_pad_fips(k): v for k, v in cached.items()}
    except Exception:
        cache_path = None

    rows = fetch_places_counties(st, dataset=dataset)
    by_fips = {r["county_fips"]: r for r in rows if r.get("county_fips")}
    if by_fips and cache_path is not None:
        try:
            cache_path.write_text(json.dumps(by_fips))
        except Exception:
            pass
    return by_fips
