"""Declarative specs for the NLM Clinical Tables HCPCS endpoint.

One :class:`EndpointSpec` per source endpoint. The spec is the single
place that knows the NLM-specific quirks: the URL path, the display
fields (``df``) to request back, the set of code-prefix seeds a full
ingest iterates, and the canonical table the normalizer writes into.

HCPCS Level II is CMS's national procedure/supply code set — the billing
vocabulary for everything CPT doesn't cover: DME (E-codes), drugs
administered incident-to (J-codes), ambulance (A-codes), orthotics/
prosthetics (L-codes), temporary national codes (G/K/Q/S/T), vision/
hearing (V-codes). CPT itself (HCPCS Level I) is AMA-licensed and NOT
available from any public API, so this connector deliberately carries
Level II only.

Why specs and not code branches: adding or retuning an endpoint is a
data edit here, never new routing logic elsewhere. The registry rows
(:mod:`connectors.hcpcs.registry`) and the connector both read these.

The NLM Clinical Tables API is public and keyless, and shares its
response shape with the ICD-10 endpoints this estate already drains — a
JSON **array** of four elements — so the connector pages it the same
way: iterating ``seeds`` (``q=code:A*`` … ``code:V*``) with ``offset``
paging inside each seed.
"""
from __future__ import annotations

import string
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


# Base host for every NLM Clinical Tables endpoint (public, no key).
_HCPCS_BASE = "https://clinicaltables.nlm.nih.gov/api"


@dataclass(frozen=True)
class EndpointSpec:
    """One NLM Clinical Tables HCPCS endpoint.

    Attributes
    ----------
    key:
        Short dataset id, also the ``/v1/query/{dataset}`` slug suffix
        and the value stored in ``dim_hcpcs_code.source_endpoint``.
    code_type:
        Which HCPCS level this endpoint carries (``lvl2`` — Level I/CPT
        is AMA-licensed and has no public API).
    path:
        The URL path (``/hcpcs/v3/search``).
    df:
        Ordered display fields to request via ``df=``. The API returns
        one row per match with these columns *in this order*; when a
        requested column is unavailable the API simply returns fewer
        columns, so downstream zips defensively (the same variable-width
        contract the ICD-10 connector verified live).
    sf:
        Search fields the ``terms`` query matches against (``sf=``).
    seeds:
        Code-prefix seeds a full ingest iterates. HCPCS Level II codes
        are one letter (A–V) + four digits, so the letter seeds keep
        each ``q=code:{seed}*`` window well under the offset ceiling.
    target_table:
        Canonical table the normalizer upserts into.
    join_keys:
        Keys other datasets join to this one on (``code`` joins to
        data.cms.gov utilization files' ``hcpcs_cd``).
    refresh_cadence:
        HCPCS Level II updates quarterly (Jan/Apr/Jul/Oct).
    default_params:
        Extra query params always sent for this endpoint.
    """

    key: str
    code_type: str
    path: str
    df: Tuple[str, ...]
    seeds: Tuple[str, ...]
    target_table: str = "dim_hcpcs_code"
    sf: str = "code,display"
    join_keys: Tuple[str, ...] = ("code",)
    refresh_cadence: str = "quarterly"
    default_params: Dict[str, str] = field(default_factory=dict)

    @property
    def dataset_id(self) -> str:
        return f"hcpcs_{self.key}"

    @property
    def base_url(self) -> str:
        return _HCPCS_BASE


# HCPCS Level II codes begin with a letter A–V (D, F, I, N are unassigned
# today; harmless empty seeds kept so a future assignment is picked up
# without a code edit).
_LVL2_SEEDS: Tuple[str, ...] = tuple(string.ascii_uppercase[:22])


_ENDPOINT_LIST: List[EndpointSpec] = [
    EndpointSpec(
        key="lvl2",
        code_type="lvl2",
        path="/hcpcs/v3/search",
        # short_desc/long_desc/obsolete are requested for richer text;
        # when the endpoint omits one the row just comes back narrower
        # (variable df width, absorbed by the zip in the connector).
        df=("code", "display", "short_desc", "long_desc", "obsolete"),
        seeds=_LVL2_SEEDS,
    ),
]

ENDPOINTS: Dict[str, EndpointSpec] = {s.key: s for s in _ENDPOINT_LIST}


def get_endpoint(key: str) -> EndpointSpec:
    """Look up an endpoint spec by key, raising a clear error if absent."""
    try:
        return ENDPOINTS[key]
    except KeyError as exc:
        raise KeyError(
            f"unknown HCPCS endpoint {key!r}; known: {sorted(ENDPOINTS)}"
        ) from exc


def lvl2_endpoint() -> EndpointSpec:
    return ENDPOINTS["lvl2"]
