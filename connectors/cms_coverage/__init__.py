"""CMS Coverage API (``api.coverage.cms.gov``) connector — full slice.

This package is the self-contained CMS Coverage (Medicare Coverage
Database) workstream: connector, declarative registry rows, normalized
canonical tables, a ``/v1/query`` engine + two ``/v1/lookup`` handlers,
and a standalone stdlib HTTP surface.

It mirrors the architecture of :mod:`connectors.openfda` exactly and is
**stdlib-only** (``urllib`` + ``json`` + ``sqlite3`` + ``time`` +
``http.server``) so it runs in the same no-extra-deps environment as the
rest of RCM-MC.

Import surface is intentionally lazy: nothing here touches the network or
a database at import time. Construct a :class:`CmsCoverageConnector` and
drive it with an injectable opener for tests, or serve the ``/v1``
surface via :mod:`connectors.cms_coverage.api_server`.
"""
from __future__ import annotations

from .connector import CmsCoverageConnector, FetchResult
from .endpoints import ENDPOINTS, EndpointSpec, get_endpoint
from .transport import CmsCoverageApiError, CmsCoverageTransport, RawResponse

__all__ = [
    "ENDPOINTS",
    "EndpointSpec",
    "get_endpoint",
    "CmsCoverageConnector",
    "FetchResult",
    "CmsCoverageTransport",
    "RawResponse",
    "CmsCoverageApiError",
]

CONNECTOR = "cms_coverage"
SOURCE_TAG = "cms_coverage"
