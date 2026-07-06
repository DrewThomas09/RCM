"""NIH RePORTER v2 API (``api.reporter.nih.gov``) connector — full slice.

This package is the self-contained NIH RePORTER workstream: connector,
declarative registry rows, normalized canonical tables (funded projects +
project↔publication link edges), a ``/v1/query`` engine + two
``/v1/lookup`` handlers, and a standalone stdlib HTTP surface.

It mirrors the architecture of :mod:`connectors.cms_coverage` exactly and
is **stdlib-only** (``urllib`` + ``json`` + ``sqlite3`` + ``time`` +
``http.server``) so it runs in the same no-extra-deps environment as the
rest of RCM-MC. The one shape difference from the estate's GET
connectors: RePORTER searches are HTTP **POSTs** with a JSON body, so the
transport's workhorse is ``post_json`` (same retry envelope, injectable
opener carrying the encoded body).

Import surface is intentionally lazy: nothing here touches the network or
a database at import time. Construct a :class:`NihReporterConnector` and
drive it with an injectable opener for tests, or serve the ``/v1``
surface via :mod:`connectors.nih_reporter.api_server`.
"""
from __future__ import annotations

from .connector import FetchResult, NihReporterConnector
from .endpoints import ENDPOINTS, EndpointSpec, get_endpoint
from .transport import NihReporterApiError, NihReporterTransport, RawResponse

__all__ = [
    "ENDPOINTS",
    "EndpointSpec",
    "get_endpoint",
    "NihReporterConnector",
    "FetchResult",
    "NihReporterTransport",
    "RawResponse",
    "NihReporterApiError",
]

CONNECTOR = "nih_reporter"
SOURCE_TAG = "nih_reporter"
