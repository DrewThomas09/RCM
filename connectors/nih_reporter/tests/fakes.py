"""In-memory fake NIH RePORTER server for tests — no socket, deterministic.

A :class:`FakeNihReporter` is an :data:`Opener` (``(url, data, headers,
timeout) -> RawResponse``) that serves canned records per endpoint path
and models the live POST paging shape::

    body {"criteria": {...}, "offset": N, "limit": M}
    → {"meta": {"total": T, "offset": N, "limit": M, ...}, "results": [...]}

including RePORTER's two hard validation errors, verified live: limit >
500 and offset > 14,999 both return HTTP 400 with a JSON *array of
message strings* (not an object). It also models 429 + ``Retry-After``
and 5xx via a scripted ``transients`` map so the transport's retry path
is exercised without a network.

The fixture builders mirror the REAL v2 response shapes (probed live
2026-07): projects are deeply nested (``organization``,
``agency_ic_admin``, ``principal_investigators`` …); publications are
flat ``{coreproject, pmid, applid}`` link edges.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from ..transport import RawResponse

PROJECTS_PATH = "/v2/projects/search"
PUBLICATIONS_PATH = "/v2/publications/search"

_LIMIT_MAX = 500
_OFFSET_CAP = 14_999


def project_record(
    appl_id: int = 11184227,
    project_num: str = "5R37GM070977-24",
    core_project_num: str = "R37GM070977",
    fiscal_year: int = 2025,
    title: str = "Genetic analysis of innate immunity using C. elegans",
    org_name: str = "UNIVERSITY OF TX MD ANDERSON CAN CTR",
    org_state: str = "TX",
    award_amount: int = 408750,
    activity_code: str = "R37",
) -> Dict[str, Any]:
    """One project result mirroring the live v2 shape (trimmed blobs)."""
    return {
        "appl_id": appl_id,
        "subproject_id": None,
        "fiscal_year": fiscal_year,
        "project_num": project_num,
        "project_serial_num": core_project_num[3:] if len(core_project_num) > 3 else core_project_num,
        "core_project_num": core_project_num,
        "organization": {
            "org_name": org_name,
            "city": None,
            "country": None,
            "org_city": "HOUSTON",
            "org_country": "UNITED STATES",
            "org_state": org_state,
            "org_state_name": None,
            "dept_type": "BIOLOGY",
            "fips_country_code": None,
            "org_duns": ["800772139"],
            "org_ueis": ["S3GMKS8ELA16"],
            "primary_duns": "800772139",
            "primary_uei": "S3GMKS8ELA16",
            "org_fips": "US",
            "org_ipf_code": "578407",
            "org_zipcode": "770304009",
            "external_org_id": 578407,
        },
        "award_type": "5",
        "activity_code": activity_code,
        "award_amount": award_amount,
        "is_active": True,
        "is_new": False,
        "project_num_split": {
            "appl_type_code": "5", "activity_code": activity_code,
            "ic_code": "GM", "serial_num": "070977", "support_year": "24",
            "full_support_year": "24", "suffix_code": "",
        },
        "principal_investigators": [
            {"profile_id": 7604113, "first_name": "Alejandro",
             "middle_name": "", "last_name": "Aballay",
             "is_contact_pi": True,
             "full_name": "Alejandro  Aballay", "title": "DEAN"},
        ],
        "contact_pi_name": "ABALLAY, ALEJANDRO ",
        "program_officers": [
            {"first_name": "XIAOLI", "middle_name": "", "last_name": "ZHAO",
             "full_name": "XIAOLI  ZHAO"},
        ],
        "agency_ic_admin": {
            "code": "GM", "abbreviation": "NIGMS",
            "name": "National Institute of General Medical Sciences",
            "admin_org_id": "12500024", "admin_funding_url": "",
        },
        "agency_ic_fundings": [
            {"fy": fiscal_year, "code": "GM",
             "name": "National Institute of General Medical Sciences",
             "abbreviation": "NIGMS", "total_cost": float(award_amount),
             "direct_cost_ic": 250000.0, "indirect_cost_ic": 158750.0},
        ],
        "cong_dist": "TX-09",
        "project_start_date": "2004-09-30T00:00:00",
        "project_end_date": "2027-08-31T00:00:00",
        "organization_type": {"name": "HOSPITALS", "code": "10",
                              "is_other": True},
        "geo_lat_lon": {"lon": -95.397195, "lat": 29.706319},
        "opportunity_number": "PA-16-160",
        "full_study_section": {
            "srg_code": "NSS", "srg_flex": None, "sra_designator_code": None,
            "sra_flex_code": None, "group_code": None, "name": "NSS",
        },
        "award_notice_date": "2025-08-14T00:00:00",
        "mechanism_code_dc": "RP",
        "covid_response": None,
        "arra_funded": "N",
        "budget_start": "2025-09-01T00:00:00",
        "budget_end": "2026-08-31T00:00:00",
        "cfda_code": "93.859",
        "funding_mechanism": "Non-SBIR/STTR",
        "direct_cost_amt": 250000,
        "indirect_cost_amt": 158750,
        "project_detail_url": f"https://reporter.nih.gov/project-details/{appl_id}",
        "date_added": "2025-09-07T22:56:09",
        "agency_code": "NIH",
        "project_title": title,
        "phr_text": "Public health relevance …",
        "spending_categories": [276, 338, 525],
        "abstract_text": "Long abstract …",
        "pref_terms": "immunity;innate immunity",
        "terms": "<immunity><innate immunity>",
        "spending_categories_desc": "Genetics; Infectious Diseases",
    }


def publication_record(pmid: int = 23959030, applid: int = 10247478,
                       coreproject: str = "R37GM070977") -> Dict[str, Any]:
    """One publication link edge mirroring the live v2 shape (verbatim)."""
    return {"coreproject": coreproject, "pmid": pmid, "applid": applid}


class FakeNihReporter:
    """Opener double: canned per-path records, live paging + error shapes."""

    def __init__(self) -> None:
        self.records: Dict[str, List[Dict[str, Any]]] = {}
        # Captured calls: (url, decoded POST body dict).
        self.calls: List[Tuple[str, Dict[str, Any]]] = []
        # Scripted transient responses keyed by call index: {idx: (status, headers)}.
        self.transients: Dict[int, Any] = {}

    def add(self, path: str, records: List[Dict[str, Any]]) -> "FakeNihReporter":
        self.records[path] = list(records)
        return self

    def __call__(self, url: str, data: bytes, headers: Dict[str, str],
                 timeout: float) -> RawResponse:
        try:
            body = json.loads(data or b"{}")
        except json.JSONDecodeError:
            body = {}
        idx = len(self.calls)
        self.calls.append((url, body))
        if idx in self.transients:
            status, hdrs = self.transients[idx]
            return RawResponse(status=status, headers=hdrs or {}, body=b"{}")

        offset = int(body.get("offset", 0))
        limit = int(body.get("limit", 25))
        # Live-verified validation errors: 400 + JSON array of strings.
        if limit > _LIMIT_MAX:
            return RawResponse(status=400, body=json.dumps(
                ["System doesn't support limit value greater than 500. "
                 "Please reduce your limit value."]).encode())
        if offset > _OFFSET_CAP:
            return RawResponse(status=400, body=json.dumps(
                ["System doesn't support offset value greater than 14,999. "
                 "Please narrow down your search criteria."]).encode())

        path = urlparse(url).path
        recs = self.records.get(path, [])
        total = len(recs)
        page = recs[offset:offset + limit]
        payload = {
            "meta": {"search_id": None, "total": total, "offset": offset,
                     "limit": limit, "sort_field": None, "sort_order": "ASC",
                     "sorted_by_relevance": False, "properties": {}},
            "results": page,
        }
        return RawResponse(status=200, body=json.dumps(payload).encode())
