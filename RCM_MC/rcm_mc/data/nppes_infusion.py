"""NPPES infusion-provider counts — real provider supply by taxonomy.

The NPPES NPI Registry is the authoritative roster of every enrolled
US provider. Filtering it to the **infusion taxonomies** gives a real,
verifiable count of ambulatory infusion centers, infusion pharmacies,
and home-infusion agencies in a market — the answer to "how many AICs /
home-infusion providers are actually here", instead of a model estimate.

The NUCC taxonomy codes below are public facts. Counts are pulled live
from the keyless NPPES API (via the existing
``data_public.nppes_api_client``); the call fails closed when egress is
blocked, and the page falls back to the modeled estimate, clearly
labeled. Nothing here fabricates a count.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

#: Real NUCC taxonomy codes for the infusion provider types (public).
INFUSION_TAXONOMIES: List[Dict[str, str]] = [
    {"code": "261QI0500N", "label": "Clinic/Center — Infusion Therapy",
     "kind": "Ambulatory infusion center (AIC)"},
    {"code": "3336I0012X", "label": "Pharmacy — Infusion Therapy",
     "kind": "Infusion pharmacy"},
    {"code": "251F00000X", "label": "Agencies — Home Infusion",
     "kind": "Home-infusion agency"},
]

# NPPES matches these on the human-readable taxonomy description.
_TAXO_DESCRIPTIONS = ["Infusion Therapy", "Home Infusion"]


def count_infusion_providers(
    state: str, city: str = "", *, timeout_s: int = 20,
) -> Dict[str, Any]:
    """Live count of infusion providers in a state (optionally one city)
    from NPPES. Returns ``{"count": int, "capped": bool, "live": True}``
    or ``{"live": False}`` when the registry is unreachable — the caller
    then uses the modeled estimate."""
    st = str(state or "").strip().upper()
    if not st:
        return {"live": False}
    try:
        from ..data_public.nppes_api_client import _request_json
    except Exception:
        return {"live": False}
    total = 0
    capped = False
    try:
        for desc in _TAXO_DESCRIPTIONS:
            params = {
                "version": "2.1",
                "taxonomy_description": desc,
                "state": st,
                "enumeration_type": "NPI-2",
                "limit": "200",
            }
            if city:
                params["city"] = city
            # Fail fast (no retries) — this is a best-effort enrichment,
            # not worth blocking a page render on NPPES backoff.
            data = _request_json(params, timeout_s=timeout_s,
                                 retry_count=0)
            n = int(data.get("result_count") or 0)
            total += n
            if n >= 200:
                capped = True
    except Exception as exc:
        logger.warning("NPPES infusion count unavailable: %s", exc)
        return {"live": False}
    return {"count": total, "capped": capped, "live": True}
