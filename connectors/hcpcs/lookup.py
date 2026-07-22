"""HCPCS lookup handlers: code, section, and a search convenience.

Three router-agnostic handlers over the canonical ``dim_hcpcs_code``
table, provided as plain callables plus a handler map
(:func:`v1_handlers`) so a router that supports plugin registration can
mount them *without editing its core*.

  * :func:`lookup_code`     — the single row for a HCPCS code.
  * :func:`lookup_section`  — every code in a letter section (e.g. ``J``).
  * :func:`search_codes`    — a convenience wrapper that matches a term
    against the descriptions OR ``code`` (a single ``LIKE`` sweep).

Route templates are estate-unique (``hcpcs``-prefixed nouns) so the
unified server's first-match-wins router can never confuse them with the
ICD-10 slice's ``/v1/lookup/code/{code}`` / ``/v1/search/{code_type}``.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List

from .tables import HcpcsStore


def lookup_code(store: HcpcsStore, code: str) -> Dict[str, Any]:
    """The ``dim_hcpcs_code`` row for ``code`` (e.g. ``J9271``, ``E0601``).

    Returns ``{}`` when the code is unknown. Codes are matched
    case-insensitively (HCPCS codes are stored upper-case).
    """
    c = str(code).strip().upper()
    rows = _rows(store, "SELECT * FROM dim_hcpcs_code WHERE code_key = ?",
                 (f"lvl2:{c}",))
    if rows:
        return rows[0]
    # Fallback: match on the bare code directly.
    rows = _rows(store, "SELECT * FROM dim_hcpcs_code WHERE code = ?", (c,))
    return rows[0] if rows else {}


def lookup_section(store: HcpcsStore, section: str, *, limit: int = 500
                   ) -> Dict[str, Any]:
    """Every code in a letter section (e.g. ``E`` DME, ``J`` drugs)."""
    s = str(section).strip().upper()[:1]
    rows = _rows(store,
                 "SELECT * FROM dim_hcpcs_code WHERE section = ? "
                 "ORDER BY code LIMIT ?", (s, _clamp(limit, default=500, hi=10_000)))
    return {
        "section": s,
        "count": store.count("dim_hcpcs_code", "section = ?", (s,)),
        "codes": rows,
    }


def search_codes(store: HcpcsStore, q: str, *, limit: int = 50
                 ) -> List[Dict[str, Any]]:
    """Convenience search: match ``q`` against descriptions OR ``code``.

    Kept deliberately simple — a single case-insensitive ``LIKE`` over
    the ``display``/``short_desc``/``long_desc`` text columns and the
    ``code`` column.
    """
    like = f"%{str(q).strip()}%"
    return _rows(store,
                 "SELECT * FROM dim_hcpcs_code WHERE "
                 "(display LIKE ? OR short_desc LIKE ? OR long_desc LIKE ? "
                 "OR code LIKE ?) ORDER BY code LIMIT ?",
                 (like, like, like, like, _clamp(limit)))


# ── router-agnostic plugin surface ────────────────────────────────────
def v1_handlers(store: HcpcsStore) -> Dict[str, Callable[..., Any]]:
    """Return ``{route_template: handler}`` for plugin registration.

    A router that accepts plugins can mount these without core edits::

        for route, fn in v1_handlers(store).items():
            router.register(route, fn)

    Each handler takes the path parameter(s) plus optional query params
    (``q``/``limit``) and returns a JSON-able value. Kept framework-free
    (no request/response objects) so it binds to any router shape.
    """
    return {
        "/v1/lookup/hcpcs/{code}":
            lambda code: lookup_code(store, code),
        "/v1/lookup/hcpcs-section/{section}":
            lambda section, limit=500: lookup_section(store, section,
                                                      limit=limit),
        "/v1/lookup/hcpcs-search/{term}":
            lambda term, limit=50: {
                "q": term,
                "results": search_codes(store, term, limit=limit),
            },
    }


def _rows(store: HcpcsStore, sql: str, args: tuple) -> List[Dict[str, Any]]:
    return [dict(r) for r in store.fetchall(sql, args)]


def _clamp(limit: Any, default: int = 50, lo: int = 1, hi: int = 1000) -> int:
    try:
        n = int(limit)
    except (TypeError, ValueError):
        return default
    return max(lo, min(n, hi))
