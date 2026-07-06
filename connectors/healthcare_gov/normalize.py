"""Map raw data.healthcare.gov payloads → canonical rows.

Three mapper families:

  * catalog — one DCAT metastore item → one ``healthcare_gov_catalog``
    row. Nested ``contactPoint``/``publisher``/``distribution`` fields
    are flattened defensively; camelCase DCAT keys become snake_case via
    :func:`_snake` (the documented name-normalization rule for this
    connector).
  * curated datastore rows — DKAN already returns the PUF CSV headers
    lower-cased, so mapping is a straight column pick against the
    snapshotted schema in :mod:`tables`; the composed upsert key
    ``{endpoint_key}:{id_field values...}`` makes re-ingest idempotent
    and lets one physical table host future plan years without
    collisions.
  * generic rows — any catalog dataset's rows land as
    ``{dataset_key}:{row_idx}``-keyed JSON blobs so arbitrary datasets
    stay queryable through the uniform engine without a bespoke table.

Every mapper is *defensive*: it reaches for fields with
:func:`~connectors.healthcare_gov.flatten.dig`/:func:`~connectors.healthcare_gov.flatten.coalesce`
and never assumes a path exists. Anything present on the record that the
mapper does not place is recorded as an unmapped key so the pipeline can
log schema drift.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .endpoints import EndpointSpec
from .flatten import as_list, coalesce, dig, join_list, unmapped_keys
from .tables import TABLES

# DKAN's optional ``rowIds=true`` adds this bookkeeping column to every
# datastore row; it is not part of any PUF schema, so mappers treat it
# as known (used for generic row ids, dropped from curated rows).
_ROW_ID_FIELD = "record_number"


def _snake(name: str) -> str:
    """camelCase / punctuated name → snake_case.

    The documented normalization rule for caller-facing column names:
    insert ``_`` at lower→upper boundaries, replace every non-alnum run
    with ``_``, lower-case, collapse repeats. ``accrualPeriodicity`` →
    ``accrual_periodicity``; DKAN's already-lowercase datastore headers
    pass through unchanged.
    """
    s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(name))
    s = re.sub(r"[^0-9a-zA-Z]+", "_", s)
    return re.sub(r"_+", "_", s).strip("_").lower()


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


# DCAT keys the catalog mapper places (raw, pre-_snake names — the audit
# compares against the record's own top-level keys).
_CATALOG_KNOWN = {
    "@type", "identifier", "title", "description", "accessLevel",
    "accrualPeriodicity", "issued", "modified", "license", "theme",
    "keyword", "publisher", "contactPoint", "bureauCode", "programCode",
    "distribution", "landingPage",
}


def _catalog_row(rec: Dict[str, Any], res: NormalizeResult,
                 spec: EndpointSpec) -> None:
    ident = dig(rec, "identifier")
    if ident in (None, ""):
        return
    dists = as_list(rec.get("distribution"))
    res.add("healthcare_gov_catalog", {
        "identifier": ident,
        "title": coalesce(rec, ["title"]),
        "description": coalesce(rec, ["description"]),
        "access_level": coalesce(rec, ["accessLevel"]),
        "accrual_periodicity": coalesce(rec, ["accrualPeriodicity"]),
        "issued": coalesce(rec, ["issued"]),
        "modified": coalesce(rec, ["modified"]),
        "license": coalesce(rec, ["license"]),
        "theme": join_list(rec.get("theme")),
        "keyword": join_list(rec.get("keyword")),
        "publisher_name": coalesce(rec, ["publisher.name"]),
        "contact_fn": coalesce(rec, ["contactPoint.fn"]),
        "contact_email": coalesce(rec, ["contactPoint.hasEmail"]),
        "bureau_code": join_list(rec.get("bureauCode")),
        "program_code": join_list(rec.get("programCode")),
        "distribution_count": len(dists),
        "download_url": coalesce(rec, ["distribution.0.downloadURL"]),
        "media_type": coalesce(rec, ["distribution.0.mediaType"]),
        "format": coalesce(rec, ["distribution.0.format"]),
        "described_by": coalesce(rec, ["distribution.0.describedBy"]),
        # DKAN's stable landing-page convention; not in the payload.
        "landing_page": coalesce(
            rec, ["landingPage"],
            default=f"https://data.healthcare.gov/dataset/{ident}"),
        "source_endpoint": spec.key,
    })
    res.note_unmapped(unmapped_keys(rec, _CATALOG_KNOWN))


def _compose_key(spec: EndpointSpec, rec: Dict[str, Any]) -> Optional[str]:
    """``{endpoint_key}:{v1}:{v2}...`` from the spec's ordered id fields.

    Returns ``None`` (skip the row) when the *first* id field is empty —
    a record with no primary dimension is unkeyable noise. Later fields
    may legitimately be empty (e.g. statewide service areas have no
    ``county``) and become empty segments, keeping keys aligned.
    """
    values = []
    for i, f in enumerate(spec.id_fields):
        v = rec.get(f)
        if v in (None, ""):
            if i == 0:
                return None
            v = ""
        values.append(str(v))
    return ":".join([spec.key, *values])


def _datastore_row(rec: Dict[str, Any], res: NormalizeResult,
                   spec: EndpointSpec) -> None:
    key = _compose_key(spec, rec)
    if key is None:
        return
    tdef = TABLES[spec.target_table]
    row: Dict[str, Any] = {tdef.pk: key, "source_endpoint": spec.key}
    known = {tdef.pk, "source_endpoint", "ingested_at", _ROW_ID_FIELD}
    for col in tdef.columns:
        if col in row or col in ("source_endpoint", "ingested_at"):
            continue
        row[col] = rec.get(col)
        known.add(col)
    res.add(spec.target_table, row)
    res.note_unmapped(unmapped_keys(rec, known))


def normalize(spec: EndpointSpec, raw_rows: List[Dict[str, Any]]
              ) -> NormalizeResult:
    """Normalize a batch of raw records for one endpoint into canonical rows."""
    res = NormalizeResult()
    if spec.kind == "catalog":
        mapper = _catalog_row
    elif spec.kind == "datastore":
        mapper = _datastore_row
    else:
        raise KeyError(
            f"no normalizer for endpoint kind {spec.kind!r} (endpoint "
            f"{spec.key!r}); generic rows go through generic_rows()")
    for rec in raw_rows:
        if isinstance(rec, dict):
            mapper(rec, res, spec)
    return res


def generic_rows(dataset_key: str, raw_rows: List[Dict[str, Any]],
                 start_idx: int = 0, *,
                 fetched_at: Optional[str] = None) -> List[Dict[str, Any]]:
    """Any dataset's raw rows → ``healthcare_gov_rows`` records.

    ``row_idx`` prefers DKAN's ``record_number`` (stable across partial
    fetches of one import) and falls back to ``start_idx + position``
    (the absolute fetch offset). The composed pk
    ``{dataset_key}:{row_idx}`` keeps re-fetches idempotent, and
    ``dataset_key`` doubles as ``source_endpoint`` so the query engine's
    slice-pinning convention keeps working on this shared table.
    """
    now = fetched_at or _utc_now()
    out: List[Dict[str, Any]] = []
    for i, rec in enumerate(raw_rows):
        if not isinstance(rec, dict):
            continue
        body = dict(rec)
        row_idx = body.pop(_ROW_ID_FIELD, None)
        if row_idx in (None, ""):
            row_idx = start_idx + i
        out.append({
            "row_key": f"{dataset_key}:{row_idx}",
            "dataset_key": dataset_key,
            "row_idx": str(row_idx),
            "row_json": json.dumps(body, ensure_ascii=False, sort_keys=True),
            "fetched_at": now,
            "source_endpoint": dataset_key,
        })
    return out
