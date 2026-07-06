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


def ckd_places_rows() -> List[Dict[str, Any]]:
    """PLACES county CKD rows (h3ej-a9ec shape; measureid=KIDNEY only, the
    measure-pinned curated slice). Note: no totalpop18plus in this vintage,
    and nulls omitted per Socrata."""
    return [
        {
            "year": "2021", "stateabbr": "AL", "statedesc": "Alabama",
            "locationname": "Jefferson", "datasource": "BRFSS",
            "category": "Health Outcomes",
            "measure": "Chronic kidney disease among adults aged >=18 years",
            "data_value_unit": "%", "data_value_type": "Crude prevalence",
            "data_value": "3.4", "low_confidence_limit": "3.1",
            "high_confidence_limit": "3.7", "totalpopulation": "658573",
            "locationid": "01073", "categoryid": "HLTHOUT",
            "measureid": "KIDNEY", "datavaluetypeid": "CrdPrv",
            "short_question_text": "Chronic Kidney Disease",
            "geolocation": {"type": "Point",
                            "coordinates": [-86.8904, 33.5453]},
        },
        {
            "year": "2021", "stateabbr": "AL", "statedesc": "Alabama",
            "locationname": "Jefferson", "datasource": "BRFSS",
            "category": "Health Outcomes",
            "measure": "Chronic kidney disease among adults aged >=18 years",
            "data_value_unit": "%",
            "data_value_type": "Age-adjusted prevalence",
            "data_value": "3.1", "locationid": "01073",
            "categoryid": "HLTHOUT", "measureid": "KIDNEY",
            "datavaluetypeid": "AgeAdjPrv",
            "short_question_text": "Chronic Kidney Disease",
        },
        {
            "year": "2021", "stateabbr": "LA", "statedesc": "Louisiana",
            "locationname": "Ouachita", "datasource": "BRFSS",
            "category": "Health Outcomes",
            "measure": "Chronic kidney disease among adults aged >=18 years",
            "data_value_unit": "%", "data_value_type": "Crude prevalence",
            "data_value": "3.6", "locationid": "22073",
            "categoryid": "HLTHOUT", "measureid": "KIDNEY",
            "datavaluetypeid": "CrdPrv",
            "short_question_text": "Chronic Kidney Disease"},
    ]


def monthly_deaths_rows() -> List[Dict[str, Any]]:
    """Monthly select-causes death rows (9dzk-mvmi shape). The
    nephritis_nephrotic_syndrome column is national kidney-disease deaths."""
    return [
        {"data_as_of": "2024-01-14T00:00:00.000",
         "start_date": "2020-01-01T00:00:00.000",
         "end_date": "2020-01-31T00:00:00.000",
         "jurisdiction_of_occurrence": "United States",
         "year": "2020", "month": "1", "all_cause": "264681",
         "natural_cause": "245479", "nephritis_nephrotic_syndrome": "4886",
         "diseases_of_heart": "58254", "diabetes_mellitus": "7104"},
        {"data_as_of": "2024-01-14T00:00:00.000",
         "start_date": "2020-02-01T00:00:00.000",
         "end_date": "2020-02-29T00:00:00.000",
         "jurisdiction_of_occurrence": "United States",
         "year": "2020", "month": "2", "all_cause": "244966",
         "natural_cause": "226893", "nephritis_nephrotic_syndrome": "4507",
         "diseases_of_heart": "54357", "diabetes_mellitus": "6789"},
    ]


def teen_birth_rows() -> List[Dict[str, Any]]:
    """NCHS teen-birth-by-county rows (3h58-x6cd shape). combined_fips_code
    is the 5-digit county FIPS the key composes on."""
    return [
        {"year": "2020", "state": "Alabama", "county": "Autauga",
         "state_fips_code": "1", "county_fips_code": "1",
         "combined_fips_code": "01001", "birth_rate": "22.1",
         "lower_confidence_limit": "17.8", "upper_confidence_limit": "27.2"},
        {"year": "2019", "state": "Alabama", "county": "Autauga",
         "state_fips_code": "1", "county_fips_code": "1",
         "combined_fips_code": "01001", "birth_rate": "24.5",
         "lower_confidence_limit": "19.9", "upper_confidence_limit": "29.8"},
    ]


def infant_mortality_rows() -> List[Dict[str, Any]]:
    """DQS infant-mortality rows (pjb2-jvdr shape). Live ``group`` is an SQL
    keyword the normalizer renames to group_field."""
    return [
        {"topic": "Infant mortality", "subtopic": "By race and Hispanic origin",
         "subtopic_id": "SUB1", "classification": "All races",
         "classification_id": "C1", "group": "Total",
         "group_id": "G1", "subgroup": "All",
         "subgroup_id": "SG1", "estimate_type": "Rate",
         "estimate_type_id": "ET1", "time_period": "2021",
         "time_period_id": "TP2021", "estimate": "5.4",
         "state_fips": "01"},
        {"topic": "Infant mortality", "subtopic": "By race and Hispanic origin",
         "subtopic_id": "SUB1", "classification": "Black",
         "classification_id": "C2", "group": "Race",
         "group_id": "G2", "subgroup": "Non-Hispanic Black",
         "subgroup_id": "SG2", "estimate_type": "Rate",
         "estimate_type_id": "ET1", "time_period": "2021",
         "time_period_id": "TP2021", "estimate": "10.9",
         "state_fips": "01"},
    ]


def maternal_death_rows() -> List[Dict[str, Any]]:
    """VSRR maternal-death rows (e2d5-ggg7 shape; live ``group`` keyword)."""
    return [
        {"data_as_of": "2026-04-22T00:00:00.000", "jurisdiction": "United States",
         "group": "Total", "subgroup": "All", "year_of_death": "2023",
         "month_of_death": "December", "time_period": "12 month-ending",
         "month_ending_date": "2023-12-31T00:00:00.000",
         "maternal_deaths": "817", "live_births": "3591328",
         "maternal_mortality_rate": "22.8"},
        {"data_as_of": "2026-04-22T00:00:00.000", "jurisdiction": "United States",
         "group": "Race", "subgroup": "Non-Hispanic Black", "year_of_death": "2023",
         "month_of_death": "December", "time_period": "12 month-ending",
         "month_ending_date": "2023-12-31T00:00:00.000",
         "maternal_deaths": "202", "live_births": "500000",
         "maternal_mortality_rate": "40.4"},
    ]


def pm25_county_rows() -> List[Dict[str, Any]]:
    """Daily county PM2.5 rows (53mz-4zqd shape). countyfips is the
    within-state code, so the key needs statefips too."""
    return [
        {"year": "2001", "date": "01JAN2001", "statefips": "1", "countyfips": "1",
         "pm25_max_pred": "10.66", "pm25_med_pred": "10.26",
         "pm25_mean_pred": "10.13", "pm25_pop_pred": "10.18"},
        # Same county code, different STATE — must not collide with the row
        # above (this is why statefips is in the key).
        {"year": "2001", "date": "01JAN2001", "statefips": "4", "countyfips": "1",
         "pm25_max_pred": "6.10", "pm25_med_pred": "5.80",
         "pm25_mean_pred": "5.77", "pm25_pop_pred": "5.79"},
    ]


def generic_rows(n: int = 3) -> List[Dict[str, Any]]:
    """Rows for an arbitrary uncurated 4x4 (shape doesn't matter — that's
    the point of the generic table)."""
    return [{"some_col": f"v{i}", "other": i} for i in range(n)]
