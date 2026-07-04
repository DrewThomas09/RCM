"""NPPES NPI Registry (``npiregistry.cms.hhs.gov``) connector — vertical slice.

A self-contained connector over the US healthcare-provider registry:
seeded-search connector, declarative registry rows, normalized canonical
tables (``dim_provider`` + ``fact_provider_taxonomy`` +
``fact_provider_address``), a ``/v1/query`` engine, ``/v1/lookup`` and
``/v1/validate`` handlers, and a stdlib HTTP surface.

Everything is **stdlib-only** (``urllib`` + ``json`` + ``sqlite3`` +
``time``) so it runs in the same no-extra-deps environment as the rest of
RCM. Nothing here touches the network or a database at import time:
construct an :class:`NppesConnector` and drive it with an injectable
opener for tests.
"""
from __future__ import annotations

from .connector import FetchResult, NppesConnector
from .endpoints import ENDPOINTS, EndpointSpec, get_endpoint
from .transport import NppesApiError, NppesTransport, RawResponse
from .validate import is_valid_npi, validate_npi

__all__ = [
    "ENDPOINTS",
    "EndpointSpec",
    "get_endpoint",
    "NppesConnector",
    "FetchResult",
    "NppesTransport",
    "RawResponse",
    "NppesApiError",
    "validate_npi",
    "is_valid_npi",
]

CONNECTOR = "npi_registry"
SOURCE_TAG = "npi_registry"
