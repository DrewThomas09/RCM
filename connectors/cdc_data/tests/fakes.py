"""In-memory fake data.cdc.gov server for tests — no socket, deterministic.

A :class:`FakeCdcData` is an :data:`Opener` (``(url, headers, timeout)
-> RawResponse``) that serves canned records per URL path and models the
two live pagination shapes exactly as verified against the real domain:

  * ``/resource/{4x4}.json`` returns a bare JSON array and pages by
    ``$limit``/``$offset`` (plus simple ``column=value`` equality
    filtering so ``$where``-free filter params are exercised);
  * ``/api/views/metadata/v1`` returns a bare JSON array and pages by
    ``limit`` + 1-based ``page`` — mirroring the live quirk that
    ``offset`` is IGNORED on data.cdc.gov.

It also models 429 + ``Retry-After`` and 5xx via a scripted
``transients`` map so the transport's retry path is exercised without a
network, and records every request's URL + headers so token handling is
assertable.

The fixture payloads below are hand-written from LIVE samples probed on
2026-07-06 (same field names, realistic values, tiny row counts).
"""
from __future__ import annotations

import json
from typing import Any, Dict, List
from urllib.parse import parse_qs, urlparse

from ..transport import RawResponse

CATALOG_PATH = "/api/views/metadata/v1"


class FakeCdcData:
    def __init__(self) -> None:
        self.records: Dict[str, List[Dict[str, Any]]] = {}
        self.calls: List[str] = []
        self.headers_seen: List[Dict[str, str]] = []
        # Scripted transient responses keyed by call index: {idx: (status, headers)}.
        self.transients: Dict[int, Any] = {}

    def add(self, path: str, records: List[Dict[str, Any]]) -> "FakeCdcData":
        self.records[path] = list(records)
        return self

    def __call__(self, url: str, headers: Dict[str, str], timeout: float
                 ) -> RawResponse:
        idx = len(self.calls)
        self.calls.append(url)
        self.headers_seen.append(dict(headers))
        if idx in self.transients:
            status, hdrs = self.transients[idx]
            return RawResponse(status=status, headers=hdrs or {}, body=b"{}")

        parsed = urlparse(url)
        path = parsed.path
        qs = parse_qs(parsed.query, keep_blank_values=True)
        if path not in self.records:
            return RawResponse(status=404, body=b'{"error": true}')
        recs = self.records[path]

        if path == CATALOG_PATH:
            # Live quirk: limit + 1-based page; offset ignored.
            limit = int(qs.get("limit", ["500"])[0])
            page = int(qs.get("page", ["1"])[0])
            start = (page - 1) * limit
            body = json.dumps(recs[start:start + limit]).encode()
            return RawResponse(status=200, body=body)

        # SODA rows: $limit/$offset paging + plain column equality filters.
        limit = int(qs.get("$limit", ["1000"])[0])
        offset = int(qs.get("$offset", ["0"])[0])
        rows = recs
        for key, vals in qs.items():
            if key.startswith("$"):
                continue
            rows = [r for r in rows if str(r.get(key)) == vals[0]]
        body = json.dumps(rows[offset:offset + limit]).encode()
        return RawResponse(status=200, body=body)


# ── fixtures: live shapes, tiny counts ────────────────────────────────
def catalog_items(n: int = 5) -> List[Dict[str, Any]]:
    """Catalog metadata items in the live camelCase shape."""
    out = []
    for i in range(n):
        uid = f"aaa{i}-bbb{i}"
        out.append({
            "id": uid,
            "name": f"Test Dataset {i}",
            "attribution": "NCHS" if i % 2 else None,
            "attributionLink": None,
            "category": "National Center for Health Statistics",
            "createdAt": "2026-06-23T20:04:56+0000",
            "dataUpdatedAt": f"2026-06-2{i}T15:36:30+0000",
            "dataUri": f"https://data.cdc.gov/resource/{uid}",
            "description": f"Description of test dataset {i}.",
            "domain": "data.cdc.gov",
            "externalId": None,
            "hideFromCatalog": False,
            "hideFromDataJson": False,
            "license": "See Terms of Use",
            "metadataUpdatedAt": "2026-06-23T20:07:20+0000",
            "provenance": "OFFICIAL",
            "updatedAt": "2026-06-23T20:07:21+0000",
            "webUri": f"https://data.cdc.gov/d/{uid}",
            "approvals": [{"state": "approved"}],
            "customFields": {
                "Common Core": {
                    "Update Frequency": "Annually",
                    "Publisher": "Centers for Disease Control and Prevention",
                },
            },
            "tags": ["test", f"tag{i}"],
        })
    return out


def places_rows() -> List[Dict[str, Any]]:
    """PLACES county rows (swc5-untb shape; geolocation nested, nulls omitted)."""
    return [
        {
            "year": "2023", "stateabbr": "AR", "statedesc": "Arkansas",
            "locationname": "Drew", "datasource": "BRFSS",
            "category": "Health Outcomes", "measure": "Arthritis among adults",
            "data_value_unit": "%", "data_value_type": "Crude prevalence",
            "data_value": "29.9", "low_confidence_limit": "26.6",
            "high_confidence_limit": "33.3", "totalpopulation": "16945",
            "totalpop18plus": "13230", "locationid": "05043",
            "categoryid": "HLTHOUT", "measureid": "ARTHRITIS",
            "datavaluetypeid": "CrdPrv", "short_question_text": "Arthritis",
            "geolocation": {"type": "Point",
                            "coordinates": [-91.7196579, 33.5894113]},
            ":@computed_region_hjsp_umg2": "15",
        },
        {
            "year": "2023", "stateabbr": "AR", "statedesc": "Arkansas",
            "locationname": "Drew", "datasource": "BRFSS",
            "category": "Health Outcomes", "measure": "Arthritis among adults",
            "data_value_unit": "%", "data_value_type": "Age-adjusted prevalence",
            "data_value": "27.1", "locationid": "05043",
            "categoryid": "HLTHOUT", "measureid": "ARTHRITIS",
            "datavaluetypeid": "AgeAdjPrv", "short_question_text": "Arthritis",
        },
        {
            "year": "2023", "stateabbr": "AL", "statedesc": "Alabama",
            "locationname": "Jefferson", "datasource": "BRFSS",
            "category": "Health Outcomes",
            "measure": "Current smoking among adults",
            "data_value_unit": "%", "data_value_type": "Crude prevalence",
            "data_value": "17.4", "locationid": "01073",
            "categoryid": "HLTHOUT", "measureid": "CSMOKING",
            "datavaluetypeid": "CrdPrv", "short_question_text": "Smoking",
        },
    ]


def leading_causes_rows() -> List[Dict[str, Any]]:
    """NCHS leading-causes rows (bi63-dtpu shape)."""
    return [
        {"year": "2017", "_113_cause_name":
            "Accidents (unintentional injuries) (V01-X59,Y85-Y86)",
         "cause_name": "Unintentional injuries", "state": "Alabama",
         "deaths": "2703", "aadr": "53.8"},
        {"year": "2017", "_113_cause_name": "All causes",
         "cause_name": "All causes", "state": "Alabama",
         "deaths": "52356", "aadr": "917.4"},
        {"year": "2016", "_113_cause_name": "All causes",
         "cause_name": "All causes", "state": "Alaska",
         "deaths": "4316", "aadr": "745.4"},
    ]


def vsrr_rows() -> List[Dict[str, Any]]:
    """VSRR drug-overdose rows (xkb8-kh2a shape)."""
    return [
        {"state": "CA", "year": "2023", "month": "January",
         "period": "12 month-ending", "indicator": "Cocaine (T40.5)",
         "data_value": "2333", "percent_complete": "100",
         "percent_pending_investigation": "1.4", "state_name": "California"},
        {"state": "CA", "year": "2023", "month": "February",
         "period": "12 month-ending", "indicator": "Cocaine (T40.5)",
         "data_value": "2380", "percent_complete": "100",
         "percent_pending_investigation": "1.3", "state_name": "California"},
    ]


def provisional_deaths_rows() -> List[Dict[str, Any]]:
    """Provisional COVID deaths rows (9bhg-hcku shape). Note the live
    ``group`` field — an SQL keyword the normalizer must rename."""
    return [
        {"data_as_of": "2023-09-27T00:00:00.000",
         "start_date": "2020-01-01T00:00:00.000",
         "end_date": "2023-09-23T00:00:00.000", "group": "By Total",
         "state": "United States", "sex": "All Sexes",
         "age_group": "All Ages", "covid_19_deaths": "1146774",
         "total_deaths": "11491623", "pneumonia_deaths": "1163625"},
        {"data_as_of": "2023-09-27T00:00:00.000",
         "start_date": "2021-01-01T00:00:00.000",
         "end_date": "2021-01-31T00:00:00.000", "group": "By Month",
         "year": "2021", "month": "1", "state": "United States",
         "sex": "Male", "age_group": "65-74 years",
         "covid_19_deaths": "12345", "total_deaths": "67890"},
    ]


def drug_poisoning_rows() -> List[Dict[str, Any]]:
    """NCHS county drug-poisoning rows (rpvx-m2md shape; FIPS unpadded)."""
    return [
        {"fips": "1073", "year": "2017", "state": "Alabama",
         "fipsstate": "1", "county": "Jefferson County, AL",
         "population": "659197", "model_based_death_rate": "23.28",
         "standard_deviation": "1.86", "lower95ci": "19.9",
         "upper95ci": "27.1", "urbanrural": "Large Central Metro",
         "censusdivision": "6"},
    ]


def heart_disease_rows() -> List[Dict[str, Any]]:
    """Heart-disease mortality rows (th8y-thx5 shape)."""
    return [
        {"year": "2022", "locationabbr": "AL", "locationdesc": "Jefferson",
         "geographiclevel": "County", "datasource": "NVSS",
         "class": "Cardiovascular Diseases", "topic": "Heart Disease Mortality",
         "data_value": "401.5", "data_value_unit": "per 100,000 population",
         "data_value_type": "Age-adjusted, Spatially Smoothed, 3-year Average Rate",
         "stratificationcategory1": "Sex", "stratification1": "Overall",
         "stratificationcategory2": "Race/Ethnicity", "stratification2": "Overall",
         "topicid": "T2", "locationid": "01073",
         "y_lat": "33.55", "x_lon": "-86.89"},
    ]


def generic_rows(n: int = 3) -> List[Dict[str, Any]]:
    """Rows for an arbitrary uncurated 4x4 (shape doesn't matter — that's
    the point of the generic table)."""
    return [{"some_col": f"v{i}", "other": i} for i in range(n)]
