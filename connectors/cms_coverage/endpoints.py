"""Declarative specs for every CMS Coverage API endpoint this connector ingests.

One :class:`EndpointSpec` per source endpoint. The spec is the single
place that knows CMS-Coverage-specific quirks: the native id fields the
idempotent upsert keys on, whether the endpoint pages by an opaque
``next_page_token`` cursor or returns everything in one call, the date
field used for recency sorting, and the canonical table the normalizer
writes into.

Why specs and not code branches: adding or retuning an endpoint is a
data edit here, never new routing logic elsewhere. The registry rows
(:mod:`connectors.cms_coverage.registry`) and the connector both read
these.

The Medicare Coverage Database exposes two families of documents —
*national* coverage (NCDs, NCAs, CALs, MEDCAC meetings, technology
assessments) and *local* coverage (LCDs, Proposed LCDs, Articles) — plus
a Medicare Administrative Contractor dimension. The national/local report
paths are the best-known mapping; verify live params/paths at the CMS
Medicare Coverage Database developer portal before a bulk run (see
README, same "verify live" disclaimer openFDA carries).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

_CMS_COVERAGE_BASE = "https://api.coverage.cms.gov"


@dataclass(frozen=True)
class EndpointSpec:
    """One CMS Coverage API endpoint.

    Attributes
    ----------
    key:
        Short dataset id, also the ``/v1/query/{dataset}`` slug and the
        value written into each row's ``source_endpoint`` column so
        endpoints sharing a table stay individually queryable.
    path:
        URL path under ``api.coverage.cms.gov`` (e.g.
        ``/v1/reports/national-coverage-ncd``).
    target_table:
        Canonical table the normalizer upserts into.
    coverage_level:
        ``national`` | ``local`` | ``dimension``. Drives which
        normalizer mapper runs and the ``coverage_level`` column value.
    document_type:
        The CMS document type (``NCD``, ``NCA``, ``CAL``, ``MEDCAC``,
        ``technology_assessment``, ``LCD``, ``Proposed LCD``,
        ``Article``). ``None`` for the contractor dimension.
    paginated:
        ``True`` when the list endpoint pages by an opaque
        ``next_page_token`` cursor (national/local docs); ``False`` when
        the endpoint returns every item in one call (contractors).
    id_fields:
        Ordered candidate keys for the native record id; the composed
        upsert key is built from these in the normalizer.
    date_field:
        Field used for recency ordering / registry ``date_field``.
    """

    key: str
    path: str
    target_table: str
    coverage_level: str
    document_type: Optional[str] = None
    paginated: bool = True
    id_fields: Tuple[str, ...] = ()
    date_field: Optional[str] = None
    join_keys: Tuple[str, ...] = ()
    refresh_cadence: str = "weekly"
    default_params: Dict[str, str] = field(default_factory=dict)

    @property
    def dataset_id(self) -> str:
        return f"cms_coverage_{self.key}"

    @property
    def base_url(self) -> str:
        return _CMS_COVERAGE_BASE


# ── National coverage documents ───────────────────────────────────────
_NATIONAL: List[EndpointSpec] = [
    EndpointSpec(
        key="national_ncd",
        path="/v1/reports/national-coverage-ncd",
        target_table="dim_coverage_document",
        coverage_level="national",
        document_type="NCD",
        id_fields=("document_id", "document_version"),
        date_field="last_updated_sort",
        join_keys=("document_id",),
        refresh_cadence="weekly",
    ),
    EndpointSpec(
        key="national_nca",
        path="/v1/reports/national-coverage-nca",
        target_table="dim_coverage_document",
        coverage_level="national",
        document_type="NCA",
        id_fields=("document_id", "document_version"),
        date_field="last_updated_sort",
        join_keys=("document_id",),
        refresh_cadence="weekly",
    ),
    EndpointSpec(
        key="national_cal",
        path="/v1/reports/national-coverage-cal",
        target_table="dim_coverage_document",
        coverage_level="national",
        document_type="CAL",
        id_fields=("document_id", "document_version"),
        date_field="last_updated_sort",
        join_keys=("document_id",),
        refresh_cadence="weekly",
    ),
    EndpointSpec(
        key="national_medcac",
        path="/v1/reports/national-coverage-medcac",
        target_table="dim_coverage_document",
        coverage_level="national",
        document_type="MEDCAC",
        id_fields=("document_id", "document_version"),
        date_field="last_updated_sort",
        join_keys=("document_id",),
        refresh_cadence="weekly",
    ),
    EndpointSpec(
        key="national_technology_assessment",
        path="/v1/reports/national-coverage-technology-assessment",
        target_table="dim_coverage_document",
        coverage_level="national",
        document_type="technology_assessment",
        id_fields=("document_id", "document_version"),
        date_field="last_updated_sort",
        join_keys=("document_id",),
        refresh_cadence="weekly",
    ),
]

# ── Local coverage documents ──────────────────────────────────────────
_LOCAL: List[EndpointSpec] = [
    EndpointSpec(
        key="local_lcd",
        path="/v1/reports/local-coverage-lcd",
        target_table="dim_coverage_document",
        coverage_level="local",
        document_type="LCD",
        id_fields=("document_id", "document_version"),
        date_field="last_updated_sort",
        join_keys=("document_id", "contractor_id"),
        refresh_cadence="weekly",
    ),
    EndpointSpec(
        key="local_proposed_lcd",
        path="/v1/reports/local-coverage-proposed-lcd",
        target_table="dim_coverage_document",
        coverage_level="local",
        document_type="Proposed LCD",
        id_fields=("document_id", "document_version"),
        date_field="last_updated_sort",
        join_keys=("document_id", "contractor_id"),
        refresh_cadence="weekly",
    ),
    EndpointSpec(
        key="local_article",
        path="/v1/reports/local-coverage-article",
        target_table="dim_coverage_document",
        coverage_level="local",
        document_type="Article",
        id_fields=("document_id", "document_version"),
        date_field="last_updated_sort",
        join_keys=("document_id", "contractor_id"),
        refresh_cadence="weekly",
    ),
]

# ── Contractor dimension (Medicare Administrative Contractors) ─────────
_DIMENSION: List[EndpointSpec] = [
    EndpointSpec(
        key="contractors",
        path="/v1/metadata/contractors",
        target_table="dim_medicare_contractor",
        coverage_level="dimension",
        document_type=None,
        paginated=False,                       # returns every item in one call
        id_fields=("contractor_id", "contractor_version"),
        date_field=None,
        join_keys=("contractor_id",),
        refresh_cadence="monthly",
    ),
]

ENDPOINTS: Dict[str, EndpointSpec] = {
    s.key: s for s in (_NATIONAL + _LOCAL + _DIMENSION)
}


def get_endpoint(key: str) -> EndpointSpec:
    """Look up an endpoint spec by key, raising a clear error if absent."""
    try:
        return ENDPOINTS[key]
    except KeyError as exc:
        raise KeyError(
            f"unknown CMS Coverage endpoint {key!r}; known: {sorted(ENDPOINTS)}"
        ) from exc


def national_endpoints() -> List[EndpointSpec]:
    return [s for s in ENDPOINTS.values() if s.coverage_level == "national"]


def local_endpoints() -> List[EndpointSpec]:
    return [s for s in ENDPOINTS.values() if s.coverage_level == "local"]


def dimension_endpoints() -> List[EndpointSpec]:
    return [s for s in ENDPOINTS.values() if s.coverage_level == "dimension"]
