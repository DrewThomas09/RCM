"""In-memory fake CMS Coverage server for tests — no socket, deterministic.

A :class:`FakeCmsCoverage` is an :data:`Opener` (``(url, headers, timeout)
-> RawResponse``) that serves canned records per endpoint path and models
the two live pagination shapes:

  * national/local list endpoints page by an opaque, base64 ``page_token``
    cursor and wrap items in ``{"result": {..., "next_page_token", "items"}}``;
  * the contractor dimension returns every item in one ``{"count", "items"}``
    envelope.

It also models 429 + ``Retry-After`` and 5xx via a scripted ``transients``
map so the transport's retry path is exercised without a network.
"""
from __future__ import annotations

import base64
import json
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

from ..transport import RawResponse

_CONTRACTORS_PATH = "/v1/metadata/contractors"


def _encode_token(offset: int) -> str:
    raw = json.dumps({"o": offset}, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode()


def _decode_token(token: str) -> int:
    try:
        raw = base64.urlsafe_b64decode(token.encode())
        return int(json.loads(raw).get("o", 0))
    except Exception:
        return 0


class FakeCmsCoverage:
    def __init__(self, page_size: int = 2) -> None:
        self.records: Dict[str, List[Dict[str, Any]]] = {}
        self.calls: List[str] = []
        # Scripted transient responses keyed by call index: {idx: (status, headers)}.
        self.transients: Dict[int, Any] = {}
        self.page_size = page_size

    def add(self, path: str, records: List[Dict[str, Any]]) -> "FakeCmsCoverage":
        self.records[path] = list(records)
        return self

    def __call__(self, url: str, headers: Dict[str, str], timeout: float
                 ) -> RawResponse:
        idx = len(self.calls)
        self.calls.append(url)
        if idx in self.transients:
            status, hdrs = self.transients[idx]
            return RawResponse(status=status, headers=hdrs or {}, body=b"{}")

        parsed = urlparse(url)
        path = parsed.path
        qs = parse_qs(parsed.query, keep_blank_values=True)
        recs = self.records.get(path, [])

        if path.endswith(_CONTRACTORS_PATH):
            payload = {"count": len(recs), "items": recs}
            return RawResponse(status=200, body=json.dumps(payload).encode())

        # Paginated national/local list: opaque page_token → offset.
        limit = int(qs.get("limit", [str(self.page_size)])[0])
        token = qs.get("page_token", [None])[0]
        offset = _decode_token(token) if token else 0
        total = len(recs)
        page = recs[offset:offset + limit]
        next_offset = offset + limit
        result: Dict[str, Any] = {
            "count": len(page),
            "total": total,
            "next_page_token": _encode_token(next_offset) if next_offset < total else None,
            "items": page,
        }
        return RawResponse(status=200, body=json.dumps({"result": result}).encode())
