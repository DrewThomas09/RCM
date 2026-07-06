"""BLS QCEW (Quarterly Census of Employment & Wages) connector — full slice.

This package is the self-contained BLS QCEW workstream: connector,
declarative registry rows, one normalized canonical table, a
``/v1/query`` engine + two ``/v1/lookup`` handlers, and a standalone
stdlib HTTP surface.

QCEW is the labor-market ground truth for healthcare markets: quarterly
establishment counts, monthly employment levels and wages for every
county/MSA/state x NAICS industry x ownership, straight from state UI
tax records. BLS publishes it as an **open CSV slice API** (no key)::

    https://data.bls.gov/cew/data/api/{year}/{qtr}/industry/{naics}.csv
    https://data.bls.gov/cew/data/api/{year}/{qtr}/area/{area_fips}.csv

Both slice kinds return the identical 42-column quarterly row shape, so
the two datasets (``industry_area`` / ``area_industry``) share one
canonical table sliced by ``source_endpoint``. The transport streams
CSV bytes through the same retry envelope the other connectors use.

It mirrors the architecture of :mod:`connectors.cms_coverage` /
:mod:`connectors.hrsa_data` exactly and is **stdlib-only** (``urllib``
+ ``csv`` + ``json`` + ``sqlite3`` + ``http.server``) so it runs in the
same no-extra-deps environment as the rest of RCM-MC.

Import surface is intentionally lazy: nothing here touches the network
or a database at import time. Construct a :class:`BlsQcewConnector` and
drive it with an injectable opener for tests, or serve the ``/v1``
surface via :mod:`connectors.bls_qcew.api_server`.
"""
from __future__ import annotations

from .connector import DEFAULT_MAX_ROWS, BlsQcewConnector, FetchResult
from .endpoints import (EARLIEST_YEAR, ENDPOINTS, LATEST_QTR, LATEST_YEAR,
                        EndpointSpec, get_endpoint)
from .transport import CsvResult, QcewApiError, QcewTransport, RawResponse

__all__ = [
    "ENDPOINTS",
    "EndpointSpec",
    "get_endpoint",
    "EARLIEST_YEAR",
    "LATEST_YEAR",
    "LATEST_QTR",
    "BlsQcewConnector",
    "FetchResult",
    "DEFAULT_MAX_ROWS",
    "QcewTransport",
    "CsvResult",
    "RawResponse",
    "QcewApiError",
]

CONNECTOR = "bls_qcew"
SOURCE_TAG = "bls_qcew"
