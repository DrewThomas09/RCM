"""In-memory fake data.cms.gov server for tests — no socket, deterministic.

A :class:`FakeCmsOpenData` is an :data:`Opener` (``(url, headers, timeout)
-> RawResponse``) that serves canned records per dataset UUID and models
the live surfaces:

  * ``/data.json``                              → a DCAT catalog document,
  * ``/data-api/v1/dataset/{uuid}/data``        → a bare JSON array paged
    by ``size``/``offset`` with ``filter[COL]=v`` equality applied,
  * ``/data-api/v1/dataset/{uuid}/data/stats``  → ``{found_rows, total_rows}``,
  * an unknown UUID → 404 (exactly what a rotated dataset version does).

It also models 429 + ``Retry-After`` and 5xx via a scripted ``transients``
map so the transport's retry path is exercised without a network.

The fixture payloads mirror the REAL API shapes (live size=5 probes,
2026-07-06): row objects keyed by original column names with all-string
values; catalog entries with the distribution list carrying the
``description == "latest"`` API entry whose accessURL holds the current
UUID.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

from ..transport import RawResponse

_DATA_RE = re.compile(r"^/data-api/v1/dataset/([0-9a-fA-F-]{36})/data(/stats)?$")

# UUIDs the FAKE catalog advertises — deliberately different from the
# pinned literals in endpoints.py so tests can prove the catalog-first
# UUID re-resolution path.
CAT_PHYS_UUID = "aaaaaaaa-1111-2222-3333-444444444444"
CAT_COST_UUID = "bbbbbbbb-1111-2222-3333-444444444444"

PHYS_TITLE = "Medicare Physician & Other Practitioners - by Provider"
COST_TITLE = "Hospital Provider Cost Report"
HRR_TITLE = "Medicare Geographic Variation - by Hospital Referral Region"


def catalog_doc() -> Dict[str, Any]:
    """A 3-dataset DCAT document mirroring the live data.json shapes."""
    return {
        "@context": "https://project-open-data.cio.gov/v1.1/schema/catalog.jsonld",
        "@type": "dcat:Catalog",
        "dataset": [
            {
                "@type": "dcat:Dataset",
                "title": PHYS_TITLE,
                "description": "Services and procedures provided to Medicare "
                               "beneficiaries, aggregated by provider.",
                "identifier": f"https://data.cms.gov/data-api/v1/dataset/{CAT_PHYS_UUID}/data-viewer",
                "modified": "2026-01-15",
                "accrualPeriodicity": "R/P1Y",
                "temporal": "2023-01-01/2023-12-31",
                "theme": ["Medicare"],
                "keyword": ["providers", "utilization"],
                "landingPage": "https://data.cms.gov/provider-summary-by-type-of-service",
                "describedBy": "https://data.cms.gov/resources/mup-phy-data-dictionary",
                "contactPoint": {
                    "@type": "vcard:Contact",
                    "fn": "PUF - OEDA",
                    "hasEmail": "mailto:Medicare_Provider_Data@cms.hhs.gov",
                },
                "distribution": [
                    {"@type": "dcat:Distribution", "format": "API",
                     "description": "latest",
                     "accessURL": f"https://data.cms.gov/data-api/v1/dataset/{CAT_PHYS_UUID}/data",
                     "title": f"{PHYS_TITLE} : 2023-01-01", "modified": "2026-01-15"},
                    {"@type": "dcat:Distribution", "format": "API",
                     "accessURL": "https://data.cms.gov/data-api/v1/dataset/"
                                  "99999999-9999-9999-9999-999999999999/data",
                     "title": f"{PHYS_TITLE} : 2022-01-01", "modified": "2025-01-20"},
                    {"@type": "dcat:Distribution", "format": "CSV",
                     "mediaType": "text/csv",
                     "downloadURL": "https://data.cms.gov/sites/default/files/mup_phy.csv",
                     "title": f"{PHYS_TITLE} : 2023-01-01"},
                ],
            },
            {
                "@type": "dcat:Dataset",
                "title": COST_TITLE,
                "description": "Hospital cost report data (HCRIS).",
                "identifier": f"https://data.cms.gov/data-api/v1/dataset/{CAT_COST_UUID}/data-viewer",
                "modified": "2026-04-30",
                "accrualPeriodicity": "R/P1Y",
                "temporal": "2024-01-01/2024-12-31",
                "theme": ["Medicare"],
                "landingPage": "https://data.cms.gov/provider-compliance",
                "describedBy": "https://data.cms.gov/resources/hcris-data-dictionary",
                "contactPoint": {"@type": "vcard:Contact", "fn": "HCRIS - CM",
                                 "hasEmail": "mailto:CostReports@cms.hhs.gov"},
                "distribution": [
                    {"@type": "dcat:Distribution", "format": "API",
                     "description": "latest",
                     "accessURL": f"https://data.cms.gov/data-api/v1/dataset/{CAT_COST_UUID}/data"},
                ],
            },
            {
                # Live quirk worth modelling: ZIP-only dataset, no API
                # distribution at all — api_url must normalize to "".
                "@type": "dcat:Dataset",
                "title": HRR_TITLE,
                "description": "Geographic variation by hospital referral region.",
                "identifier": "https://data.cms.gov/data-api/v1/dataset/"
                              "6d7b229d-5bfb-4666-a2d2-38cea44a112c/data-viewer",
                "modified": "2023-08-25",
                "accrualPeriodicity": "R/P1Y",
                "theme": ["Medicare"],
                "distribution": [
                    {"@type": "dcat:Distribution", "format": "ZIP",
                     "mediaType": "application/zip",
                     "temporal": "2021-01-01/2021-12-31"},
                ],
            },
        ],
    }


def phys_rows(n: int = 5) -> List[Dict[str, Any]]:
    """Row objects shaped like the live by-provider dataset (string values)."""
    rows = []
    for i in range(n):
        rows.append({
            "Rndrng_NPI": str(1003000126 + i),
            "Rndrng_Prvdr_Last_Org_Name": f"Prov{i}",
            "Rndrng_Prvdr_First_Name": "Ardalan",
            "Rndrng_Prvdr_Crdntls": "M.D.",
            "Rndrng_Prvdr_Ent_Cd": "I",
            "Rndrng_Prvdr_City": "Bethesda",
            "Rndrng_Prvdr_State_Abrvtn": "MD",
            "Rndrng_Prvdr_Type": "Internal Medicine",
            "Tot_HCPCS_Cds": "15",
            "Tot_Benes": str(328 + i),
            "Tot_Srvcs": "399",
            "Tot_Sbmtd_Chrg": "202783.88",
            "Tot_Mdcr_Pymt_Amt": "35325.46",
        })
    return rows


def cost_rows() -> List[Dict[str, Any]]:
    """Row objects shaped like the live HCRIS hospital cost report."""
    return [
        {"rpt_rec_num": "747534", "Provider CCN": "110130",
         "Hospital Name": "IRWIN COUNTY HOSPITAL", "City": "OCILLA",
         "State Code": "GA", "Fiscal Year Begin Date": "2025-01-01",
         "Fiscal Year End Date": "2025-12-31"},
        {"rpt_rec_num": "747999", "Provider CCN": "110130",
         "Hospital Name": "IRWIN COUNTY HOSPITAL", "City": "OCILLA",
         "State Code": "GA", "Fiscal Year Begin Date": "2024-01-01",
         "Fiscal Year End Date": "2024-12-31"},
    ]


class FakeCmsOpenData:
    def __init__(self) -> None:
        self.datasets: Dict[str, List[Dict[str, Any]]] = {}
        self.catalog: Optional[Dict[str, Any]] = None
        self.calls: List[str] = []
        # Scripted transient responses keyed by call index: {idx: (status, headers)}.
        self.transients: Dict[int, Any] = {}

    def set_catalog(self, doc: Dict[str, Any]) -> "FakeCmsOpenData":
        self.catalog = doc
        return self

    def add_dataset(self, uuid: str, rows: List[Dict[str, Any]]
                    ) -> "FakeCmsOpenData":
        self.datasets[uuid] = list(rows)
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

        if path == "/data.json":
            doc = self.catalog if self.catalog is not None else catalog_doc()
            return RawResponse(status=200, body=json.dumps(doc).encode())

        m = _DATA_RE.match(path)
        if not m:
            return RawResponse(status=404, body=b'{"error":"no such path"}')
        uuid, is_stats = m.group(1), bool(m.group(2))
        if uuid not in self.datasets:
            # Exactly what the live API does for a rotated/unknown version.
            return RawResponse(status=404, body=b'{"error":"not found"}')
        recs = self.datasets[uuid]

        # filter[COL]=value equality, like the live data API.
        for key, values in qs.items():
            if key.startswith("filter[") and key.endswith("]"):
                col = key[len("filter["):-1]
                recs = [r for r in recs if str(r.get(col, "")) == values[0]]

        if is_stats:
            payload = {"found_rows": len(recs), "total_rows": len(recs)}
            return RawResponse(status=200, body=json.dumps(payload).encode())

        size = int(qs.get("size", ["1000"])[0])
        offset = int(qs.get("offset", ["0"])[0])
        page = recs[offset:offset + size]
        return RawResponse(status=200, body=json.dumps(page).encode())
