"""HHS OIG LEIE (``oig.hhs.gov``) connector — provider-exclusion screening.

This package is the self-contained OIG exclusion-list workstream:
connector, declarative registry rows, normalized canonical tables, a
``/v1/query`` engine + two ``/v1/lookup`` handlers, and a standalone
stdlib HTTP surface.

The List of Excluded Individuals/Entities is the compliance list every
RCM provider screen must consult: individuals and entities excluded from
participation in Medicare/Medicaid and all federal health care programs.
OIG publishes no query API — it publishes stable **CSV file downloads**:
a full-replacement database (``UPDATED.csv``, ~83k rows / ~15 MB,
refreshed monthly) plus monthly supplement files of new exclusions and
reinstatements. The transport therefore streams CSV bytes through the
same retry envelope the other connectors use, and ``max_rows`` caps
ingest (the default cap covers the whole full file — a compliance list
must not be silently partial).

Two normalizations make the data safe to screen against: the NPI
unknown-sentinel ``0000000000`` becomes ``''`` (so an NPI join can never
"match" the ~85% of rows without one), and ``yyyymmdd`` dates with the
``00000000`` null-sentinel become ISO ``yyyy-mm-dd`` or ``''``.

It mirrors the architecture of :mod:`connectors.cms_coverage` exactly
(via the CSV-download shape of :mod:`connectors.hrsa_data`) and is
**stdlib-only** (``urllib`` + ``csv`` + ``json`` + ``sqlite3`` +
``http.server``) so it runs in the same no-extra-deps environment as the
rest of RCM-MC.

Import surface is intentionally lazy: nothing here touches the network
or a database at import time. Construct an :class:`OigLeieConnector` and
drive it with an injectable opener for tests, or serve the ``/v1``
surface via :mod:`connectors.oig_leie.api_server`.
"""
from __future__ import annotations

from .connector import (DEFAULT_MAX_ROWS, SUPPLEMENT_LOOKBACK_MONTHS,
                        FetchResult, OigLeieConnector)
from .endpoints import ENDPOINTS, EndpointSpec, get_endpoint, supplement_path
from .transport import CsvResult, OigLeieApiError, OigLeieTransport, RawResponse

__all__ = [
    "ENDPOINTS",
    "EndpointSpec",
    "get_endpoint",
    "supplement_path",
    "OigLeieConnector",
    "FetchResult",
    "DEFAULT_MAX_ROWS",
    "SUPPLEMENT_LOOKBACK_MONTHS",
    "OigLeieTransport",
    "CsvResult",
    "RawResponse",
    "OigLeieApiError",
]

CONNECTOR = "oig_leie"
SOURCE_TAG = "oig_leie"
