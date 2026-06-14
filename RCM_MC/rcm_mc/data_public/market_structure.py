"""Two-source market-structure reconciliation: NPPES supply × Census CBP.

NPPES counts *enrolled providers* (by NUCC taxonomy); Census CBP counts
*establishments* (by NAICS). They measure related-but-different things, and
for diligence the interesting signal is having both side by side: how many
billing providers vs how many physical establishments in a market, and the
ratio between them (a rough multi-site / consolidation hint).

This module is the pure reconciler over already-fetched inputs — no network
here, so it is fully offline-testable. Live fetching stays in
``nppes_infusion.supply_by_vertical`` (NPPES) and ``census_market.fetch_cbp``
(CBP). Either side may be missing; the reconciler keeps the gap explicit
(``None``) rather than fabricating a count or a ratio.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from . import nucc_taxonomy as _nucc


def _sum_establishments(cbp_rows: List[Dict[str, Any]]) -> Optional[int]:
    """Total establishments across CBP county rows, ignoring suppressed
    (``None``) cells. Returns ``None`` only when *every* row is suppressed, so a
    fully-withheld market is distinguishable from a real zero."""
    seen = False
    total = 0
    for row in cbp_rows or []:
        est = row.get("establishments")
        if est is not None:
            total += int(est)
            seen = True
    return total if seen else None


def reconcile_vertical(
    vertical: str,
    nppes_supply: Optional[Dict[str, Any]] = None,
    cbp_rows: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Combine one vertical's NPPES supply row and CBP rows into a market-
    structure record:

      ``{vertical, naics, providers, establishments, providers_per_estab}``

    ``providers`` comes from a *live* NPPES supply row (``{live, count}`` as
    returned by ``supply_by_vertical``); ``establishments`` is the CBP sum.
    ``providers_per_estab`` is computed only when both are present and there is
    at least one establishment — otherwise ``None`` (never a divide-by-zero or a
    fabricated ratio). ``naics`` is ``""`` for verticals with no CBP mapping.
    """
    providers: Optional[int] = None
    if nppes_supply and nppes_supply.get("live"):
        providers = int(nppes_supply.get("count", 0))

    establishments = _sum_establishments(cbp_rows or [])

    ratio: Optional[float] = None
    if providers is not None and establishments:
        ratio = round(providers / establishments, 2)

    return {
        "vertical": vertical,
        "naics": _nucc.naics_for(vertical),
        "providers": providers,
        "establishments": establishments,
        "providers_per_estab": ratio,
    }
