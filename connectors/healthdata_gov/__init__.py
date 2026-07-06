"""healthdata.gov (HHS-wide Socrata meta-catalog) connector — full slice.

This package is the self-contained HHS open-data workstream: connector,
declarative registry rows, normalized canonical tables (the full
healthdata.gov catalog + eight curated NATIVE flagship datasets + a
generic any-4x4 rows table), a ``/v1/query`` engine + two ``/v1/lookup``
handlers, and a standalone stdlib HTTP surface.

healthdata.gov is the HHS-wide *meta*-catalog: most of its entries are
federated pointers whose home is another portal the estate already
covers (data.cdc.gov, data.cms.gov, data.medicaid.gov, HRSA, PDC …), so
the curated slice deliberately carries only datasets whose home IS
healthdata.gov — chiefly the HHS Protect COVID-era hospital capacity /
utilization reporting system — while the catalog table records the
``domain``/``attribution`` of every entry so mirrors stay identifiable.

It mirrors the architecture of :mod:`connectors.cdc_data` (same Socrata
platform, same paging quirks) and is **stdlib-only** (``urllib`` +
``json`` + ``sqlite3`` + ``time`` + ``http.server``) so it runs in the
same no-extra-deps environment as the rest of RCM-MC.

Import surface is intentionally lazy: nothing here touches the network or
a database at import time. Construct a :class:`HealthdataGovConnector`
and drive it with an injectable opener for tests, or serve the ``/v1``
surface via :mod:`connectors.healthdata_gov.api_server`.
"""
from __future__ import annotations

from .connector import FetchResult, HealthdataGovConnector
from .endpoints import ENDPOINTS, EndpointSpec, get_endpoint
from .transport import HealthdataGovApiError, HealthdataSodaTransport, RawResponse

__all__ = [
    "ENDPOINTS",
    "EndpointSpec",
    "get_endpoint",
    "HealthdataGovConnector",
    "FetchResult",
    "HealthdataSodaTransport",
    "RawResponse",
    "HealthdataGovApiError",
]

CONNECTOR = "healthdata_gov"
SOURCE_TAG = "healthdata_gov"
