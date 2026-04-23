"""Warehouse adapter abstraction.

Every DB interaction in :mod:`rcm_mc_diligence` goes through a
:class:`WarehouseAdapter`. DuckDB is the only working implementation
today; Snowflake and Postgres are real stubs that raise
``NotImplementedError`` on use and point back at this module's interface
contract.

The adapter is intentionally thin — just enough surface for the
ingestion pipeline + DQ rules to function, plus a handful of hooks the
dbt invocation needs (``profile_config`` for profile rendering,
``close`` for teardown). Heavier analytical SQL lives in dbt models,
not here; Python is the caller, dbt is the transformer.

We keep the contract small on purpose. If a Phase 0.B analysis needs
richer surface, add the method here, implement it in DuckDB first, and
update the two stubs so the interface stays visible. Do not grow the
surface silently through subclass helpers.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


# ── Types ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class TableRef:
    """A fully-qualified table reference.

    ``schema`` may be None for adapters that don't use schemas at a
    query level (DuckDB is permissive; Snowflake/Postgres are not).
    """
    name: str
    schema: Optional[str] = None

    def qualified(self) -> str:
        if self.schema:
            return f'"{self.schema}"."{self.name}"'
        return f'"{self.name}"'


@dataclass
class LoadResult:
    """Summary of a single file → table load."""
    table: str
    rows_loaded: int
    columns: Tuple[str, ...]
    source_path: str


# ── Abstract base ────────────────────────────────────────────────────

class WarehouseAdapter(abc.ABC):
    """Minimal warehouse surface shared by every backend.

    Why an ABC rather than duck typing: the dbt invocation builds a
    profiles.yml whose shape depends on the target backend. Without a
    formal contract, the profile-rendering code would grow a per-backend
    ``isinstance`` ladder. The ABC gives us :meth:`profile_config`
    instead — each adapter owns its dbt profile shape.
    """

    backend_name: str = "abstract"

    @abc.abstractmethod
    def connect(self) -> Any:  # pragma: no cover - concrete adapters override
        """Return a driver-native connection. DuckDB returns a
        ``duckdb.DuckDBPyConnection``; other backends will return their
        native equivalents.
        """

    @abc.abstractmethod
    def close(self) -> None:  # pragma: no cover
        """Release the connection. Idempotent — safe to call twice."""

    @abc.abstractmethod
    def execute(self, sql: str, params: Optional[Sequence[Any]] = None) -> None:
        """Execute a single statement with *parameterised* arguments.

        No f-string SQL. If the caller needs dynamic identifiers (table
        names, schema names) they must quote them via the adapter's own
        :meth:`quote_identifier` — still not a value substitution, but
        centralised so every backend quotes identically.
        """

    @abc.abstractmethod
    def fetchall(
        self, sql: str, params: Optional[Sequence[Any]] = None
    ) -> List[Tuple[Any, ...]]:
        """Run a SELECT and return all rows. Same parameterised-SQL
        discipline as :meth:`execute`."""

    @abc.abstractmethod
    def table_exists(self, ref: TableRef) -> bool:
        """True if the table exists in the current catalog."""

    @abc.abstractmethod
    def drop_schema(self, schema: str, cascade: bool = True) -> None:
        """Drop a schema if it exists. Idempotent."""

    @abc.abstractmethod
    def create_schema(self, schema: str) -> None:
        """Create a schema if it doesn't exist."""

    @abc.abstractmethod
    def load_arrow(
        self, table: TableRef, arrow_table: Any, *, replace: bool = True
    ) -> LoadResult:
        """Materialise a pyarrow ``Table`` into the warehouse. Replaces
        the target table when ``replace=True`` (the default).
        """

    @abc.abstractmethod
    def row_count(self, ref: TableRef) -> int:
        """Count rows in a table. Raises :class:`LookupError` if
        missing."""

    @abc.abstractmethod
    def columns(self, ref: TableRef) -> List[str]:
        """Return the table's column names in declaration order."""

    @abc.abstractmethod
    def null_rate(self, ref: TableRef, column: str) -> float:
        """Fraction of NULLs in ``column`` in 0..1 inclusive. Returns
        0.0 on empty tables (no rows = no nulls to report)."""

    @abc.abstractmethod
    def profile_config(self, run_db_path: Path) -> Dict[str, Any]:
        """Return the dbt profile block (the ``outputs.dev`` map) that
        targets ``run_db_path`` for this adapter.

        The :class:`~rcm_mc_diligence.ingest.connector.DbtConnector`
        wraps this in a full ``profiles.yml`` with profile + target
        names. The per-backend differences live here so the connector
        is backend-agnostic.
        """

    def quote_identifier(self, ident: str) -> str:
        """Safe identifier quoting. Override if a backend uses
        different escape rules (Snowflake prefers ``"`` same as DuckDB;
        Postgres identical). Default doubles embedded ``"`` and wraps
        in double quotes — ANSI standard.
        """
        return '"' + ident.replace('"', '""') + '"'


# ── DuckDB implementation ────────────────────────────────────────────

_NOT_IMPL_HINT = (
    "See rcm_mc_diligence.ingest.warehouse.WarehouseAdapter for the "
    "contract. DuckDBAdapter is the Phase 0.A reference implementation; "
    "Snowflake and Postgres ship in Phase 0.B+. Do not subclass around "
    "the abstract methods — implement them."
)


class DuckDBAdapter(WarehouseAdapter):
    """DuckDB implementation — the Phase 0.A reference.

    Connection lifecycle: one connection per adapter instance. The
    pipeline opens an adapter per run, uses it, closes it. Because dbt
    wants to open its own connection via the profile, the adapter
    closes its Python-side connection before dbt runs and reopens
    afterward for DQ rule queries. That's managed by the pipeline, not
    here.
    """

    backend_name = "duckdb"

    def __init__(self, db_path: Path | str):
        self._db_path = Path(db_path)
        self._conn: Optional[Any] = None

    # ------- connection ---------------------------------------------

    def connect(self) -> Any:
        import duckdb
        if self._conn is None:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = duckdb.connect(str(self._db_path))
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    @property
    def db_path(self) -> Path:
        return self._db_path

    # ------- core SQL -----------------------------------------------

    def execute(self, sql: str, params: Optional[Sequence[Any]] = None) -> None:
        conn = self.connect()
        if params is None:
            conn.execute(sql)
        else:
            conn.execute(sql, list(params))

    def fetchall(
        self, sql: str, params: Optional[Sequence[Any]] = None
    ) -> List[Tuple[Any, ...]]:
        conn = self.connect()
        if params is None:
            cur = conn.execute(sql)
        else:
            cur = conn.execute(sql, list(params))
        return [tuple(r) for r in cur.fetchall()]

    def table_exists(self, ref: TableRef) -> bool:
        if ref.schema:
            rows = self.fetchall(
                "select count(*) from information_schema.tables "
                "where table_schema = ? and table_name = ?",
                [ref.schema, ref.name],
            )
        else:
            rows = self.fetchall(
                "select count(*) from information_schema.tables "
                "where table_name = ?",
                [ref.name],
            )
        return bool(rows and rows[0][0])

    def drop_schema(self, schema: str, cascade: bool = True) -> None:
        # Parameterised SQL cannot template identifiers — quote via our
        # own escaper so we still reject injection at the call site.
        qs = self.quote_identifier(schema)
        suffix = " cascade" if cascade else ""
        self.execute(f"drop schema if exists {qs}{suffix}")

    def create_schema(self, schema: str) -> None:
        qs = self.quote_identifier(schema)
        self.execute(f"create schema if not exists {qs}")

    def load_arrow(
        self, table: TableRef, arrow_table: Any, *, replace: bool = True
    ) -> LoadResult:
        conn = self.connect()
        qt = table.qualified()
        # Register the arrow table under a temporary alias, then CTAS.
        # DuckDB's register API is safe — the arrow object is bound by
        # name, not substituted into SQL text.
        alias = f"__arrow_{abs(hash(table.qualified())) % (10**9)}"
        conn.register(alias, arrow_table)
        try:
            if table.schema:
                self.create_schema(table.schema)
            if replace:
                self.execute(f"drop table if exists {qt}")
            self.execute(f"create table {qt} as select * from {alias}")
        finally:
            conn.unregister(alias)
        return LoadResult(
            table=table.qualified(),
            rows_loaded=self.row_count(table),
            columns=tuple(self.columns(table)),
            source_path="<in-memory arrow>",
        )

    def row_count(self, ref: TableRef) -> int:
        if not self.table_exists(ref):
            raise LookupError(f"table not found: {ref.qualified()}")
        rows = self.fetchall(f"select count(*) from {ref.qualified()}")
        return int(rows[0][0])

    def columns(self, ref: TableRef) -> List[str]:
        if ref.schema:
            rows = self.fetchall(
                "select column_name from information_schema.columns "
                "where table_schema = ? and table_name = ? "
                "order by ordinal_position",
                [ref.schema, ref.name],
            )
        else:
            rows = self.fetchall(
                "select column_name from information_schema.columns "
                "where table_name = ? order by ordinal_position",
                [ref.name],
            )
        return [r[0] for r in rows]

    def null_rate(self, ref: TableRef, column: str) -> float:
        total = self.row_count(ref)
        if total == 0:
            return 0.0
        qc = self.quote_identifier(column)
        rows = self.fetchall(
            f"select sum(case when {qc} is null then 1 else 0 end) "
            f"from {ref.qualified()}"
        )
        nulls = int(rows[0][0] or 0)
        return nulls / total

    # ------- dbt profile --------------------------------------------

    def profile_config(self, run_db_path: Path) -> Dict[str, Any]:
        return {
            "type": "duckdb",
            "path": str(run_db_path),
            "threads": 1,
        }


# ── Stubs for Phase 0.B+ ─────────────────────────────────────────────

class SnowflakeAdapter(WarehouseAdapter):
    """Scaffolded — Phase 0.B. Every method raises
    :class:`NotImplementedError` pointing at the ABC contract.

    Kept as a real class (not a TODO comment) so the warehouse selector
    in the CLI has a concrete symbol to import, and so the interface
    rigidity of the adapter surfaces at construction time instead of
    leaking downstream.
    """

    backend_name = "snowflake"

    def __init__(self, **_kwargs: Any):
        raise NotImplementedError("SnowflakeAdapter — Phase 0.B. " + _NOT_IMPL_HINT)

    # All abstract methods delegate to a single raise for consistency.
    # They are unreachable because __init__ raises first, but we keep
    # them so abc's registration accepts the class as concrete and so a
    # future contributor has the exact slots to fill.
    def connect(self) -> Any: raise NotImplementedError(_NOT_IMPL_HINT)
    def close(self) -> None: raise NotImplementedError(_NOT_IMPL_HINT)
    def execute(self, sql: str, params: Optional[Sequence[Any]] = None) -> None:
        raise NotImplementedError(_NOT_IMPL_HINT)
    def fetchall(self, sql: str, params: Optional[Sequence[Any]] = None) -> List[Tuple[Any, ...]]:
        raise NotImplementedError(_NOT_IMPL_HINT)
    def table_exists(self, ref: TableRef) -> bool: raise NotImplementedError(_NOT_IMPL_HINT)
    def drop_schema(self, schema: str, cascade: bool = True) -> None:
        raise NotImplementedError(_NOT_IMPL_HINT)
    def create_schema(self, schema: str) -> None: raise NotImplementedError(_NOT_IMPL_HINT)
    def load_arrow(self, table: TableRef, arrow_table: Any, *, replace: bool = True) -> LoadResult:
        raise NotImplementedError(_NOT_IMPL_HINT)
    def row_count(self, ref: TableRef) -> int: raise NotImplementedError(_NOT_IMPL_HINT)
    def columns(self, ref: TableRef) -> List[str]: raise NotImplementedError(_NOT_IMPL_HINT)
    def null_rate(self, ref: TableRef, column: str) -> float:
        raise NotImplementedError(_NOT_IMPL_HINT)
    def profile_config(self, run_db_path: Path) -> Dict[str, Any]:
        raise NotImplementedError(_NOT_IMPL_HINT)


class PostgresAdapter(WarehouseAdapter):
    """Scaffolded — Phase 0.B. See :class:`SnowflakeAdapter`."""

    backend_name = "postgres"

    def __init__(self, **_kwargs: Any):
        raise NotImplementedError("PostgresAdapter — Phase 0.B. " + _NOT_IMPL_HINT)

    def connect(self) -> Any: raise NotImplementedError(_NOT_IMPL_HINT)
    def close(self) -> None: raise NotImplementedError(_NOT_IMPL_HINT)
    def execute(self, sql: str, params: Optional[Sequence[Any]] = None) -> None:
        raise NotImplementedError(_NOT_IMPL_HINT)
    def fetchall(self, sql: str, params: Optional[Sequence[Any]] = None) -> List[Tuple[Any, ...]]:
        raise NotImplementedError(_NOT_IMPL_HINT)
    def table_exists(self, ref: TableRef) -> bool: raise NotImplementedError(_NOT_IMPL_HINT)
    def drop_schema(self, schema: str, cascade: bool = True) -> None:
        raise NotImplementedError(_NOT_IMPL_HINT)
    def create_schema(self, schema: str) -> None: raise NotImplementedError(_NOT_IMPL_HINT)
    def load_arrow(self, table: TableRef, arrow_table: Any, *, replace: bool = True) -> LoadResult:
        raise NotImplementedError(_NOT_IMPL_HINT)
    def row_count(self, ref: TableRef) -> int: raise NotImplementedError(_NOT_IMPL_HINT)
    def columns(self, ref: TableRef) -> List[str]: raise NotImplementedError(_NOT_IMPL_HINT)
    def null_rate(self, ref: TableRef, column: str) -> float:
        raise NotImplementedError(_NOT_IMPL_HINT)
    def profile_config(self, run_db_path: Path) -> Dict[str, Any]:
        raise NotImplementedError(_NOT_IMPL_HINT)


def warehouse_from_name(name: str, **kwargs: Any) -> WarehouseAdapter:
    """Factory used by the CLI — keeps the name→class mapping in one
    place so the CLI doesn't import concrete classes directly. Raises
    :class:`ValueError` on unknown names rather than falling back to a
    default, since a silent default would mask typos in partner
    scripts.
    """
    name_lc = (name or "").strip().lower()
    if name_lc == "duckdb":
        return DuckDBAdapter(**kwargs)
    if name_lc == "snowflake":
        return SnowflakeAdapter(**kwargs)
    if name_lc in ("postgres", "postgresql"):
        return PostgresAdapter(**kwargs)
    raise ValueError(
        f"unknown warehouse adapter: {name!r}. "
        f"Supported: duckdb, snowflake (stub), postgres (stub)."
    )
