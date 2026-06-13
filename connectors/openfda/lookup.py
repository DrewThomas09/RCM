"""Enriched lookup handlers: ``/v1/lookup/drug/{ndc}`` & ``/device/{product_code}``.

These fan out one key across every canonical table to return the full
diligence picture for a drug NDC or a device product_code. They are
provided as **plain callables** plus a router-agnostic handler map
(:func:`v1_handlers`) so a router that supports plugin registration can
mount them *without editing its core* — which is the only condition under
which the contract permits adding these handlers. If the core router
can't accept plugins, these stay usable directly (and via the CLI) and
nothing in the router is touched.

The drug lookup carries the resolved RxCUI through (null when no RxNorm
session has run); the device lookup carries the clearance timeline by
product_code plus MAUDE adverse-event and recall counts — the safety /
competitive-entry signals the schema exists to preserve.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List

from .tables import OpenFdaStore


def lookup_drug(store: OpenFdaStore, ndc: str) -> Dict[str, Any]:
    """Everything keyed to an NDC: product + RxCUI + FAERS + recalls + approval."""
    ndc = str(ndc).strip()
    product = _rows(store,
                    "SELECT * FROM dim_drug_product WHERE ndc = ? OR product_ndc = ?",
                    (ndc, ndc))
    rxcui = None
    for p in product:
        if p.get("rxcui"):
            rxcui = p["rxcui"]
            break
    if rxcui is None:
        xw = _rows(store, "SELECT rxcui FROM xwalk_ndc_rxcui WHERE ndc = ?", (ndc,))
        rxcui = xw[0]["rxcui"] if xw else None
    events = _rows(store,
                   "SELECT * FROM fact_drug_adverse_event WHERE ndc = ? "
                   "ORDER BY receivedate DESC LIMIT 100", (ndc,))
    recalls = _rows(store,
                    "SELECT * FROM fact_drug_recall WHERE ndc = ? "
                    "ORDER BY report_date DESC", (ndc,))
    appno = next((p.get("application_number") for p in product
                  if p.get("application_number")), None)
    approval = []
    if appno:
        approval = _rows(store,
                         "SELECT * FROM dim_drug_approval WHERE application_number = ?",
                         (appno,))
    company_key = next((p.get("company_key") for p in product if p.get("company_key")), None)
    return {
        "ndc": ndc,
        "rxcui": rxcui,
        "rxcui_resolved": rxcui is not None,
        "company_key": company_key,
        "product": product,
        "adverse_events": {"count": _count(store,
                            "fact_drug_adverse_event", "ndc", ndc),
                           "sample": events},
        "recalls": {"count": len(recalls), "rows": recalls},
        "approval": approval,
    }


def lookup_device(store: OpenFdaStore, product_code: str) -> Dict[str, Any]:
    """Everything keyed to a device product_code: clearance timeline,
    UDI, MAUDE adverse events, recalls, and the crosswalk rollup."""
    pc = str(product_code).strip().upper()
    dimension = _rows(store, "SELECT * FROM xwalk_device_product_code "
                      "WHERE product_code = ?", (pc,))
    # Clearance / approval timeline by product_code (competitive entry signal).
    timeline = _rows(store,
                     "SELECT device_key, k_number, pma_number, decision_date, "
                     "decision_type, applicant, company_key, source_endpoint "
                     "FROM dim_device WHERE product_code = ? "
                     "AND decision_date IS NOT NULL AND decision_date <> '' "
                     "ORDER BY decision_date ASC", (pc,))
    udi = _rows(store, "SELECT * FROM dim_device_udi WHERE product_code = ? LIMIT 100",
                (pc,))
    events = _rows(store,
                   "SELECT * FROM fact_device_adverse_event WHERE product_code = ? "
                   "ORDER BY date_received DESC LIMIT 100", (pc,))
    recalls = _rows(store, "SELECT * FROM fact_device_recall WHERE product_code = ? "
                    "ORDER BY report_date DESC", (pc,))
    event_count = _count(store, "fact_device_adverse_event", "product_code", pc)
    udi_count = _count(store, "dim_device_udi", "product_code", pc)
    # MAUDE counts normalized by approximate units in market (UDI as proxy).
    maude_per_udi = round(event_count / udi_count, 4) if udi_count else None
    return {
        "product_code": pc,
        "dimension": dimension[0] if dimension else None,
        "clearance_timeline": timeline,
        "clearance_count": len(timeline),
        "udi": {"count": udi_count, "sample": udi},
        "adverse_events": {"count": event_count, "sample": events,
                           "per_udi_unit": maude_per_udi},
        "recalls": {"count": len(recalls), "rows": recalls},
    }


# ── router-agnostic plugin surface ────────────────────────────────────
def v1_handlers(store: OpenFdaStore) -> Dict[str, Callable[[str], Dict[str, Any]]]:
    """Return ``{route_template: handler}`` for plugin registration.

    A router that accepts plugins can mount these without core edits::

        for route, fn in v1_handlers(store).items():
            router.register(route, fn)

    Each handler takes the single path parameter and returns a JSON-able
    dict. Kept deliberately framework-free (no request/response objects)
    so it binds to any router shape.
    """
    return {
        "/v1/lookup/drug/{ndc}": lambda ndc: lookup_drug(store, ndc),
        "/v1/lookup/device/{product_code}": lambda pc: lookup_device(store, pc),
    }


def _rows(store: OpenFdaStore, sql: str, args: tuple) -> List[Dict[str, Any]]:
    return [dict(r) for r in store.fetchall(sql, args)]


def _count(store: OpenFdaStore, table: str, col: str, value: str) -> int:
    return store.count(table, f"{col} = ?", (value,))
