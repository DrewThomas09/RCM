"""CMS Quality Payment Program (QPP) connector — self-contained slice.

This package is the QPP workstream: a connector over the public, keyless
QPP API (``qpp.cms.gov/api``) for MACRA's MIPS/APM clinician payment-
adjustment program — the Eligibility API (clinician MIPS eligibility,
specialty, and practice organizations by NPI x performance year) and the
Submissions API's public quality-measure benchmarks (deciles by
submission method per year) — declarative registry rows, normalized
canonical tables (``qpp_clinician`` / ``qpp_organization`` /
``qpp_benchmark``), a ``/v1/query`` engine + lookup handlers, and a
standalone stdlib HTTP surface.

``npi`` joins straight onto the estate's NPPES provider universe and the
data.cms.gov utilization files, adding the MIPS/APM program dimension to
every clinician already tracked. Eligibility pulls are roster-driven
(per-NPI, like the NPI Registry connector); benchmarks pull unattended,
one request per performance year.

Everything is **stdlib-only** (``urllib`` + ``json`` + ``sqlite3`` +
``time`` + ``http.server``) so it runs in the same no-extra-deps
environment as the rest of RCM-MC. The QPP API answers top-level JSON
**objects** (``{"data": {...}}``), so the transport requires a dict —
the openFDA shape, not the NLM array shape.

Import surface is intentionally lazy: nothing here touches the network or
a database at import time.
"""
from __future__ import annotations

from .connector import FetchResult, QppConnector
from .endpoints import DEFAULT_YEAR, ENDPOINTS, EndpointSpec, get_endpoint
from .transport import QppApiError, QppTransport, RawResponse

__all__ = [
    "DEFAULT_YEAR",
    "ENDPOINTS",
    "EndpointSpec",
    "get_endpoint",
    "QppConnector",
    "FetchResult",
    "QppTransport",
    "RawResponse",
    "QppApiError",
]

CONNECTOR = "qpp"
SOURCE_TAG = "qpp"
