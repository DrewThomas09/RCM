"""Map raw data.medicaid.gov payloads → canonical rows.

Three mappers, one per endpoint kind:

  * ``catalog`` — flattens the nested DCAT metastore item (publisher,
    contactPoint, distribution[0], theme/keyword lists) into the flat
    ``medicaid_data_catalog`` row.
  * ``datastore`` — the curated flagship datasets. DKAN already returns
    lower-snake-case column names matching the live-sampled table
    columns, so this mapper copies the whitelisted columns verbatim and
    only *composes the natural key*; there is no renaming layer to drift.
  * ``generic`` — arbitrary catalog datasets land as raw row JSON in
    ``medicaid_data_rows``.

Cross-cutting normalizations done here:
  * Every composed key is prefixed with the endpoint key
    (``nadac_2026:{ndc}:{effective_date}:{as_of_date}``) so datasets
    sharing one physical table (the per-year NADAC/SDUD files) can never
    collide across slices, and re-ingesting the same rows is idempotent.
  * Every row carries ``source_endpoint`` = the endpoint key (the
    registry's ``source_filter``), which is what lets the shared-table
    slices stay individually queryable. Generic rows write their
    ``dataset_key`` there instead, so ad-hoc datasets get the same
    slice-pinning behaviour via an explicit filter.
  * Anything present on a record that the mapper does not place is
    recorded as an unmapped key so the pipeline can log schema drift
    (DKAN regenerates hash-suffixed column names when CMS re-uploads a
    file with changed headers — drift is a real risk here).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .endpoints import EndpointSpec
from .flatten import dig, join_list, unmapped_keys
from .tables import TABLES

# Meta columns are set here / by the store, never read from the raw row.
_META_COLS = {"source_endpoint", "ingested_at"}


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


def compose_key(spec: EndpointSpec, rec: Dict[str, Any]) -> Optional[str]:
    """Compose the upsert key ``{endpoint_key}:{id_field values...}``.

    Returns ``None`` (→ skip the row) when the FIRST id field is missing:
    a NADAC row without an NDC or an SDUD row without a utilization_type
    is unkeyable noise, but trailing blanks (e.g. an empty quarter) are
    tolerated so near-conformant rows still land.
    """
    values = [rec.get(f) for f in spec.id_fields]
    if not values or values[0] in (None, ""):
        return None
    return ":".join([spec.key] + ["" if v is None else str(v) for v in values])


# ── catalog (DKAN metastore item → flat row) ──────────────────────────
_CATALOG_KNOWN = {
    "identifier", "title", "description", "theme", "keyword", "accessLevel",
    "accrualPeriodicity", "issued", "modified", "temporal", "publisher",
    "contactPoint", "license", "references", "distribution", "@type",
    "bureauCode", "programCode",
}


def _catalog_row(rec: Dict[str, Any], res: NormalizeResult,
                 spec: EndpointSpec) -> None:
    identifier = dig(rec, "identifier")
    if identifier in (None, ""):
        return
    distributions = rec.get("distribution") or []
    email = dig(rec, "contactPoint.hasEmail", "")
    res.add("medicaid_data_catalog", {
        "identifier": identifier,
        "title": dig(rec, "title"),
        "description": dig(rec, "description"),
        "themes": join_list(rec.get("theme")),
        "keywords": join_list(rec.get("keyword")),
        "access_level": dig(rec, "accessLevel"),
        "periodicity": dig(rec, "accrualPeriodicity"),
        "issued": dig(rec, "issued"),
        "modified": dig(rec, "modified"),
        "temporal": dig(rec, "temporal"),
        "publisher": dig(rec, "publisher.name"),
        "contact": dig(rec, "contactPoint.fn"),
        # "mailto:Medicaid.gov@cms.hhs.gov" → keep just the address.
        "contact_email": str(email).replace("mailto:", "") if email else None,
        "license": dig(rec, "license"),
        "references_urls": join_list(rec.get("references")),
        "distribution_format": dig(rec, "distribution.0.format"),
        "distribution_download_url": dig(rec, "distribution.0.downloadURL"),
        "distribution_described_by": dig(rec, "distribution.0.describedBy"),
        "n_distributions": len(distributions),
        # Every dataset's rows are reachable at the same datastore route;
        # storing it makes the catalog row a ready-to-fetch pointer.
        "api_url": f"{spec.base_url}/api/1/datastore/query/{identifier}/0",
        "source_endpoint": spec.key,
    })
    res.note_unmapped(unmapped_keys(rec, _CATALOG_KNOWN))


# ── curated datastore datasets (columns snapshotted live) ─────────────
def _datastore_row(rec: Dict[str, Any], res: NormalizeResult,
                   spec: EndpointSpec) -> None:
    key = compose_key(spec, rec)
    if key is None:
        return
    tdef = TABLES[spec.target_table]
    pk = tdef.pk
    row: Dict[str, Any] = {pk: key, "source_endpoint": spec.key}
    for col in tdef.columns:
        if col == pk or col in _META_COLS:
            continue
        row[col] = rec.get(col)
    res.add(spec.target_table, row)
    res.note_unmapped(
        unmapped_keys(rec, set(tdef.columns) - _META_COLS - {pk}))


_MAPPERS = {
    "catalog": _catalog_row,
    "datastore": _datastore_row,
}


def normalize(spec: EndpointSpec, raw_rows: List[Dict[str, Any]]
              ) -> NormalizeResult:
    """Normalize a batch of raw rows for one endpoint into canonical rows."""
    mapper = _MAPPERS.get(spec.kind)
    if mapper is None:
        raise KeyError(
            f"no normalizer for endpoint kind {spec.kind!r} "
            f"(endpoint {spec.key!r}); generic rows use normalize_generic()")
    res = NormalizeResult()
    for rec in raw_rows:
        if isinstance(rec, dict):
            mapper(rec, res, spec)
    return res


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


def normalize_generic(dataset_key: str, raw_rows: List[Dict[str, Any]],
                      *, start_idx: int = 0,
                      fetched_at: Optional[str] = None,
                      slice_params: Optional[Dict[str, Any]] = None
                      ) -> NormalizeResult:
    """Normalize arbitrary datastore rows into ``medicaid_data_rows``.

    ``row_key`` composes ``{dataset_key}:{row_idx}`` where ``row_idx`` is
    the row's absolute position in the datastore (page offset + index),
    so re-fetching the same pages is idempotent while different pages
    extend the set. ``dataset_key`` is also written to
    ``source_endpoint`` so slice-pinning/filtering works uniformly.

    ``slice_params`` are the filter/condition params that scoped the
    fetch, if any: they add a :func:`slice_signature` segment to the key
    (``{dataset_key}:{sig}:{row_idx}``) so differently-filtered fetches
    of one dataset coexist, and the human-readable params are carried in
    the row's JSON under the reserved ``_slice_params`` key. Unfiltered
    fetches produce byte-identical output to earlier versions.
    """
    res = NormalizeResult()
    sig = slice_signature(slice_params)
    canon = _canonical_slice_params(slice_params)
    for i, rec in enumerate(raw_rows):
        if not isinstance(rec, dict):
            continue
        idx = start_idx + i
        if sig:
            body: Dict[str, Any] = dict(rec)
            body["_slice_params"] = canon
            key = f"{dataset_key}:{sig}:{idx}"
        else:
            body = rec
            key = f"{dataset_key}:{idx}"
        res.add("medicaid_data_rows", {
            "row_key": key,
            "dataset_key": dataset_key,
            "row_idx": idx,
            "row_json": json.dumps(body, ensure_ascii=False, sort_keys=True),
            "fetched_at": fetched_at,
            "source_endpoint": dataset_key,
        })
    return res
