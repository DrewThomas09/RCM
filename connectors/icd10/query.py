"""The ``/v1/query`` engine: uniform filter / select / sort / paginate.

The API contract: the caller gets one uniform query surface and never
sees the NLM API's native paging — that was absorbed at ingest time
(:mod:`connectors.icd10.connector`). Here the data is already in the
canonical ``dim_icd10_code`` table, so a query is plain parameterised SQL
over a registry-resolved table + ``source_endpoint`` slice.

Safety: column identifiers are validated against the target table's
known column set (a whitelist from :mod:`tables`) — we never interpolate
a caller-supplied identifier. All values are bound parameters. Limit is
clamped. This mirrors the RCM-MC rules (parameterised SQL only,
``_clamp_int`` every integer param).

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
from .tables import TABLES, Icd10Store

_OPS = {
    "eq": "=", "ne": "!=", "gt": ">", "gte": ">=", "lt": "<", "lte": "<=",
    "like": "LIKE", "in": "IN",
    # Null/range operators (handled specially in _build_where).
    "isnull": "", "notnull": "", "between": "",
}
_DEFAULT_LIMIT = 50
_MAX_LIMIT = 1000
# SQL aggregate functions reachable through the uniform ``metrics`` grammar
# (``"sum:field"``). A fixed whitelist: the interpolated SQL token always
# comes from this dict, never from caller input.
_METRIC_FUNCS = {"sum": "SUM", "avg": "AVG", "min": "MIN", "max": "MAX"}


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


def _numeric(value: Any) -> Optional[float]:
    """The float form of *value* when it is numeric, else ``None``.

    Canonical columns are all TEXT, so range operators need an explicit
    numeric compare (``CAST``) when the caller's value is a number —
    lexicographic TEXT compare silently mis-ranks 9 vs 10. Non-numeric
    values (ISO dates, codes) keep the TEXT compare.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _columns(table: str) -> Tuple[str, ...]:
    return TABLES[table].columns


def _split_field_op(key: str) -> Tuple[str, str]:
    if "__" in key:
        field_name, op = key.rsplit("__", 1)
        if op in _OPS:
            return field_name, op
    return key, "eq"


def query(
    store: Icd10Store,
    dataset_id: str,
    *,
    filters: Optional[Dict[str, Any]] = None,
    select: Optional[List[str]] = None,
    sort: Optional[List[str]] = None,
    limit: Any = _DEFAULT_LIMIT,
    offset: Any = 0,
    registry: Optional[Dict[str, RegistryRow]] = None,
) -> QueryResult:
    """Run a uniform query against a registered ICD-10 dataset."""
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
    # Always pin to this dataset's endpoint slice (shared physical table).
    if row.source_filter and "source_endpoint" in colset:
        clauses.append("source_endpoint = ?")
        args.append(row.source_filter)
    for key, value in filters.items():
        field_name, op = _split_field_op(key)
        if field_name not in colset:
            raise QueryError(f"unknown filter field {field_name!r}")
        sql_op = _OPS[op]
        if op == "isnull":
            # Null OR empty-string — TEXT columns store "" for absent values.
            clauses.append(f"({field_name} IS NULL OR {field_name} = '')")
        elif op == "notnull":
            clauses.append(f"({field_name} IS NOT NULL AND {field_name} <> '')")
        elif op == "between":
            parts = value if isinstance(value, (list, tuple)) else str(value).split(",")
            if len(parts) != 2:
                raise QueryError(f"between expects two values, got {value!r}")
            nums = [_numeric(p) for p in parts]
            if all(n is not None for n in nums):
                # Numeric bounds → numeric compare over the TEXT storage.
                clauses.append(f"CAST({field_name} AS REAL) BETWEEN ? AND ?")
                args.extend(nums)
            else:
                clauses.append(f"{field_name} BETWEEN ? AND ?")
                args.extend(str(p) for p in parts)
        elif op == "in":
            # HTTP/CLI callers can only send ONE string per key, so a
            # comma-joined list is the documented grammar (mirroring
            # ``between``); a Python-API list passes through unchanged.
            vals = (value if isinstance(value, (list, tuple))
                    else str(value).split(","))
            if not vals:
                clauses.append("0 = 1")  # empty IN matches nothing
                continue
            placeholders = ", ".join("?" for _ in vals)
            clauses.append(f"{field_name} IN ({placeholders})")
            args.extend(str(v) for v in vals)
        else:
            num = _numeric(value) if op in ("gt", "gte", "lt", "lte") else None
            if num is not None:
                # Numeric bound → numeric compare (see _numeric).
                clauses.append(f"CAST({field_name} AS REAL) {sql_op} ?")
                args.append(num)
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
    rows: List[Dict[str, Any]]      # each: {group cols..., "count": n, metrics...}
    limit: int
    metrics: Optional[List[str]] = None   # canonical "func:field" specs, if any

    def as_dict(self) -> Dict[str, Any]:
        return {
            "dataset": self.dataset,
            "group_by": self.group_by,
            "limit": self.limit,
            "metrics": list(self.metrics or []),
            "count": len(self.rows),
            "rows": self.rows,
        }


def _build_metrics(metrics: Optional[List[Any]], group_by: List[str],
                   colset: set) -> Tuple[str, List[str]]:
    """SQL select fragments + canonical spec names for ``metrics``.

    Each entry is ``"func:field"`` (the HTTP/CLI form, e.g. ``sum:tot_clms``)
    or a ``(func, field)`` pair. The function name must be in the fixed
    :data:`_METRIC_FUNCS` whitelist and the field in the table's column
    set, so every interpolated identifier is validated — never raw caller
    input. Values are ``CAST`` to REAL over the all-TEXT storage (the same
    trade-off as the numeric range operators: non-numeric junk reads as
    0.0). Result columns are aliased ``{func}_{field}``.
    """
    frags: List[str] = []
    names: List[str] = []
    for m in metrics or []:
        if isinstance(m, (list, tuple)) and len(m) == 2:
            func, col = str(m[0]).strip(), str(m[1]).strip()
        else:
            func, _, col = str(m).partition(":")
            func, col = func.strip(), col.strip()
        func = func.lower()
        if func not in _METRIC_FUNCS:
            raise QueryError(
                f"unknown metric function {func!r} (use sum/avg/min/max)")
        if col not in colset:
            raise QueryError(f"unknown metric field {col!r}")
        alias = f"{func}_{col}"
        if alias in group_by or alias == "count":
            raise QueryError(
                f"metric alias {alias!r} collides with a result column")
        frags.append(f"{_METRIC_FUNCS[func]}(CAST({col} AS REAL)) AS {alias}")
        names.append(f"{func}:{col}")
    return ", ".join(frags), names


def aggregate(
    store: Icd10Store,
    dataset_id: str,
    *,
    group_by: List[str],
    filters: Optional[Dict[str, Any]] = None,
    limit: Any = _DEFAULT_LIMIT,
    descending: bool = True,
    metrics: Optional[List[Any]] = None,
    registry: Optional[Dict[str, RegistryRow]] = None,
) -> AggregateResult:
    """Uniform group-by/count aggregate over a registered dataset.

    A cheap market-map path served from the already-ingested canonical
    table (no NLM round-trips): group by one or more whitelisted columns
    and count rows, ordered by frequency. Same dataset slicing and
    identifier whitelisting as :func:`query`.
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
    metric_sql, metric_names = _build_metrics(metrics, list(group_by), colset)
    lim = _clamp_int(limit, _DEFAULT_LIMIT, 1, _MAX_LIMIT)
    cols = ", ".join(group_by)
    order = "DESC" if descending else "ASC"
    select_cols = f"{cols}, COUNT(*) AS count"
    if metric_sql:
        select_cols += f", {metric_sql}"
    sql = (f"SELECT {select_cols} FROM {table} {where_sql} "
           f"GROUP BY {cols} ORDER BY count {order} LIMIT ?")
    rows = [dict(r) for r in store.fetchall(sql, (*args, lim))]
    return AggregateResult(dataset=dataset_id, group_by=list(group_by),
                           rows=rows, limit=lim, metrics=metric_names)
