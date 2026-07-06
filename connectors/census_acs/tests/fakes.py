"""In-memory fake Census ACS server for tests — no socket, deterministic.

A :class:`FakeCensusApi` is an :data:`Opener` (``(url, headers, timeout)
-> RawResponse``) that serves canned **array-of-arrays** payloads keyed
by ``(dataset path, geography)`` — the same two axes the live API routes
on. Fixtures below mirror the REAL response shapes probed live on
2026-07-06 (variable ids and the CBSA geography string were verified
against the 2023 vintage's keyless metadata endpoints; the
array-of-arrays envelope, header row first with geography columns
appended last, is the documented and long-stable ACS shape).

It also models scripted transients (429 + ``Retry-After``, 5xx) and the
API's missing-key HTML page so the transport's retry and key-error paths
are exercised without a network.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple
from urllib.parse import parse_qs, urlparse

from ..transport import RawResponse

_CBSA_GEO = "metropolitan statistical area/micropolitan statistical area"

# The literal body api.census.gov serves (after the 302) when the key is
# missing — reproduced so the transport's detection is tested verbatim.
MISSING_KEY_HTML = (
    b"<html>\n    <head>\n        <title>Missing Key</title>\n    </head>\n"
    b"    <body>\n        <p>\n            A valid <em>key</em> must be "
    b"included with each data API request.\n        </p>\n    </body>\n</html>"
)

# ── Realistic 2023 vintage fixtures (values approximate the live API) ──
COUNTY_DETAIL: List[List[str]] = [
    ["NAME", "B01001_001E", "B01002_001E", "B19013_001E", "B17001_002E",
     "state", "county"],
    ["Harris County, Texas", "4835125", "34.4", "70789", "770564", "48", "201"],
    ["Travis County, Texas", "1334196", "34.9", "97600", "148213", "48", "453"],
    # Loving County: median household income is a jam value (suppressed).
    ["Loving County, Texas", "43", "54.2", "-666666666", "4", "48", "301"],
]

COUNTY_SUBJECT: List[List[str]] = [
    ["NAME", "S0101_C01_030E", "S2701_C05_001E", "state", "county"],
    ["Harris County, Texas", "555417", "21.5", "48", "201"],
    ["Travis County, Texas", "130876", "12.4", "48", "453"],
    # Loving County intentionally ABSENT from the subject payload so the
    # detail-drives-the-join / missing-subject → None path is covered.
]

STATE_DETAIL: List[List[str]] = [
    ["NAME", "B01001_001E", "B01002_001E", "B19013_001E", "B17001_002E",
     "state"],
    ["Texas", "29243342", "35.5", "73035", "4029200", "48"],
    ["California", "38965193", "37.3", "91905", "4552837", "06"],
]

STATE_SUBJECT: List[List[str]] = [
    ["NAME", "S0101_C01_030E", "S2701_C05_001E", "state"],
    ["Texas", "3902946", "16.6", "48"],
    ["California", "5976369", "6.5", "06"],
]

CBSA_DETAIL: List[List[str]] = [
    ["NAME", "B01001_001E", "B01002_001E", "B19013_001E", "B17001_002E",
     _CBSA_GEO],
    ["Houston-Pasadena-The Woodlands, TX Metro Area", "7142603", "34.9",
     "74640", "980112", "26420"],
    ["Austin-Round Rock-San Marcos, TX Metro Area", "2352064", "35.1",
     "94654", "246118", "12420"],
]

CBSA_SUBJECT: List[List[str]] = [
    ["NAME", "S0101_C01_030E", "S2701_C05_001E", _CBSA_GEO],
    ["Houston-Pasadena-The Woodlands, TX Metro Area", "801245", "20.1",
     "26420"],
    ["Austin-Round Rock-San Marcos, TX Metro Area", "255430", "11.9",
     "12420"],
]


class FakeCensusApi:
    """Route canned arrays by ``(path, geography)``; script failures by call index."""

    def __init__(self) -> None:
        # {(path, geo_name): array-of-arrays}
        self.tables: Dict[Tuple[str, str], List[List[str]]] = {}
        self.calls: List[str] = []
        # Scripted responses keyed by call index:
        # {idx: (status, headers)} or {idx: (status, headers, body_bytes)}.
        self.transients: Dict[int, Any] = {}

    def add(self, path: str, geo: str, table: List[List[str]]) -> "FakeCensusApi":
        self.tables[(path, geo)] = table
        return self

    @classmethod
    def with_defaults(cls, year: int = 2023) -> "FakeCensusApi":
        """A fake pre-loaded with every profile's fixtures for one vintage."""
        detail = f"/{year}/acs/acs5"
        subject = f"/{year}/acs/acs5/subject"
        return (cls()
                .add(detail, "county", COUNTY_DETAIL)
                .add(subject, "county", COUNTY_SUBJECT)
                .add(detail, "state", STATE_DETAIL)
                .add(subject, "state", STATE_SUBJECT)
                .add(detail, _CBSA_GEO, CBSA_DETAIL)
                .add(subject, _CBSA_GEO, CBSA_SUBJECT))

    def __call__(self, url: str, headers: Dict[str, str], timeout: float
                 ) -> RawResponse:
        idx = len(self.calls)
        self.calls.append(url)
        if idx in self.transients:
            scripted = self.transients[idx]
            status, hdrs = scripted[0], scripted[1] or {}
            body = scripted[2] if len(scripted) > 2 else b"{}"
            return RawResponse(status=status, headers=hdrs, body=body)

        parsed = urlparse(url)
        qs = parse_qs(parsed.query, keep_blank_values=True)
        geo_for = qs.get("for", [""])[0]
        geo_name = geo_for.split(":", 1)[0]
        # The live path includes no host prefix beyond /data; our base_url
        # already carries /data so parsed.path starts at the vintage.
        path = parsed.path[len("/data"):] if parsed.path.startswith("/data") else parsed.path
        table = self.tables.get((path, geo_name))
        if table is None:
            # Unknown vintage/dataset → the API's real 404 text shape.
            return RawResponse(status=404, body=b"error: unknown data set")
        rows = self._filtered(table, qs)
        if len(rows) <= 1:
            # Valid query, nothing matched → the API's documented 204.
            return RawResponse(status=204, body=b"")
        return RawResponse(status=200, body=json.dumps(rows).encode())

    @staticmethod
    def _filtered(table: List[List[str]], qs: Dict[str, List[str]]
                  ) -> List[List[str]]:
        """Apply ``in=state:XX`` / ``for=state:XX`` narrowing like the API."""
        header, data = table[0], table[1:]
        state_filter = None
        in_clause = qs.get("in", [""])[0]
        if in_clause.startswith("state:"):
            state_filter = in_clause.split(":", 1)[1]
        for_clause = qs.get("for", [""])[0]
        if for_clause.startswith("state:") and not for_clause.endswith(":*"):
            state_filter = for_clause.split(":", 1)[1]
        if state_filter and "state" in header:
            i = header.index("state")
            data = [r for r in data if r[i] == state_filter]
        return [header] + data
