"""Uniform query + lookup layer over the RxNorm tables.

The API contract: a caller gets uniform filter / select / sort / paginate and
never sees RxNav's native response shape — we absorb that in the connector and
expose flat normalized rows here. This module is deliberately *router-agnostic*:
it exposes plain functions a router could register, because this repo's HTTP
server has no ``/v1`` plugin-registration surface and the ``/v1`` router core is
out of scope to edit (see DECISIONS.md). The intended routes, if a registrable
router lands, are:

    GET /v1/query/{dataset}            -> query_dataset(dataset_id, ...)
    GET /v1/lookup/rxnorm/{rxcui}      -> lookup_rxcui(rxcui)
    GET /v1/lookup/rxnorm/ndc/{ndc}    -> lookup_ndc(ndc)

The ``rxnorm`` lookup namespace is deliberate: openFDA owns
``/v1/lookup/drug/{ndc}``, so we never define that path (path-collision
warning in the spec).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from . import registry
from . import store as st
from .normalize import normalize_ndc, NdcNormalizationError

# Columns we allow callers to filter / sort on, per target table. Whitelisting
# keeps the dynamic SQL parameterised on values and validated on identifiers
# (never f-string a user value into SQL).
_TABLE_COLUMNS: Dict[str, Tuple[str, ...]] = {
    "dim_rxnorm_concept": ("rxcui", "name", "tty", "status",
                           "remapped_to_rxcui", "loaded_at"),
    "xwalk_ndc_rxcui": ("ndc_11", "ndc_raw", "rxcui", "status", "loaded_at"),
    "bridge_rxcui_related": ("rxcui", "related_rxcui", "relationship",
                             "loaded_at"),
    "dim_drug_class": ("rxcui", "class_id", "class_name", "class_type",
                       "loaded_at"),
    "dim_ndc_properties": ("ndc_11", "ndc_raw", "rxcui", "labeler",
                           "packaging", "status", "loaded_at"),
}

_MAX_LIMIT = 1000


def datasets() -> List[Dict[str, Any]]:
    """Every queryable dataset (the registry rows) — the discovery surface."""
    return registry.dataset_rows()


def query_dataset(
    store: Any,
    dataset_id: str,
    *,
    filters: Optional[Dict[str, Any]] = None,
    select: Optional[List[str]] = None,
    sort: Optional[str] = None,
    descending: bool = False,
    limit: int = 100,
    offset: int = 0,
) -> Dict[str, Any]:
    """Uniform query over a registered dataset's target table.

    ``filters`` are equality matches (``{column: value}``); unknown columns are
    rejected. ``select`` restricts columns; ``sort`` orders (validated against
    the column whitelist); ``limit``/``offset`` paginate. Returns
    ``{dataset, total, count, limit, offset, rows}`` — a stable envelope that
    hides RxNav's native shape entirely.
    """
    row = registry.get(dataset_id)
    if not row:
        raise KeyError(f"unknown dataset: {dataset_id!r}")
    table = row["target_table"]
    cols = _TABLE_COLUMNS[table]

    # Validate select / sort / filter identifiers against the whitelist.
    sel = [c for c in (select or cols) if c in cols] or list(cols)
    where_sql = ""
    where_params: List[Any] = []
    if filters:
        clauses = []
        for k, v in filters.items():
            if k not in cols:
                raise ValueError(f"unknown filter column: {k!r}")
            clauses.append(f"{k} = ?")
            where_params.append(v)
        if clauses:
            where_sql = " WHERE " + " AND ".join(clauses)

    order_sql = ""
    if sort:
        if sort not in cols:
            raise ValueError(f"unknown sort column: {sort!r}")
        order_sql = f" ORDER BY {sort} {'DESC' if descending else 'ASC'}"

    lim = max(1, min(int(limit), _MAX_LIMIT))
    off = max(0, int(offset))
    select_sql = ", ".join(sel)

    with store.connect() as con:
        st.ensure_tables(con)
        total = con.execute(
            f"SELECT COUNT(*) AS n FROM {table}{where_sql}", where_params
        ).fetchone()["n"]
        rows = con.execute(
            f"SELECT {select_sql} FROM {table}{where_sql}{order_sql} "
            f"LIMIT ? OFFSET ?",
            where_params + [lim, off],
        ).fetchall()

    return {
        "dataset": dataset_id,
        "target_table": table,
        "total": total,
        "count": len(rows),
        "limit": lim,
        "offset": off,
        "rows": [dict(r) for r in rows],
    }


# ── lookup namespace (rxnorm/*) ─────────────────────────────────────────────

def lookup_rxcui(store: Any, rxcui: str) -> Dict[str, Any]:
    """Resolve one RxCUI to its current concept, relations, classes, and NDCs.

    Resolves through remaps so a retired/remapped code returns the *active*
    concept it points to.
    """
    current = st.resolve_rxcui(store, rxcui)
    with store.connect() as con:
        st.ensure_tables(con)
        related = [dict(r) for r in con.execute(
            "SELECT related_rxcui, relationship FROM bridge_rxcui_related "
            "WHERE rxcui = ? ORDER BY relationship, related_rxcui", (str(rxcui),)
        ).fetchall()]
        classes = [dict(r) for r in con.execute(
            "SELECT class_id, class_name, class_type FROM dim_drug_class "
            "WHERE rxcui = ? ORDER BY class_type, class_id", (str(rxcui),)
        ).fetchall()]
        ndcs = [r["ndc_11"] for r in con.execute(
            "SELECT ndc_11 FROM xwalk_ndc_rxcui WHERE rxcui = ? ORDER BY ndc_11",
            (str(rxcui),)
        ).fetchall()]
    return {
        "rxcui": str(rxcui),
        "resolved": current,                 # None if unknown
        "current_rxcui": (current or {}).get("rxcui", str(rxcui)),
        "related": related,
        "drug_classes": classes,
        "ndcs": ndcs,
    }


def lookup_ndc(store: Any, ndc: str) -> Dict[str, Any]:
    """Resolve any NDC representation to its current RxCUI via the crosswalk.

    Normalizes the input NDC to canonical 11-digit form first, so a caller can
    pass a 10-digit hyphenated NDC and still hit the crosswalk.
    """
    try:
        ndc_11 = normalize_ndc(ndc)
    except NdcNormalizationError as exc:
        return {"ndc_input": ndc, "ndc_11": None, "error": str(exc),
                "match": None}
    rec = st.lookup_ndc(store, ndc_11)
    return {
        "ndc_input": ndc,
        "ndc_11": ndc_11,
        "match": rec,                        # None if no crosswalk row
    }
