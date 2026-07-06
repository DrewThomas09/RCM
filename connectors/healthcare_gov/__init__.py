"""data.healthcare.gov (DKAN Marketplace catalog) connector — full slice.

This package is the self-contained data.healthcare.gov workstream:
connector, declarative registry rows, normalized canonical tables, a
``/v1/query`` engine + two ``/v1/lookup`` handlers, and a standalone
stdlib HTTP surface.

It covers the ENTIRE catalog three ways: a synced catalog table (every
dataset's metadata), curated canonical tables for the flagship
Marketplace PY2026 public-use files (Plan Attributes, Benefits and Cost
Sharing, Rates, Quality, Service Areas — the datasets that are actually
queryable through the DKAN datastore), and a generic rows table any
other catalog dataset can be pulled into on demand by its DKAN id.

It mirrors the architecture of :mod:`connectors.cms_coverage` exactly
and is **stdlib-only** (``urllib`` + ``json`` + ``sqlite3`` + ``time`` +
``http.server``) so it runs in the same no-extra-deps environment as the
rest of the estate.

Import surface is intentionally lazy: nothing here touches the network
or a database at import time. Construct a
:class:`HealthcareGovConnector` and drive it with an injectable opener
for tests, or serve the ``/v1`` surface via
:mod:`connectors.healthcare_gov.api_server`.
"""
from __future__ import annotations

from .connector import FetchResult, HealthcareGovConnector
from .endpoints import ENDPOINTS, EndpointSpec, get_endpoint
from .transport import HealthcareGovApiError, HealthcareGovTransport, RawResponse

__all__ = [
    "ENDPOINTS",
    "EndpointSpec",
    "get_endpoint",
    "HealthcareGovConnector",
    "FetchResult",
    "HealthcareGovTransport",
    "RawResponse",
    "HealthcareGovApiError",
]

CONNECTOR = "healthcare_gov"
SOURCE_TAG = "healthcare_gov"
