"""HRSA data downloads (``data.hrsa.gov``) connector — full slice.

This package is the self-contained HRSA workstream: connector,
declarative registry rows, normalized canonical tables, a ``/v1/query``
engine + two ``/v1/lookup`` handlers, and a standalone stdlib HTTP
surface.

Unlike the JSON-API connectors, HRSA publishes no query API for these
datasets — it publishes stable **CSV file downloads** under
``https://data.hrsa.gov/DataDownload/DD_Files/{NAME}.csv`` (Health
Professional Shortage Areas for three disciplines, Medically Underserved
Areas/Populations, and Health Center Program service delivery sites).
The transport therefore streams CSV bytes through the same retry
envelope the other connectors use, and ``max_rows`` caps ingest because
the files run 10-60 MB.

It mirrors the architecture of :mod:`connectors.cms_coverage` exactly
and is **stdlib-only** (``urllib`` + ``csv`` + ``json`` + ``sqlite3`` +
``http.server``) so it runs in the same no-extra-deps environment as the
rest of RCM-MC.

Import surface is intentionally lazy: nothing here touches the network
or a database at import time. Construct a :class:`HrsaDataConnector` and
drive it with an injectable opener for tests, or serve the ``/v1``
surface via :mod:`connectors.hrsa_data.api_server`.
"""
from __future__ import annotations

from .connector import DEFAULT_MAX_ROWS, FetchResult, HrsaDataConnector
from .endpoints import ENDPOINTS, EndpointSpec, get_endpoint
from .transport import CsvResult, HrsaApiError, HrsaTransport, RawResponse

__all__ = [
    "ENDPOINTS",
    "EndpointSpec",
    "get_endpoint",
    "HrsaDataConnector",
    "FetchResult",
    "DEFAULT_MAX_ROWS",
    "HrsaTransport",
    "CsvResult",
    "RawResponse",
    "HrsaApiError",
]

CONNECTOR = "hrsa_data"
SOURCE_TAG = "hrsa_data"
