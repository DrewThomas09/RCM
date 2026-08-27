"""RxNorm lookup handlers: NDC, drug name, and RxCUI concept.

Three router-agnostic handlers over the canonical RxNorm tables,
provided as plain callables plus a handler map (:func:`v1_handlers`) so a
router that supports plugin registration can mount them *without editing
its core*.

  * :func:`lookup_ndc`     — the RxCUI + concept for an NDC (matched on
    the digits-only form, so hyphenated and padded NDC spellings from
    different CMS files all land on the same row).
  * :func:`lookup_concept` — the concept row for an RxCUI plus every NDC
    and name that resolved to it (the reverse crosswalk).
  * :func:`lookup_drug_name` — the RxCUI a free-text drug name resolved
    to, including whether the match was exact or approximate.

Route templates are estate-unique (``rx``-prefixed nouns) so the unified
server's first-match-wins router can never confuse them with openFDA's
``/v1/lookup/drug/{ndc}``, which answers from the FDA NDC directory —
a different source and a different grain.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List

from .tables import RxNormStore


def lookup_ndc(store: RxNormStore, ndc: str) -> Dict[str, Any]:
    """The crosswalk row + resolved concept for one NDC.

    Matched on the digits-only form: CMS files spell the same NDC as
    ``0002-1200-01``, ``00021200 01`` and ``00002120001`` across NADAC,
    SDUD and the Part D files, and all three must find the row.
    """
    raw = str(ndc).strip()
    digits = "".join(ch for ch in raw if ch.isdigit())
    rows = _rows(store, "SELECT * FROM xwalk_ndc_rxcui WHERE ndc = ?", (raw,))
    if not rows and digits:
        rows = _rows(store,
                     "SELECT * FROM xwalk_ndc_rxcui WHERE ndc_digits = ?",
                     (digits,))
    if not rows:
        return {}
    row = rows[0]
    return {**row, "concept": _concept(store, row.get("rxcui") or "")}


def lookup_concept(store: RxNormStore, rxcui: str) -> Dict[str, Any]:
    """The concept row for an RxCUI plus every identifier that maps to it."""
    rx = str(rxcui).strip()
    ndcs = _rows(store,
                 "SELECT ndc, ndc_digits FROM xwalk_ndc_rxcui WHERE rxcui = ? "
                 "ORDER BY ndc", (rx,))
    names = _rows(store,
                  "SELECT query_name, match_type FROM xwalk_name_rxcui "
                  "WHERE rxcui = ? ORDER BY query_name", (rx,))
    return {
        "rxcui": rx,
        "concept": _concept(store, rx),
        "n_ndcs": len(ndcs),
        "ndcs": ndcs,
        "names": names,
    }


def lookup_drug_name(store: RxNormStore, name: str) -> Dict[str, Any]:
    """The crosswalk row + resolved concept for a free-text drug name."""
    key = str(name).strip().lower()
    rows = _rows(store, "SELECT * FROM xwalk_name_rxcui WHERE name_key = ?",
                 (key,))
    if not rows:
        return {}
    row = rows[0]
    return {**row, "concept": _concept(store, row.get("rxcui") or "")}


def _concept(store: RxNormStore, rxcui: str) -> Dict[str, Any]:
    if not rxcui:
        return {}
    rows = _rows(store, "SELECT * FROM dim_rxnorm_concept WHERE rxcui = ?",
                 (rxcui,))
    return rows[0] if rows else {}


# ── router-agnostic plugin surface ────────────────────────────────────
def v1_handlers(store: RxNormStore) -> Dict[str, Callable[..., Any]]:
    """Return ``{route_template: handler}`` for plugin registration.

    A router that accepts plugins can mount these without core edits::

        for route, fn in v1_handlers(store).items():
            router.register(route, fn)

    Each handler takes the path parameter and returns a JSON-able value.
    Kept framework-free (no request/response objects) so it binds to any
    router shape.
    """
    return {
        "/v1/lookup/rxnorm-ndc/{ndc}": lambda ndc: lookup_ndc(store, ndc),
        "/v1/lookup/rxnorm-concept/{rxcui}":
            lambda rxcui: lookup_concept(store, rxcui),
        "/v1/lookup/rxnorm-name/{name}":
            lambda name: lookup_drug_name(store, name),
    }


def _rows(store: RxNormStore, sql: str, args: tuple) -> List[Dict[str, Any]]:
    return [dict(r) for r in store.fetchall(sql, args)]
