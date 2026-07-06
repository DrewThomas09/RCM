"""The ``/v1/query`` engine: uniform filter / select / sort / paginate.

The API contract: the caller gets one uniform query surface and never
sees the LEIE download mechanics — the CSV pull was absorbed at ingest
time (:mod:`connectors.oig_leie.connector`). Here the data is already in
canonical SQLite tables, so a query is plain parameterised SQL over a
registry-resolved table. (This connector's registry rows carry no
``source_filter`` — full file and supplement are one logical cumulative
dataset — so the slice-pinning branch below is inert here, but it is
kept verbatim so the engine stays byte-comparable across the estate.)

This engine is copied wholesale from ``connectors/cms_coverage/query.py``
(the estate's shared query grammar) with only the imports, store type
hints and docstring adjusted — the uniform surface stays uniform because
the code is identical, not merely similar.

Safety: column identifiers are validated against the target table's known
column set (a whitelist from :mod:`tables`) — we never interpolate a
caller-supplied identifier. All values are bound parameters. Limit is
clamped with :func:`_clamp_int`.

Filter grammar (uniform across every dataset)::

    {"field": value}                      # equality
    {"field__gte": value, "field__like": "%x%", "field__in": [a, b]}

Supported ops: eq, ne, gt, gte, lt, lte, like, in, between, isnull, notnull.
``between`` takes ``"lo,hi"`` (or a 2-tuple); ``isnull``/``notnull`` ignore
the value. Sort: ``"field"`` asc or ``"-field"`` desc.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .registry import RegistryRow, by_dataset_id
from .tables import TABLES, OigLeieStore

_OPS = {
    "eq": "=", "ne": "!=", "gt": ">", "gte": ">=", "lt": "<", "lte": "<=",
    "like": "LIKE", "in": "IN",
    # Null/range operators (handled specially in _build_where).
    "isnull": "", "notnull": "", "between": "",
}
_DEFAULT_LIMIT = 50
_MAX_LIMIT = 1000


class QueryError(ValueError):
    """Raised on an invalid dataset, column, or operator (a 400-class error)."""


@dataclass
class QueryResult:
    dataset: str
    rows: List[Dict[str, Any]]
    total: int
    limit: int
    offset: int

    def as_dict(self) -> Dict[str, Any]:
        return {
            "dataset": self.dataset,
            "total": self.total,
            "limit": self.limit,
            "offset": self.offset,
            "count": len(self.rows),
            "rows": self.rows,
        }


def _clamp_int(value: Any, default: int, lo: int, hi: int) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    return max(lo, min(n, hi))


def _columns(table: str) -> Tuple[str, ...]:
    return TABLES[table].columns


def _split_field_op(key: str) -> Tuple[str, str]:
    if "__" in key:
        field_name, op = key.rsplit("__", 1)
        if op in _OPS:
            return field_name, op
    return key, "eq"


def query(
    store: OigLeieStore,
    dataset_id: str,
    *,
    filters: Optional[Dict[str, Any]] = None,
    select: Optional[List[str]] = None,
    sort: Optional[List[str]] = None,
    limit: Any = _DEFAULT_LIMIT,
    offset: Any = 0,
    registry: Optional[Dict[str, RegistryRow]] = None,
) -> QueryResult:
    """Run a uniform query against a registered LEIE dataset."""
    registry = registry or by_dataset_id()
    row = registry.get(dataset_id)
    if row is None:
        raise QueryError(f"unknown dataset {dataset_id!r}")
    table = row.target_table
    cols = _columns(table)
    colset = set(cols)

    where_sql, args = _build_where(row, filters or {}, colset)
    select_sql = _build_select(select, cols, colset)
    order_sql = _build_order(sort, colset)
    lim = _clamp_int(limit, _DEFAULT_LIMIT, 1, _MAX_LIMIT)
    off = _clamp_int(offset, 0, 0, 10_000_000)

    total = store.count(table, where_sql.replace("WHERE ", "", 1) if where_sql else "",
                        args)
    sql = f"SELECT {select_sql} FROM {table} {where_sql} {order_sql} LIMIT ? OFFSET ?"
    rows = store.fetchall(sql, (*args, lim, off))
    return QueryResult(
        dataset=dataset_id,
        rows=[dict(r) for r in rows],
        total=total, limit=lim, offset=off,
    )


def _build_where(row: RegistryRow, filters: Dict[str, Any], colset: set
                 ) -> Tuple[str, List[Any]]:
    clauses: List[str] = []
    args: List[Any] = []
    # Always pin to this dataset's endpoint slice when the table is shared.
    if row.source_filter and "source_endpoint" in colset:
        clauses.append("source_endpoint = ?")
        args.append(row.source_filter)
    for key, value in filters.items():
        field_name, op = _split_field_op(key)
        if field_name not in colset:
            raise QueryError(f"unknown filter field {field_name!r}")
        sql_op = _OPS[op]
        if op == "isnull":
            clauses.append(f"({field_name} IS NULL OR {field_name} = '')")
        elif op == "notnull":
            clauses.append(f"({field_name} IS NOT NULL AND {field_name} <> '')")
        elif op == "between":
            parts = value if isinstance(value, (list, tuple)) else str(value).split(",")
            if len(parts) != 2:
                raise QueryError(f"between expects two values, got {value!r}")
            clauses.append(f"{field_name} BETWEEN ? AND ?")
            args.extend(str(p) for p in parts)
        elif op == "in":
            vals = value if isinstance(value, (list, tuple)) else [value]
            if not vals:
                clauses.append("0 = 1")  # empty IN matches nothing
                continue
            placeholders = ", ".join("?" for _ in vals)
            clauses.append(f"{field_name} IN ({placeholders})")
            args.extend(str(v) for v in vals)
        else:
            clauses.append(f"{field_name} {sql_op} ?")
            args.append(str(value))
    if not clauses:
        return "", args
    return "WHERE " + " AND ".join(clauses), args


def _build_select(select: Optional[List[str]], cols: Tuple[str, ...],
                  colset: set) -> str:
    if not select:
        return ", ".join(cols)
    chosen = []
    for c in select:
        if c not in colset:
            raise QueryError(f"unknown select field {c!r}")
        chosen.append(c)
    return ", ".join(chosen) if chosen else ", ".join(cols)


def _build_order(sort: Optional[List[str]], colset: set) -> str:
    if not sort:
        return ""
    parts = []
    for s in sort:
        desc = s.startswith("-")
        field_name = s[1:] if desc else s
        if field_name not in colset:
            raise QueryError(f"unknown sort field {field_name!r}")
        parts.append(f"{field_name} {'DESC' if desc else 'ASC'}")
    return "ORDER BY " + ", ".join(parts) if parts else ""


@dataclass
class AggregateResult:
    dataset: str
    group_by: List[str]
    rows: List[Dict[str, Any]]      # each: {group cols..., "count": n}
    limit: int

    def as_dict(self) -> Dict[str, Any]:
        return {
            "dataset": self.dataset,
            "group_by": self.group_by,
            "limit": self.limit,
            "count": len(self.rows),
            "rows": self.rows,
        }


def aggregate(
    store: OigLeieStore,
    dataset_id: str,
    *,
    group_by: List[str],
    filters: Optional[Dict[str, Any]] = None,
    limit: Any = _DEFAULT_LIMIT,
    descending: bool = True,
    registry: Optional[Dict[str, RegistryRow]] = None,
) -> AggregateResult:
    """Uniform group-by/count aggregate over a registered dataset.

    Served straight from the already-ingested canonical tables (no extra
    file round-trips): group by one or more whitelisted columns and count
    rows, ordered by frequency. Same dataset slicing and identifier
    whitelisting as :func:`query`.
    """
    registry = registry or by_dataset_id()
    row = registry.get(dataset_id)
    if row is None:
        raise QueryError(f"unknown dataset {dataset_id!r}")
    if not group_by:
        raise QueryError("aggregate requires at least one group_by field")
    table = row.target_table
    colset = set(_columns(table))
    for g in group_by:
        if g not in colset:
            raise QueryError(f"unknown group_by field {g!r}")
    where_sql, args = _build_where(row, filters or {}, colset)
    lim = _clamp_int(limit, _DEFAULT_LIMIT, 1, _MAX_LIMIT)
    cols = ", ".join(group_by)
    order = "DESC" if descending else "ASC"
    sql = (f"SELECT {cols}, COUNT(*) AS count FROM {table} {where_sql} "
           f"GROUP BY {cols} ORDER BY count {order} LIMIT ?")
    rows = [dict(r) for r in store.fetchall(sql, (*args, lim))]
    return AggregateResult(dataset=dataset_id, group_by=list(group_by),
                           rows=rows, limit=lim)
