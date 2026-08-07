"""RxNorm (NLM RxNav) connector — self-contained vertical slice.

This package is the RxNorm workstream: a connector over the public,
keyless RxNav REST API (``rxnav.nlm.nih.gov/REST``) resolving NDCs and
free-text drug names to a stable ``rxcui``, its ingredient set, and its
ATC / DailyMed pharmacologic class — declarative registry rows,
normalized canonical tables (``dim_rxnorm_concept`` +
``xwalk_ndc_rxcui`` + ``xwalk_name_rxcui``), a ``/v1/query`` engine +
lookup handlers, and a standalone stdlib HTTP surface.

Why it belongs in a CMS estate: RxNorm is the **join dimension for drug
money**. Medicaid NADAC and State Drug Utilization (``medicaid_data``),
Medicare Part B and Part D spending by drug (``cms_open_data``), and the
openFDA NDC directory all identify products by NDC or by a label name.
RxNorm turns those into per-ingredient and per-class spend — the same
role ``icd10`` plays for diagnoses and ``hcpcs`` for procedures.

Every dataset is roster-driven (RxNav resolves one identifier per
request), so ingest is manual like the NPI Registry connector: feed it a
distinct-NDC list from the tables above.

Everything is **stdlib-only** (``urllib`` + ``json`` + ``sqlite3`` +
``time`` + ``http.server``) so it runs in the same no-extra-deps
environment as the rest of RCM-MC. RxNav answers top-level JSON
**objects** under per-endpoint envelope keys, so the transport requires
a dict — not the array shape the NLM Clinical Tables connectors drain.

Import surface is intentionally lazy: nothing here touches the network or
a database at import time.
"""
from __future__ import annotations

from .connector import FetchResult, RxNormConnector
from .endpoints import ENDPOINTS, EndpointSpec, get_endpoint
from .transport import RawResponse, RxNavApiError, RxNavTransport

__all__ = [
    "ENDPOINTS",
    "EndpointSpec",
    "get_endpoint",
    "RxNormConnector",
    "FetchResult",
    "RxNavTransport",
    "RawResponse",
    "RxNavApiError",
]

CONNECTOR = "rxnorm"
SOURCE_TAG = "rxnorm"
