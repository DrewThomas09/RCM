"""In-memory fake NLM Clinical Tables server — no socket, deterministic.

A :class:`FakeNlm` is an :data:`Opener` (``(url, headers, timeout) ->
RawResponse``) that serves canned HCPCS records per endpoint path and
honours the subset of the NLM query language the connector emits:
``offset``/``maxList`` paging, the ``q=code:PREFIX*`` prefix filter, a
``terms`` substring match, and the 4-element **JSON array** response
shape ``[total, [codes], hash, [rows]]``. It also models 429 +
``Retry-After`` and 5xx so the transport's retry path is exercised
without a network.

Records are plain dicts (e.g. ``{"code": "J9271", "display": "..."}``);
the display rows a request returns are projected over the requested
``df`` columns, *including only the fields the record actually has* — so
a record lacking ``long_desc`` yields a narrower row and exercises the
connector's variable-df-width handling.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from ..transport import RawResponse

_PREFIX_RE = re.compile(r"code:(.*?)\*?$")


class FakeNlm:
    def __init__(self) -> None:
        self.records: Dict[str, List[Dict[str, Any]]] = {}
        self.calls: List[str] = []
        # Scripted transient responses keyed by call index: {idx: (status, headers)}.
        self.transients: Dict[int, Any] = {}

    def add(self, path: str, records: List[Dict[str, Any]]) -> "FakeNlm":
        self.records[path] = list(records)
        return self

    def __call__(self, url: str, headers: Dict[str, str], timeout: float
                 ) -> RawResponse:
        idx = len(self.calls)
        self.calls.append(url)
        if idx in self.transients:
            status, hdrs = self.transients[idx]
            return RawResponse(status=status, headers=hdrs or {}, body=b"[]")

        from urllib.parse import parse_qs, unquote_plus, urlparse
        parsed = urlparse(url)
        path = parsed.path
        qs = parse_qs(parsed.query, keep_blank_values=True)
        # The base URL carries an "/api" path segment, so the request path is
        # "/api/icd10cm/v3/search"; match canned records by endpoint suffix.
        recs = self._records_for(path)

        q = unquote_plus(qs.get("q", [""])[0])
        recs = self._filter_prefix(recs, q)
        terms = unquote_plus(qs.get("terms", [""])[0])
        recs = self._filter_terms(recs, terms)

        df = unquote_plus(qs.get("df", ["code,display"])[0]).split(",")
        total = len(recs)
        offset = int(qs.get("offset", ["0"])[0])
        max_list = int((qs.get("maxList") or qs.get("count") or ["7"])[0])
        page = recs[offset:offset + max_list]

        codes = [r.get(df[0]) for r in page]
        # Variable df width: only emit fields the record actually carries.
        disp = [[r[f] for f in df if f in r and r.get(f) not in (None, "")]
                for r in page]
        payload = [total, codes, None, disp]
        return RawResponse(status=200, body=json.dumps(payload).encode())

    def _records_for(self, path: str) -> List[Dict[str, Any]]:
        if path in self.records:
            return self.records[path]
        for key, recs in self.records.items():
            if path == key or path.endswith(key):
                return recs
        return []

    def _filter_prefix(self, recs: List[Dict[str, Any]], q: str
                       ) -> List[Dict[str, Any]]:
        if not q:
            return recs
        m = _PREFIX_RE.match(q.strip())
        if not m:
            return recs
        prefix = m.group(1)
        return [r for r in recs if str(r.get("code", "")).startswith(prefix)]

    def _filter_terms(self, recs: List[Dict[str, Any]], terms: str
                      ) -> List[Dict[str, Any]]:
        if not terms:
            return recs
        t = terms.lower()
        return [r for r in recs
                if t in str(r.get("code", "")).lower()
                or t in str(r.get("display", "")).lower()]
