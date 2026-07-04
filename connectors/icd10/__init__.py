"""ICD-10 (NLM Clinical Tables) connector — self-contained vertical slice.

This package is the ICD-10 workstream: a connector over the NLM Clinical
Tables API (``clinicaltables.nlm.nih.gov/api``) for ICD-10-CM diagnoses
and ICD-10-PCS procedures, declarative registry rows, a normalized
canonical table (``dim_icd10_code``), a ``/v1/query`` engine + lookup /
search handlers, and a standalone stdlib HTTP surface.

Everything is **stdlib-only** (``urllib`` + ``json`` + ``sqlite3`` +
``time`` + ``http.server``) so it runs in the same no-extra-deps
environment as the rest of RCM-MC. The NLM API is public and keyless.

The one shape wrinkle versus the openFDA connector: the NLM API answers
with a top-level **JSON array** (``[total, [codes], hash, [rows]]``), so
the transport's ``get_json`` returns a list, not a dict.

Import surface is intentionally lazy: nothing here touches the network or
a database at import time.
"""
from __future__ import annotations

from .connector import FetchResult, Icd10Connector
from .endpoints import ENDPOINTS, EndpointSpec, get_endpoint
from .transport import NlmApiError, NlmTransport, RawResponse

__all__ = [
    "ENDPOINTS",
    "EndpointSpec",
    "get_endpoint",
    "Icd10Connector",
    "FetchResult",
    "NlmTransport",
    "RawResponse",
    "NlmApiError",
]

CONNECTOR = "icd10"
SOURCE_TAG = "icd10"
