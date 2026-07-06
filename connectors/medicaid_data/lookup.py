"""Enriched lookup handlers: ndc-cost, state-drug, medicaid-dataset.

These fan out one key across the canonical tables to return the full
Medicaid-drug-economics picture for an NDC, a state, or a catalog
dataset. They are provided as **plain callables** plus a router-agnostic
handler map (:func:`v1_handlers`) so a router that supports plugin
registration can mount them *without editing its core*.

Route nouns (``ndc-cost``, ``state-drug``, ``medicaid-dataset``) are
deliberately unique across the estate — the shared ``/v1`` surface merges
every connector's lookups into one namespace, so colliding with e.g.
openFDA's ``drug`` or NPPES's ``provider`` would shadow a handler.

  /v1/lookup/ndc-cost/{ndc}
      Latest NADAC acquisition costs for an 11-digit NDC (most recent
      as-of snapshots first) plus recent NADAC Comparison rate changes
      and the drug's Medicaid rebate-program registrations.
  /v1/lookup/state-drug/{state}
      A state's drug-utilization profile from SDUD: top products by
      Medicaid spend (suppressed rows excluded, since their amounts are
      null by design) plus per-year/quarter row coverage.
  /v1/lookup/medicaid-dataset/{identifier}
      One catalog dataset by DKAN UUID: the synced catalog row, whether a
      curated slice exists for it, and how many generic rows have been
      fetched — i.e. "how connected is this dataset right now".
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List

from .endpoints import ENDPOINTS
from .tables import MedicaidDataStore

_COST_LIMIT = 25
_CHANGE_LIMIT = 10
_REBATE_LIMIT = 5
_TOP_DRUGS_LIMIT = 15


def lookup_ndc_cost(store: MedicaidDataStore, ndc: str) -> Dict[str, Any]:
    """Latest NADAC rows for an NDC + recent rate changes + rebate status."""
    key = str(ndc).strip()
    costs = _rows(
        store,
        "SELECT * FROM medicaid_nadac WHERE ndc = ? "
        "ORDER BY as_of_date DESC, effective_date DESC LIMIT ?",
        (key, _COST_LIMIT))
    changes = _rows(
        store,
        "SELECT * FROM medicaid_nadac_comparison WHERE ndc = ? "
        "ORDER BY effective_date DESC LIMIT ?",
        (key, _CHANGE_LIMIT))
    # Rebate NDCs are stored bare (no dashes) like NADAC's, so a direct
    # equality join works; latest (year, quarter) registrations first.
    rebate = _rows(
        store,
        "SELECT * FROM medicaid_rebate_drug_product WHERE ndc = ? "
        "ORDER BY year DESC, quarter DESC LIMIT ?",
        (key, _REBATE_LIMIT))
    return {
        "ndc": key,
        "latest": costs[0] if costs else None,
        "costs": {"count": _count(store, "medicaid_nadac", "ndc", key),
                  "sample": costs},
        "rate_changes": {"count": _count(store, "medicaid_nadac_comparison",
                                         "ndc", key),
                         "sample": changes},
        "rebate_program": {"count": _count(store,
                                           "medicaid_rebate_drug_product",
                                           "ndc", key),
                           "sample": rebate},
    }


def lookup_state_drug(store: MedicaidDataStore, state: str) -> Dict[str, Any]:
    """SDUD utilization profile for a state: top drugs by Medicaid spend.

    Suppressed rows carry NULL amounts by design (CMS privacy rule), so
    they are excluded from the spend ranking but reported in the counts.
    """
    key = str(state).strip().upper()
    top_drugs = _rows(
        store,
        "SELECT product_name, "
        "COUNT(*) AS rows_reported, "
        "SUM(CAST(total_amount_reimbursed AS REAL)) AS total_reimbursed, "
        "SUM(CAST(medicaid_amount_reimbursed AS REAL)) AS medicaid_reimbursed, "
        "SUM(CAST(number_of_prescriptions AS REAL)) AS prescriptions "
        "FROM medicaid_sdud "
        "WHERE state = ? AND suppression_used != 'true' "
        "AND total_amount_reimbursed IS NOT NULL "
        "GROUP BY product_name ORDER BY total_reimbursed DESC LIMIT ?",
        (key, _TOP_DRUGS_LIMIT))
    periods = _rows(
        store,
        "SELECT year, quarter, utilization_type, COUNT(*) AS count "
        "FROM medicaid_sdud WHERE state = ? "
        "GROUP BY year, quarter, utilization_type "
        "ORDER BY year DESC, quarter DESC",
        (key,))
    return {
        "state": key,
        "rows": _count(store, "medicaid_sdud", "state", key),
        "suppressed_rows": store.count(
            "medicaid_sdud", "state = ? AND suppression_used = 'true'", (key,)),
        "top_drugs_by_spend": top_drugs,
        "periods": periods,
    }


def lookup_medicaid_dataset(store: MedicaidDataStore, identifier: str
                            ) -> Dict[str, Any]:
    """One catalog dataset by DKAN UUID + its connection status."""
    key = str(identifier).strip()
    rows = _rows(
        store,
        "SELECT * FROM medicaid_data_catalog WHERE identifier = ?", (key,))
    curated = [
        {"dataset_id": s.dataset_id, "key": s.key,
         "target_table": s.target_table}
        for s in ENDPOINTS.values() if s.identifier == key
    ]
    fetched_rows = _count(store, "medicaid_data_rows", "dataset_key", key)
    return {
        "identifier": key,
        "found": bool(rows),
        "dataset": rows[0] if rows else None,
        "curated_datasets": curated,
        "fetched_rows": fetched_rows,
    }


# ── router-agnostic plugin surface ────────────────────────────────────
def v1_handlers(store: MedicaidDataStore
                ) -> Dict[str, Callable[[str], Dict[str, Any]]]:
    """Return ``{route_template: handler}`` for plugin registration.

    A router that accepts plugins can mount these without core edits::

        for route, fn in v1_handlers(store).items():
            router.register(route, fn)

    Each handler takes the single path parameter and returns a JSON-able
    dict. Kept deliberately framework-free so it binds to any router shape.
    """
    return {
        "/v1/lookup/ndc-cost/{ndc}":
            lambda ndc: lookup_ndc_cost(store, ndc),
        "/v1/lookup/state-drug/{state}":
            lambda state: lookup_state_drug(store, state),
        "/v1/lookup/medicaid-dataset/{identifier}":
            lambda identifier: lookup_medicaid_dataset(store, identifier),
    }


def _rows(store: MedicaidDataStore, sql: str, args: tuple) -> List[Dict[str, Any]]:
    return [dict(r) for r in store.fetchall(sql, args)]


def _count(store: MedicaidDataStore, table: str, col: str, value: str) -> int:
    return store.count(table, f"{col} = ?", (value,))
