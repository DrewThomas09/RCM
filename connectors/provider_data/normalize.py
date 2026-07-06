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

import hashlib
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
# First N hex chars of the sha1 over the canonicalized slice params —
# short enough to keep keys readable, long enough to never collide for
# the handful of filter combinations a dataset realistically sees.
_SLICE_SIG_LEN = 10


def _canonical_slice_params(slice_params: Optional[Dict[str, Any]]
                            ) -> Optional[Dict[str, Any]]:
    """A JSON-safe, deterministically ordered copy of the slice params.

    Returns ``None`` when there is no *effective* filter: an absent/empty
    dict, or one whose values are all empty (``None``/``""``/``{}``/
    ``[]``), degrades to the unfiltered key shape so the common
    full-crawl case keeps its historical keys byte-identical.
    """
    if not slice_params:
        return None
    kept = {str(k): v for k, v in slice_params.items()
            if v is not None and v != "" and v != {} and v != []}
    if not kept:
        return None
    return json.loads(
        json.dumps(kept, ensure_ascii=False, sort_keys=True, default=str))


def slice_signature(slice_params: Optional[Dict[str, Any]] = None) -> str:
    """Short stable signature of the filter params that scoped a fetch.

    ``""`` for an unfiltered fetch (the historical, common case — keys
    stay ``{dataset_key}:{row_idx}``, byte-identical with what earlier
    versions wrote). Otherwise the first :data:`_SLICE_SIG_LEN` hex chars
    of the sha1 over the canonicalized (sorted-keys JSON, values coerced
    via ``str``) params. The signature becomes a key segment
    (``{dataset_key}:{sig}:{row_idx}``) so two fetches of the same
    dataset with different filters can never overwrite each other's rows
    in the shared table — ``row_idx`` is only meaningful *within* one
    filter slice.
    """
    canon = _canonical_slice_params(slice_params)
    if canon is None:
        return ""
    blob = json.dumps(canon, ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:_SLICE_SIG_LEN]


def _generic_row(rec: Dict[str, Any], res: NormalizeResult,
                 dataset_key: str, row_idx: int, fetched_at: str,
                 sig: str = "",
                 canon_params: Optional[Dict[str, Any]] = None) -> None:
    if sig:
        body: Dict[str, Any] = dict(rec)
        # Human-readable record of the filters that scoped this row's
        # fetch (the reserved _slice_params key mirrors the sig segment).
        body["_slice_params"] = canon_params
        key = f"{dataset_key}:{sig}:{row_idx}"
    else:
        body = rec
        key = f"{dataset_key}:{row_idx}"
    res.add("provider_data_rows", {
        "row_key": key,
        "dataset_key": dataset_key,
        "row_idx": row_idx,
        "row_json": json.dumps(body, ensure_ascii=False, sort_keys=True),
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
    slice_params: Optional[Dict[str, Any]] = None,
) -> NormalizeResult:
    """Normalize a batch of raw rows for one endpoint into canonical rows.

    ``dataset_key``/``start_idx``/``fetched_at``/``slice_params`` only
    apply to the generic kind: ``dataset_key`` names which catalog
    dataset the rows came from (defaults to the 4x4 identifier is
    required), and ``start_idx`` is the datastore offset of the first row
    so paged/resumed fetches compose stable absolute ``row_idx`` values
    instead of colliding at 0. ``slice_params`` are the conditions/filter
    params that scoped the fetch, if any — they add a
    :func:`slice_signature` segment to the key
    (``{dataset_key}:{sig}:{row_idx}``) so differently-filtered fetches
    of one dataset coexist, and the human-readable params are carried in
    the row's JSON under the reserved ``_slice_params`` key. Unfiltered
    fetches produce byte-identical output to earlier versions.
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
        sig = slice_signature(slice_params)
        canon = _canonical_slice_params(slice_params)
        idx = start_idx
        for rec in raw_rows:
            if isinstance(rec, dict):
                _generic_row(rec, res, key, idx, stamp, sig, canon)
                idx += 1
        return res
    raise KeyError(f"no normalizer for kind {spec.kind!r} (endpoint {spec.key!r})")
