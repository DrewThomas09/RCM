"""ICD-10 lookup handlers: code, category, and a search convenience.

Three router-agnostic handlers over the canonical ``dim_icd10_code``
table, provided as plain callables plus a handler map
(:func:`v1_handlers`) so a router that supports plugin registration can
mount them *without editing its core* — the only condition under which
the contract permits adding these handlers.

  * :func:`lookup_code`      — the single row for a code (default CM).
  * :func:`lookup_category`  — every code sharing a 3-char category.
  * :func:`search_codes`     — a convenience wrapper that matches a term
    against ``name`` OR ``code`` (a single ``LIKE`` over both columns).
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List

from .tables import Icd10Store


def lookup_code(store: Icd10Store, code: str, code_type: str = "cm") -> Dict[str, Any]:
    """The ``dim_icd10_code`` row for ``code`` (default ``type=cm``).

    Returns ``{}`` when the code is unknown. Codes are matched
    case-insensitively (ICD-10 codes are stored upper-case).
    """
    ct = str(code_type).strip().lower()
    c = str(code).strip().upper()
    rows = _rows(store, "SELECT * FROM dim_icd10_code WHERE code_key = ?",
                 (f"{ct}:{c}",))
    if rows:
        return rows[0]
    # Fallback: match on (code_type, code) directly.
    rows = _rows(store, "SELECT * FROM dim_icd10_code WHERE code_type = ? AND code = ?",
                 (ct, c))
    return rows[0] if rows else {}


def lookup_category(store: Icd10Store, category: str, code_type: str = "cm"
                    ) -> Dict[str, Any]:
    """Every code sharing a 3-char category (e.g. ``E11``), default CM."""
    ct = str(code_type).strip().lower()
    cat = str(category).strip().upper()
    rows = _rows(store,
                 "SELECT * FROM dim_icd10_code WHERE code_type = ? AND category = ? "
                 "ORDER BY code", (ct, cat))
    return {
        "code_type": ct,
        "category": cat,
        "count": len(rows),
        "codes": rows,
    }


def search_codes(store: Icd10Store, code_type: str, q: str, *, limit: int = 50
                 ) -> List[Dict[str, Any]]:
    """Convenience search: match ``q`` against ``name`` OR ``code``.

    Kept deliberately simple — a single case-insensitive ``LIKE`` over
    both the ``name`` and ``code`` columns within the requested code set,
    which is the merge of a ``name__like`` and a ``code__like`` filter.
    """
    ct = str(code_type).strip().lower()
    like = f"%{str(q).strip()}%"
    return _rows(store,
                 "SELECT * FROM dim_icd10_code WHERE code_type = ? "
                 "AND (name LIKE ? OR code LIKE ?) ORDER BY code LIMIT ?",
                 (ct, like, like, _clamp(limit)))


# ── router-agnostic plugin surface ────────────────────────────────────
def v1_handlers(store: Icd10Store) -> Dict[str, Callable[..., Any]]:
    """Return ``{route_template: handler}`` for plugin registration.

    A router that accepts plugins can mount these without core edits::

        for route, fn in v1_handlers(store).items():
            router.register(route, fn)

    Each handler takes the path parameter(s) plus optional query params
    (``code_type``/``q``/``limit``) and returns a JSON-able value. Kept
    framework-free (no request/response objects) so it binds to any
    router shape.
    """
    return {
        "/v1/lookup/code/{code}":
            lambda code, code_type="cm": lookup_code(store, code, code_type),
        "/v1/lookup/category/{category}":
            lambda category, code_type="cm": lookup_category(store, category, code_type),
        "/v1/search/{code_type}":
            lambda code_type, q="", limit=50: {
                "code_type": str(code_type).strip().lower(),
                "q": q,
                "results": search_codes(store, code_type, q, limit=limit),
            },
    }


def _rows(store: Icd10Store, sql: str, args: tuple) -> List[Dict[str, Any]]:
    return [dict(r) for r in store.fetchall(sql, args)]


def _clamp(limit: Any, default: int = 50, lo: int = 1, hi: int = 1000) -> int:
    try:
        n = int(limit)
    except (TypeError, ValueError):
        return default
    return max(lo, min(n, hi))
