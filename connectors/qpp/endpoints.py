"""Declarative specs for every QPP API dataset this connector ingests.

One :class:`EndpointSpec` per registered dataset. The spec is the single
place that knows the QPP-specific quirks: the URL path template, which
canonical table the normalizer writes into, and the performance year the
default pull targets. The registry rows (:mod:`connectors.qpp.registry`)
and the connector both read these — adding or retuning a dataset is a
data edit here, never new routing logic elsewhere.

The Quality Payment Program is CMS's MIPS/APM clinician payment-
adjustment program under MACRA. Two public, keyless API families feed
this connector:

``eligibility``
    The QPP Eligibility API (``/eligibility/npis/{npi}?year=``): one
    clinician's MIPS eligibility, specialty, and practice organizations
    for a performance year. Per-NPI — a pull needs a caller-supplied NPI
    list (the estate's NPI universe joins here), so this family is
    manual-ingest, like the NPI Registry connector.
``organizations``
    The same fetch, second grain: the clinician's practice organizations
    (one row per NPI x organization), written by the same normalize pass.
``benchmarks``
    The Submissions API's public benchmarks
    (``/submissions/public/benchmarks?year=``): every MIPS quality-
    measure benchmark (deciles by submission method) for a performance
    year — unattended, one request per year.

Performance-year note: ``default_params['year']`` pins the default pull;
any other year is one ``--year`` flag away. Years are additive — rows
compose the year into their upsert key, so multi-year history coexists
in the same tables.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

_QPP_BASE = "https://qpp.cms.gov/api"

# Default performance year for unparameterised pulls.
DEFAULT_YEAR = "2025"

ELIGIBILITY_PATH_TEMPLATE = "/eligibility/npis/{npi}"
BENCHMARKS_PATH = "/submissions/public/benchmarks"


@dataclass(frozen=True)
class EndpointSpec:
    """One QPP dataset.

    Attributes
    ----------
    key:
        Short dataset id, also the ``/v1/query/{dataset}`` slug suffix
        and the value written into each row's ``source_endpoint`` column.
    kind:
        ``eligibility`` | ``organizations`` | ``benchmarks`` — drives
        which fetch path and normalizer mapper runs. ``organizations``
        shares the eligibility fetch (same payload, second grain).
    path:
        The URL path (template for the per-NPI eligibility route).
    target_table:
        Canonical table the normalizer upserts into.
    date_field:
        Column used for recency ordering / registry ``date_field``.
    join_keys:
        Keys other datasets join to this one on (``npi`` joins the NPPES
        provider universe; ``measure_id`` joins measure inventories).
    """

    key: str
    kind: str
    path: str
    target_table: str
    date_field: str = ""
    join_keys: Tuple[str, ...] = ()
    refresh_cadence: str = "annual"
    default_params: Dict[str, str] = field(default_factory=dict)

    @property
    def dataset_id(self) -> str:
        return f"qpp_{self.key}"

    @property
    def base_url(self) -> str:
        return _QPP_BASE


_SPECS: List[EndpointSpec] = [
    EndpointSpec(
        key="eligibility",
        kind="eligibility",
        path=ELIGIBILITY_PATH_TEMPLATE,
        target_table="qpp_clinician",
        date_field="year",
        join_keys=("npi",),
        default_params={"year": DEFAULT_YEAR},
    ),
    EndpointSpec(
        key="organizations",
        kind="organizations",
        path=ELIGIBILITY_PATH_TEMPLATE,
        target_table="qpp_organization",
        date_field="year",
        join_keys=("npi",),
        default_params={"year": DEFAULT_YEAR},
    ),
    EndpointSpec(
        key="benchmarks",
        kind="benchmarks",
        path=BENCHMARKS_PATH,
        target_table="qpp_benchmark",
        date_field="performance_year",
        join_keys=("measure_id",),
        default_params={"year": DEFAULT_YEAR},
    ),
]

ENDPOINTS: Dict[str, EndpointSpec] = {s.key: s for s in _SPECS}


def get_endpoint(key: str) -> EndpointSpec:
    """Look up an endpoint spec by key, raising a clear error if absent."""
    try:
        return ENDPOINTS[key]
    except KeyError as exc:
        raise KeyError(
            f"unknown QPP endpoint {key!r}; known: {sorted(ENDPOINTS)}"
        ) from exc
