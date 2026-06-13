"""RxNorm / RxNav connector vertical slice for PEDesk.

Self-contained, stdlib-only package that owns the NDC→RxCUI crosswalk and the
RxNorm concept / relationship / drug-class tables. See README.md for the layout
and DECISIONS.md for the choices made under this environment's constraints.

Public surface:
    RxNormConnector        — discover() + fetch(endpoint, params, cursor)
    RxnormPipeline / run   — resumable, idempotent ingestion
    normalize_ndc          — canonical 11-digit NDC normalization
    query_dataset          — uniform filter/select/sort/paginate over datasets
    lookup_rxcui/lookup_ndc — rxnorm-namespace lookups
    registry.dataset_rows  — the declarative dataset registry (source=rxnorm)
"""
from __future__ import annotations

from . import query, registry, store, validation
from .connector import RxNormApiError, RxNormConnector
from .normalize import NdcNormalizationError, format_ndc_11, normalize_ndc
from .pipeline import RxnormPipeline, run
from .query import lookup_ndc, lookup_rxcui, query_dataset

__all__ = [
    "RxNormConnector",
    "RxNormApiError",
    "RxnormPipeline",
    "run",
    "normalize_ndc",
    "format_ndc_11",
    "NdcNormalizationError",
    "query_dataset",
    "lookup_rxcui",
    "lookup_ndc",
    "registry",
    "store",
    "query",
    "validation",
]
