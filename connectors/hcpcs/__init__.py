"""HCPCS Level II (NLM Clinical Tables) connector — self-contained slice.

This package is the HCPCS workstream: a connector over the NLM Clinical
Tables API (``clinicaltables.nlm.nih.gov/api/hcpcs/v3``) for CMS's HCPCS
Level II code set — the national billing vocabulary for DME (E-codes),
incident-to drugs (J-codes), ambulance (A-codes), orthotics/prosthetics
(L-codes) and the temporary G/K/Q/S/T ranges — declarative registry rows,
a normalized canonical table (``dim_hcpcs_code``), a ``/v1/query`` engine
+ lookup/search handlers, and a standalone stdlib HTTP surface.

``code`` joins straight onto the data.cms.gov utilization files' HCPCS
columns (Physician & Other Practitioners by service, PSPS, RBCS, DMEPOS),
making this the code dimension for every procedure-level Medicare fact
table already in the estate. HCPCS Level I (CPT) is AMA-licensed with no
public API and is deliberately out of scope.

Everything is **stdlib-only** (``urllib`` + ``json`` + ``sqlite3`` +
``time`` + ``http.server``) so it runs in the same no-extra-deps
environment as the rest of RCM-MC. The NLM API is public and keyless and
shares its top-level JSON-array response shape (``[total, [codes], hash,
[rows]]``) with the ICD-10 endpoints this estate already drains.

Import surface is intentionally lazy: nothing here touches the network or
a database at import time.
"""
from __future__ import annotations

from .connector import FetchResult, HcpcsConnector
from .endpoints import ENDPOINTS, EndpointSpec, get_endpoint
from .transport import NlmApiError, NlmTransport, RawResponse

__all__ = [
    "ENDPOINTS",
    "EndpointSpec",
    "get_endpoint",
    "HcpcsConnector",
    "FetchResult",
    "NlmTransport",
    "RawResponse",
    "NlmApiError",
]

CONNECTOR = "hcpcs"
SOURCE_TAG = "hcpcs"
