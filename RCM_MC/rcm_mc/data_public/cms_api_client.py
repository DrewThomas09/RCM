"""CMS Data API HTTP client for the public deals corpus.

Stdlib-only paginated fetcher for CMS Open Payments / Provider Utilization
datasets.  No pandas, no numpy — returns raw list-of-dicts so callers can
process with whatever tool they prefer.

Ported and cleaned from cms_medicare/cms_api_advisory_analytics.py
(commit: DrewThomas09/cms_medicare).  Only the transport layer is kept here;
analytics live in market_concentration.py and provider_regime.py.

CMS Data API base: https://data.cms.gov/data-api/v1/dataset/{id}/data

Column aliases (canonical → possible CMS field names):
    provider_type  → rndrng_prvdr_type
    state          → nppes_provider_state / rndrng_prvdr_state_abrvtn
    total_services → tot_srvcs
    total_unique_benes → tot_benes
    total_submitted_chrg_amt → tot_submitted_chrg_amt
    total_medicare_payment_amt → tot_mdcr_pymt_amt
    beneficiary_average_age → bene_avg_age
    beneficiary_average_risk_score → Beneficiary_Average_Risk_Score

Public API:
    COLUMN_ALIASES           — canonical → [field_name, ...]
    CmsApiError              — raised on HTTP / parse failures
    fetch_pages(endpoint, ...)         -> List[dict]
    resolve_column(row, canonical)     -> Optional[str]
    normalize_row(row)                 -> dict  (renames aliases to canonical)
    fetch_provider_utilization(year, ...)   -> List[dict]
    fetch_geographic_variation(year, ...)   -> List[dict]
"""
from __future__ import annotations

import json
import time
from typing import Any, Dict, Iterable, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CMS_BASE = "https://data.cms.gov/data-api/v1/dataset"

# Provider utilization and payment by provider — annual datasets
# Dataset IDs from CMS Data Catalog (2021 vintage; update as new releases ship)
DATASET_IDS = {
    "provider_utilization_2021": "9767cb68-8ea9-4f0b-8179-9431abc89f11",
    "provider_utilization_2022": "8889d81e-2ee7-448f-8713-f071038289bf",
    "geographic_variation_2021": "4f53fc0e-0dc1-4e2d-a699-6cfd4524a47c",
    "hospital_general_info":     "64f5c2d5-7a15-4bbb-98e0-e6e4e7ac7dc6",
}

# Canonical field name → list of possible CMS column names
COLUMN_ALIASES: Dict[str, List[str]] = {
    "provider_type":                ["provider_type", "rndrng_prvdr_type"],
    "state":                        ["state", "nppes_provider_state", "rndrng_prvdr_state_abrvtn"],
    "year":                         ["year"],
    "total_services":               ["total_services", "tot_srvcs"],
    "total_unique_benes":           ["total_unique_benes", "tot_benes"],
    "total_submitted_chrg_amt":     ["total_submitted_chrg_amt", "tot_submitted_chrg_amt"],
    "total_medicare_payment_amt":   ["total_medicare_payment_amt", "tot_mdcr_pymt_amt"],
    "beneficiary_average_age":      ["beneficiary_average_age", "bene_avg_age"],
    "beneficiary_average_risk_score": [
        "beneficiary_average_risk_score",
        "Beneficiary_Average_Risk_Score",
    ],
}

_DEFAULT_USER_AGENT = (
    "rcm-mc/data-public-corpus (github.com/DrewThomas09/RCM_MC; "
    "CMS data research — contact: research@example.com)"
)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class CmsApiError(RuntimeError):
    """Raised when the CMS API is unreachable or returns unexpected data."""


# ---------------------------------------------------------------------------
# Core transport
# ---------------------------------------------------------------------------

def fetch_pages(
    endpoint: str,
    *,
    limit: int = 5000,
    max_pages: int = 10,
    offset_param: str = "offset",
    limit_param: str = "size",
    extra_params: Optional[Dict[str, str]] = None,
    retry_count: int = 2,
    retry_backoff_s: float = 1.5,
    timeout_s: int = 45,
    user_agent: str = _DEFAULT_USER_AGENT,
) -> List[Dict[str, Any]]:
    """Fetch paginated JSON from a CMS Data API endpoint.

    Args:
        endpoint:         full URL (may already include query params)
        limit:            page size (CMS default max: 5000)
        max_pages:        hard cap on number of pages to fetch
        offset_param:     query-string key for the offset
        limit_param:      query-string key for page size
        extra_params:     additional query params merged into each request
        retry_count:      number of retries on transient HTTP/network errors
        retry_backoff_s:  base backoff between retries (multiplied by attempt)
        timeout_s:        socket timeout per request
        user_agent:       User-Agent header (CMS requires a contact string)

    Returns:
        Flat list of row dicts from all pages.

    Raises:
        CmsApiError: on unrecoverable HTTP error, parse failure, or empty result.
    """
    all_rows: List[Dict[str, Any]] = []

    for page in range(max_pages):
        offset = page * limit
        params: Dict[str, Any] = {offset_param: offset, limit_param: limit}
        if extra_params:
            params.update(extra_params)

        sep = "&" if "?" in endpoint else "?"
        url = endpoint + sep + urlencode(params)

        rows = _fetch_one(url, retry_count, retry_backoff_s, timeout_s, user_agent)
        if not rows:
            break

        all_rows.extend(rows)

        # If we got fewer rows than the limit, we've reached the last page
        if len(rows) < limit:
            break

    return all_rows


def _fetch_one(
    url: str,
    retry_count: int,
    backoff_s: float,
    timeout_s: int,
    user_agent: str,
) -> List[Dict[str, Any]]:
    last_exc: Optional[Exception] = None

    for attempt in range(retry_count + 1):
        try:
            req = Request(url, headers={"User-Agent": user_agent})
            with urlopen(req, timeout=timeout_s) as resp:
                raw = resp.read().decode("utf-8")
            payload = json.loads(raw)
            if isinstance(payload, dict) and "data" in payload:
                payload = payload["data"]
            if not isinstance(payload, list):
                raise CmsApiError(f"Expected JSON array from CMS API, got {type(payload).__name__}")
            return payload
        except (HTTPError, URLError, TimeoutError) as exc:
            last_exc = exc
            if attempt < retry_count:
                time.sleep(backoff_s * (attempt + 1))
        except json.JSONDecodeError as exc:
            raise CmsApiError(f"CMS API returned non-JSON response: {exc}") from exc

    raise CmsApiError(f"CMS API unreachable after {retry_count + 1} attempts: {last_exc}") from last_exc


# ---------------------------------------------------------------------------
# Column normalisation (stdlib, no pandas)
# ---------------------------------------------------------------------------

def resolve_column(row: Dict[str, Any], canonical: str) -> Optional[str]:
    """Return the actual key in `row` that maps to the canonical field name, or None."""
    for candidate in COLUMN_ALIASES.get(canonical, [canonical]):
        if candidate in row:
            return candidate
    return None


def normalize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Rename CMS alias fields to canonical names in a single row dict."""
    out = dict(row)
    for canonical, candidates in COLUMN_ALIASES.items():
        for alias in candidates[1:]:          # skip the canonical name itself
            if alias in out and canonical not in out:
                out[canonical] = out.pop(alias)
                break
    return out


def normalize_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """normalize_row applied to a list."""
    return [normalize_row(r) for r in rows]


# ---------------------------------------------------------------------------
# Convenience fetchers for known CMS datasets
# ---------------------------------------------------------------------------

def fetch_provider_utilization(
    year: int = 2021,
    state: Optional[str] = None,
    provider_type: Optional[str] = None,
    max_pages: int = 10,
    limit: int = 5000,
) -> List[Dict[str, Any]]:
    """Fetch Medicare Provider Utilization and Payment data for a given year.

    Args:
        year:           dataset year (2019-2022 available as of 2024)
        state:          filter to a single two-letter state abbreviation
        provider_type:  filter to a specific provider type string
        max_pages:      max pages to fetch (each up to 5000 rows)
        limit:          rows per page

    Returns:
        List of normalized row dicts.
    """
    dataset_key = f"provider_utilization_{year}"
    dataset_id = DATASET_IDS.get(dataset_key)
    if not dataset_id:
        # Fallback: use a CMS search-style URL pattern
        endpoint = (
            f"https://data.cms.gov/data-api/v1/dataset/"
            f"?keyword=Medicare+Physician+Utilization+{year}&limit=1"
        )
        raise CmsApiError(
            f"No dataset ID configured for year {year}. "
            f"Add to DATASET_IDS in cms_api_client.py. "
            f"Known years: {[k.split('_')[-1] for k in DATASET_IDS if 'provider_utilization' in k]}"
        )

    endpoint = f"{CMS_BASE}/{dataset_id}/data"
    extra: Dict[str, str] = {}
    if state:
        extra["filter[rndrng_prvdr_state_abrvtn]"] = state
    if provider_type:
        extra["filter[rndrng_prvdr_type]"] = provider_type

    rows = fetch_pages(endpoint, limit=limit, max_pages=max_pages, extra_params=extra or None)
    return normalize_rows(rows)


def fetch_geographic_variation(
    year: int = 2021,
    max_pages: int = 5,
    limit: int = 5000,
) -> List[Dict[str, Any]]:
    """Fetch CMS Geographic Variation in Medicare Services data."""
    dataset_key = f"geographic_variation_{year}"
    dataset_id = DATASET_IDS.get(dataset_key)
    if not dataset_id:
        raise CmsApiError(
            f"No dataset ID configured for geographic variation year {year}."
        )
    endpoint = f"{CMS_BASE}/{dataset_id}/data"
    rows = fetch_pages(endpoint, limit=limit, max_pages=max_pages)
    return normalize_rows(rows)


def safe_float(value: Any, default: float = 0.0) -> float:
    """Convert a CMS API string value to float, returning default on failure."""
    if value is None:
        return default
    try:
        return float(str(value).replace(",", ""))
    except (ValueError, TypeError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(str(value).replace(",", "").split(".")[0])
    except (ValueError, TypeError):
        return default
