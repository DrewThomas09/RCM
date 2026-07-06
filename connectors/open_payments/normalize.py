"""Map raw Open Payments records → canonical rows.

One mapper per spec kind. Each is *defensive*: it reaches for fields
with :func:`dig`/:func:`coalesce` and never assumes a path exists.
Anything present on the record that the mapper does not place is
recorded as an unmapped key so the pipeline can log schema drift.

Cross-cutting normalizations done here:

  * The **catalog** mapper flattens the nested DKAN metastore entry
    (contactPoint / publisher / first distribution) and composes the
    two URLs the estate actually uses: ``api_url`` (the datastore query
    endpoint for the UUID) and ``landing_page`` (the portal's dataset
    page). ``theme``/``keyword``/``bureauCode``/``programCode`` lists
    are joined ``|``-delimited so they stay filterable TEXT.
  * The **datastore** mapper is column-driven: the target table's
    native column set (a live snapshot in :mod:`tables`) is the map, so
    curated datasets of any width (91-column general payments,
    252-column research payments) share one mapper. Composed natural
    keys (e.g. ``{amgpo_id}:{nature_code}``) are built here per the
    spec's ``pk_fields`` — the pre-aggregated summary datasets have no
    ``record_id``.
  * The **generic** mapper wraps arbitrary rows as
    ``{dataset_key}:{row_idx}``-keyed JSON so any of the 74 catalog
    datasets stays queryable through the uniform engine. ``row_idx`` is
    zero-padded (8 digits) so TEXT ordering matches numeric order, and
    ``dataset_key`` doubles as ``source_endpoint`` so slice-pinning
    works.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .endpoints import EndpointSpec
from .flatten import coalesce, dig, join_list, unmapped_keys
from .tables import _META, TABLES

_OPEN_PAYMENTS_BASE = "https://openpaymentsdata.cms.gov"

# Zero-pad width for generic row indexes: 8 digits comfortably covers the
# bounded page budget (max_pages cap × 500-row pages) while keeping TEXT
# sort order numeric.
_ROW_IDX_WIDTH = 8


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


_CATALOG_KNOWN = {
    "identifier", "title", "description", "theme", "keyword", "accessLevel",
    "issued", "modified", "temporal", "distribution", "contactPoint",
    "publisher", "license", "bureauCode", "programCode", "dataQuality",
}


def _catalog_row(rec: Dict[str, Any], res: NormalizeResult,
                 spec: EndpointSpec) -> None:
    identifier = dig(rec, "identifier")
    if identifier in (None, ""):
        return
    email = dig(rec, "contactPoint.hasEmail", "") or ""
    dists = rec.get("distribution") or []
    res.add("open_payments_catalog", {
        "identifier": identifier,
        "title": coalesce(rec, ["title"]),
        "description": coalesce(rec, ["description"]),
        "theme": join_list(rec.get("theme")),
        "keyword": join_list(rec.get("keyword")),
        "access_level": coalesce(rec, ["accessLevel"]),
        "issued": coalesce(rec, ["issued"]),
        "modified": coalesce(rec, ["modified"]),
        "temporal": coalesce(rec, ["temporal"]),
        "distribution_title": dig(rec, "distribution.0.title"),
        "media_type": dig(rec, "distribution.0.mediaType"),
        "format": dig(rec, "distribution.0.format"),
        "download_url": dig(rec, "distribution.0.downloadURL"),
        "described_by": dig(rec, "distribution.0.describedBy"),
        "n_distributions": len(dists) if isinstance(dists, list) else 0,
        "api_url": f"{_OPEN_PAYMENTS_BASE}/api/1/datastore/query/{identifier}/0",
        "landing_page": f"{_OPEN_PAYMENTS_BASE}/dataset/{identifier}",
        "contact_name": dig(rec, "contactPoint.fn"),
        "contact_email": email.replace("mailto:", "") or None,
        "publisher": dig(rec, "publisher.name"),
        "license": coalesce(rec, ["license"]),
        "bureau_code": join_list(rec.get("bureauCode")),
        "program_code": join_list(rec.get("programCode")),
        "data_quality": rec.get("dataQuality"),
        "source_endpoint": spec.key,
    })
    res.note_unmapped(unmapped_keys(rec, _CATALOG_KNOWN))


def _datastore_row(rec: Dict[str, Any], res: NormalizeResult,
                   spec: EndpointSpec) -> None:
    """Column-driven mapper for every curated datastore dataset.

    The table's native column snapshot is the whole mapping — DKAN
    already returns lowercase snake_case keys, so mapping is identity
    per column. Rows missing every pk field are skipped (nothing to key
    an upsert on).
    """
    native = [c for c in TABLES[spec.target_table].columns
              if c not in _META and c != spec.pk_column]
    row: Dict[str, Any] = {c: rec.get(c) for c in native}
    if spec.pk_column:
        parts = [str(rec.get(f) if rec.get(f) is not None else "")
                 for f in spec.pk_fields]
        if not any(parts):
            return
        row[spec.pk_column] = ":".join(parts)
    else:
        pk = spec.pk_fields[0]
        if rec.get(pk) in (None, ""):
            return
    row["source_endpoint"] = spec.key
    res.add(spec.target_table, row)
    res.note_unmapped(unmapped_keys(rec, native))


def normalize(spec: EndpointSpec, raw_rows: List[Dict[str, Any]]
              ) -> NormalizeResult:
    """Normalize a batch of raw rows for one curated/catalog endpoint."""
    res = NormalizeResult()
    if spec.kind == "catalog":
        mapper = _catalog_row
    elif spec.kind == "datastore":
        mapper = _datastore_row
    else:
        raise KeyError(
            f"no batch normalizer for kind {spec.kind!r} (endpoint "
            f"{spec.key!r}); generic rows go through normalize_generic()")
    for rec in raw_rows:
        if isinstance(rec, dict):
            mapper(rec, res, spec)
    return res


def normalize_generic(dataset_key: str, raw_rows: List[Dict[str, Any]],
                      *, row_offset: int = 0,
                      fetched_at: Optional[str] = None) -> NormalizeResult:
    """Wrap arbitrary datastore rows as JSON for ``open_payments_rows``.

    ``row_offset`` is the datastore offset the page started at, so the
    composed ``{dataset_key}:{row_idx}`` key is stable across paged
    fetches and a re-fetch of the same slice upserts in place instead of
    appending. ``dataset_key`` is also written to ``source_endpoint`` so
    the query engine's slice pinning works on the shared table.
    """
    res = NormalizeResult()
    stamp = fetched_at or datetime.now(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%S+00:00")
    for i, rec in enumerate(raw_rows):
        if not isinstance(rec, dict):
            continue
        idx = row_offset + i
        padded = str(idx).zfill(_ROW_IDX_WIDTH)
        res.add("open_payments_rows", {
            "row_key": f"{dataset_key}:{padded}",
            "dataset_key": dataset_key,
            "row_idx": padded,
            "row_json": json.dumps(rec, ensure_ascii=False, sort_keys=True),
            "fetched_at": stamp,
            "source_endpoint": dataset_key,
        })
    return res
