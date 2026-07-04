"""Enriched lookup handlers + NPI validation, router-agnostic.

Two fan-out lookups plus the check-digit validator, provided as plain
callables and a router-agnostic handler map (:func:`v1_handlers`) so a
router that supports plugin registration can mount them *without editing
its core*. If the core router can't accept plugins, these stay usable
directly (and via the CLI) and nothing in the router is touched.

  * :func:`lookup_provider` — the ``dim_provider`` row for an NPI, with
    its full taxonomy and address fan-out joined back in.
  * :func:`lookup_taxonomy` — every provider whose **primary** taxonomy
    is a given code (served from ``fact_provider_taxonomy``).
  * :func:`validate` — Luhn/``80840`` check-digit validation, no I/O.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List

from .tables import NpiStore
from .validate import validate_npi


def lookup_provider(store: NpiStore, npi: str) -> Dict[str, Any]:
    """Everything keyed to an NPI: the provider row + taxonomies + addresses."""
    npi = str(npi).strip()
    provider = _rows(store, "SELECT * FROM dim_provider WHERE npi = ?", (npi,))
    taxonomies = _rows(
        store,
        "SELECT * FROM fact_provider_taxonomy WHERE npi = ? "
        "ORDER BY is_primary DESC, code ASC", (npi,))
    addresses = _rows(
        store,
        "SELECT * FROM fact_provider_address WHERE npi = ? "
        "ORDER BY address_purpose ASC", (npi,))
    return {
        "npi": npi,
        "found": bool(provider),
        "provider": provider[0] if provider else None,
        "taxonomies": {"count": len(taxonomies), "rows": taxonomies},
        "addresses": {"count": len(addresses), "rows": addresses},
    }


def lookup_taxonomy(store: NpiStore, code: str, *, limit: int = 200
                    ) -> Dict[str, Any]:
    """Every provider whose primary taxonomy is ``code``.

    Reads from ``fact_provider_taxonomy`` (the primary rows) and joins
    the flattened provider dimension for a compact result list.
    """
    code = str(code).strip()
    lim = max(1, min(int(limit), 1000))
    providers = _rows(
        store,
        "SELECT p.npi, p.enumeration_type, p.first_name, p.last_name, "
        "p.organization_name, p.state, p.primary_taxonomy_desc "
        "FROM fact_provider_taxonomy t "
        "JOIN dim_provider p ON p.npi = t.npi "
        "WHERE t.code = ? AND t.is_primary = '1' "
        "ORDER BY p.npi ASC LIMIT ?", (code, lim))
    count = store.count(
        "fact_provider_taxonomy", "code = ? AND is_primary = '1'", (code,))
    return {
        "taxonomy_code": code,
        "count": count,
        "providers": providers,
    }


def validate(_store: NpiStore, npi: str) -> Dict[str, Any]:
    """NPI check-digit validation — no store access, pure arithmetic."""
    return validate_npi(npi)


# ── router-agnostic plugin surface ────────────────────────────────────
def v1_handlers(store: NpiStore) -> Dict[str, Callable[[str], Dict[str, Any]]]:
    """Return ``{route_template: handler}`` for plugin registration.

    A router that accepts plugins can mount these without core edits::

        for route, fn in v1_handlers(store).items():
            router.register(route, fn)

    Each handler takes the single path parameter and returns a JSON-able
    dict. Kept deliberately framework-free so it binds to any router.
    """
    return {
        "/v1/lookup/provider/{npi}": lambda npi: lookup_provider(store, npi),
        "/v1/lookup/taxonomy/{code}": lambda code: lookup_taxonomy(store, code),
        "/v1/validate/npi/{npi}": lambda npi: validate(store, npi),
    }


def _rows(store: NpiStore, sql: str, args: tuple) -> List[Dict[str, Any]]:
    return [dict(r) for r in store.fetchall(sql, args)]
