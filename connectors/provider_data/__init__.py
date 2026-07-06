"""CMS Provider Data Catalog (``data.cms.gov/provider-data``) connector — full slice.

This package is the self-contained Care Compare / Provider Data Catalog
workstream: connector, declarative registry rows, normalized canonical
tables (the full DKAN catalog, 18 curated flagship datasets, and a
generic rows table covering all 234 catalog datasets), a ``/v1/query``
engine + seven ``/v1/lookup`` handlers, and a standalone stdlib HTTP
surface.

It mirrors the architecture of :mod:`connectors.cms_coverage` exactly and
is **stdlib-only** (``urllib`` + ``json`` + ``sqlite3`` + ``time`` +
``http.server``) so it runs in the same no-extra-deps environment as the
rest of RCM-MC.

Import surface is intentionally lazy: nothing here touches the network or
a database at import time. Construct a :class:`ProviderDataConnector` and
drive it with an injectable opener for tests, or serve the ``/v1``
surface via :mod:`connectors.provider_data.api_server`.
"""
from __future__ import annotations

from .connector import FetchResult, ProviderDataConnector
from .endpoints import ENDPOINTS, EndpointSpec, get_endpoint
from .transport import ProviderDataApiError, ProviderDataTransport, RawResponse

__all__ = [
    "ENDPOINTS",
    "EndpointSpec",
    "get_endpoint",
    "ProviderDataConnector",
    "FetchResult",
    "ProviderDataTransport",
    "RawResponse",
    "ProviderDataApiError",
]

CONNECTOR = "provider_data"
SOURCE_TAG = "provider_data"
