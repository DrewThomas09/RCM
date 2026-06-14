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

from ..data_public import nucc_taxonomy as _nucc

logger = logging.getLogger(__name__)

#: Real NUCC taxonomy codes for the infusion provider types (public). Derived
#: from the general crosswalk so the codes/labels stay in one place; the shape
#: ({code,label,kind}) is preserved for existing callers.
INFUSION_TAXONOMIES: List[Dict[str, str]] = [
    {"code": t.code, "label": t.label, "kind": t.kind}
    for t in _nucc.for_vertical("infusion")
]

# NPPES matches these on the human-readable taxonomy description.
_TAXO_DESCRIPTIONS = _nucc.descriptions_for("infusion")


def count_providers_by_taxonomy(
    state: str, descriptions: List[str], city: str = "", *, timeout_s: int = 20,
) -> Dict[str, Any]:
    """Live count of providers in a state (optionally one city) for a set of
    NPPES ``taxonomy_description`` tokens. Returns
    ``{"count": int, "capped": bool, "live": True}`` or ``{"live": False}`` when
    the registry is unreachable — the caller then uses a modeled estimate.

    Generalizes the infusion counter to any vertical; pair with
    ``nucc_taxonomy.descriptions_for(vertical)`` to supply ``descriptions``.
    ``capped`` flags that at least one description hit the 200-result page cap,
    so the true count is an undercount (surface it, never silently round)."""
    st = str(state or "").strip().upper()
    if not st or not descriptions:
        return {"live": False}
    try:
        from ..data_public.nppes_api_client import _request_json
    except Exception:
        return {"live": False}
    total = 0
    capped = False
    try:
        for desc in descriptions:
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
        logger.warning("NPPES provider count unavailable: %s", exc)
        return {"live": False}
    return {"count": total, "capped": capped, "live": True}


def count_infusion_providers(
    state: str, city: str = "", *, timeout_s: int = 20,
) -> Dict[str, Any]:
    """Live count of infusion providers — thin wrapper over the general
    by-taxonomy counter for backward compatibility."""
    return count_providers_by_taxonomy(
        state, _TAXO_DESCRIPTIONS, city=city, timeout_s=timeout_s)


def supply_by_vertical(
    state: str, verticals: List[str] = None, city: str = "", *,
    timeout_s: int = 20,
) -> List[Dict[str, Any]]:
    """Live provider-supply counts across PE verticals for a state — one row
    per vertical: ``{vertical, live, count?, capped?}``. Uses the NUCC crosswalk
    to map each vertical to its NPPES descriptions.

    A vertical whose NPPES call fails is returned with ``live=False`` and no
    count (the market is unknown, not empty) so a partial-egress run degrades
    per-vertical instead of failing the whole sweep. ``verticals`` defaults to
    the full crosswalk coverage."""
    verts = verticals if verticals is not None else _nucc.VERTICALS
    rows: List[Dict[str, Any]] = []
    for v in verts:
        descs = _nucc.descriptions_for(v)
        if not descs:
            rows.append({"vertical": v, "live": False})
            continue
        res = count_providers_by_taxonomy(
            state, descs, city=city, timeout_s=timeout_s)
        row: Dict[str, Any] = {"vertical": v, "live": bool(res.get("live"))}
        if res.get("live"):
            row["count"] = res["count"]
            row["capped"] = res["capped"]
        rows.append(row)
    return rows
