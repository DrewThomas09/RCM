"""Enriched lookup handlers: ``/v1/lookup/physician-payments/{npi}``,
``/v1/lookup/manufacturer/{name}`` & ``/v1/lookup/op-dataset/{identifier}``.

These fan out one key across the canonical tables to return the full
Sunshine-Act picture for a prescriber NPI, a reporting manufacturer/GPO,
or a catalog dataset. They are provided as **plain callables** plus a
router-agnostic handler map (:func:`v1_handlers`) so a router that
supports plugin registration can mount them *without editing its core*.

Nouns are unique to this connector's domain (``physician-payments``,
``manufacturer``, ``op-dataset``) so they never collide with the estate's
existing lookup routes (drug/device/company/document/contractor/provider/
taxonomy/code/category).

Dollar figures are stored TEXT (like everything in the estate); the
summaries here CAST explicitly so totals are real sums, not string
concatenation.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List

from .tables import OpenPaymentsStore

_SAMPLE_LIMIT = 25
_MAX_SAMPLE_LIMIT = 200

# The columns worth echoing in a payment sample (the full 91-column rows
# stay one /v1/query call away).
_GENERAL_SAMPLE_COLS = (
    "record_id, date_of_payment, total_amount_of_payment_usdollars, "
    "nature_of_payment_or_transfer_of_value, form_of_payment_or_transfer_of_value, "
    "applicable_manufacturer_or_applicable_gpo_making_payment_name, "
    "covered_recipient_npi, covered_recipient_first_name, "
    "covered_recipient_last_name, recipient_city, recipient_state, program_year"
)


def _clamp_limit(limit: Any) -> int:
    try:
        n = int(limit)
    except (TypeError, ValueError):
        return _SAMPLE_LIMIT
    return max(1, min(n, _MAX_SAMPLE_LIMIT))


def lookup_physician_payments(store: OpenPaymentsStore, npi: str,
                              limit: Any = _SAMPLE_LIMIT) -> Dict[str, Any]:
    """Every 2024 general payment for an NPI + research/ownership context.

    Returns the general-payment sample (largest first), a by-nature
    aggregate, and row counts in the research/ownership tables so a
    caller sees the whole exposure without three queries.
    """
    key = str(npi).strip()
    lim = _clamp_limit(limit)
    general = _rows(
        store,
        f"SELECT {_GENERAL_SAMPLE_COLS} FROM op_general_payment "
        f"WHERE covered_recipient_npi = ? "
        f"ORDER BY CAST(total_amount_of_payment_usdollars AS REAL) DESC "
        f"LIMIT ?", (key, lim))
    totals = store.fetchall(
        "SELECT COUNT(*) AS n, "
        "ROUND(SUM(CAST(total_amount_of_payment_usdollars AS REAL)), 2) AS amount "
        "FROM op_general_payment WHERE covered_recipient_npi = ?", (key,))[0]
    by_nature = _rows(
        store,
        "SELECT nature_of_payment_or_transfer_of_value AS nature, "
        "COUNT(*) AS count, "
        "ROUND(SUM(CAST(total_amount_of_payment_usdollars AS REAL)), 2) AS amount "
        "FROM op_general_payment WHERE covered_recipient_npi = ? "
        "GROUP BY nature_of_payment_or_transfer_of_value "
        "ORDER BY amount DESC", (key,))
    return {
        "npi": key,
        "general_payments": {
            "count": int(totals["n"] or 0),
            "total_amount_usd": totals["amount"],
            "by_nature": by_nature,
            "sample": general,
        },
        "research_payment_count": store.count(
            "op_research_payment", "covered_recipient_npi = ?", (key,)),
        "ownership_payment_count": store.count(
            "op_ownership_payment", "physician_npi = ?", (key,)),
    }


def lookup_manufacturer(store: OpenPaymentsStore, name: str,
                        limit: Any = _SAMPLE_LIMIT) -> Dict[str, Any]:
    """Payments filtered by manufacturer/GPO name (substring LIKE).

    Matches ``applicable_manufacturer_or_applicable_gpo_making_payment_name``
    across the general/research/ownership tables; the caller passes any
    fragment ("MERCK" matches "MERCK SHARP & DOHME LLC").
    """
    frag = str(name).strip()
    like = f"%{frag}%"
    lim = _clamp_limit(limit)
    col = "applicable_manufacturer_or_applicable_gpo_making_payment_name"
    matched = _rows(
        store,
        f"SELECT DISTINCT {col} AS name, "
        f"applicable_manufacturer_or_applicable_gpo_making_payment_id AS id "
        f"FROM op_general_payment WHERE {col} LIKE ? LIMIT ?", (like, lim))
    general_totals = store.fetchall(
        f"SELECT COUNT(*) AS n, "
        f"ROUND(SUM(CAST(total_amount_of_payment_usdollars AS REAL)), 2) AS amount "
        f"FROM op_general_payment WHERE {col} LIKE ?", (like,))[0]
    sample = _rows(
        store,
        f"SELECT {_GENERAL_SAMPLE_COLS} FROM op_general_payment "
        f"WHERE {col} LIKE ? "
        f"ORDER BY CAST(total_amount_of_payment_usdollars AS REAL) DESC "
        f"LIMIT ?", (like, lim))
    return {
        "query": frag,
        "matched_entities": matched,
        "general_payments": {
            "count": int(general_totals["n"] or 0),
            "total_amount_usd": general_totals["amount"],
            "sample": sample,
        },
        "research_payment_count": store.count(
            "op_research_payment", f"{col} LIKE ?", (like,)),
        "ownership_payment_count": store.count(
            "op_ownership_payment", f"{col} LIKE ?", (like,)),
    }


def lookup_op_dataset(store: OpenPaymentsStore, identifier: str
                      ) -> Dict[str, Any]:
    """A catalog row by UUID (or title fragment) + on-demand fetch state.

    Exact identifier match wins; otherwise a title LIKE so humans can
    pass "General Payment". Also reports how many rows of that dataset
    are already sitting in the generic ``open_payments_rows`` table.
    """
    key = str(identifier).strip()
    rows = _rows(store,
                 "SELECT * FROM open_payments_catalog WHERE identifier = ?",
                 (key,))
    if not rows:
        rows = _rows(
            store,
            "SELECT * FROM open_payments_catalog WHERE title LIKE ? "
            "ORDER BY modified DESC LIMIT 10", (f"%{key}%",))
    exact = rows[0] if len(rows) == 1 else None
    fetched = store.count("open_payments_rows", "dataset_key = ?", (key,))
    return {
        "identifier": key,
        "found": len(rows),
        "dataset": exact,
        "candidates": rows if exact is None else [],
        "fetched_rows_count": fetched,
    }


# ── router-agnostic plugin surface ────────────────────────────────────
def v1_handlers(store: OpenPaymentsStore) -> Dict[str, Callable[..., Dict[str, Any]]]:
    """Return ``{route_template: handler}`` for plugin registration.

    A router that accepts plugins can mount these without core edits::

        for route, fn in v1_handlers(store).items():
            router.register(route, fn)

    Each handler takes the single path parameter (plus optional
    query-string params with defaults) and returns a JSON-able dict.
    Kept deliberately framework-free so it binds to any router shape.
    """
    return {
        "/v1/lookup/physician-payments/{npi}":
            lambda npi, limit=_SAMPLE_LIMIT:
                lookup_physician_payments(store, npi, limit),
        "/v1/lookup/manufacturer/{name}":
            lambda name, limit=_SAMPLE_LIMIT:
                lookup_manufacturer(store, name, limit),
        "/v1/lookup/op-dataset/{identifier}":
            lambda identifier: lookup_op_dataset(store, identifier),
    }


def _rows(store: OpenPaymentsStore, sql: str, args: tuple) -> List[Dict[str, Any]]:
    return [dict(r) for r in store.fetchall(sql, args)]
