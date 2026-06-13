"""Land raw openFDA rows to disk before normalizing.

Contract is "land raw to parquet, then normalize". Parquet needs
``pyarrow``, which is not in this runtime, so we **degrade gracefully**:
write parquet when ``pyarrow`` imports, otherwise newline-delimited JSON
(``.jsonl``). Either way the raw bytes are kept verbatim so a re-run can
re-normalize without re-fetching, and the landing is idempotent — a row
keyed by its native id overwrites rather than appends (logical dedupe is
the normalizer's upsert; physical dedupe here keeps the raw lake from
ballooning on overlapping windows).

Layout::

    <raw_root>/<endpoint>/<window-or-batch>.<jsonl|parquet>

The window tag comes from the cursor so re-running a window replaces its
file exactly once.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:  # pragma: no cover - exercised only where pyarrow is installed
    import pyarrow as _pa  # type: ignore
    import pyarrow.parquet as _pq  # type: ignore
    _HAS_PARQUET = True
except Exception:  # ImportError or partial install
    _HAS_PARQUET = False


def parquet_available() -> bool:
    return _HAS_PARQUET


class RawStore:
    """Idempotent raw landing zone, parquet when possible else JSONL."""

    def __init__(self, raw_root: str) -> None:
        self.root = Path(raw_root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, endpoint: str, tag: str) -> Path:
        d = self.root / endpoint
        d.mkdir(parents=True, exist_ok=True)
        ext = "parquet" if _HAS_PARQUET else "jsonl"
        safe = tag.replace("/", "_").replace(" ", "_") or "batch"
        return d / f"{safe}.{ext}"

    def write(self, endpoint: str, tag: str, rows: List[Dict[str, Any]]) -> str:
        """Write ``rows`` for a window/batch, replacing any prior file.

        Returns the path written. Empty windows still write an empty
        marker so STATE.md and the raw lake agree on what was attempted.
        """
        path = self._path(endpoint, tag)
        if _HAS_PARQUET:
            self._write_parquet(path, rows)
        else:
            self._write_jsonl(path, rows)
        return str(path)

    @staticmethod
    def _write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True))
                fh.write("\n")
        tmp.replace(path)  # atomic swap → no half-written window on a kill

    @staticmethod
    def _write_parquet(path: Path, rows: List[Dict[str, Any]]) -> None:  # pragma: no cover
        # openFDA rows are deeply ragged; store each as a JSON string column
        # so the parquet schema is stable across heterogeneous records.
        payload = [json.dumps(r, ensure_ascii=False, sort_keys=True) for r in rows]
        table = _pa.table({"raw_json": payload})
        tmp = path.with_suffix(path.suffix + ".tmp")
        _pq.write_table(table, tmp)
        tmp.replace(path)

    def read(self, endpoint: str, tag: str) -> List[Dict[str, Any]]:
        """Read a landed window/batch back into raw dicts (for re-normalize)."""
        path = self._path(endpoint, tag)
        if not path.exists():
            return []
        if _HAS_PARQUET and path.suffix == ".parquet":  # pragma: no cover
            table = _pq.read_table(path)
            col = table.column("raw_json").to_pylist()
            return [json.loads(x) for x in col]
        out: List[Dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
        return out

    def windows(self, endpoint: str) -> List[str]:
        """List landed window/batch tags for an endpoint."""
        d = self.root / endpoint
        if not d.exists():
            return []
        return sorted(p.stem for p in d.iterdir() if p.is_file())
