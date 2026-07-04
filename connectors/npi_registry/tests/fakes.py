"""In-memory fake NPPES server for tests — no socket, fully deterministic.

A :class:`FakeNppes` is an :data:`Opener` (``(url, headers, timeout) ->
RawResponse``) that serves canned NPI records and honours the subset of
the NPI Registry query language the connector emits: ``limit``/``skip``
paging with ``result_count``, and simple equality filters on
``enumeration_type``/``state``/``number``. It also models 429 +
``Retry-After`` and 5xx so the transport's retry path is exercised
without a network.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List
from urllib.parse import parse_qs, urlparse

from ..transport import RawResponse

# A canned individual (NPI-1) record mirroring the NPPES v2.1 shape.
INDIVIDUAL: Dict[str, Any] = {
    "number": "1234567893",
    "enumeration_type": "NPI-1",
    "created_epoch": 1173974400,
    "last_updated_epoch": 1700000000,
    "basic": {
        "first_name": "JANE", "last_name": "DOE", "credential": "MD",
        "sole_proprietor": "NO", "gender": "F",
        "enumeration_date": "2007-03-15", "last_updated": "2023-11-14",
        "status": "A", "name_prefix": "DR.",
    },
    "addresses": [
        {"country_code": "US", "address_purpose": "LOCATION",
         "address_1": "123 MAIN ST", "city": "BALTIMORE", "state": "MD",
         "postal_code": "212011234", "telephone_number": "410-555-1212"},
        {"country_code": "US", "address_purpose": "MAILING",
         "address_1": "PO BOX 7", "city": "BALTIMORE", "state": "MD",
         "postal_code": "21201"},
    ],
    "taxonomies": [
        {"code": "207RC0000X", "desc": "Cardiovascular Disease",
         "primary": True, "state": "MD", "license": "12345"},
        {"code": "207R00000X", "desc": "Internal Medicine",
         "primary": False, "state": "MD", "license": "12346"},
    ],
    "identifiers": [{"identifier": "X1", "code": "05", "desc": "MEDICAID",
                     "state": "MD"}],
    "other_names": [],
}

# A canned organization (NPI-2) record.
ORGANIZATION: Dict[str, Any] = {
    "number": "1245319599",
    "enumeration_type": "NPI-2",
    "created_epoch": 1200000000,
    "last_updated_epoch": 1699000000,
    "basic": {
        "organization_name": "GENERAL HOSPITAL",
        "authorized_official_first_name": "JOHN",
        "authorized_official_last_name": "SMITH",
        "authorized_official_title": "CEO",
        "status": "A", "last_updated": "2022-05-01",
        "enumeration_date": "2008-01-10",
    },
    "addresses": [
        {"country_code": "US", "address_purpose": "LOCATION",
         "address_1": "1 HEALTH PLZ", "city": "NEW YORK", "state": "NY",
         "postal_code": "100160000", "telephone_number": "212-555-2000"},
    ],
    "taxonomies": [
        {"code": "282N00000X", "desc": "General Acute Care Hospital",
         "primary": True, "state": "NY", "license": "H-9"},
    ],
    "identifiers": [],
    "other_names": [],
}


def make_records(base: Dict[str, Any], n: int, start: int = 0
                 ) -> List[Dict[str, Any]]:
    """Clone ``base`` ``n`` times with distinct 10-digit NPI numbers."""
    out = []
    for i in range(start, start + n):
        rec = json.loads(json.dumps(base))  # deep copy
        rec["number"] = str(1000000000 + i)
        out.append(rec)
    return out


class FakeNppes:
    def __init__(self, records: List[Dict[str, Any]] | None = None) -> None:
        self.records: List[Dict[str, Any]] = list(records or [])
        self.calls: List[str] = []
        # Scripted transient responses keyed by call index: {idx: (status, headers)}.
        self.transients: Dict[int, Any] = {}

    def add(self, records: List[Dict[str, Any]]) -> "FakeNppes":
        self.records.extend(records)
        return self

    def __call__(self, url: str, headers: Dict[str, str], timeout: float
                 ) -> RawResponse:
        idx = len(self.calls)
        self.calls.append(url)
        if idx in self.transients:
            status, hdrs = self.transients[idx]
            return RawResponse(status=status, headers=hdrs or {}, body=b"{}")

        qs = parse_qs(urlparse(url).query, keep_blank_values=True)
        recs = self._filter(self.records, qs)

        limit = int(qs.get("limit", ["1"])[0])
        skip = int(qs.get("skip", ["0"])[0])
        total = len(recs)
        page = recs[skip:skip + limit]
        payload = {"result_count": len(page), "results": page}
        # NPPES echoes result_count as the size of the returned page.
        return RawResponse(status=200, body=json.dumps(payload).encode())

    def _filter(self, recs: List[Dict[str, Any]], qs: Dict[str, List[str]]
                ) -> List[Dict[str, Any]]:
        out = recs
        et = qs.get("enumeration_type", [None])[0]
        if et:
            out = [r for r in out if r.get("enumeration_type") == et]
        st = qs.get("state", [None])[0]
        if st:
            out = [r for r in out
                   if any(a.get("state") == st for a in r.get("addresses", []))]
        num = qs.get("number", [None])[0]
        if num:
            out = [r for r in out if str(r.get("number")) == num]
        return out
