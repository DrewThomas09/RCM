"""Map raw Provider Data Catalog payloads → canonical rows.

Three mappers, one per dataset kind:

  * ``catalog``  — DKAN metastore items (dataset metadata) →
    ``provider_data_catalog`` rows;
  * ``curated``  — datastore result rows for the 18 flagship Care
    Compare datasets → their canonical tables;
  * ``generic``  — datastore result rows for *any* catalog dataset →
    ``provider_data_rows`` (one JSON blob per row).

Each mapper is *defensive*: fields are reached with ``dict.get`` and a
row missing its natural key is skipped, never crashed on. Raw keys a
curated mapper does not place are recorded as unmapped so schema drift
on the live files surfaces in pipeline logs instead of silently dropping
columns.

Cross-cutting normalizations done here:

  * :func:`_snake` canonicalises raw field names. Datastore columns are
    already lowercase snake-ish, but the live files contain hazards a
    SQL identifier cannot carry verbatim: ``_condition`` (leading
    underscore), ``95_ci_upper_limit_for_fyswr`` (leading digit) and
    doubled underscores from DKAN's header mangling. The same function
    generated the frozen column tuples in :mod:`tables`, so runtime
    mapping and schema stay in lock-step by construction.
  * ``record_key`` composes the spec's ``pk_fields`` values with ``:``
    so re-ingesting is idempotent (single-field keys degrade to the bare
    value, e.g. ``record_key == facility_id`` for hospital_general).
  * generic rows compose ``row_key = "{dataset_key}:{row_idx}"`` and
    carry ``dataset_key`` in ``source_endpoint`` so per-dataset slices
    of the shared table stay individually queryable.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .endpoints import EndpointSpec
from .tables import TABLES

_META_COLS = {"source_endpoint", "ingested_at", "record_key"}


def _snake(name: str) -> str:
    """Canonicalise a raw column/field name into a safe SQL identifier.

    Lowercase; every run of non-alphanumerics becomes one underscore;
    leading/trailing underscores are stripped; a leading digit gets an
    ``n_`` prefix (SQLite identifiers cannot start with a digit
    unquoted, and the estate's TableDef interpolates identifiers bare).
    """
    s = re.sub(r"[^0-9a-z]+", "_", str(name).lower())
    s = re.sub(r"_+", "_", s).strip("_")
    if s and s[0].isdigit():
        s = "n_" + s
    return s


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


@dataclass
class NormalizeResult:
    """Canonical rows grouped by table, plus an unmapped-field audit."""

    rows: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    unmapped: Dict[str, int] = field(default_factory=dict)

    def add(self, table: str, row: Dict[str, Any]) -> None:
        self.rows.setdefault(table, []).append(row)

    def note_unmapped(self, keys: List[str]) -> None:
        for k in keys:
            self.unmapped[k] = self.unmapped.get(k, 0) + 1


# ── catalog metastore items ───────────────────────────────────────────
def _first_download_url(rec: Dict[str, Any]) -> Optional[str]:
    dist = rec.get("distribution")
    if isinstance(dist, list) and dist and isinstance(dist[0], dict):
        return dist[0].get("downloadURL")
    return None


def _join(value: Any, sep: str = "|") -> str:
    """Join a list into stable, LIKE-searchable text ('' when absent)."""
    if isinstance(value, list):
        return sep.join(str(v) for v in value if v not in (None, ""))
    return "" if value is None else str(value)


def _catalog_row(rec: Dict[str, Any], res: NormalizeResult,
                 spec: EndpointSpec) -> None:
    identifier = rec.get("identifier")
    if identifier in (None, ""):
        return
    res.add("provider_data_catalog", {
        "identifier": str(identifier),
        "title": rec.get("title"),
        "description": rec.get("description"),
        "themes": _join(rec.get("theme")),
        "keywords": _join(rec.get("keyword")),
        "issued": rec.get("issued"),
        "modified": rec.get("modified"),
        "csv_url": _first_download_url(rec),
        "landing_page": rec.get("landingPage"),
        "source_endpoint": spec.key,
    })


# ── curated datastore rows ────────────────────────────────────────────
def _record_key(row: Dict[str, Any], spec: EndpointSpec) -> Optional[str]:
    """Compose the idempotent upsert key from the spec's pk_fields.

    Returns ``None`` (skip the row) when the leading key field is empty —
    a datastore row without its natural id cannot be upserted safely.
    """
    values = [row.get(f) for f in spec.pk_fields]
    if values[0] in (None, ""):
        return None
    return ":".join("" if v is None else str(v) for v in values)


def _curated_row(rec: Dict[str, Any], res: NormalizeResult,
                 spec: EndpointSpec) -> None:
    colset = set(TABLES[spec.target_table].columns)
    row: Dict[str, Any] = {}
    unmapped: List[str] = []
    for raw_key, value in rec.items():
        col = _snake(raw_key)
        if col in colset and col not in _META_COLS:
            row[col] = value
        else:
            unmapped.append(raw_key)
    key = _record_key(row, spec)
    if key is None:
        return
    row["record_key"] = key
    row["source_endpoint"] = spec.key
    res.add(spec.target_table, row)
    res.note_unmapped(unmapped)


# ── generic rows (any catalog dataset) ────────────────────────────────
def _generic_row(rec: Dict[str, Any], res: NormalizeResult,
                 dataset_key: str, row_idx: int, fetched_at: str) -> None:
    res.add("provider_data_rows", {
        "row_key": f"{dataset_key}:{row_idx}",
        "dataset_key": dataset_key,
        "row_idx": row_idx,
        "row_json": json.dumps(rec, ensure_ascii=False, sort_keys=True),
        "fetched_at": fetched_at,
        # dataset_key doubles as the slice value so a per-dataset view of
        # the shared table stays pinnable by the query engine.
        "source_endpoint": dataset_key,
    })


def normalize(
    spec: EndpointSpec,
    raw_rows: List[Dict[str, Any]],
    *,
    dataset_key: Optional[str] = None,
    start_idx: int = 0,
    fetched_at: Optional[str] = None,
) -> NormalizeResult:
    """Normalize a batch of raw rows for one endpoint into canonical rows.

    ``dataset_key``/``start_idx``/``fetched_at`` only apply to the
    generic kind: ``dataset_key`` names which catalog dataset the rows
    came from (defaults to the 4x4 identifier is required), and
    ``start_idx`` is the datastore offset of the first row so paged
    fetches compose stable ``row_idx`` values instead of colliding at 0.
    """
    res = NormalizeResult()
    if spec.kind == "catalog":
        for rec in raw_rows:
            if isinstance(rec, dict):
                _catalog_row(rec, res, spec)
        return res
    if spec.kind == "curated":
        for rec in raw_rows:
            if isinstance(rec, dict):
                _curated_row(rec, res, spec)
        return res
    if spec.kind == "generic":
        key = dataset_key or spec.identifier
        if not key:
            raise ValueError("generic normalize requires dataset_key")
        stamp = fetched_at or _utc_now()
        idx = start_idx
        for rec in raw_rows:
            if isinstance(rec, dict):
                _generic_row(rec, res, key, idx, stamp)
                idx += 1
        return res
    raise KeyError(f"no normalizer for kind {spec.kind!r} (endpoint {spec.key!r})")
