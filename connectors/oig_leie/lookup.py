"""Enriched lookup handlers: ``/v1/lookup/exclusion/{npi}`` &
``/v1/lookup/exclusion-name/{name}``.

These are the provider-compliance screening primitives: "is this NPI on
the exclusion list?" and "is anyone by this name on it?". They are
provided as **plain callables** plus a router-agnostic handler map
(:func:`v1_handlers`) so a router that supports plugin registration can
mount them *without editing its core*. If the core router can't accept
plugins, these stay usable directly (and via the CLI) and nothing in the
router is touched.

The NPI lookup guards the dataset's most dangerous foot-gun: ~85% of
historic LEIE rows carry no NPI (published as ``0000000000``, normalized
to ``''`` at ingest). An empty or all-zero NPI must NEVER match — it
would "flag" tens of thousands of unrelated exclusions — so the handler
refuses to query and says why instead. A clean NPI answers with both the
exclusion rows *and* any reinstatement rows, because a reinstated
provider showing up in a stale exclusions pull is exactly the
false-positive a screen must not raise.

The name lookup LIKE-matches over ``lastname`` and ``busname`` together
(an excluded owner and their excluded company both surface), with an
optional ``?first=`` refinement — the fallback screen for the NPI-less
majority of the file.

Route nouns are unique to this domain (``exclusion``, ``exclusion-name``)
— the estate's taken nouns (drug, device, provider, contractor, …) are
avoided so the unified server can mount every connector's lookups side
by side.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List

from .tables import OigLeieStore

_SAMPLE_LIMIT = 25
_MAX_SAMPLE_LIMIT = 200

# Full LEIE rows are only 21 columns, but lookups return the columns a
# screening decision actually reads, in a stable order.
_ROW_COLS = (
    "exclusion_key, lastname, firstname, midname, busname, general, "
    "specialty, npi, dob, address, city, state, zip, excltype, excldate, "
    "reindate, waiverdate, wvrstate, source_endpoint")
_REIN_COLS = _ROW_COLS.replace("exclusion_key", "reinstatement_key")


def _clamp_limit(limit: Any) -> int:
    try:
        n = int(limit)
    except (TypeError, ValueError):
        return _SAMPLE_LIMIT
    return max(1, min(n, _MAX_SAMPLE_LIMIT))


def lookup_exclusion(store: OigLeieStore, npi: str,
                     limit: Any = _SAMPLE_LIMIT) -> Dict[str, Any]:
    """Screen one NPI against the exclusion list (and reinstatements).

    ``npi`` is matched exactly against the normalized ``npi`` column.
    An empty or all-zero NPI (the LEIE's unknown-sentinel) never
    matches: the handler answers ``matchable=False`` with zero rows
    rather than running a query that would return every NPI-less
    exclusion in the file.
    """
    q = str(npi).strip()
    lim = _clamp_limit(limit)
    if not q or set(q) == {"0"}:
        return {
            "npi": q,
            "matchable": False,
            "excluded": False,
            "count": 0,
            "exclusions": [],
            "reinstatements": {"count": 0, "rows": []},
            "note": ("empty or all-zero NPI never matches: the LEIE "
                     "publishes 0000000000 when the NPI is unknown "
                     "(normalized to '' at ingest); screen by name via "
                     "/v1/lookup/exclusion-name/{name} instead"),
        }
    excl = _rows(
        store,
        f"SELECT {_ROW_COLS} FROM oig_exclusions WHERE npi = ? "
        f"ORDER BY excldate DESC LIMIT ?", (q, lim))
    excl_count = store.count("oig_exclusions", "npi = ?", (q,))
    rein = _rows(
        store,
        f"SELECT {_REIN_COLS} FROM oig_reinstatements WHERE npi = ? "
        f"ORDER BY reindate DESC LIMIT ?", (q, lim))
    rein_count = store.count("oig_reinstatements", "npi = ?", (q,))
    return {
        "npi": q,
        "matchable": True,
        "excluded": excl_count > 0,
        "count": excl_count,
        "exclusions": excl,
        "reinstatements": {"count": rein_count, "rows": rein},
    }


def lookup_exclusion_name(store: OigLeieStore, name: str, first: str = "",
                          limit: Any = _SAMPLE_LIMIT) -> Dict[str, Any]:
    """Screen a last name OR business name against the exclusion list.

    ``name`` is a substring LIKE over ``lastname`` and ``busname``
    together (SQLite LIKE is case-insensitive for ASCII, and LEIE values
    are uppercase). ``first`` optionally narrows to first names starting
    with the given prefix — individuals only, so it is applied as
    ``lastname matched AND firstname LIKE first%`` (a business match has
    no first name and is excluded once ``first`` is given).
    """
    q = str(name).strip()
    fi = str(first or "").strip()
    lim = _clamp_limit(limit)
    if not q:
        return {"name": q, "first": fi, "count": 0, "matches": [],
                "by_excltype": [],
                "note": "empty name never matches; pass a last name or "
                        "business name substring"}
    like = f"%{q}%"
    if fi:
        where = "(lastname LIKE ? AND firstname LIKE ?)"
        args: tuple = (like, f"{fi}%")
    else:
        where = "(lastname LIKE ? OR busname LIKE ?)"
        args = (like, like)
    matches = _rows(
        store,
        f"SELECT {_ROW_COLS} FROM oig_exclusions WHERE {where} "
        f"ORDER BY excldate DESC LIMIT ?", (*args, lim))
    count = store.count("oig_exclusions", where, args)
    by_excltype = _rows(
        store,
        f"SELECT excltype, COUNT(*) AS count FROM oig_exclusions "
        f"WHERE {where} GROUP BY excltype ORDER BY count DESC", args)
    return {
        "name": q,
        "first": fi,
        "count": count,
        "matches": matches,
        "by_excltype": by_excltype,
    }


# ── router-agnostic plugin surface ────────────────────────────────────
def v1_handlers(store: OigLeieStore) -> Dict[str, Callable[..., Dict[str, Any]]]:
    """Return ``{route_template: handler}`` for plugin registration.

    A router that accepts plugins can mount these without core edits::

        for route, fn in v1_handlers(store).items():
            router.register(route, fn)

    Each handler takes the path parameter as its leading positional
    argument; ``first``/``limit`` have defaults so they bind from the
    query string. Kept deliberately framework-free so it binds to any
    router shape.
    """
    return {
        "/v1/lookup/exclusion/{npi}":
            lambda npi, limit=_SAMPLE_LIMIT:
                lookup_exclusion(store, npi, limit),
        "/v1/lookup/exclusion-name/{name}":
            lambda name, first="", limit=_SAMPLE_LIMIT:
                lookup_exclusion_name(store, name, first, limit),
    }


def _rows(store: OigLeieStore, sql: str, args: tuple) -> List[Dict[str, Any]]:
    return [dict(r) for r in store.fetchall(sql, args)]
