"""In-memory fake openFDA server for tests — no socket, fully deterministic.

A :class:`FakeFda` is an :data:`Opener` (``(url, headers, timeout) ->
RawResponse``) that serves canned records per endpoint path and honours
the subset of openFDA's query language the connector emits:
``limit``/``skip`` paging, ``meta.results.total``, ``search`` date-range
``field:[a TO b]``, ``field.exact:"term"`` partition filters, and the
``count=`` aggregation. It also models 429 + ``Retry-After`` and 5xx so
the transport's retry path is exercised without a network.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, unquote_plus, urlparse

from ..transport import RawResponse

_RANGE_RE = re.compile(r"([\w.]+):\[(\S+)\s+TO\s+(\S+)\]")
_EXACT_RE = re.compile(r'([\w.]+)\.exact:"([^"]+)"')


def _dig(rec: Any, path: str) -> Any:
    cur = rec
    for seg in path.replace(".exact", "").split("."):
        if isinstance(cur, list):
            cur = cur[0] if cur else None
        if isinstance(cur, dict):
            cur = cur.get(seg)
        else:
            return None
    return cur


class FakeFda:
    def __init__(self) -> None:
        self.records: Dict[str, List[Dict[str, Any]]] = {}
        self.calls: List[str] = []
        # Scripted transient responses keyed by call index: {idx: (status, headers)}.
        self.transients: Dict[int, Any] = {}

    def add(self, path: str, records: List[Dict[str, Any]]) -> "FakeFda":
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

        search = unquote_plus(qs.get("search", [""])[0])
        recs = self._filter(recs, search)

        if "count" in qs:
            return self._count(recs, qs["count"][0])

        limit = int(qs.get("limit", ["1"])[0])
        skip = int(qs.get("skip", ["0"])[0])
        total = len(recs)
        page = recs[skip:skip + limit]
        payload = {
            "meta": {"results": {"skip": skip, "limit": limit, "total": total}},
            "results": page,
        }
        if not page and skip == 0 and total == 0:
            # openFDA returns 404 NOT_FOUND for an empty match.
            return RawResponse(status=404, body=b'{"error":{"code":"NOT_FOUND"}}')
        return RawResponse(status=200, body=json.dumps(payload).encode())

    def _filter(self, recs: List[Dict[str, Any]], search: str
                ) -> List[Dict[str, Any]]:
        if not search:
            return recs
        out = recs
        for field_name, lo, hi in _RANGE_RE.findall(search):
            out = [r for r in out
                   if (_dig(r, field_name) is not None
                       and str(lo) <= str(_dig(r, field_name)) <= str(hi))]
        for field_name, term in _EXACT_RE.findall(search):
            out = [r for r in out if str(_dig(r, field_name)) == term]
        return out

    def _count(self, recs: List[Dict[str, Any]], field_name: str) -> RawResponse:
        counts: Dict[str, int] = {}
        for r in recs:
            val = _dig(r, field_name)
            if val is None:
                continue
            counts[str(val)] = counts.get(str(val), 0) + 1
        results = [{"term": k, "count": v}
                   for k, v in sorted(counts.items(), key=lambda x: -x[1])]
        payload = {"meta": {"results": {"total": len(counts)}}, "results": results}
        return RawResponse(status=200, body=json.dumps(payload).encode())
