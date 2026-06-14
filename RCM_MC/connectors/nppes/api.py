"""API surface for the NPPES slice.

Two framework-agnostic layers, both pure functions over an ``NppesStore``
so they can be mounted by any router (the ``/v1`` core is *not* edited):

  • ``query_dataset`` — the engine behind ``/v1/query/{dataset}``. Resolves
    a registry ``dataset_id`` to its ``target_table`` and applies a uniform
    filter / select / sort / paginate over it. The caller never sees NPPES's
    native response shape — only canonical columns. Anything in the registry
    is queryable with zero new routing code.

  • ``lookup_provider`` / ``search_providers`` — the handlers behind
    ``/v1/lookup/provider/{npi}`` and ``/v1/lookup/provider/search``. These
    assemble the full provider view (dimension + taxonomy crosswalk +
    addresses + affiliations + endpoints).

``mount_router(router)`` wires both into a host router *iff* it exposes a
plugin-registration hook (``add_route``/``register``), so the core stays
untouched; if no hook exists, the functions are still importable and
callable directly.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from . import registry

# Columns we allow to be queried/sorted, per canonical table. Acts as an
# allow-list so a caller can never inject arbitrary SQL identifiers.
_TABLE_COLUMNS: Dict[str, Tuple[str, ...]] = {
    "dim_provider": (
        "npi", "entity_type", "first_name", "middle_name", "last_name",
        "name_prefix", "name_suffix", "credential", "organization_name",
        "authorized_official_last_name", "authorized_official_first_name",
        "authorized_official_title", "sole_proprietor", "enumeration_date",
        "last_update_date", "deactivation_date", "reactivation_date",
        "status", "replacement_npi", "nppes_last_updated", "source_row"),
    "bridge_provider_taxonomy": (
        "npi", "taxonomy_code", "primary_flag", "license_number",
        "license_state", "taxonomy_group"),
    "dim_taxonomy": (
        "taxonomy_code", "grouping", "classification", "specialization",
        "display_name", "section", "nucc_version"),
    "dim_provider_address": (
        "npi", "address_purpose", "address_seq", "address_line_1",
        "address_line_2", "city", "state", "postal_code", "zip5",
        "country_code", "fips_county", "latitude", "longitude",
        "geocode_status"),
    "bridge_provider_affiliation": (
        "individual_npi", "organization_npi", "method", "confidence",
        "evidence"),
    "dim_provider_endpoint": (
        "npi", "endpoint_seq", "endpoint_type", "endpoint_type_description",
        "endpoint", "affiliation", "use_description", "content_type"),
    "nppes_other_name": (
        "npi", "other_name_seq", "other_name", "other_name_type_code"),
}

_OPERATORS = {
    "eq": "=", "ne": "<>", "gt": ">", "gte": ">=", "lt": "<", "lte": "<=",
    "like": "LIKE", "in": "IN",
}
MAX_LIMIT = 1000
DEFAULT_LIMIT = 50


class QueryError(ValueError):
    pass


def _columns_for(table: str) -> Tuple[str, ...]:
    cols = _TABLE_COLUMNS.get(table)
    if not cols:
        raise QueryError(f"table {table!r} is not query-exposed")
    return cols


def _parse_filter_key(key: str) -> Tuple[str, str]:
    """``col`` or ``col__op`` → (col, sql_op)."""
    if "__" in key:
        col, op = key.rsplit("__", 1)
        if op not in _OPERATORS:
            col, op = key, "eq"
    else:
        col, op = key, "eq"
    return col, op


def query_dataset(
    store: Any,
    dataset_id: str,
    *,
    filters: Optional[Dict[str, Any]] = None,
    select: Optional[List[str]] = None,
    sort: Optional[List[str]] = None,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> Dict[str, Any]:
    """Uniform query over the registry dataset's target table.

    ``filters``: ``{"state": "TX", "entity_type__eq": 2,
                    "organization_name__like": "%HOSPITAL%",
                    "taxonomy_code__in": ["207Q00000X", "208D00000X"]}``
    ``select``: column allow-list subset; ``sort``: ``["state", "-npi"]``
    (``-`` prefix = DESC). Returns ``{data, total, limit, offset,
    next_offset, dataset_id, target_table}``.
    """
    # Accept either a registry dataset_id or a canonical table name directly
    # (so /v1/query/nppes_monthly_full and /v1/query/dim_provider both work).
    try:
        ds = registry.dataset_by_id(dataset_id)
        table = ds["target_table"]
    except KeyError:
        if dataset_id in _TABLE_COLUMNS:
            table = dataset_id
        else:
            raise QueryError(
                f"unknown dataset_id/table {dataset_id!r}; valid datasets: "
                f"{sorted(registry.query_exposed_tables())} or tables: "
                f"{sorted(_TABLE_COLUMNS)}")
    cols = _columns_for(table)
    colset = set(cols)

    limit = max(1, min(int(limit), MAX_LIMIT))
    offset = max(0, int(offset))

    where_sql: List[str] = []
    args: List[Any] = []
    for raw_key, val in (filters or {}).items():
        col, op = _parse_filter_key(raw_key)
        if col not in colset:
            raise QueryError(f"unknown/forbidden filter column {col!r} for {table}")
        sql_op = _OPERATORS[op]
        if op == "in":
            seq = list(val) if isinstance(val, (list, tuple, set)) else [val]
            if not seq:
                where_sql.append("0")
                continue
            ph = ",".join("?" for _ in seq)
            where_sql.append(f"{col} IN ({ph})")
            args.extend(seq)
        else:
            where_sql.append(f"{col} {sql_op} ?")
            args.append(val)

    if select:
        bad = [c for c in select if c not in colset]
        if bad:
            raise QueryError(f"unknown/forbidden select column(s): {bad}")
        sel_sql = ", ".join(select)
    else:
        sel_sql = ", ".join(cols)

    order_sql = ""
    if sort:
        terms = []
        for s in sort:
            desc = s.startswith("-")
            c = s[1:] if desc else s
            if c not in colset:
                raise QueryError(f"unknown/forbidden sort column {c!r}")
            terms.append(f"{c} {'DESC' if desc else 'ASC'}")
        order_sql = " ORDER BY " + ", ".join(terms)

    where = (" WHERE " + " AND ".join(where_sql)) if where_sql else ""
    with store.connect() as con:
        total = con.execute(
            f"SELECT COUNT(*) c FROM {table}{where}", args).fetchone()["c"]
        rows = con.execute(
            f"SELECT {sel_sql} FROM {table}{where}{order_sql} LIMIT ? OFFSET ?",
            args + [limit, offset]).fetchall()
    data = [dict(r) for r in rows]
    next_offset = offset + limit if (offset + limit) < total else None
    return {
        "dataset_id": dataset_id,
        "target_table": table,
        "total": total,
        "limit": limit,
        "offset": offset,
        "next_offset": next_offset,
        "data": data,
    }


# ── lookup handlers ─────────────────────────────────────────────────
def lookup_provider(store: Any, npi: str) -> Optional[Dict[str, Any]]:
    """Full provider view for one NPI. Returns None if not found."""
    npi = str(npi).strip()
    with store.connect() as con:
        prov = con.execute(
            "SELECT * FROM dim_provider WHERE npi=?", (npi,)).fetchone()
        if prov is None:
            return None
        taxos = con.execute(
            "SELECT b.taxonomy_code, b.primary_flag, b.license_number, "
            "       b.license_state, t.grouping, t.classification, "
            "       t.specialization, t.display_name "
            "FROM bridge_provider_taxonomy b "
            "LEFT JOIN dim_taxonomy t ON t.taxonomy_code=b.taxonomy_code "
            "WHERE b.npi=? ORDER BY b.primary_flag DESC", (npi,)).fetchall()
        addrs = con.execute(
            "SELECT * FROM dim_provider_address WHERE npi=? "
            "ORDER BY address_seq", (npi,)).fetchall()
        endpoints = con.execute(
            "SELECT * FROM dim_provider_endpoint WHERE npi=? "
            "ORDER BY endpoint_seq", (npi,)).fetchall()
        if prov["entity_type"] == 1:
            affil = con.execute(
                "SELECT organization_npi AS npi, method, confidence, evidence "
                "FROM bridge_provider_affiliation WHERE individual_npi=? "
                "ORDER BY confidence DESC", (npi,)).fetchall()
        else:
            affil = con.execute(
                "SELECT individual_npi AS npi, method, confidence, evidence "
                "FROM bridge_provider_affiliation WHERE organization_npi=? "
                "ORDER BY confidence DESC", (npi,)).fetchall()
    return {
        "provider": dict(prov),
        "taxonomies": [dict(r) for r in taxos],
        "addresses": [dict(r) for r in addrs],
        "endpoints": [dict(r) for r in endpoints],
        "affiliations": [dict(r) for r in affil],
    }


def search_providers(
    store: Any,
    *,
    last_name: Optional[str] = None,
    organization_name: Optional[str] = None,
    state: Optional[str] = None,
    city: Optional[str] = None,
    taxonomy_code: Optional[str] = None,
    entity_type: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> Dict[str, Any]:
    """Targeted provider search across dim_provider (+ address/taxonomy
    joins). Mirrors the NPI Registry API's name/taxonomy/location search
    but over the local universe."""
    limit = max(1, min(int(limit), MAX_LIMIT))
    offset = max(0, int(offset))
    where: List[str] = []
    args: List[Any] = []
    joins = ""
    if last_name:
        where.append("p.last_name LIKE ?"); args.append(f"{last_name.upper()}%")
    if organization_name:
        where.append("p.organization_name LIKE ?")
        args.append(f"%{organization_name.upper()}%")
    if entity_type is not None:
        where.append("p.entity_type = ?"); args.append(int(entity_type))
    if status:
        where.append("p.status = ?"); args.append(status)
    if state or city:
        joins += (" JOIN dim_provider_address a ON a.npi=p.npi "
                  "AND a.address_purpose='practice'")
        if state:
            where.append("a.state = ?"); args.append(state.upper())
        if city:
            where.append("a.city = ?"); args.append(city.upper())
    if taxonomy_code:
        joins += " JOIN bridge_provider_taxonomy bt ON bt.npi=p.npi"
        where.append("bt.taxonomy_code = ?"); args.append(taxonomy_code)
    wsql = (" WHERE " + " AND ".join(where)) if where else ""
    with store.connect() as con:
        total = con.execute(
            f"SELECT COUNT(DISTINCT p.npi) c FROM dim_provider p{joins}{wsql}",
            args).fetchone()["c"]
        rows = con.execute(
            f"SELECT DISTINCT p.npi, p.entity_type, p.organization_name, "
            f"p.last_name, p.first_name, p.credential, p.status "
            f"FROM dim_provider p{joins}{wsql} ORDER BY p.npi LIMIT ? OFFSET ?",
            args + [limit, offset]).fetchall()
    return {
        "total": total, "limit": limit, "offset": offset,
        "next_offset": (offset + limit) if (offset + limit) < total else None,
        "data": [dict(r) for r in rows],
    }


# ── optional router mounting (no core edits) ────────────────────────
def mount_router(router: Any, store: Any) -> bool:
    """Mount the lookup + query handlers onto a host router *iff* it exposes
    a plugin hook. Returns True if mounted, False if the router has no
    supported registration surface (in which case callers use the functions
    directly). The ``/v1`` core is never edited by this slice."""
    def _provider_handler(npi):
        return lookup_provider(store, npi)

    def _search_handler(**params):
        return search_providers(store, **params)

    def _query_handler(dataset, **params):
        return query_dataset(store, dataset, **params)

    def _market_handler(metric, **params):
        # CDD market-structure analytics, exposed read-only.
        from . import cdd, report, screen, systems
        dispatch = {
            "tam": cdd.tam_by_taxonomy_geography,
            "systems": systems.health_systems,
            "screen": screen.screen_targets,
            "concentration": cdd.market_concentration,
            "fragmentation": cdd.fragmentation_scan,
            "growth": cdd.enumeration_trend,
            "referral_hubs": cdd.referral_hubs,
            "roster": cdd.roster_integrity,
            "platforms": cdd.affiliation_footprint,
            "rollup": cdd.rollup_targets,
            "brief": report.market_brief_data,
        }
        fn = dispatch.get(metric)
        if fn is None:
            raise QueryError(f"unknown market metric {metric!r}")
        return fn(store, **params)

    def _profile_handler(**params):
        from . import profile
        return profile.profile_universe(store)

    routes = [
        ("/v1/lookup/provider/{npi}", _provider_handler),
        ("/v1/lookup/provider/search", _search_handler),
        ("/v1/lookup/market/{metric}", _market_handler),
        ("/v1/lookup/universe/profile", _profile_handler),
        ("/v1/query/{dataset}", _query_handler),
    ]
    hook = None
    for name in ("add_route", "register", "register_route", "route"):
        if hasattr(router, name):
            hook = getattr(router, name)
            break
    if hook is None:
        return False
    for path, fn in routes:
        hook(path, fn)
    return True
