"""In-memory fake data.healthcare.gov server for tests — no socket.

A :class:`FakeHealthcareGov` is an :data:`Opener` (``(url, headers,
timeout) -> RawResponse``) that serves canned records and models the two
live DKAN shapes (both probed live during the build):

  * the metastore catalog path returns a bare JSON **list** of DCAT
    dataset items in one call (no paging);
  * datastore query paths return the ``{"count", "results", "schema",
    "query"}`` envelope, page by ``limit``/``offset``, honour equality
    ``conditions[i][property/value]`` params, reject ``limit`` > 500
    with HTTP 400 (like live), and add a 1-based ``record_number`` to
    every row when ``rowIds=true`` is requested.

It also models 429 + ``Retry-After`` / 5xx / arbitrary bodies via a
scripted ``transients`` map so the transport's retry path is exercised
without a network.

The fixture payloads below are hand-written minimal replicas of REAL
API responses sampled live (July 2026): a catalog item mirrors the DCAT
document shape, and each PUF row uses the real lower-cased datastore
column names.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple
from urllib.parse import parse_qs, urlparse

from ..endpoints import CATALOG_PATH
from ..transport import RawResponse

_DATASTORE_PREFIX = "/api/1/datastore/query/"
_MAX_LIMIT = 500

# ── realistic fixture payloads (trimmed live shapes) ───────────────────
CATALOG_ITEMS: List[Dict[str, Any]] = [
    {
        "@type": "dcat:Dataset",
        "title": "Plan Attributes PUF - PY2026",
        "identifier": "ca253298-c4ef-4a77-9c44-0de0bbe91941",
        "description": "Plan-level attributes for certified QHPs.",
        "accessLevel": "public",
        "accrualPeriodicity": "R/PT1S",
        "issued": "2025-05-04T14:00:00+00:00",
        "modified": "2026-05-04T19:00:00+00:00",
        "license": "https://www.usa.gov/publicdomain/label/1.0/",
        "publisher": {"@type": "org:Organization", "name": "data.healthcare.gov"},
        "contactPoint": {"fn": "CMS CCIIO",
                         "hasEmail": "mailto:CCIIO@cms.hhs.gov"},
        "keyword": ["puf", "healthcare"],
        "distribution": [{
            "@type": "dcat:Distribution",
            "title": "CSV file",
            "format": "csv",
            "mediaType": "text/csv",
            "downloadURL": "https://data.healthcare.gov/sites/default/files/PlanAttributes.csv",
            "describedBy": "https://data.healthcare.gov/api/1/metastore/schemas/data-dictionary/items/abc",
        }],
        "bureauCode": ["009:38"],
        "programCode": ["009:000"],
    },
    {
        "@type": "dcat:Dataset",
        "title": "QHP Landscape PY2026 Individual Medical",
        "identifier": "6fe7fb77-7291-4104-952f-7c7e2c5d0c45",
        "description": "Dataset.",
        "accessLevel": "public",
        "modified": "2026-05-04T19:00:00+00:00",
        "contactPoint": {"fn": "Marketplace",
                         "hasEmail": "mailto:marketplace@cms.hhs.gov"},
        "keyword": ["qhp"],
        "distribution": [{
            "@type": "dcat:Distribution",
            "format": "zip",
            "downloadURL": "https://data.healthcare.gov/datafile/py2026/individual_market_medical.zip",
        }],
        "bureauCode": ["009:38"],
        "programCode": ["009:000"],
    },
    {
        # A record with no identifier — must be skipped by the normalizer.
        "@type": "dcat:Dataset",
        "title": "Orphan item",
        "description": "No identifier.",
        "accessLevel": "public",
    },
]

PLAN_ATTRIBUTES_ROWS: List[Dict[str, Any]] = [
    {"businessyear": "2026", "statecode": "AK", "issuerid": "21989",
     "issuermarketplacemarketingname": "Best Life and Health",
     "sourcename": "SERFF", "importdate": "2025-05-01",
     "marketcoverage": "Individual", "dentalonlyplan": "Yes",
     "standardcomponentid": "21989AK0030001", "planid": "21989AK0030001-00",
     "planmarketingname": "Dental Value", "plantype": "PPO",
     "metallevel": "Low", "serviceareaid": "AKS001",
     "issueractuarialvalue": "70%"},
    {"businessyear": "2026", "statecode": "AK", "issuerid": "21989",
     "issuermarketplacemarketingname": "Best Life and Health",
     "sourcename": "SERFF", "importdate": "2025-05-01",
     "marketcoverage": "Individual", "dentalonlyplan": "Yes",
     "standardcomponentid": "21989AK0030001", "planid": "21989AK0030001-01",
     "planmarketingname": "Dental Value CSR", "plantype": "PPO",
     "metallevel": "Low", "serviceareaid": "AKS001",
     "issueractuarialvalue": "73%"},
    {"businessyear": "2026", "statecode": "TX", "issuerid": "33602",
     "issuermarketplacemarketingname": "Texas Health Co",
     "sourcename": "HIOS", "importdate": "2025-05-01",
     "marketcoverage": "Individual", "dentalonlyplan": "No",
     "standardcomponentid": "33602TX0450002", "planid": "33602TX0450002-04",
     "planmarketingname": "Silver Saver", "plantype": "HMO",
     "metallevel": "Silver", "serviceareaid": "TXS002",
     "issueractuarialvalue": "71%"},
]

RATES_ROWS: List[Dict[str, Any]] = [
    {"businessyear": "2026", "statecode": "AK", "issuerid": "21989",
     "sourcename": "SERFF", "importdate": "2025-05-01",
     "rateeffectivedate": "2026-01-01", "rateexpirationdate": "2026-12-31",
     "planid": "21989AK0030001", "ratingareaid": "Rating Area 1",
     "tobacco": "No Preference", "age": "0-14", "individualrate": "65.0",
     "individualtobaccorate": "", "couple": ""},
    {"businessyear": "2026", "statecode": "AK", "issuerid": "21989",
     "sourcename": "SERFF", "importdate": "2025-05-01",
     "rateeffectivedate": "2026-01-01", "rateexpirationdate": "2026-12-31",
     "planid": "21989AK0030001", "ratingareaid": "Rating Area 1",
     "tobacco": "No Preference", "age": "15", "individualrate": "68.5",
     "individualtobaccorate": "", "couple": ""},
]

BENEFITS_ROWS: List[Dict[str, Any]] = [
    {"businessyear": "2026", "statecode": "AK", "issuerid": "21989",
     "sourcename": "SERFF", "importdate": "2025-05-01",
     "standardcomponentid": "21989AK0030001", "planid": "21989AK0030001-00",
     "benefitname": "Routine Dental Services (Adult)", "copayinntier1": "$0",
     "coinsinntier1": "20%", "isehb": "", "iscovered": "Covered",
     "quantlimitonsvc": "Yes", "limitqty": "2", "limitunit": "Visit(s)"},
    {"businessyear": "2026", "statecode": "AK", "issuerid": "21989",
     "sourcename": "SERFF", "importdate": "2025-05-01",
     "standardcomponentid": "21989AK0030001", "planid": "21989AK0030001-00",
     "benefitname": "Orthodontia - Child", "copayinntier1": "$0",
     "coinsinntier1": "50%", "isehb": "Yes", "iscovered": "Covered",
     "quantlimitonsvc": "No", "limitqty": "", "limitunit": ""},
]

QUALITY_ROWS: List[Dict[str, Any]] = [
    {"issuerid": "38344", "state": "AK", "plan_type": "PPO",
     "reportingunitid": "38344-AK-PPO", "planid": "38344AK1060001",
     "overallratingvalue": "3", "medicalcareratingvalue": "3",
     "memberexperienceratingvalue": "5", "planadministrationratingvalue": "4"},
    {"issuerid": "21989", "state": "AK", "plan_type": "PPO",
     "reportingunitid": "21989-AK-PPO", "planid": "21989AK0030001",
     "overallratingvalue": "4", "medicalcareratingvalue": "4",
     "memberexperienceratingvalue": "4", "planadministrationratingvalue": "3"},
]

SERVICE_AREA_ROWS: List[Dict[str, Any]] = [
    {"businessyear": "2026", "statecode": "AK", "issuerid": "21989",
     "sourcename": "SERFF", "importdate": "2025-05-01",
     "serviceareaid": "AKS001", "serviceareaname": "Statewide",
     "coverentirestate": "Yes", "county": "", "partialcounty": "",
     "zipcodes": "", "partialcountyjustification": "",
     "marketcoverage": "Individual", "dentalonlyplan": "Yes"},
    {"businessyear": "2026", "statecode": "AK", "issuerid": "21989",
     "sourcename": "SERFF", "importdate": "2025-05-01",
     "serviceareaid": "AKS002", "serviceareaname": "Southeast",
     "coverentirestate": "No", "county": "02170", "partialcounty": "No",
     "zipcodes": "", "partialcountyjustification": "",
     "marketcoverage": "SHOP (Small Group)", "dentalonlyplan": "Yes"},
    {"businessyear": "2026", "statecode": "AK", "issuerid": "21989",
     "sourcename": "SERFF", "importdate": "2025-05-01",
     "serviceareaid": "AKS002", "serviceareaname": "Southeast",
     "coverentirestate": "No", "county": "02090", "partialcounty": "No",
     "zipcodes": "", "partialcountyjustification": "",
     "marketcoverage": "SHOP (Small Group)", "dentalonlyplan": "Yes"},
]


class FakeHealthcareGov:
    """Scriptable opener: catalog list + paged datastore + transients."""

    def __init__(self) -> None:
        self.catalog: List[Dict[str, Any]] = []
        self.datastores: Dict[str, List[Dict[str, Any]]] = {}
        self.calls: List[str] = []
        # Scripted responses keyed by call index:
        # {idx: (status, headers)} or {idx: (status, headers, body_bytes)}.
        self.transients: Dict[int, Tuple[Any, ...]] = {}

    def add_catalog(self, items: List[Dict[str, Any]]) -> "FakeHealthcareGov":
        self.catalog = list(items)
        return self

    def add_datastore(self, identifier: str,
                      records: List[Dict[str, Any]]) -> "FakeHealthcareGov":
        self.datastores[identifier] = list(records)
        return self

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
        path = parsed.path
        qs = parse_qs(parsed.query, keep_blank_values=True)

        if path == CATALOG_PATH:
            return RawResponse(
                status=200, body=json.dumps(self.catalog).encode())

        if path.startswith(_DATASTORE_PREFIX):
            ident = path[len(_DATASTORE_PREFIX):].split("/", 1)[0]
            if ident not in self.datastores:
                # Live DKAN answers 400 "No datastore storage found ...".
                return RawResponse(status=400, body=json.dumps({
                    "message": f"No datastore storage found for {ident}.",
                    "status": 400}).encode())
            return self._datastore_page(ident, qs)

        return RawResponse(status=404, body=b'{"message": "not found"}')

    # ── the live paging model ──────────────────────────────────────────
    def _datastore_page(self, ident: str, qs: Dict[str, List[str]]
                        ) -> RawResponse:
        recs = self.datastores[ident]
        limit = int(qs.get("limit", ["500"])[0])
        if limit > _MAX_LIMIT:
            # Live: HTTP 400 "JSON Schema validation failed."
            return RawResponse(status=400, body=json.dumps(
                {"message": "JSON Schema validation failed.",
                 "status": 400}).encode())
        offset = int(qs.get("offset", ["0"])[0])
        row_ids = qs.get("rowIds", ["false"])[0].lower() == "true"

        # Equality conditions[i][property]/[value], like live DKAN.
        matched = list(enumerate(recs, start=1))   # record_number is 1-based
        i = 0
        while f"conditions[{i}][property]" in qs:
            prop = qs[f"conditions[{i}][property]"][0]
            val = qs.get(f"conditions[{i}][value]", [""])[0]
            matched = [(n, r) for n, r in matched
                       if str(r.get(prop, "")) == val]
            i += 1

        page = matched[offset:offset + limit]
        results = []
        for n, r in page:
            row = dict(r)
            if row_ids:
                row = {"record_number": n, **row}
            results.append(row)
        payload = {
            "results": results,
            "count": len(matched),
            "schema": {ident: {"fields": {}}},
            "query": {"limit": limit, "offset": offset},
        }
        return RawResponse(status=200, body=json.dumps(payload).encode())
