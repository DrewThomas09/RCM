"""Diligence analytics over the RxNorm tables.

These turn the normalized crosswalk + concept + class tables into the answers a
healthcare-PE deal team actually asks:

  * "How big is this molecule's competitive set?" — branded/clinical drugs and
    brands that share an ingredient (``molecule_competitive_set``).
  * "Size the target's space by therapeutic class or mechanism." — rxcui counts
    per drug class, the use RxClass grouping is built for
    (``competitive_set_by_class`` / ``class_members``).
  * "Which codes are retired/remapped and where do they point?" — so a stale
    code never silently drops a record (``retired_remapped_audit``).
  * "What's our crosswalk + class coverage, and does it join to openFDA?" —
    one headline summary (``coverage_summary``).

Pure reads over the store; no network. Everything is parameterised SQL.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from . import store as st
from . import validation


def coverage_summary(store: Any) -> Dict[str, Any]:
    """Headline KPIs for the page: counts, class coverage, openFDA join rate."""
    counts = st.counts(store)
    cov = st.class_coverage(store)
    with store.connect() as con:
        st.ensure_tables(con)
        distinct_rxcui_with_ndc = con.execute(
            "SELECT COUNT(DISTINCT rxcui) AS n FROM xwalk_ndc_rxcui"
        ).fetchone()["n"]
        retired = con.execute(
            "SELECT COUNT(*) AS n FROM dim_rxnorm_concept "
            "WHERE status IN ('retired','remapped')"
        ).fetchone()["n"]
    join = validation.openfda_ndc_match_rate(store)
    return {
        "counts": counts,
        "class_coverage": cov,
        "rxcui_with_ndc": distinct_rxcui_with_ndc,
        "retired_or_remapped": retired,
        "openfda_join": join,
    }


def search_concepts(store: Any, term: str, *, tty: str = "",
                    limit: int = 25) -> List[Dict[str, Any]]:
    """Name search over the concept table (offline, LIKE-based).

    The page's free-text box uses this so name lookup works without hitting the
    live ``approximateTerm`` / ``drugs`` endpoints. Matches are case-insensitive
    substring; active concepts first, then by name.
    """
    term = (term or "").strip()
    if not term:
        return []
    sql = ("SELECT rxcui, name, tty, status, remapped_to_rxcui "
           "FROM dim_rxnorm_concept WHERE name LIKE ? ESCAPE '\\'")
    like = "%" + term.replace("\\", "\\\\").replace("%", "\\%").replace(
        "_", "\\_") + "%"
    params: List[Any] = [like]
    if tty:
        sql += " AND tty = ?"
        params.append(tty.upper())
    sql += (" ORDER BY (status='active') DESC, length(name) ASC, name ASC "
            "LIMIT ?")
    params.append(max(1, min(int(limit), 200)))
    with store.connect() as con:
        st.ensure_tables(con)
        rows = con.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def competitive_set_by_class(store: Any, *, class_type: str = "",
                             limit: int = 25) -> List[Dict[str, Any]]:
    """Drug classes ranked by the number of distinct molecules in them.

    This is how you size a target's competitive set by therapeutic class or
    mechanism of action: each class with the count of rxcuis grouped under it.
    """
    sql = ("SELECT class_id, class_name, class_type, "
           "COUNT(DISTINCT rxcui) AS n_rxcui "
           "FROM dim_drug_class")
    params: List[Any] = []
    if class_type:
        sql += " WHERE class_type = ?"
        params.append(class_type)
    sql += (" GROUP BY class_id, class_name, class_type "
            "ORDER BY n_rxcui DESC, class_name ASC LIMIT ?")
    params.append(max(1, min(int(limit), 200)))
    with store.connect() as con:
        st.ensure_tables(con)
        rows = con.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def class_members(store: Any, class_id: str, *,
                  limit: int = 100) -> List[Dict[str, Any]]:
    """The molecules (rxcui + name + tty) grouped under one drug class."""
    with store.connect() as con:
        st.ensure_tables(con)
        rows = con.execute(
            "SELECT d.rxcui, c.name, c.tty, c.status "
            "FROM dim_drug_class d "
            "LEFT JOIN dim_rxnorm_concept c ON c.rxcui = d.rxcui "
            "WHERE d.class_id = ? "
            "ORDER BY c.name ASC LIMIT ?",
            (str(class_id), max(1, min(int(limit), 500))),
        ).fetchall()
    return [dict(r) for r in rows]


def molecule_competitive_set(store: Any, rxcui: str) -> Dict[str, Any]:
    """Branded + clinical-drug competitive set sharing a molecule (ingredient).

    Resolves the input through any remap first, then collects related concepts
    grouped by relationship (brands, branded drugs, clinical drugs). This is the
    "who else plays in this molecule" view for a drug-target thesis.
    """
    current = st.resolve_rxcui(store, rxcui)
    root = (current or {}).get("rxcui", str(rxcui))
    with store.connect() as con:
        st.ensure_tables(con)
        rows = con.execute(
            "SELECT b.related_rxcui, b.relationship, c.name, c.tty, c.status "
            "FROM bridge_rxcui_related b "
            "LEFT JOIN dim_rxnorm_concept c ON c.rxcui = b.related_rxcui "
            "WHERE b.rxcui = ? ORDER BY b.relationship, c.name",
            (root,),
        ).fetchall()
        ndc_count = con.execute(
            "SELECT COUNT(*) AS n FROM xwalk_ndc_rxcui WHERE rxcui = ?", (root,)
        ).fetchone()["n"]
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for r in rows:
        grouped.setdefault(r["relationship"], []).append(dict(r))
    brands = grouped.get("brand_of", [])
    branded = grouped.get("branded_drug", [])
    clinical = grouped.get("clinical_drug", [])
    return {
        "root_rxcui": root,
        "root_name": (current or {}).get("name", ""),
        "ndc_count": ndc_count,
        "brand_count": len(brands),
        "branded_drug_count": len(branded),
        "clinical_drug_count": len(clinical),
        "by_relationship": grouped,
    }


def retired_remapped_audit(store: Any, *,
                           limit: int = 100) -> List[Dict[str, Any]]:
    """Retired/remapped concepts with their remap target and resolved active.

    The audit that proves stale codes resolve forward rather than dropping
    records: each row shows the dead rxcui, where it remaps, and the active
    concept the resolver lands on.
    """
    with store.connect() as con:
        st.ensure_tables(con)
        rows = con.execute(
            "SELECT rxcui, name, status, remapped_to_rxcui "
            "FROM dim_rxnorm_concept WHERE status IN ('retired','remapped') "
            "ORDER BY status, rxcui LIMIT ?",
            (max(1, min(int(limit), 500)),),
        ).fetchall()
    out: List[Dict[str, Any]] = []
    for r in rows:
        resolved = st.resolve_rxcui(store, r["rxcui"])
        out.append({
            **dict(r),
            "resolves_to_rxcui": (resolved or {}).get("rxcui", ""),
            "resolves_to_name": (resolved or {}).get("name", ""),
            "resolves_to_status": (resolved or {}).get("status", ""),
        })
    return out
