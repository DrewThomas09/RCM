"""NPPES connector — the provider (NPI) universe + taxonomy crosswalk.

This slice is the authoritative producer of the provider dimension
(``dim_provider``) and the NUCC taxonomy crosswalk (``dim_taxonomy``).
Other sources (CMS claims/utilization) reference NPIs but treat this as the
source of truth.

Public surface::

    from connectors.nppes import NppesConnector, NppesStore, pipeline, api
    from connectors.nppes import registry

    store = NppesStore("nppes.db")
    pipeline.run(store, monthly_path=..., nucc_path=..., monthly_version=...)
    api.lookup_provider(store, "1003456789")
    api.query_dataset(store, "dim_provider", filters={"state": "TX"})

The connector lands raw to a partitioned parquet/NDJSON zone, then
normalizes to the canonical dimensions; the registry exposes every dataset
through ``/v1/query`` with zero new routing code.
"""
from __future__ import annotations

from . import affiliation, api, connector, dq, landing, normalize, parse
from . import pipeline, registry, synth
from .connector import NppesConnector
from .luhn import is_valid_npi, make_valid_npi
from .store import NppesStore

__all__ = [
    "NppesConnector", "NppesStore", "is_valid_npi", "make_valid_npi",
    "affiliation", "api", "connector", "dq", "landing", "normalize",
    "parse", "pipeline", "registry", "synth",
]
