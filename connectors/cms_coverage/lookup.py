"""Enriched lookup handlers: ``/v1/lookup/document/{id}`` & ``/contractor/{id}``.

These fan out one key across the canonical tables to return the full
coverage picture for a document id or a Medicare contractor. They are
provided as **plain callables** plus a router-agnostic handler map
(:func:`v1_handlers`) so a router that supports plugin registration can
mount them *without editing its core*. If the core router can't accept
plugins, these stay usable directly (and via the CLI) and nothing in the
router is touched.

The document lookup returns every version/type of a document id plus a
small "related" fan-out over the same ``chapter``. The contractor lookup
returns the contractor row plus the local documents (LCDs / Proposed
LCDs / Articles) associated with that ``contractor_id``.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List

from .tables import CmsCoverageStore

_RELATED_LIMIT = 50
_DOCS_LIMIT = 200


def lookup_document(store: CmsCoverageStore, document_id: str) -> Dict[str, Any]:
    """Every row for a document id (across versions/types) + same-chapter kin."""
    did = str(document_id).strip()
    documents = _rows(
        store,
        "SELECT * FROM dim_coverage_document WHERE document_id = ? "
        "ORDER BY document_version DESC", (did,))
    chapters = sorted({d["chapter"] for d in documents
                       if d.get("chapter") not in (None, "")})
    related: List[Dict[str, Any]] = []
    if chapters:
        placeholders = ", ".join("?" for _ in chapters)
        related = _rows(
            store,
            f"SELECT document_key, document_id, document_display_id, "
            f"document_type, title, chapter, coverage_level "
            f"FROM dim_coverage_document "
            f"WHERE chapter IN ({placeholders}) AND document_id <> ? "
            f"ORDER BY chapter, document_id LIMIT ?",
            (*chapters, did, _RELATED_LIMIT))
    return {
        "document_id": did,
        "count": len(documents),
        "documents": documents,
        "chapters": chapters,
        "related": {"count": len(related), "by_chapter": related},
    }


def lookup_contractor(store: CmsCoverageStore, contractor_id: str) -> Dict[str, Any]:
    """A contractor row + every local document associated with its id."""
    cid = str(contractor_id).strip()
    contractor = _rows(
        store,
        "SELECT * FROM dim_medicare_contractor WHERE contractor_id = ? "
        "ORDER BY contractor_version DESC", (cid,))
    local_docs = _rows(
        store,
        "SELECT document_key, document_id, document_display_id, "
        "document_type, title, coverage_level, contractor_id, contractor_name, "
        "last_updated FROM dim_coverage_document "
        "WHERE contractor_id = ? AND coverage_level = 'local' "
        "ORDER BY last_updated_sort DESC LIMIT ?", (cid, _DOCS_LIMIT))
    return {
        "contractor_id": cid,
        "contractor": contractor[0] if contractor else None,
        "contractor_versions": contractor,
        "local_documents": {
            "count": _count(store, "dim_coverage_document", "contractor_id", cid),
            "sample": local_docs,
        },
    }


# ── router-agnostic plugin surface ────────────────────────────────────
def v1_handlers(store: CmsCoverageStore) -> Dict[str, Callable[[str], Dict[str, Any]]]:
    """Return ``{route_template: handler}`` for plugin registration.

    A router that accepts plugins can mount these without core edits::

        for route, fn in v1_handlers(store).items():
            router.register(route, fn)

    Each handler takes the single path parameter and returns a JSON-able
    dict. Kept deliberately framework-free so it binds to any router shape.
    """
    return {
        "/v1/lookup/document/{document_id}":
            lambda did: lookup_document(store, did),
        "/v1/lookup/contractor/{contractor_id}":
            lambda cid: lookup_contractor(store, cid),
    }


def _rows(store: CmsCoverageStore, sql: str, args: tuple) -> List[Dict[str, Any]]:
    return [dict(r) for r in store.fetchall(sql, args)]


def _count(store: CmsCoverageStore, table: str, col: str, value: str) -> int:
    return store.count(table, f"{col} = ?", (value,))
