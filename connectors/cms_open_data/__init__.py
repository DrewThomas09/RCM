"""CMS Open Data (``data.cms.gov`` data-api v1) connector — full slice.

This package is the self-contained CMS Open Data workstream: the DCAT
catalog (``data.json``, every dataset data.cms.gov publishes), a set of
curated flagship datasets (Medicare utilization & payment, cost reports,
enrollments, ownership, market saturation, …) landed in canonical
snake_cased tables, and a generic on-demand row store so *any* of the
catalog's datasets can be pulled and queried without new code.

It mirrors the architecture of :mod:`connectors.cms_coverage` exactly and
is **stdlib-only** (``urllib`` + ``json`` + ``sqlite3`` + ``time`` +
``http.server``) so it runs in the same no-extra-deps environment as the
rest of RCM-MC.

Import surface is intentionally lazy: nothing here touches the network or
a database at import time. Construct a :class:`CmsOpenDataConnector` and
drive it with an injectable opener for tests, or serve the ``/v1``
surface via :mod:`connectors.cms_open_data.api_server`.
"""
from __future__ import annotations

from .connector import CmsOpenDataConnector, FetchResult
from .endpoints import ENDPOINTS, EndpointSpec, get_endpoint
from .transport import CmsOpenDataApiError, CmsOpenDataTransport, RawResponse

__all__ = [
    "ENDPOINTS",
    "EndpointSpec",
    "get_endpoint",
    "CmsOpenDataConnector",
    "FetchResult",
    "CmsOpenDataTransport",
    "RawResponse",
    "CmsOpenDataApiError",
]

CONNECTOR = "cms_open_data"
SOURCE_TAG = "cms_open_data"
