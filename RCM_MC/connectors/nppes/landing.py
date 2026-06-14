"""Raw landing zone.

Contract: *land raw to parquet, then normalize*, partitioned by entity type
or state, streamed not loaded whole. We honor the behavioral intent with a
pluggable writer:

  • If ``pyarrow`` is importable, raw rows land as real parquet, one file per
    partition (``entity_type=<n>/state=<ST>/part-*.parquet``).
  • Otherwise we fall back to gzip-compressed NDJSON with the *same*
    partition layout (``entity_type=<n>/state=<ST>/part-*.ndjson.gz``).

Either way the writer is streaming (rows are flushed per partition buffer),
partition-aware, and the downstream normalizer reads back through one
``read_partitions`` iterator that hides the format. The fallback keeps the
slice runnable with zero heavy dependencies; the parquet path is selected
automatically wherever the diligence extras are installed. The chosen
format is recorded in STATE/DECISIONS by the pipeline.
"""
from __future__ import annotations

import gzip
import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional

try:  # optional — selected automatically when present
    import pyarrow as pa  # type: ignore
    import pyarrow.parquet as pq  # type: ignore
    _HAVE_PYARROW = True
except Exception:  # noqa: BLE001
    _HAVE_PYARROW = False


def landing_format() -> str:
    return "parquet" if _HAVE_PYARROW else "ndjson.gz"


def _safe(part: object) -> str:
    s = str(part) if part not in (None, "") else "NA"
    return "".join(c if (c.isalnum() or c in "-_") else "_" for c in s)


def _row_to_dict(row: object) -> Dict:
    if isinstance(row, dict):
        return row
    if is_dataclass(row):
        return asdict(row)
    raise TypeError(f"cannot land row of type {type(row)!r}")


class RawLander:
    """Streaming, partitioned raw writer.

    Buffers rows by partition key and flushes per partition when the buffer
    crosses ``flush_rows`` (bounded memory regardless of input size).
    """

    def __init__(
        self,
        root: str,
        dataset: str,
        *,
        partition_keys: Iterable[str] = ("entity_type", "state"),
        flush_rows: int = 50_000,
    ) -> None:
        self.root = Path(root) / dataset
        self.partition_keys = tuple(partition_keys)
        self.flush_rows = max(1, int(flush_rows))
        self._buffers: Dict[str, List[Dict]] = {}
        self._part_index: Dict[str, int] = {}
        self.rows_written = 0
        self.root.mkdir(parents=True, exist_ok=True)

    def _partition_dir(self, d: Dict) -> Path:
        parts = []
        for k in self.partition_keys:
            parts.append(f"{k}={_safe(d.get(k))}")
        return self.root.joinpath(*parts)

    def write(self, row: object) -> None:
        d = _row_to_dict(row)
        # JSON-safe scalars only (raw landing is flat string-ish data)
        key = "/".join(f"{k}={_safe(d.get(k))}" for k in self.partition_keys)
        buf = self._buffers.setdefault(key, [])
        buf.append(d)
        self.rows_written += 1
        if len(buf) >= self.flush_rows:
            self._flush_partition(key)

    def write_all(self, rows: Iterable[object]) -> int:
        for r in rows:
            self.write(r)
        return self.rows_written

    def _flush_partition(self, key: str) -> None:
        buf = self._buffers.get(key)
        if not buf:
            return
        pdir = self.root.joinpath(*key.split("/"))
        pdir.mkdir(parents=True, exist_ok=True)
        idx = self._part_index.get(key, 0)
        self._part_index[key] = idx + 1
        if _HAVE_PYARROW:
            target = pdir / f"part-{idx:05d}.parquet"
            # Normalize each buffer to a common column set.
            cols: List[str] = []
            seen = set()
            for d in buf:
                for c in d.keys():
                    if c not in seen:
                        seen.add(c)
                        cols.append(c)
            table = pa.table(
                {c: [_jsonable(d.get(c)) for d in buf] for c in cols}
            )
            pq.write_table(table, target)
        else:
            target = pdir / f"part-{idx:05d}.ndjson.gz"
            with gzip.open(target, "wt", encoding="utf-8") as fh:
                for d in buf:
                    fh.write(json.dumps(_jsonable_dict(d), default=str))
                    fh.write("\n")
        self._buffers[key] = []

    def close(self) -> int:
        for key in list(self._buffers.keys()):
            self._flush_partition(key)
        return self.rows_written


def _jsonable(v):
    if isinstance(v, (list, dict, tuple)):
        return json.dumps(v, default=str)
    return v


def _jsonable_dict(d: Dict) -> Dict:
    return {k: (v if not isinstance(v, (list, dict, tuple)) else v) for k, v in d.items()}


def read_partitions(root: str, dataset: str) -> Iterator[Dict]:
    """Read back a landed dataset, hiding the storage format. Streams
    rows one at a time across all partitions."""
    base = Path(root) / dataset
    if not base.is_dir():
        return
    if _HAVE_PYARROW:
        for f in sorted(base.rglob("*.parquet")):
            # Read the file directly (ParquetFile, not a dataset) so pyarrow
            # does not re-infer hive partition columns from the path and
            # collide with the same columns stored inside the file.
            table = pq.ParquetFile(str(f)).read()
            for batch in table.to_pylist():
                yield batch
    for f in sorted(base.rglob("*.ndjson.gz")):
        with gzip.open(f, "rt", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    yield json.loads(line)


def partition_count(root: str, dataset: str) -> int:
    base = Path(root) / dataset
    if not base.is_dir():
        return 0
    n = 0
    for _ in base.rglob("part-*.*"):
        n += 1
    return n
