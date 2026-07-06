"""In-memory fake healthdata.gov server for tests — no socket, deterministic.

A :class:`FakeHealthdataGov` is an :data:`Opener` (``(url, headers,
timeout) -> RawResponse``) that serves canned records per URL path and
models the two live pagination shapes exactly as verified against the
real domain on 2026-07-06:

  * ``/resource/{4x4}.json`` returns a bare JSON array and pages by
    ``$limit``/``$offset`` (plus simple ``column=value`` equality
    filtering so ``$where``-free filter params are exercised);
  * ``/api/views/metadata/v1`` returns a bare JSON array and pages by
    ``limit`` + 1-based ``page`` — mirroring the live quirk that
    ``offset`` is IGNORED on healthdata.gov (same as data.cdc.gov).

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


class FakeHealthdataGov:
    def __init__(self) -> None:
        self.records: Dict[str, List[Dict[str, Any]]] = {}
        self.calls: List[str] = []
        self.headers_seen: List[Dict[str, str]] = []
        # Scripted transient responses keyed by call index: {idx: (status, headers)}.
        self.transients: Dict[int, Any] = {}

    def add(self, path: str, records: List[Dict[str, Any]]) -> "FakeHealthdataGov":
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
            limit = int(qs.get("limit", ["1000"])[0])
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
    """Catalog metadata items in the live camelCase shape.

    Mirrors healthdata.gov's meta-catalog anatomy as VERIFIED LIVE:
    items cycle through the three real record classes —

      i % 3 == 0: HHS hub native (``domain=datahub.hhs.gov``, HHS
                  attribution) — the class whose tabular assets actually
                  serve rows on ``/resource/``;
      i % 3 == 1: federal-portal mirror (``domain=datahub.hhs.gov`` with
                  ``attribution`` naming the home portal, e.g.
                  data.cdc.gov) — an href pointer, 403 on /resource/;
      i % 3 == 2: state/city-portal copy federated in
                  (``domain=healthdata.gov``) — also 403 on /resource/.
    """
    flavors = [
        ("datahub.hhs.gov", "U.S. Department of Health & Human Services"),
        ("datahub.hhs.gov", "data.cdc.gov"),
        ("healthdata.gov", "chhs.data.ca.gov"),
    ]
    out = []
    for i in range(n):
        uid = f"aaa{i}-bbb{i}"
        domain, attribution = flavors[i % 3]
        out.append({
            "id": uid,
            "name": f"Test Dataset {i}",
            "attribution": attribution,
            "attributionLink": None,
            "category": "Health" if i % 3 == 0 else None,
            "createdAt": "2026-06-23T20:04:56+0000",
            "dataUpdatedAt": f"2026-06-2{i}T15:36:30+0000",
            "dataUri": f"https://healthdata.gov/resource/{uid}",
            "description": f"Description of test dataset {i}.",
            "domain": domain,
            "externalId": None,
            "hideFromCatalog": False,
            "hideFromDataJson": False,
            "license": "Public Domain U.S. Government",
            "metadataUpdatedAt": "2026-06-23T20:07:20+0000",
            "provenance": "OFFICIAL",
            "updatedAt": "2026-06-23T20:07:21+0000",
            "webUri": f"https://healthdata.gov/d/{uid}",
            "approvals": [{"state": "approved"}],
            "customFields": {
                "Common Core": {
                    "Update Frequency": "Weekly",
                    "Publisher": "Department of Health & Human Services",
                },
            },
            "tags": ["test", f"tag{i}"],
        })
    return out


def facility_capacity_rows() -> List[Dict[str, Any]]:
    """Facility weekly capacity rows (anag-cw7u shape; nulls omitted,
    geocoded point nested — Socrata JSON conventions)."""
    return [
        {
            "hospital_pk": "010039", "collection_week": "2024-04-21T00:00:00.000",
            "state": "AL", "ccn": "010039",
            "hospital_name": "HUNTSVILLE HOSPITAL",
            "address": "101 SIVLEY RD", "city": "HUNTSVILLE", "zip": "35801",
            "hospital_subtype": "Short Term", "fips_code": "01089",
            "is_metro_micro": True,
            "total_beds_7_day_avg": "941.9",
            "inpatient_beds_used_7_day_avg": "802.6",
            "inpatient_beds_7_day_avg": "858.4",
            "total_icu_beds_7_day_avg": "104.0",
            "icu_beds_used_7_day_avg": "92.4",
            "inpatient_beds_used_covid_7_day_avg": "6.1",
            "total_beds_7_day_coverage": "7",
            "geocoded_hospital_address": {
                "type": "Point", "coordinates": [-86.581917, 34.720866]},
            "hhs_ids": "C010039-A,C010039-B",
            "is_corrected": False,
            ":@computed_region_abcd_1234": "3",
        },
        {
            "hospital_pk": "010039", "collection_week": "2024-04-14T00:00:00.000",
            "state": "AL", "ccn": "010039",
            "hospital_name": "HUNTSVILLE HOSPITAL",
            "address": "101 SIVLEY RD", "city": "HUNTSVILLE", "zip": "35801",
            "hospital_subtype": "Short Term", "fips_code": "01089",
            "total_beds_7_day_avg": "938.0",
            "inpatient_beds_used_7_day_avg": "799.9",
        },
        {
            "hospital_pk": "450054", "collection_week": "2024-04-21T00:00:00.000",
            "state": "TX", "ccn": "450054",
            "hospital_name": "ASCENSION SETON MEDICAL CENTER AUSTIN",
            "address": "1201 W 38TH ST", "city": "AUSTIN", "zip": "78705",
            "hospital_subtype": "Short Term", "fips_code": "48453",
            "total_beds_7_day_avg": "480.3",
        },
    ]


def state_ts_rows() -> List[Dict[str, Any]]:
    """State daily capacity rows (sgxm-t72h shape; sparse)."""
    return [
        {"state": "AL", "date": "2024-04-26T00:00:00.000",
         "critical_staffing_shortage_today_yes": "0",
         "critical_staffing_shortage_today_no": "5",
         "inpatient_beds": "14761", "inpatient_beds_used": "11934",
         "inpatient_beds_used_covid": "78",
         "inpatient_beds_utilization": "0.8085",
         "deaths_covid": "1",
         "geocoded_state": {"type": "Point", "coordinates": [-86.8287, 32.7794]}},
        {"state": "AL", "date": "2024-04-25T00:00:00.000",
         "inpatient_beds": "14761", "inpatient_beds_used": "11890",
         "inpatient_beds_used_covid": "83"},
        {"state": "TX", "date": "2024-04-26T00:00:00.000",
         "inpatient_beds": "58212", "inpatient_beds_used": "45301",
         "inpatient_beds_used_covid": "412"},
    ]


def pcr_testing_rows() -> List[Dict[str, Any]]:
    """PCR testing time-series rows (j8mb-icvb shape)."""
    return [
        {"state": "AL", "state_name": "Alabama", "state_fips": "01",
         "fema_region": "Region 4", "overall_outcome": "Negative",
         "date": "2020-03-01T00:00:00.000",
         "new_results_reported": "96", "total_results_reported": "96"},
        {"state": "AL", "state_name": "Alabama", "state_fips": "01",
         "fema_region": "Region 4", "overall_outcome": "Positive",
         "date": "2020-03-01T00:00:00.000",
         "new_results_reported": "7", "total_results_reported": "7"},
        {"state": "TX", "state_name": "Texas", "state_fips": "48",
         "fema_region": "Region 6", "overall_outcome": "Positive",
         "date": "2020-03-01T00:00:00.000",
         "new_results_reported": "11", "total_results_reported": "11"},
    ]


def hhs_ids_rows() -> List[Dict[str, Any]]:
    """HHS ID ↔ CCN crosswalk rows (vz64-k9wr shape)."""
    return [
        {"hhs_id": "C010039-C", "ccn": "010039",
         "facility_name": "Huntsville Hospital for Women & Children",
         "address": "245 GOVERNORS DR SE", "city": "HUNTSVILLE",
         "zip": "35801", "fips_code": "01089", "state": "AL",
         "geohash": "34.720741,-86.574529",
         "geocoded_hospital_address": {
             "type": "Point", "coordinates": [-86.574529, 34.720741]}},
        {"hhs_id": "C010039-A", "ccn": "010039",
         "facility_name": "Huntsville Hospital",
         "address": "101 SIVLEY RD", "city": "HUNTSVILLE",
         "zip": "35801", "fips_code": "01089", "state": "AL"},
        {"hhs_id": "H450054", "ccn": "450054",
         "facility_name": "Ascension Seton Medical Center Austin",
         "address": "1201 W 38TH ST", "city": "AUSTIN",
         "zip": "78705", "fips_code": "48453", "state": "TX"},
    ]


def therapeutics_rows() -> List[Dict[str, Any]]:
    """Therapeutic locator rows (rxn6-qnx8 shape). The two Kaiser rows
    mirror the live duplicate that forced address2 into the key."""
    return [
        {"provider_name": "KAISER PERMANENTE",
         "address1": "401 Bicentennial Way",
         "address2": "Hosp Bldg FL 1 Discharge Pharmacy",
         "city": "Santa Rosa", "county": "Sonoma", "state_code": "CA",
         "zip": "95403", "national_drug_code": "00069-1085-30",
         "order_label": "Paxlovid", "courses_available": "110",
         "geocoded_address": {"type": "Point",
                              "coordinates": [-122.726, 38.47162]},
         "npi": "1447606819", "last_report_date": "2023-12-13T00:00:00.000",
         "provider_status": "UNKNOWN INVENTORY"},
        {"provider_name": "KAISER PERMANENTE",
         "address1": "401 Bicentennial Way",
         "address2": "Outpatient Pharmacy",
         "city": "Santa Rosa", "county": "Sonoma", "state_code": "CA",
         "zip": "95403", "national_drug_code": "00069-1085-30",
         "order_label": "Paxlovid", "courses_available": "35",
         "npi": "1447606819", "last_report_date": "2023-12-13T00:00:00.000"},
        {"provider_name": "HOPE Community Medicine-Center Loc",
         "address1": "620 Tenaha St", "city": "Center", "county": "Shelby",
         "state_code": "TX", "zip": "75935",
         "national_drug_code": "00069-1085-30", "order_label": "Paxlovid",
         "courses_available": "16", "npi": "1093413191",
         "last_report_date": "2023-11-02T00:00:00.000"},
    ]


def policy_orders_rows() -> List[Dict[str, Any]]:
    """Policy order rows (gyqz-9u7n shape). The two Alameda rows mirror
    the live duplicate that forced comments+source into the key."""
    return [
        {"state_id": "CA", "county": "Alameda County", "fips_code": "06001",
         "policy_level": "county", "date": "2020-06-08T00:00:00.000",
         "policy_type": "Phase 2", "start_stop": "start",
         "comments": "Reopening outdoor museums", "source": "sip_submission_form",
         "total_phases": "4"},
        {"state_id": "CA", "county": "Alameda County", "fips_code": "06001",
         "policy_level": "county", "date": "2020-06-08T00:00:00.000",
         "policy_type": "Phase 2", "start_stop": "start",
         "comments": "Reopening retail curbside", "source": "BIA",
         "total_phases": "4"},
        {"state_id": "DE", "policy_level": "state",
         "date": "2020-07-06T00:00:00.000", "policy_type": "Phase 1",
         "start_stop": "stop",
         "comments": "Policy_Details: Governor Carney extended Delaware's "
                     "State of Emergency", "source": "BU COVID-19 State "
                     "Policy Database"},
    ]


def school_modality_rows() -> List[Dict[str, Any]]:
    """School learning modality rows (aitj-yx37 shape)."""
    return [
        {"district_nces_id": "0100005", "district_name": "Albertville City",
         "week": "2022-12-25T00:00:00.000", "learning_modality": "In Person",
         "operational_schools": "6", "student_count": "5824",
         "city": "Albertville", "state": "AL", "zip_code": "35950"},
        {"district_nces_id": "0100005", "district_name": "Albertville City",
         "week": "2022-12-18T00:00:00.000", "learning_modality": "In Person",
         "operational_schools": "6", "student_count": "5824",
         "city": "Albertville", "state": "AL", "zip_code": "35950"},
    ]


def community_profile_rows() -> List[Dict[str, Any]]:
    """Community Profile Report county rows (di4u-7yu6 shape)."""
    return [
        {"fips": "1089", "county": "Madison County, AL", "state": "AL",
         "fema_region": "4", "date": "2023-05-10T00:00:00.000",
         "cases_last_7_days": "63", "cases_per_100k_last_7_days": "16.2",
         "total_cases": "112690", "deaths_last_7_days": "0",
         "total_deaths": "804", "test_positivity_rate_last_7_days": "0.061",
         "pct_inpatient_beds_used_avg_last_7_days": "0.72",
         "pct_fully_vacc_total_pop": "0.52"},
        {"fips": "48453", "county": "Travis County, TX", "state": "TX",
         "fema_region": "6", "date": "2023-05-10T00:00:00.000",
         "cases_last_7_days": "182", "total_cases": "398112",
         "pct_fully_vacc_total_pop": "0.71"},
    ]


def generic_rows(n: int = 3) -> List[Dict[str, Any]]:
    """Rows for an arbitrary uncurated 4x4 (shape doesn't matter — that's
    the point of the generic table)."""
    return [{"some_col": f"v{i}", "other": i} for i in range(n)]
