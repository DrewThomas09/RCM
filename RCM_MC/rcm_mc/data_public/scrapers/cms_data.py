"""CMS Data API → public_deals corpus bridge.

Uses cms_api_client to pull Medicare provider utilization and geographic
variation data, then converts the aggregated rows into deal-like dicts
suitable for normalize_batch() and corpus upsert.

This is not a traditional scraper — CMS doesn't publish M&A deal data.
Instead we build *market-intelligence* records: one record per
provider-type / state / year combination that reflects the Medicare
revenue concentration and growth profile for that segment.  These
records supplement real M&A deals in the corpus with data-backed market
intelligence that calibrates the base-rate API.

Public API:
    fetch_cms_market_intelligence(year, state, ...)  -> List[dict]
    cms_ingest_summary(records)                      -> dict
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..cms_api_client import (
    fetch_provider_utilization,
    safe_float,
    safe_int,
    CmsApiError,
)


# ---------------------------------------------------------------------------
# Record builder
# ---------------------------------------------------------------------------

_SOURCE_TAG = "cms_data_api"


def _utilization_row_to_record(row: Dict[str, Any], year: int) -> Optional[Dict[str, Any]]:
    """Convert one CMS provider-utilization row to a corpus-compatible record.

    CMS rows are not M&A deals — they are market benchmarks.  We produce a
    record that the normalizer accepts but marks source='cms_data_api' so
    analysts can distinguish benchmark records from real deal records.
    """
    provider_type = str(row.get("provider_type") or row.get("rndrng_prvdr_type") or "").strip()
    state = str(row.get("state") or row.get("rndrng_prvdr_state_abrvtn") or "").strip()

    if not provider_type or not state:
        return None

    total_payment = safe_float(
        row.get("total_medicare_payment_amt") or row.get("tot_mdcr_pymt_amt")
    )
    total_services = safe_int(
        row.get("total_services") or row.get("tot_srvcs")
    )
    total_benes = safe_int(
        row.get("total_unique_benes") or row.get("tot_benes")
    )
    avg_risk_score = safe_float(
        row.get("beneficiary_average_risk_score")
        or row.get("Beneficiary_Average_Risk_Score")
    )

    payment_mm = total_payment / 1_000_000 if total_payment else 0.0
    source_id = f"cms_{year}_{state}_{provider_type[:30].replace(' ', '_').lower()}"

    return {
        "source_id": source_id,
        "source": _SOURCE_TAG,
        "deal_name": f"CMS Market Intelligence: {provider_type} ({state}, {year})",
        "year": year,
        "buyer": "N/A — Market Data Record",
        "seller": provider_type,
        "notes": (
            f"CMS Medicare provider utilization {year}. "
            f"State: {state}. "
            f"Total Medicare payment: ${payment_mm:.1f}M. "
            f"Services: {total_services:,}. "
            f"Unique beneficiaries: {total_benes:,}. "
            f"Avg risk score: {avg_risk_score:.2f}."
        ),
        # Market intelligence metadata (not standard deal fields but stored in notes)
        "_cms_provider_type": provider_type,
        "_cms_state": state,
        "_cms_year": year,
        "_cms_total_payment_mm": round(payment_mm, 2),
        "_cms_total_services": total_services,
        "_cms_total_benes": total_benes,
        "_cms_avg_risk_score": avg_risk_score,
    }


# ---------------------------------------------------------------------------
# Main fetch function
# ---------------------------------------------------------------------------

def fetch_cms_market_intelligence(
    year: int = 2021,
    state: Optional[str] = None,
    provider_type: Optional[str] = None,
    max_pages: int = 4,
    limit: int = 5000,
) -> List[Dict[str, Any]]:
    """Fetch CMS provider utilization and return corpus-compatible records.

    Args:
        year:           Dataset year (2021 or 2022 available in DATASET_IDS)
        state:          Optional 2-letter state filter (e.g. "TX")
        provider_type:  Optional provider type filter (e.g. "Cardiology")
        max_pages:      Max CMS API pages to fetch (5000 rows/page)
        limit:          Rows per page

    Returns:
        List of corpus-compatible dicts (source='cms_data_api').  Empty list
        if the CMS API is unreachable (does not raise — caller decides).
    """
    try:
        rows = fetch_provider_utilization(
            year=year,
            state=state,
            provider_type=provider_type,
            max_pages=max_pages,
            limit=limit,
        )
    except CmsApiError:
        return []

    records = []
    for row in rows:
        rec = _utilization_row_to_record(row, year)
        if rec is not None:
            records.append(rec)
    return records


# ---------------------------------------------------------------------------
# Summary helper
# ---------------------------------------------------------------------------

def cms_ingest_summary(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Return a brief stats dict for a list of CMS market-intelligence records."""
    if not records:
        return {"count": 0, "states": [], "years": [], "provider_types": []}

    states = sorted({r.get("_cms_state", "") for r in records if r.get("_cms_state")})
    years = sorted({r.get("_cms_year", 0) for r in records if r.get("_cms_year")})
    pts = sorted({r.get("_cms_provider_type", "") for r in records if r.get("_cms_provider_type")})
    total_payment = sum(r.get("_cms_total_payment_mm", 0.0) for r in records)

    return {
        "count": len(records),
        "states": states[:20],
        "years": years,
        "provider_types": pts[:20],
        "total_medicare_payment_mm": round(total_payment, 1),
    }
