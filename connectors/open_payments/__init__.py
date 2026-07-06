"""CMS Open Payments (``openpaymentsdata.cms.gov``) connector — full slice.

This package is the self-contained CMS Open Payments (Sunshine Act)
workstream: connector, declarative registry rows, normalized canonical
tables, a ``/v1/query`` engine + three ``/v1/lookup`` handlers, and a
standalone stdlib HTTP surface.

Open Payments is a DKAN open-data catalog (the same engine as
``data.medicaid.gov``): 74 datasets covering general / research /
ownership payment detail files per program year, covered-recipient
profiles, and pre-aggregated summaries. This connector models it three
ways so "every dataset connected" stays true without ever bulk-pulling a
15M-row payment file:

  1. the full dataset **catalog** (one row per dataset, synced by
     ``discover()``),
  2. **curated** 2024 payment / profile / summary datasets, each a
     first-class canonical table with the live-sampled column set,
  3. a **generic** fetched-rows table so any of the 74 datasets (any
     older program year) can be pulled on demand by its catalog UUID.

It mirrors the architecture of :mod:`connectors.cms_coverage` exactly
and is **stdlib-only** (``urllib`` + ``json`` + ``sqlite3`` + ``time`` +
``http.server``) so it runs in the same no-extra-deps environment as the
rest of RCM-MC.

Import surface is intentionally lazy: nothing here touches the network
or a database at import time. Construct an :class:`OpenPaymentsConnector`
and drive it with an injectable opener for tests, or serve the ``/v1``
surface via :mod:`connectors.open_payments.api_server`.
"""
from __future__ import annotations

from .connector import FetchResult, OpenPaymentsConnector
from .endpoints import ENDPOINTS, EndpointSpec, get_endpoint
from .transport import OpenPaymentsApiError, OpenPaymentsTransport, RawResponse

__all__ = [
    "ENDPOINTS",
    "EndpointSpec",
    "get_endpoint",
    "OpenPaymentsConnector",
    "FetchResult",
    "OpenPaymentsTransport",
    "RawResponse",
    "OpenPaymentsApiError",
]

CONNECTOR = "open_payments"
SOURCE_TAG = "open_payments"
