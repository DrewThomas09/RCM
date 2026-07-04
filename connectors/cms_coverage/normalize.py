"""Map raw CMS Coverage records → canonical rows.

One mapper per coverage level. Each is *defensive*: it reaches for
fields with :func:`dig`/:func:`coalesce` and never assumes a path
exists. Anything present on the record that the mapper does not place is
recorded as an unmapped key so the pipeline can log schema drift.

Cross-cutting normalizations done here:
  * ``document_key`` composes ``{document_type}:{document_id}:{document_version}``
    so re-ingesting the same version is idempotent and different
    versions of one document coexist.
  * ``contractor_key`` composes ``{contractor_id}:{contractor_version}``.
  * National documents carry ``coverage_level='national'`` and no
    contractor; local documents carry ``coverage_level='local'`` plus
    the contractor association when present.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from .endpoints import EndpointSpec
from .flatten import coalesce, dig, unmapped_keys


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


_DOCUMENT_KNOWN = {
    "document_id", "document_version", "document_display_id", "document_type",
    "title", "chapter", "is_lab", "last_updated", "last_updated_sort", "url",
    "contractor_id", "contractor_name",
}
_CONTRACTOR_KNOWN = {
    "contractor_id", "contractor_version", "contractor_name",
    "contract_type_id", "contract_subtype_id", "contract_number",
}


def _document_key(doc_type: Any, doc_id: Any, doc_ver: Any) -> str:
    return f"{doc_type}:{doc_id}:{doc_ver}"


def _contractor_key(cid: Any, cver: Any) -> str:
    return f"{cid}:{cver}"


# ── per-coverage-level mappers ─────────────────────────────────────────
def _coverage_document(rec: Dict[str, Any], res: NormalizeResult,
                       spec: EndpointSpec) -> None:
    doc_id = dig(rec, "document_id")
    if doc_id in (None, ""):
        return
    doc_ver = coalesce(rec, ["document_version"], default="")
    # Prefer the record's own document_type, fall back to the spec's.
    doc_type = coalesce(rec, ["document_type"], default=spec.document_type)
    res.add("dim_coverage_document", {
        "document_key": _document_key(doc_type, doc_id, doc_ver),
        "document_id": doc_id,
        "document_version": doc_ver,
        "document_display_id": coalesce(rec, ["document_display_id"]),
        "document_type": doc_type,
        "title": coalesce(rec, ["title"]),
        "chapter": coalesce(rec, ["chapter"]),
        "is_lab": coalesce(rec, ["is_lab"]),
        "coverage_level": spec.coverage_level,
        "contractor_id": coalesce(rec, ["contractor_id"]),
        "contractor_name": coalesce(rec, ["contractor_name"]),
        "last_updated": coalesce(rec, ["last_updated"]),
        "last_updated_sort": coalesce(rec, ["last_updated_sort"]),
        "url": coalesce(rec, ["url"]),
        "source_endpoint": spec.key,
    })
    res.note_unmapped(unmapped_keys(rec, _DOCUMENT_KNOWN))


def _medicare_contractor(rec: Dict[str, Any], res: NormalizeResult,
                         spec: EndpointSpec) -> None:
    cid = dig(rec, "contractor_id")
    if cid in (None, ""):
        return
    cver = coalesce(rec, ["contractor_version"], default="")
    res.add("dim_medicare_contractor", {
        "contractor_key": _contractor_key(cid, cver),
        "contractor_id": cid,
        "contractor_version": cver,
        "contractor_name": coalesce(rec, ["contractor_name"]),
        "contract_type_id": coalesce(rec, ["contract_type_id"]),
        "contract_subtype_id": coalesce(rec, ["contract_subtype_id"]),
        "contract_number": coalesce(rec, ["contract_number"]),
        "source_endpoint": spec.key,
    })
    res.note_unmapped(unmapped_keys(rec, _CONTRACTOR_KNOWN))


_MAPPERS = {
    "national": _coverage_document,
    "local": _coverage_document,
    "dimension": _medicare_contractor,
}


def normalize(spec: EndpointSpec, raw_rows: List[Dict[str, Any]]
              ) -> NormalizeResult:
    """Normalize a batch of raw rows for one endpoint into canonical rows."""
    res = NormalizeResult()
    mapper = _MAPPERS.get(spec.coverage_level)
    if mapper is None:
        raise KeyError(
            f"no normalizer for coverage_level {spec.coverage_level!r} "
            f"(endpoint {spec.key!r})")
    for rec in raw_rows:
        if isinstance(rec, dict):
            mapper(rec, res, spec)
    return res
