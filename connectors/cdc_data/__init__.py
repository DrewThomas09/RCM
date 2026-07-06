"""data.cdc.gov (Socrata SODA) connector — full slice.

This package is the self-contained CDC open-data workstream: connector,
declarative registry rows, normalized canonical tables (the full
data.cdc.gov catalog + twenty-seven curated flagship datasets + a generic
any-4x4 rows table), a ``/v1/query`` engine + two ``/v1/lookup``
handlers, and a standalone stdlib HTTP surface.

It mirrors the architecture of :mod:`connectors.cms_coverage` exactly
and is **stdlib-only** (``urllib`` + ``json`` + ``sqlite3`` + ``time`` +
``http.server``) so it runs in the same no-extra-deps environment as the
rest of RCM-MC.

Import surface is intentionally lazy: nothing here touches the network or
a database at import time. Construct a :class:`CdcDataConnector` and
drive it with an injectable opener for tests, or serve the ``/v1``
surface via :mod:`connectors.cdc_data.api_server`.
"""
from __future__ import annotations

from .connector import CdcDataConnector, FetchResult
from .endpoints import ENDPOINTS, EndpointSpec, get_endpoint
from .transport import CdcDataApiError, CdcSodaTransport, RawResponse

__all__ = [
    "ENDPOINTS",
    "EndpointSpec",
    "get_endpoint",
    "CdcDataConnector",
    "FetchResult",
    "CdcSodaTransport",
    "RawResponse",
    "CdcDataApiError",
]

CONNECTOR = "cdc_data"
SOURCE_TAG = "cdc_data"
