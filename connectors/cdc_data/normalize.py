"""Map raw data.cdc.gov payloads → canonical rows.

One mapper per dataset kind (catalog / curated / generic). Each is
*defensive*: Socrata JSON rows omit null fields entirely, so every
access goes through :func:`dig`/:func:`coalesce` and never assumes a
key exists. Anything present on a record that a mapper does not place
is recorded as an unmapped key so the pipeline can log schema drift.

Cross-cutting normalizations done here:
  * Catalog metadata arrives camelCase (``dataUpdatedAt``); columns are
    renamed through the documented :func:`flatten.to_snake` and the
    D.CAT "Update Frequency" is lifted out of the nested
    ``customFields."Common Core"`` block.
  * Curated rows compose ``record_key`` from the spec's ``pk_fields``
    (missing fields compose as ``""``), so re-ingesting is idempotent
    and sparse rows still key stably. A row missing EVERY pk field is
    skipped as unkeyable.
  * Generic rows compose ``row_key = "{dataset_key}:{row_idx}"`` and
    mirror ``dataset_key`` into ``source_endpoint`` so the query
    engine's slice grammar (filter on ``dataset_key``, like on
    ``row_json``) works unchanged.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List

from .endpoints import EndpointSpec
from .flatten import coalesce, dig, to_column, to_snake, unmapped_keys


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


# Catalog metadata fields we map, in their live camelCase form. Everything
# else (approvals, customFields, domain, …) is deliberately unmapped noise.
_CATALOG_KNOWN = {
    "id", "name", "description", "category", "attribution", "provenance",
    "createdAt", "dataUpdatedAt", "metadataUpdatedAt", "updatedAt",
    "dataUri", "webUri", "license", "tags", "hideFromCatalog",
    "customFields",
}


def _compose_key(rec: Dict[str, Any], fields: tuple) -> str:
    """``"a:b:c"`` from the pk fields; absent fields become ``""``."""
    return ":".join(str(coalesce(rec, [f], default="")) for f in fields)


# ── catalog mapper ────────────────────────────────────────────────────
def _catalog_row(rec: Dict[str, Any], res: NormalizeResult,
                 spec: EndpointSpec) -> None:
    uid = dig(rec, "id")
    if uid in (None, ""):
        return
    res.add("cdc_data_catalog", {
        "dataset_uid": uid,
        # to_snake documents the camelCase→snake_case column derivation.
        to_snake("name"): coalesce(rec, ["name"]),
        "description": coalesce(rec, ["description"]),
        "category": coalesce(rec, ["category"]),
        "attribution": coalesce(rec, ["attribution"]),
        "provenance": coalesce(rec, ["provenance"]),
        # D.CAT periodicity lives in the nested Common Core block.
        "update_frequency": dig(rec, "customFields.Common Core.Update Frequency"),
        to_snake("createdAt"): coalesce(rec, ["createdAt"]),
        to_snake("dataUpdatedAt"): coalesce(rec, ["dataUpdatedAt"]),
        to_snake("metadataUpdatedAt"): coalesce(rec, ["metadataUpdatedAt"]),
        to_snake("updatedAt"): coalesce(rec, ["updatedAt"]),
        to_snake("dataUri"): coalesce(rec, ["dataUri"]),
        to_snake("webUri"): coalesce(rec, ["webUri"]),
        "license": coalesce(rec, ["license"]),
        "tags": rec.get("tags"),                       # list → JSON in store
        to_snake("hideFromCatalog"): rec.get("hideFromCatalog"),
        "source_endpoint": spec.key,
    })
    res.note_unmapped(unmapped_keys(rec, _CATALOG_KNOWN))


# ── curated mapper (spec-driven, one code path for all ten) ───────────
def _curated_row(rec: Dict[str, Any], res: NormalizeResult,
                 spec: EndpointSpec) -> None:
    # Live field names → canonical column names through the documented
    # normalizer (snake_case + SQL-safe rename, e.g. group → group_field).
    canon = {to_column(k): v for k, v in rec.items()}
    key = _compose_key(canon, spec.pk_fields)
    # A row where every pk field is absent can't be keyed idempotently.
    if not key.replace(":", ""):
        return
    row: Dict[str, Any] = {"record_key": key}
    for col in spec.columns:
        row[col] = canon.get(col)        # absent (Socrata null) → NULL
    row["source_endpoint"] = spec.key
    res.add(spec.target_table, row)
    res.note_unmapped(unmapped_keys(canon, spec.columns))


def normalize(spec: EndpointSpec, raw_rows: List[Dict[str, Any]]
              ) -> NormalizeResult:
    """Normalize a batch of raw rows for one endpoint into canonical rows."""
    res = NormalizeResult()
    if spec.kind == "catalog":
        mapper = _catalog_row
    elif spec.kind == "curated":
        mapper = _curated_row
    else:
        raise KeyError(
            f"no batch normalizer for kind {spec.kind!r} (endpoint "
            f"{spec.key!r}); generic rows go through normalize_generic()")
    for rec in raw_rows:
        if isinstance(rec, dict):
            mapper(rec, res, spec)
    return res


# ── generic rows (any 4x4 on the domain) ──────────────────────────────
def normalize_generic(dataset_key: str, raw_rows: List[Dict[str, Any]],
                      *, start_idx: int = 0) -> List[Dict[str, Any]]:
    """Raw rows from an arbitrary 4x4 → ``cdc_data_rows`` records.

    ``row_idx`` continues from ``start_idx`` so multi-page pulls keep a
    stable, gap-free ordering; the same (dataset, page window) re-fetch
    overwrites in place, which is the idempotency the JSON-blob table
    can honestly promise without a native key.
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    out: List[Dict[str, Any]] = []
    for i, rec in enumerate(raw_rows):
        if not isinstance(rec, dict):
            continue
        idx = start_idx + i
        out.append({
            "row_key": f"{dataset_key}:{idx}",
            "dataset_key": dataset_key,
            "row_idx": idx,
            "row_json": json.dumps(rec, ensure_ascii=False, sort_keys=True),
            "fetched_at": now,
            # dataset_key doubles as the slice value so the uniform query
            # engine can pin/filter generic pulls per dataset.
            "source_endpoint": dataset_key,
        })
    return out
