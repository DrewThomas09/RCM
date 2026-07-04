"""Declarative specs for every NLM Clinical Tables ICD-10 endpoint.

One :class:`EndpointSpec` per source endpoint. The spec is the single
place that knows the NLM-specific quirks: the ICD-10 code type this
endpoint carries (``cm`` diagnoses vs ``pcs`` procedures), the URL path,
the display fields (``df``) to request back, the set of code-prefix
seeds a full ingest iterates, and the canonical table the normalizer
writes into.

Why specs and not code branches: adding or retuning an endpoint is a
data edit here, never new routing logic elsewhere. The registry rows
(:mod:`connectors.icd10.registry`) and the connector both read these.

The NLM Clinical Tables API is public and keyless. Both endpoints share
the same response shape — a JSON **array** of four elements — so a single
connector drains them by iterating ``seeds`` (``q=code:A*`` … ``code:Z*``)
and paging each seed by ``offset``.
"""
from __future__ import annotations

import string
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


# Base host for every ICD-10 endpoint (public, no key).
_ICD10_BASE = "https://clinicaltables.nlm.nih.gov/api"


@dataclass(frozen=True)
class EndpointSpec:
    """One NLM Clinical Tables ICD-10 endpoint.

    Attributes
    ----------
    key:
        Short dataset id, also the ``/v1/query/{dataset}`` slug and the
        value stored in ``dim_icd10_code.source_endpoint`` (``cm`` | ``pcs``).
    code_type:
        Which ICD-10 code set this endpoint carries (mirrors ``key``).
    path:
        The URL path (e.g. ``/icd10cm/v3/search``).
    df:
        Ordered display fields to request via ``df=``. The API returns
        one row per match with these columns *in this order*; when a
        requested column is unavailable (e.g. ``long_name``) the API
        simply returns fewer columns, so downstream zips defensively.
    sf:
        Search fields the ``terms`` query matches against (``sf=``).
    seeds:
        Code-prefix seeds a full ingest iterates. Each seed becomes a
        ``q=code:{seed}*`` Elasticsearch-style filter so the whole set is
        pageable under the ~7500 offset ceiling.
    target_table:
        Canonical table the normalizer upserts into.
    join_keys:
        Keys other datasets join to this one on.
    refresh_cadence:
        How often a refresh is scheduled (ICD-10 is an annual code set).
    default_params:
        Extra query params always sent for this endpoint.
    """

    key: str
    code_type: str
    path: str
    df: Tuple[str, ...]
    seeds: Tuple[str, ...]
    target_table: str = "dim_icd10_code"
    sf: str = "code,name"
    join_keys: Tuple[str, ...] = ("code",)
    refresh_cadence: str = "annual"
    default_params: Dict[str, str] = field(default_factory=dict)

    @property
    def dataset_id(self) -> str:
        return f"icd10_{self.key}"

    @property
    def base_url(self) -> str:
        return _ICD10_BASE


# ICD-10-CM diagnosis codes begin with a letter (A–Z).
_CM_SEEDS: Tuple[str, ...] = tuple(string.ascii_uppercase)
# ICD-10-PCS procedure codes are 7-char alphanumeric; the section (first
# char) ranges over the digits and letters.
_PCS_SEEDS: Tuple[str, ...] = tuple(string.digits + string.ascii_uppercase)


_ENDPOINT_LIST: List[EndpointSpec] = [
    EndpointSpec(
        key="cm",
        code_type="cm",
        path="/icd10cm/v3/search",
        # long_name is requested for richer text; when the CM endpoint
        # omits it the row just comes back narrower (variable df width).
        df=("code", "name", "long_name"),
        seeds=_CM_SEEDS,
    ),
    EndpointSpec(
        key="pcs",
        code_type="pcs",
        path="/icd10pcs/v3/search",
        df=("code", "name"),
        seeds=_PCS_SEEDS,
    ),
]

ENDPOINTS: Dict[str, EndpointSpec] = {s.key: s for s in _ENDPOINT_LIST}


def get_endpoint(key: str) -> EndpointSpec:
    """Look up an endpoint spec by key, raising a clear error if absent."""
    try:
        return ENDPOINTS[key]
    except KeyError as exc:
        raise KeyError(
            f"unknown ICD-10 endpoint {key!r}; known: {sorted(ENDPOINTS)}"
        ) from exc


def cm_endpoint() -> EndpointSpec:
    return ENDPOINTS["cm"]


def pcs_endpoint() -> EndpointSpec:
    return ENDPOINTS["pcs"]
