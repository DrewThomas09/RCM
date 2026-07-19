"""In-memory fake QPP API server — no socket, deterministic.

A :class:`FakeQpp` is an :data:`Opener` (``(url, headers, timeout) ->
RawResponse``) that serves canned eligibility payloads per NPI and a
canned benchmark list per year, honouring the exact routes the connector
emits (``/eligibility/npis/{npi}?year=`` and
``/submissions/public/benchmarks?year=``). It also models 404 (NPI with
no QPP record), 429 + ``Retry-After`` and 5xx so the transport's retry
path is exercised without a network.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from ..transport import RawResponse

_NPI_RE = re.compile(r"/eligibility/npis/([^/?]+)")


class FakeQpp:
    def __init__(self) -> None:
        # npi -> eligibility "data" payload (dict)
        self.eligibility: Dict[str, Dict[str, Any]] = {}
        # year -> list of benchmark dicts
        self.benchmarks: Dict[str, List[Dict[str, Any]]] = {}
        self.calls: List[str] = []
        # Scripted transient responses keyed by call index: {idx: (status, headers)}.
        self.transients: Dict[int, Any] = {}

    def add_clinician(self, npi: str, payload: Dict[str, Any]) -> "FakeQpp":
        self.eligibility[str(npi)] = dict(payload)
        return self

    def add_benchmarks(self, year: str, rows: List[Dict[str, Any]]) -> "FakeQpp":
        self.benchmarks[str(year)] = list(rows)
        return self

    def __call__(self, url: str, headers: Dict[str, str], timeout: float
                 ) -> RawResponse:
        idx = len(self.calls)
        self.calls.append(url)
        if idx in self.transients:
            status, hdrs = self.transients[idx]
            return RawResponse(status=status, headers=hdrs or {}, body=b"{}")

        from urllib.parse import urlparse
        path = urlparse(url).path
        m = _NPI_RE.search(path)
        if m:
            npi = m.group(1)
            data = self.eligibility.get(npi)
            if data is None:
                return RawResponse(status=404, body=b'{"error":"not found"}')
            return RawResponse(
                status=200, body=json.dumps({"data": data}).encode())
        if path.endswith("/submissions/public/benchmarks"):
            from urllib.parse import parse_qs
            qs = parse_qs(urlparse(url).query)
            year = qs.get("year", [""])[0]
            rows = self.benchmarks.get(year, [])
            return RawResponse(
                status=200,
                body=json.dumps({"data": {"benchmarks": rows}}).encode())
        return RawResponse(status=404, body=b'{"error":"no route"}')
