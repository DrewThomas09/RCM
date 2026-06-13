"""openFDA (``api.fda.gov``) PEDesk connector — full vertical slice.

This package is the self-contained openFDA workstream: connector,
declarative registry rows, normalized canonical tables, a ``/v1/query``
engine + two ``/v1/lookup`` handlers, data-quality tests, and the
continuous-operation state files (``STATE.md``, ``DECISIONS.md``,
``PROGRESS.md``).

Everything is **stdlib-only** (``urllib`` + ``json`` + ``sqlite3`` +
``time``) so it runs in the same no-extra-deps environment as the rest
of RCM-MC. Raw landing prefers parquet when ``pyarrow`` is importable
and degrades to newline-delimited JSON otherwise (see ``raw_store``).

Import surface is intentionally lazy: nothing here touches the network
or a database at import time. Construct an :class:`OpenFdaConnector`
and drive it with an injectable opener for tests, or run the
:mod:`connectors.openfda.pipeline` orchestrator for a real backfill.
"""
from __future__ import annotations

from .endpoints import ENDPOINTS, EndpointSpec, get_endpoint
from .connector import OpenFdaConnector, FetchResult
from .transport import OpenFdaTransport, RawResponse, OpenFdaApiError

__all__ = [
    "ENDPOINTS",
    "EndpointSpec",
    "get_endpoint",
    "OpenFdaConnector",
    "FetchResult",
    "OpenFdaTransport",
    "RawResponse",
    "OpenFdaApiError",
]

CONNECTOR = "openfda"
SOURCE_TAG = "openfda"
