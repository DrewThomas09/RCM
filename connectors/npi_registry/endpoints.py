"""Declarative specs for the NPPES NPI Registry ingest.

The NPI Registry (``npiregistry.cms.hhs.gov/api/``) is **not** a bulk
crawl endpoint like openFDA — it is a single search endpoint driven
entirely by query params (``state``, ``taxonomy_description``,
``organization_name`` …). There is no way to "list everything"; you ask
a question and page the answer.

So instead of one :class:`EndpointSpec` per URL path, we model ingest as
a set of **seeded searches**. Each :class:`EndpointSpec` carries a tuple
of seed query-param dicts. The connector (:mod:`connectors.npi_registry.connector`)
runs each seed and pages it by ``skip`` (step 200) up to the API's hard
1,200-result ceiling. Callers may also pass their own ad-hoc seed to
``fetch`` — the defaults here are just a sensible starting crawl.

Why specs and not code branches: adding or retuning a seeded crawl is a
data edit here, never new routing logic elsewhere. The registry rows
(:mod:`connectors.npi_registry.registry`) and any orchestrator read
these.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# Base of the public NPPES API. Always query with ``version=2.1``.
NPPES_BASE = "https://npiregistry.cms.hhs.gov/api"
NPPES_PATH = "/"


# A seed is a dict of NPPES search params (no version/limit/skip — those
# are supplied by the connector). Immutable tuples of dicts keep specs
# frozen-friendly.
Seed = Dict[str, str]


@dataclass(frozen=True)
class EndpointSpec:
    """One seeded-search dataset over the single NPPES endpoint.

    Attributes
    ----------
    key:
        Short dataset id, also the ``/v1/query/{dataset}`` slug suffix.
    enumeration_type:
        ``NPI-1`` (individual) / ``NPI-2`` (organization) / ``None`` for
        a mixed crawl. Documentary — the actual filter lives in seeds.
    target_table:
        Canonical table the normalizer's provider row upserts into
        (always ``dim_provider``; taxonomy/address fan-out rides along).
    id_field:
        Native record id NPPES returns and we key idempotent upserts on.
    seeds:
        Default seed query-param dicts. ``fetch`` runs one seed per call
        (or a caller-supplied seed), paging by ``skip``.
    date_field:
        NPPES field usable as an incremental watermark
        (``last_updated``); ``None`` when a seed has no useful date.
    """

    key: str
    enumeration_type: Optional[str]
    target_table: str
    seeds: Tuple[Seed, ...]
    id_field: str = "number"
    date_field: Optional[str] = "last_updated"
    join_keys: Tuple[str, ...] = ("npi",)
    refresh_cadence: str = "weekly"
    default_params: Dict[str, str] = field(default_factory=dict)

    @property
    def dataset_id(self) -> str:
        return f"npi_{self.key}"

    @property
    def base_url(self) -> str:
        return NPPES_BASE

    @property
    def path(self) -> str:
        return NPPES_PATH


# ── Default seeded crawls ──────────────────────────────────────────────
# Individuals: a couple of state + specialty slices. Organizations: a
# name-prefix slice. These are illustrative, sensible defaults — a real
# crawl would enumerate many more (all states × taxonomies).
_INDIVIDUAL_SEEDS: Tuple[Seed, ...] = (
    {"enumeration_type": "NPI-1", "taxonomy_description": "Internal Medicine",
     "state": "MD"},
    {"enumeration_type": "NPI-1", "taxonomy_description": "Family Medicine",
     "state": "CA"},
)
_ORGANIZATION_SEEDS: Tuple[Seed, ...] = (
    {"enumeration_type": "NPI-2", "organization_name": "HOSPITAL*",
     "state": "NY"},
)


_SPECS: List[EndpointSpec] = [
    EndpointSpec(
        key="provider_individual",
        enumeration_type="NPI-1",
        target_table="dim_provider",
        seeds=_INDIVIDUAL_SEEDS,
    ),
    EndpointSpec(
        key="provider_organization",
        enumeration_type="NPI-2",
        target_table="dim_provider",
        seeds=_ORGANIZATION_SEEDS,
    ),
]

ENDPOINTS: Dict[str, EndpointSpec] = {s.key: s for s in _SPECS}


def get_endpoint(key: str) -> EndpointSpec:
    """Look up an ingest spec by key, raising a clear error if absent."""
    try:
        return ENDPOINTS[key]
    except KeyError as exc:
        raise KeyError(
            f"unknown NPI endpoint {key!r}; known: {sorted(ENDPOINTS)}"
        ) from exc


def individual_endpoints() -> List[EndpointSpec]:
    return [s for s in ENDPOINTS.values() if s.enumeration_type == "NPI-1"]


def organization_endpoints() -> List[EndpointSpec]:
    return [s for s in ENDPOINTS.values() if s.enumeration_type == "NPI-2"]
