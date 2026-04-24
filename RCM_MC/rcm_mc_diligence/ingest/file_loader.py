"""Raw-file loader.

Reads a directory of CSV/Parquet files into the warehouse ``raw_data``
schema. One table per file, table name derived from the filename stem.
Schema is inferred by pyarrow; callers may pass a ``schema_overrides``
mapping to force specific dtypes where inference would misfire (e.g.
a ZIP code that starts with 0 → forced ``string``).

Encoding detection: UTF-8 first, fall back to latin-1 with a warning
recorded in the resulting :class:`FileLoadSummary`. A malformed file
does not abort the pipeline — it's recorded with ``status="FAILED"``
and reported in the DQ output. The calling pipeline decides whether to
proceed.

We never ``pd.read_csv`` with ``inferred = True`` — pyarrow's CSV
reader is strict about types and preserves integer/timestamp
distinctions that pandas loses on all-null columns.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from .warehouse import LoadResult, TableRef, WarehouseAdapter


# ── Constants ────────────────────────────────────────────────────────

RAW_SCHEMA = "raw_data"
SUPPORTED_SUFFIXES = {".csv", ".tsv", ".parquet", ".pq"}


# ── Result dataclasses ───────────────────────────────────────────────

@dataclass
class FileLoadSummary:
    """Per-file outcome. Flows into ``DQReport.source_inventory``."""
    path: str
    table: str
    format: str
    size_bytes: int
    rows_loaded: int
    columns_detected: Tuple[str, ...]
    columns_dropped: Tuple[str, ...]
    encoding: str
    status: str  # "OK" | "WARN" | "FAILED"
    note: str = ""


@dataclass
class LoaderResult:
    """Aggregated result for one ``load_directory`` call."""
    files: List[FileLoadSummary] = field(default_factory=list)
    tables: Dict[str, TableRef] = field(default_factory=dict)

    def ok_count(self) -> int:
        return sum(1 for f in self.files if f.status == "OK")

    def failed_count(self) -> int:
        return sum(1 for f in self.files if f.status == "FAILED")


# ── Public API ───────────────────────────────────────────────────────

def load_directory(
    adapter: WarehouseAdapter,
    directory: Path | str,
    *,
    schema_overrides: Optional[Mapping[str, Mapping[str, str]]] = None,
    schema: str = RAW_SCHEMA,
) -> LoaderResult:
    """Load every supported file in ``directory`` into ``schema``.

    Files named with a common prefix (``medical_claims_*.csv``) are
    merged into a single table by prefix — so a multi-clinic fixture
    with three medical_claims files produces one merged table. The
    merge union-by-name preserves the superset of columns; rows from a
    file that lacks a column get NULL for that column.

    Returns a :class:`LoaderResult` whose ``files`` list is in
    deterministic filesystem-sorted order, so idempotency hashes are
    stable.
    """
    directory_p = Path(directory)
    if not directory_p.is_dir():
        raise FileNotFoundError(f"not a directory: {directory_p}")

    adapter.create_schema(schema)

    # Group files by "logical table". Filenames like
    # medical_claims_clinic_a.csv, medical_claims_clinic_b.csv,
    # medical_claims_clinic_c.csv all target the "medical_claims"
    # table. A trailing _<clinic> / _part1 suffix is stripped.
    grouped: Dict[str, List[Path]] = {}
    for p in sorted(directory_p.rglob("*")):
        if not p.is_file():
            continue
        if p.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        table_name = _logical_table_name(p)
        grouped.setdefault(table_name, []).append(p)

    result = LoaderResult()
    overrides = schema_overrides or {}

    for table_name, paths in grouped.items():
        table_overrides = overrides.get(table_name, {})
        try:
            arrow_table, per_file = _merge_files(paths, table_overrides)
        except Exception as exc:
            # A fatal merge error — record each file as failed and move on.
            for p in paths:
                result.files.append(FileLoadSummary(
                    path=str(p), table=table_name, format=p.suffix.lstrip("."),
                    size_bytes=p.stat().st_size, rows_loaded=0,
                    columns_detected=(), columns_dropped=(), encoding="unknown",
                    status="FAILED", note=f"merge failed: {exc}",
                ))
            continue

        ref = TableRef(name=table_name, schema=schema)
        adapter.load_arrow(ref, arrow_table, replace=True)
        result.tables[table_name] = ref

        for entry in per_file:
            result.files.append(entry)

    return result


# ── Internals ────────────────────────────────────────────────────────

def _logical_table_name(p: Path) -> str:
    """Derive a table name from a filename.

    - ``medical_claims_clinic_a.csv``  → ``medical_claims``
    - ``medical_claims.parquet``       → ``medical_claims``
    - ``eligibility_2024Q4.tsv``       → ``eligibility``

    Heuristic: strip the trailing ``_<token>`` if that token is the
    clinic or partition slug. We detect that by looking for the last
    underscore and checking whether the stripped stem is still a
    meaningful name (i.e. not empty). This is the messiest corner of
    the loader — tested against all five fixtures in
    ``tests/test_diligence_file_loader.py``.
    """
    stem = p.stem.lower()
    # Common partition suffixes and clinic slugs.
    suffix_markers = ("_clinic_", "_part", "_partition_", "_shard_", "_q1", "_q2",
                      "_q3", "_q4", "_2024", "_2025", "_2026")
    for m in suffix_markers:
        idx = stem.rfind(m)
        if idx > 0:
            stem = stem[:idx]
            break
    # Also strip a trailing _a/_b/_c or _1/_2 if present.
    if "_" in stem:
        head, tail = stem.rsplit("_", 1)
        if tail.isdigit() or (len(tail) == 1 and tail.isalpha()):
            stem = head
    return stem


def _merge_files(
    paths: Sequence[Path],
    column_overrides: Mapping[str, str],
) -> Tuple[Any, List[FileLoadSummary]]:
    """Read each file to an arrow Table, union schemas, concatenate.

    Returns (merged_arrow_table, list of per-file summaries).
    """
    import pyarrow as pa

    tables: List[Any] = []
    summaries: List[FileLoadSummary] = []
    for p in paths:
        summary, tbl = _read_one(p, column_overrides)
        summaries.append(summary)
        if tbl is not None:
            tables.append(tbl)

    if not tables:
        # All files failed. Produce an empty table so the schema still
        # materialises — downstream code can distinguish "empty" from
        # "missing" without branching.
        return pa.table({}), summaries

    # Union by column name: pyarrow requires identical schemas for
    # concat; promote_options='default' handles name alignment.
    try:
        merged = pa.concat_tables(tables, promote_options="default")
    except (pa.lib.ArrowInvalid, pa.lib.ArrowTypeError):
        # Heterogeneous types across clinics (the multi-EHR pattern)
        # produce e.g. `date32` for one file and `string` for another
        # on the same column name. We coerce every column to string
        # and let the connector's `try_cast(... as date)` resolve the
        # types downstream. Rationale: preserving the lossless text is
        # always safe; a misinferred date32 is not.
        normalised = [_stringify_all_columns(t) for t in tables]
        merged = pa.concat_tables(normalised, promote_options="default")
    return merged, summaries


def _stringify_all_columns(tbl: Any) -> Any:
    """Cast every column in ``tbl`` to ``pa.string()``. Used as the
    heterogeneous-merge fallback; the connector SQL re-types via
    ``try_cast``. Preserves NULLs."""
    import pyarrow as pa
    import pyarrow.compute as pc

    new_cols = []
    for name in tbl.column_names:
        col = tbl.column(name)
        if pa.types.is_string(col.type):
            new_cols.append(col)
        else:
            new_cols.append(pc.cast(col, pa.string()))
    return pa.table({n: c for n, c in zip(tbl.column_names, new_cols)})


def _read_one(
    path: Path, column_overrides: Mapping[str, str]
) -> Tuple[FileLoadSummary, Optional[Any]]:
    """Read a single file. Returns a summary + pyarrow Table (or
    ``None`` on failure)."""
    import pyarrow as pa
    import pyarrow.csv as pacsv
    import pyarrow.parquet as papq

    size = path.stat().st_size
    suffix = path.suffix.lower()

    if suffix in (".parquet", ".pq"):
        try:
            tbl = papq.read_table(path)
            summary = FileLoadSummary(
                path=str(path), table=_logical_table_name(path), format="parquet",
                size_bytes=size, rows_loaded=tbl.num_rows,
                columns_detected=tuple(tbl.column_names), columns_dropped=(),
                encoding="binary", status="OK",
            )
            return summary, _apply_overrides(tbl, column_overrides)
        except Exception as exc:
            return FileLoadSummary(
                path=str(path), table=_logical_table_name(path), format="parquet",
                size_bytes=size, rows_loaded=0, columns_detected=(),
                columns_dropped=(), encoding="binary", status="FAILED",
                note=f"parquet read failed: {exc}",
            ), None

    # CSV / TSV path.
    delim = "\t" if suffix == ".tsv" else ","
    encoding, header, body_bytes = _detect_encoding(path)
    if encoding is None:
        return FileLoadSummary(
            path=str(path), table=_logical_table_name(path), format=suffix.lstrip("."),
            size_bytes=size, rows_loaded=0, columns_detected=(),
            columns_dropped=(), encoding="unknown", status="FAILED",
            note="could not decode file as utf-8 or latin-1",
        ), None

    try:
        tbl = pacsv.read_csv(
            io.BytesIO(body_bytes),
            read_options=pacsv.ReadOptions(encoding=encoding),
            parse_options=pacsv.ParseOptions(delimiter=delim),
            convert_options=pacsv.ConvertOptions(
                strings_can_be_null=True,
                null_values=["", "NA", "N/A", "null", "NULL", "None"],
            ),
        )
    except Exception as exc:
        return FileLoadSummary(
            path=str(path), table=_logical_table_name(path), format=suffix.lstrip("."),
            size_bytes=size, rows_loaded=0, columns_detected=(),
            columns_dropped=(), encoding=encoding, status="FAILED",
            note=f"csv read failed: {exc}",
        ), None

    summary = FileLoadSummary(
        path=str(path), table=_logical_table_name(path), format=suffix.lstrip("."),
        size_bytes=size, rows_loaded=tbl.num_rows,
        columns_detected=tuple(tbl.column_names), columns_dropped=(),
        encoding=encoding,
        status="OK" if encoding == "utf-8" else "WARN",
        note="" if encoding == "utf-8" else f"fell back to {encoding}",
    )
    return summary, _apply_overrides(tbl, column_overrides)


def _detect_encoding(path: Path) -> Tuple[Optional[str], Optional[str], Optional[bytes]]:
    """Try utf-8, then latin-1. Return (encoding, first_line, body_bytes)."""
    body_bytes = path.read_bytes()
    for enc in ("utf-8", "latin-1"):
        try:
            decoded = body_bytes.decode(enc)
            header = decoded.splitlines()[0] if decoded else ""
            return enc, header, body_bytes
        except UnicodeDecodeError:
            continue
    return None, None, None


def _apply_overrides(tbl: Any, column_overrides: Mapping[str, str]) -> Any:
    """Cast columns named in ``column_overrides`` to the requested dtype.

    ``column_overrides`` is ``{column_name: arrow_type_string}`` e.g.
    ``{"zip_code": "string"}``. Unknown columns are ignored (no error)
    because the override map may describe a superset — the loader is
    deliberately permissive here.
    """
    import pyarrow as pa
    if not column_overrides:
        return tbl
    for col, dtype_str in column_overrides.items():
        if col not in tbl.column_names:
            continue
        try:
            target = _arrow_type_from_string(dtype_str)
            tbl = tbl.set_column(
                tbl.column_names.index(col), col,
                tbl.column(col).cast(target, safe=False),
            )
        except Exception:
            # Silent fallthrough: the rule is "best-effort overrides";
            # a failed cast leaves the inferred type in place. The DQ
            # rules will flag mismatches downstream.
            continue
    return tbl


def _arrow_type_from_string(s: str) -> Any:
    import pyarrow as pa
    table = {
        "string": pa.string(), "varchar": pa.string(), "text": pa.string(),
        "int": pa.int64(), "integer": pa.int64(), "int64": pa.int64(),
        "int32": pa.int32(), "float": pa.float64(), "double": pa.float64(),
        "date": pa.date32(), "timestamp": pa.timestamp("us"),
        "boolean": pa.bool_(), "bool": pa.bool_(),
    }
    key = s.strip().lower()
    if key not in table:
        raise ValueError(f"unsupported override dtype: {s!r}")
    return table[key]
