"""In-memory fake data.medicaid.gov server for tests — no socket, deterministic.

A :class:`FakeMedicaidData` is an :data:`Opener` (``(url, headers,
timeout) -> RawResponse``) that serves canned records and models the two
live DKAN shapes (both verified against the real API on 2026-07-06):

  * the metastore catalog returns every dataset in one bare JSON array::

        GET /api/1/metastore/schemas/dataset/items → [ {...}, ... ]

  * datastore queries page by ``limit``/``offset`` in an object envelope
    and honour ``conditions[i][property/value/operator]`` equality
    filters::

        GET /api/1/datastore/query/{uuid}/0?limit=N&offset=M
            → {"results": [...], "count": TOTAL, "schema": {...}, "query": {...}}

It also models 429 + ``Retry-After`` and 5xx via a scripted ``transients``
map so the transport's retry path is exercised without a network. The
fixture payloads below are hand-trimmed copies of REAL API rows (live
sample 2026-07-06) so the normalizers are tested against true field names.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List
from urllib.parse import parse_qs, urlparse

from ..transport import RawResponse

CATALOG_PATH = "/api/1/metastore/schemas/dataset/items"
_DATASTORE_RE = re.compile(r"^/api/1/datastore/query/([^/]+)/0$")

# ── realistic fixture rows (trimmed live samples) ─────────────────────
NADAC_2026_ID = "fbb83258-11c7-47f5-8b18-5f8e79f7e704"
NADAC_2025_ID = "f38d0706-1239-442c-a3cc-40ef1b686ac0"
SDUD_2025_ID = "158a1baa-5506-400a-8ec3-97756f0b0536"
SDUD_2024_ID = "61729e5a-7aa8-448c-8903-ba3e0cd0ea3c"


def nadac_row(ndc: str = "24385005452", effective: str = "2025-12-17",
              as_of: str = "2026-01-07", per_unit: str = "0.26341"
              ) -> Dict[str, Any]:
    return {
        "ndc_description": "12HR NASAL DECONGEST ER 120 MG",
        "ndc": ndc,
        "nadac_per_unit": per_unit,
        "effective_date": effective,
        "pricing_unit": "EA",
        "pharmacy_type_indicator": "C/I",
        "otc": "Y",
        "explanation_code": "1",
        "classification_for_rate_setting": "G",
        "corresponding_generic_drug_nadac_per_unit": "",
        "corresponding_generic_drug_effective_date": None,
        "as_of_date": as_of,
    }


def sdud_row(state: str = "AK", ndc: str = "00002143380", year: str = "2025",
             quarter: str = "4", utype: str = "FFSU",
             suppressed: str = "false", total: Any = "106607.76",
             product: str = "TRULICITY ") -> Dict[str, Any]:
    return {
        "utilization_type": utype,
        "state": state,
        "ndc": ndc,
        "labeler_code": "00002",
        "product_code": "1433",
        "package_size": "80",
        "year": year,
        "quarter": quarter,
        "suppression_used": suppressed,
        "product_name": product,
        "units_reimbursed": None if suppressed == "true" else "226.000",
        "number_of_prescriptions": None if suppressed == "true" else "108",
        "total_amount_reimbursed": None if suppressed == "true" else total,
        "medicaid_amount_reimbursed":
            None if suppressed == "true" else "103963.72",
        "non_medicaid_amount_reimbursed":
            None if suppressed == "true" else "2644.04",
    }


def catalog_item(identifier: str = NADAC_2026_ID,
                 title: str = "NADAC (National Average Drug Acquisition Cost) 2026",
                 theme: str = "National Average Drug Acquisition Cost"
                 ) -> Dict[str, Any]:
    return {
        "@type": "dcat:Dataset",
        "title": title,
        "identifier": identifier,
        "description": "National Average Drug Acquisition Cost (NADAC) "
                       "weekly reference data for the calendar year.",
        "accessLevel": "public",
        "accrualPeriodicity": "R/P7D",
        "issued": "2026-01-05T15:00:00+00:00",
        "modified": "2026-06-30T11:50:00+00:00",
        "license": "https://www.usa.gov/publicdomain/label/1.0/",
        "publisher": {"@type": "org:Organization", "name": "data.medicaid.gov"},
        "contactPoint": {"fn": "Medicaid.gov",
                         "hasEmail": "mailto:Medicaid.gov@cms.hhs.gov"},
        "theme": [theme],
        "keyword": ["drug prices", "pharmacy"],
        "distribution": [{
            "@type": "dcat:Distribution",
            "format": "csv",
            "mediaType": "text/csv",
            "downloadURL": "https://download.medicaid.gov/data/nadac-2026.csv",
            "describedBy": "https://data.medicaid.gov/api/1/metastore/"
                           "schemas/data-dictionary/items/abc",
            "describedByType": "application/vnd.tableschema+json",
        }],
        "bureauCode": ["009:00"],
        "programCode": ["009:076"],
    }


class FakeMedicaidData:
    """Scriptable fake opener for the DKAN catalog + datastore routes."""

    def __init__(self) -> None:
        self.catalog: List[Dict[str, Any]] = []
        self.datastores: Dict[str, List[Dict[str, Any]]] = {}
        self.calls: List[str] = []
        # Scripted transient responses keyed by call index: {idx: (status, headers)}.
        self.transients: Dict[int, Any] = {}

    def add_catalog(self, items: List[Dict[str, Any]]) -> "FakeMedicaidData":
        self.catalog = list(items)
        return self

    def add_datastore(self, identifier: str, records: List[Dict[str, Any]]
                      ) -> "FakeMedicaidData":
        self.datastores[identifier] = list(records)
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

        if path == CATALOG_PATH:
            return RawResponse(status=200,
                               body=json.dumps(self.catalog).encode())

        m = _DATASTORE_RE.match(path)
        if m:
            identifier = m.group(1)
            if identifier not in self.datastores:
                # Live behaviour: unknown UUID → 404 with a message body.
                body = json.dumps({"message": f"No resource found for "
                                              f"dataset {identifier} at index 0"})
                return RawResponse(status=404, body=body.encode())
            recs = self._filtered(identifier, qs)
            limit = int(qs.get("limit", ["500"])[0])
            offset = int(qs.get("offset", ["0"])[0])
            page = recs[offset:offset + limit]
            envelope = {
                "results": page,
                "count": len(recs),
                "schema": {identifier: {"fields": {}}},
                "query": {"limit": limit, "offset": offset},
            }
            return RawResponse(status=200, body=json.dumps(envelope).encode())

        return RawResponse(status=404, body=b'{"message":"no route"}')

    def _filtered(self, identifier: str, qs: Dict[str, List[str]]
                  ) -> List[Dict[str, Any]]:
        """Apply DKAN-style conditions[i][property/value] equality filters."""
        recs = self.datastores[identifier]
        conds: Dict[str, str] = {}
        i = 0
        while f"conditions[{i}][property]" in qs:
            prop = qs[f"conditions[{i}][property]"][0]
            value = qs.get(f"conditions[{i}][value]", [""])[0]
            conds[prop] = value
            i += 1
        if not conds:
            return recs
        return [r for r in recs
                if all(str(r.get(k)) == v for k, v in conds.items())]
