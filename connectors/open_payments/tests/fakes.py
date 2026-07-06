"""In-memory fake Open Payments server for tests — no socket, deterministic.

A :class:`FakeOpenPayments` is an :data:`Opener` (``(url, headers,
timeout) -> RawResponse``) that serves canned records and models the two
live response shapes (both verified against the real portal 2026-07-06):

  * the DKAN metastore catalog returns a top-level JSON **list** of
    dataset entries;
  * datastore queries return the ``{"count", "query", "results",
    "schema"}`` envelope, page by ``limit``/``offset``, evaluate
    ``conditions[i][property/value/operator]`` filters server-side,
    honour ``count=false`` / ``schema=false``, and reject ``limit``
    above 500 with an HTTP 400 JSON-Schema error (exactly what the live
    engine does).

It also models 429 + ``Retry-After`` and 5xx via a scripted
``transients`` map so the transport's retry path is exercised without a
network.

Fixture rows mirror REAL live rows (subset of the 91 general-payment
columns; the normalizer NULL-fills the rest, same as it would for any
sparse live record).
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Tuple
from urllib.parse import parse_qs, urlparse

from ..transport import RawResponse

CATALOG_PATH = "/api/1/metastore/schemas/dataset/items"
_DATASTORE_RE = re.compile(r"^/api/1/datastore/query/([0-9a-f-]{36})/0$")

GENERAL_UUID = "e6b17c6a-2534-4207-a4a1-6746a14911ff"
RESEARCH_UUID = "2f15cb85-8887-4dcc-a318-1f8ec1d815b3"
STATE_TOTALS_UUID = "e8a6db6a-a540-46aa-b04c-e216e2c72618"
# An uncurated dataset (older program year) for the generic-rows path.
OLD_YEAR_UUID = "12345678-1234-5234-9234-123456789abc"

# ── catalog fixtures (mirror the live metastore entry shape) ──────────
CATALOG_ITEMS: List[Dict[str, Any]] = [
    {
        "bureauCode": ["009:38"],
        "programCode": ["009:000"],
        "accessLevel": "public",
        "keyword": ["2024"],
        "contactPoint": {"fn": "Open Payments",
                         "hasEmail": "mailto:openpayments@cms.hhs.gov"},
        "dataQuality": True,
        "description": "All general (non-research, non-ownership related) "
                       "payments from the 2024 program year",
        "distribution": [{
            "title": "General Payment Data – Detailed Dataset 2024 Reporting Year",
            "mediaType": "text/csv",
            "format": "csv",
            "downloadURL": "https://download.cms.gov/openpayments/PGYR2024/OP_DTL_GNRL_PGYR2024.csv",
            "describedBy": "https://openpaymentsdata.cms.gov/api/1/metastore/schemas/data-dictionary/items/71ec19df",
            "describedByType": "application/vnd.tableschema+json",
        }],
        "identifier": GENERAL_UUID,
        "title": "2024 General Payment Data",
        "issued": "2026-06-30",
        "modified": "2026-06-30",
        "temporal": "2024-01-01/2024-12-31",
        "publisher": {"name": "openpaymentsdata.cms.gov"},
        "license": "https://www.usa.gov/government-works",
        "theme": ["General Payments"],
    },
    {
        "bureauCode": ["009:38"],
        "programCode": ["009:000"],
        "accessLevel": "public",
        "keyword": ["2024"],
        "contactPoint": {"fn": "Open Payments",
                         "hasEmail": "mailto:openpayments@cms.hhs.gov"},
        "dataQuality": True,
        "description": "All research payments from the 2024 program year",
        "distribution": [{
            "title": "Research Payment Data – Detailed Dataset 2024 Reporting Year",
            "mediaType": "text/csv",
            "format": "csv",
            "downloadURL": "https://download.cms.gov/openpayments/PGYR2024/OP_DTL_RSRCH_PGYR2024.csv",
        }],
        "identifier": RESEARCH_UUID,
        "title": "2024 Research Payment Data",
        "issued": "2026-06-30",
        "modified": "2026-06-30",
        "temporal": "2024-01-01/2024-12-31",
        "publisher": {"name": "openpaymentsdata.cms.gov"},
        "license": "https://www.usa.gov/government-works",
        "theme": ["Research Payments"],
    },
    {
        # A summary-theme entry with no "temporal" (4 of the live 74 omit it).
        "bureauCode": ["009:38"],
        "programCode": ["009:000"],
        "accessLevel": "public",
        "keyword": ["summary"],
        "contactPoint": {"fn": "Open Payments",
                         "hasEmail": "mailto:openpayments@cms.hhs.gov"},
        "dataQuality": True,
        "description": "Dashboard of high level summary metrics",
        "distribution": [{"title": "Summary Dashboard", "mediaType": "text/csv",
                          "format": "csv"}],
        "identifier": "e0d225fc-8230-401d-8fad-e2262fb22b4c",
        "title": "Summary Dashboard",
        "issued": "2026-06-30",
        "modified": "2026-06-30",
        "publisher": {"name": "openpaymentsdata.cms.gov"},
        "license": "https://www.usa.gov/government-works",
        "theme": ["Summary"],
    },
]


def general_payment_row(record_id: str, *, state: str = "VT",
                        npi: str = "1992019475",
                        amount: str = "175.14",
                        manufacturer: str = "Boston Scientific Corporation",
                        nature: str = "Food and Beverage") -> Dict[str, Any]:
    """One realistic general-payment datastore row (live column names)."""
    return {
        "change_type": "UNCHANGED",
        "covered_recipient_type": "Covered Recipient Non-Physician Practitioner",
        "covered_recipient_profile_id": "11240487",
        "covered_recipient_npi": npi,
        "covered_recipient_first_name": "CHERYL",
        "covered_recipient_last_name": "MCNEIL",
        "recipient_city": "SOUTH BURLINGTON",
        "recipient_state": state,
        "recipient_zip_code": "05403-4407",
        "recipient_country": "United States",
        "covered_recipient_primary_type_1": "Nurse Practitioner",
        "covered_recipient_specialty_1":
            "Physician Assistants & Advanced Practice Nursing Providers"
            "|Nurse Practitioner|Family",
        "submitting_applicable_manufacturer_or_applicable_gpo_name": manufacturer,
        "applicable_manufacturer_or_applicable_gpo_making_payment_id": "100000005674",
        "applicable_manufacturer_or_applicable_gpo_making_payment_name": manufacturer,
        "applicable_manufacturer_or_applicable_gpo_making_payment_state": "MA",
        "applicable_manufacturer_or_applicable_gpo_making_payment_country": "United States",
        "total_amount_of_payment_usdollars": amount,
        "date_of_payment": "04/13/2024",
        "number_of_payments_included_in_total_amount": "1",
        "form_of_payment_or_transfer_of_value": "In-kind items and services",
        "nature_of_payment_or_transfer_of_value": nature,
        "record_id": record_id,
        "dispute_status_for_publication": "No",
        "related_product_indicator": "Yes",
        "covered_or_noncovered_indicator_1": "Covered",
        "indicate_drug_or_biological_or_device_or_medical_supply_1": "Device",
        "product_category_or_therapeutic_area_1": "WATCHMAN FLX_IC",
        "name_of_drug_or_biological_or_device_or_medical_supply_1": "WATCHMAN FLX",
        "associated_drug_or_biological_ndc_1": "",
        "program_year": "2024",
        "payment_publication_date": "06/30/2026",
    }


def state_totals_row(state_code: str, nature: str, *, program_year: str = "2024",
                     recipient_type: str = "Covered Recipient Physician",
                     amount: str = "1000.00") -> Dict[str, Any]:
    return {
        "country_code": "US", "country_name": "United States",
        "state_code": state_code, "state_name": state_code,
        "nature_of_payment": nature, "recipient_type": recipient_type,
        "program_year": program_year,
        "total_number_of_physicians": "10",
        "total_payment_amount_physician": amount,
        "total_payment_count_physician": "25",
    }


class FakeOpenPayments:
    """Scriptable opener mirroring the live DKAN engine's behaviour."""

    def __init__(self) -> None:
        self.catalog: List[Dict[str, Any]] = [dict(x) for x in CATALOG_ITEMS]
        self.datastores: Dict[str, List[Dict[str, Any]]] = {}
        self.calls: List[str] = []
        # Scripted transient responses keyed by call index:
        # {idx: (status, headers)} or {idx: (status, headers, body_bytes)}.
        self.transients: Dict[int, Tuple] = {}

    def add(self, identifier: str, records: List[Dict[str, Any]]
            ) -> "FakeOpenPayments":
        self.datastores[identifier] = [dict(r) for r in records]
        return self

    # ── opener protocol ───────────────────────────────────────────────
    def __call__(self, url: str, headers: Dict[str, str], timeout: float
                 ) -> RawResponse:
        idx = len(self.calls)
        self.calls.append(url)
        if idx in self.transients:
            scripted = self.transients[idx]
            status, hdrs = scripted[0], scripted[1]
            body = scripted[2] if len(scripted) > 2 else b"{}"
            return RawResponse(status=status, headers=hdrs or {}, body=body)

        parsed = urlparse(url)
        path = parsed.path
        qs = parse_qs(parsed.query, keep_blank_values=True)

        if path == CATALOG_PATH:
            return _json_response(200, self.catalog)

        m = _DATASTORE_RE.match(path)
        if m:
            return self._datastore(m.group(1), qs)
        return RawResponse(status=404, body=b'{"message":"Not found"}')

    # ── the datastore query engine ────────────────────────────────────
    def _datastore(self, identifier: str, qs: Dict[str, List[str]]
                   ) -> RawResponse:
        if identifier not in self.datastores:
            return RawResponse(status=404, body=b'{"message":"unknown dataset"}')
        limit = int(qs.get("limit", ["500"])[0])
        if limit > 500:  # live behaviour, verified 2026-07-06
            body = json.dumps({
                "message": "JSON Schema validation failed.", "status": 400,
                "data": {"keyword": "maximum", "pointer": "limit",
                         "message": "The attribute value must be less than "
                                    "or equal 500."},
            }).encode()
            return RawResponse(status=400, body=body)
        offset = int(qs.get("offset", ["0"])[0])
        conditions = _parse_conditions(qs)
        recs = [r for r in self.datastores[identifier]
                if _matches(r, conditions)]
        page = recs[offset:offset + limit]
        payload: Dict[str, Any] = {
            "query": {"limit": limit, "offset": offset,
                      "conditions": conditions},
            "results": page,
        }
        if qs.get("count", ["true"])[0] != "false":
            payload["count"] = len(recs)
        if qs.get("schema", ["true"])[0] != "false":
            payload["schema"] = {identifier: {"fields": {}}}
        return _json_response(200, payload)


def _parse_conditions(qs: Dict[str, List[str]]) -> List[Dict[str, str]]:
    """Rebuild conditions[i][...] triplets from the flattened query string."""
    triplets: Dict[str, Dict[str, str]] = {}
    for key, values in qs.items():
        m = re.match(r"^conditions\[(\d+)\]\[(property|value|operator)\]$", key)
        if m:
            triplets.setdefault(m.group(1), {})[m.group(2)] = values[0]
    return [triplets[i] for i in sorted(triplets)]


def _matches(rec: Dict[str, Any], conditions: List[Dict[str, str]]) -> bool:
    for cond in conditions:
        actual = str(rec.get(cond.get("property", ""), ""))
        expected = cond.get("value", "")
        op = cond.get("operator", "=")
        if op == "=":
            if actual != expected:
                return False
        elif op == "like":
            pattern = "^" + re.escape(expected).replace("%", ".*") + "$"
            if not re.match(pattern, actual, re.IGNORECASE):
                return False
        elif op == "<>":
            if actual == expected:
                return False
        else:  # numeric comparators
            try:
                a, b = float(actual), float(expected)
            except ValueError:
                return False
            if op == ">" and not a > b:
                return False
            if op == ">=" and not a >= b:
                return False
            if op == "<" and not a < b:
                return False
            if op == "<=" and not a <= b:
                return False
    return True


def _json_response(status: int, payload: Any) -> RawResponse:
    return RawResponse(status=status, body=json.dumps(payload).encode())
