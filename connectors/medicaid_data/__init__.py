"""data.medicaid.gov (DKAN) connector — full slice.

This package is the self-contained data.medicaid.gov workstream:
connector, declarative registry rows, normalized canonical tables (the
full 541-dataset DKAN catalog, curated NADAC/SDUD/rebate/enrollment/
managed-care/FUL/quality flagships, and a generic fetched-rows escape
hatch), a ``/v1/query`` engine + three ``/v1/lookup`` handlers, and a
standalone stdlib HTTP surface.

It mirrors the architecture of :mod:`connectors.cms_coverage` exactly and
is **stdlib-only** (``urllib`` + ``json`` + ``sqlite3`` + ``time`` +
``http.server``) so it runs in the same no-extra-deps environment as the
rest of RCM-MC.

Import surface is intentionally lazy: nothing here touches the network or
a database at import time. Construct a :class:`MedicaidDataConnector` and
drive it with an injectable opener for tests, or serve the ``/v1``
surface via :mod:`connectors.medicaid_data.api_server`.
"""
from __future__ import annotations

from .connector import FetchResult, MedicaidDataConnector
from .endpoints import ENDPOINTS, EndpointSpec, get_endpoint
from .transport import MedicaidDataApiError, MedicaidDataTransport, RawResponse

__all__ = [
    "ENDPOINTS",
    "EndpointSpec",
    "get_endpoint",
    "MedicaidDataConnector",
    "FetchResult",
    "MedicaidDataTransport",
    "RawResponse",
    "MedicaidDataApiError",
]

CONNECTOR = "medicaid_data"
SOURCE_TAG = "medicaid_data"
