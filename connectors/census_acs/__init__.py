"""US Census ACS 5-year API (``api.census.gov``) connector — full slice.

This package is the self-contained Census ACS workstream: connector,
declarative registry rows, normalized canonical tables (county / state /
CBSA demographic profiles), a ``/v1/query`` engine + two ``/v1/lookup``
handlers, and a standalone stdlib HTTP surface.

It mirrors the architecture of :mod:`connectors.cms_coverage` exactly and
is **stdlib-only** (``urllib`` + ``json`` + ``sqlite3`` + ``time`` +
``http.server``) so it runs in the same no-extra-deps environment as the
rest of RCM-MC.

Import surface is intentionally lazy: nothing here touches the network or
a database at import time. Construct a :class:`CensusAcsConnector` and
drive it with an injectable opener for tests, or serve the ``/v1``
surface via :mod:`connectors.census_acs.api_server`. Live data fetches
need ``$CENSUS_API_KEY`` — api.census.gov requires a key on every data
request (see :mod:`connectors.census_acs.transport`).
"""
from __future__ import annotations

from .connector import CensusAcsConnector, FetchResult
from .endpoints import (DEFAULT_YEAR, DETAIL_VARIABLES, ENDPOINTS,
                        SUBJECT_VARIABLES, EndpointSpec, get_endpoint)
from .transport import CensusAcsApiError, CensusAcsTransport, RawResponse

__all__ = [
    "DEFAULT_YEAR",
    "DETAIL_VARIABLES",
    "SUBJECT_VARIABLES",
    "ENDPOINTS",
    "EndpointSpec",
    "get_endpoint",
    "CensusAcsConnector",
    "FetchResult",
    "CensusAcsTransport",
    "RawResponse",
    "CensusAcsApiError",
]

CONNECTOR = "census_acs"
SOURCE_TAG = "census_acs"
