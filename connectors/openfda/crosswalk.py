"""Crosswalk: NDC → RxCUI resolution + the device ``product_code`` dimension.

This workstream *appends* two things to the crosswalk contract and
rewrites none of it (NPI, NUCC, FIPS, CPT/HCPCS, MS-DRG, NDC stay as
they are):

  1. ``xwalk_ndc_rxcui`` — resolves each ingested NDC to an RxNorm RxCUI.
     RxNorm is a separate source. If no RxNorm session has run, RxCUI is
     populated ``NULL`` with ``resolution_status='deferred_no_rxnorm'``,
     the gap is logged to DECISIONS.md, and the join stays wireable — we
     never block drug ingestion on it.
  2. ``xwalk_device_product_code`` — the device ``product_code``
     dimension: one row per product_code with its classification facts
     and a clearance count/earliest-decision rollup, the entry point for
     "clearance timeline by product_code" diligence.

The RxCUI resolver is injectable (``resolver=`` callable). The default
resolver returns nothing (deferred) so the no-RxNorm path is the safe
default; a real run passes the RxNorm client's ``ndc → rxcui`` function.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, Dict, Iterable, List, Optional

from .normalize import ndc11
from .tables import OpenFdaStore

# A resolver maps an NDC string to an RxCUI string (or None if unknown).
RxcuiResolver = Callable[[str], Optional[str]]


def deferred_resolver(_ndc: str) -> Optional[str]:
    """Default: no RxNorm session → leave RxCUI null, status 'deferred'."""
    return None


def resolve_ndc_rxcui(
    store: OpenFdaStore,
    ndcs: Iterable[str],
    *,
    resolver: Optional[RxcuiResolver] = None,
) -> Dict[str, int]:
    """Populate ``xwalk_ndc_rxcui`` for the given NDCs and back-fill
    ``dim_drug_product.rxcui`` where resolved.

    Returns a small stats dict (resolved / deferred / total) the DQ layer
    reports as NDC→RxCUI coverage. Idempotent: re-resolving an NDC
    upserts its row.
    """
    resolver = resolver or deferred_resolver
    now = _utc_now()
    rows: List[Dict[str, object]] = []
    resolved = 0
    seen = set()
    for ndc in ndcs:
        if not ndc or ndc in seen:
            continue
        seen.add(ndc)
        rxcui = None
        try:
            rxcui = resolver(ndc) or (resolver(ndc11(ndc) or "") if ndc11(ndc) else None)
        except Exception:
            rxcui = None  # a flaky RxNorm call must not break the crosswalk
        status = "resolved" if rxcui else "deferred_no_rxnorm"
        if rxcui:
            resolved += 1
        rows.append({
            "ndc": ndc, "rxcui": rxcui, "resolution_status": status,
            "resolved_at": now, "source": "rxnorm" if rxcui else "deferred",
        })
    if rows:
        store.upsert("xwalk_ndc_rxcui", rows)
        # Back-fill resolved RxCUIs onto the drug product dimension.
        with store.conn:
            for r in rows:
                if r["rxcui"]:
                    store.conn.execute(
                        "UPDATE dim_drug_product SET rxcui=? WHERE ndc=?",
                        (r["rxcui"], r["ndc"]))
    return {
        "total": len(seen),
        "resolved": resolved,
        "deferred": len(seen) - resolved,
    }


def rebuild_device_product_code(store: OpenFdaStore) -> int:
    """(Re)build ``xwalk_device_product_code`` from ``dim_device``.

    One row per product_code: classification facts plus a clearance
    rollup (count of decisioned rows + earliest decision date) — the
    competitive-entry / margin-compression signal keyed by product_code.
    Returns the number of product_code rows written.
    """
    sql = """
        SELECT
          product_code,
          MAX(CASE WHEN decision_type='classification' THEN device_name END) AS class_name,
          MAX(device_name) AS any_name,
          MAX(device_class) AS device_class,
          MAX(regulation_number) AS regulation_number,
          MAX(medical_specialty) AS medical_specialty,
          MIN(CASE WHEN decision_date IS NOT NULL AND decision_date <> ''
                   THEN decision_date END) AS first_decision_date,
          SUM(CASE WHEN decision_date IS NOT NULL AND decision_date <> ''
                   THEN 1 ELSE 0 END) AS clearance_count
        FROM dim_device
        WHERE product_code IS NOT NULL AND product_code <> ''
        GROUP BY product_code
    """
    now = _utc_now()
    rows = []
    for r in store.fetchall(sql):
        rows.append({
            "product_code": r["product_code"],
            "device_name": r["class_name"] or r["any_name"],
            "device_class": r["device_class"],
            "regulation_number": r["regulation_number"],
            "medical_specialty": r["medical_specialty"],
            "first_decision_date": r["first_decision_date"],
            "clearance_count": str(r["clearance_count"] or 0),
            "ingested_at": now,
        })
    if rows:
        store.upsert("xwalk_device_product_code", rows)
    return len(rows)


def persist_companies(store: OpenFdaStore, companies: Dict[str, Dict]) -> int:
    """Upsert the normalized company rollup (manufacturer/sponsor → company)."""
    import json
    rows = []
    now = _utc_now()
    for key, c in companies.items():
        raw = c.get("raw_names")
        raw_list = sorted(raw) if isinstance(raw, set) else (raw or [])
        rows.append({
            "company_key": key,
            "normalized_name": c.get("normalized_name"),
            "raw_names_json": json.dumps(raw_list, ensure_ascii=False),
            "kind": c.get("kind"),
            "ingested_at": now,
        })
    if rows:
        store.upsert("dim_company", rows)
    return len(rows)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
