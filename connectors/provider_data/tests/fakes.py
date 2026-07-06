"""In-memory fake Provider Data Catalog server for tests — no socket.

A :class:`FakeProviderData` is an :data:`Opener` (``(url, headers,
timeout) -> RawResponse``) that serves canned records and models the two
live response shapes (probed 2026-07-06):

  * the metastore catalog path returns a bare JSON **array** of dataset
    metadata items;
  * datastore query paths page by ``limit``/``offset`` and wrap rows in
    ``{"results": [...], "count": total, "query": {...}, "schema": {...}}``
    — ``count`` is always present and reflects the *filtered* total when
    ``conditions[i][...]`` equality params are sent;
  * an unknown identifier is a 404 with a JSON message.

It also models 429 + ``Retry-After`` and 5xx via a scripted
``transients`` map so the transport's retry path is exercised without a
network. Fixture payloads below carry the REAL live column names so the
normalize/tables tests bind to the schema the API actually serves.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List
from urllib.parse import parse_qs, urlparse

from ..transport import RawResponse

CATALOG_PATH = "/api/1/metastore/schemas/dataset/items"
# Identifiers are 4x4s (xubh-q36u) or ESRD QIP slugs (complete_qip_data,
# tps, pppw) — the live datastore serves both shapes at the same path.
_DATASTORE_RE = re.compile(r"/api/1/datastore/query/([0-9a-z_-]+)/0$")


class FakeProviderData:
    def __init__(self) -> None:
        # Datastore records keyed by 4x4 identifier.
        self.records: Dict[str, List[Dict[str, Any]]] = {}
        self.catalog: List[Dict[str, Any]] = []
        self.calls: List[str] = []
        # Scripted transient responses keyed by call index: {idx: (status, headers)}.
        self.transients: Dict[int, Any] = {}

    def add(self, identifier: str, records: List[Dict[str, Any]]
            ) -> "FakeProviderData":
        self.records[identifier] = list(records)
        return self

    def add_catalog(self, items: List[Dict[str, Any]]) -> "FakeProviderData":
        self.catalog = list(items)
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

        if path.endswith(CATALOG_PATH):
            return RawResponse(status=200,
                               body=json.dumps(self.catalog).encode())

        m = _DATASTORE_RE.search(path)
        if m:
            identifier = m.group(1)
            if identifier not in self.records:
                body = {"message": f"No resource found for dataset {identifier} at index 0"}
                return RawResponse(status=404, body=json.dumps(body).encode())
            recs = self._filtered(self.records[identifier], qs)
            limit = int(qs.get("limit", ["500"])[0])
            offset = int(qs.get("offset", ["0"])[0])
            page = recs[offset:offset + limit]
            envelope = {
                "results": page,
                "count": len(recs),        # filtered total, like the live API
                "query": {"limit": limit, "offset": offset},
                "schema": {},
            }
            return RawResponse(status=200, body=json.dumps(envelope).encode())

        return RawResponse(status=404, body=b'{"message":"no route"}')

    @staticmethod
    def _filtered(recs: List[Dict[str, Any]], qs: Dict[str, List[str]]
                  ) -> List[Dict[str, Any]]:
        """Apply DKAN ``conditions[i][property/value]`` equality filters."""
        i = 0
        out = recs
        while f"conditions[{i}][property]" in qs:
            prop = qs[f"conditions[{i}][property]"][0]
            value = qs.get(f"conditions[{i}][value]", [""])[0]
            out = [r for r in out if str(r.get(prop, "")) == value]
            i += 1
        return out


# ── realistic fixtures (field names copied from live payloads) ────────
def catalog_items() -> List[Dict[str, Any]]:
    """Three metastore items shaped exactly like the live catalog."""
    return [
        {
            "@type": "dcat:Dataset",
            "accessLevel": "public",
            "identifier": "xubh-q36u",
            "title": "Hospital General Information",
            "description": "A list of all hospitals that have been registered with Medicare.",
            "theme": ["Hospitals"],
            "keyword": ["Comparison Tool"],
            "issued": "2020-12-10",
            "modified": "2026-04-09",
            "released": "2026-04-09",
            "landingPage": "https://data.cms.gov/provider-data/dataset/xubh-q36u",
            "distribution": [{
                "@type": "dcat:Distribution",
                "downloadURL": "https://data.cms.gov/provider-data/sites/default/files/resources/hospital_general.csv",
                "mediaType": "text/csv",
            }],
        },
        {
            "@type": "dcat:Dataset",
            "accessLevel": "public",
            "identifier": "4pq5-n9py",
            "title": "Nursing homes including rehab services - Provider Information",
            "description": "General information on currently active nursing homes.",
            "theme": ["Nursing homes including rehab services"],
            "keyword": ["Five Star", "Quality"],
            "issued": "2020-03-14",
            "modified": "2026-06-01",
            "landingPage": "https://data.cms.gov/provider-data/dataset/4pq5-n9py",
            "distribution": [{
                "@type": "dcat:Distribution",
                "downloadURL": "https://data.cms.gov/provider-data/sites/default/files/resources/nh_provider.csv",
                "mediaType": "text/csv",
            }],
        },
        {
            "@type": "dcat:Dataset",
            "accessLevel": "public",
            "identifier": "77hc-ibv8",
            "title": "Healthcare Associated Infections - Hospital",
            "description": "The Healthcare-Associated Infection (HAI) measures show how often patients in a particular hospital contract certain infections.",
            "theme": ["Hospitals"],
            "keyword": ["Quality"],
            "issued": "2020-12-10",
            "modified": "2026-01-15",
            "landingPage": "https://data.cms.gov/provider-data/dataset/77hc-ibv8",
            # A catalog entry with no distribution — csv_url must degrade.
            "distribution": [],
        },
    ]


def hospital_rows(n: int = 5) -> List[Dict[str, Any]]:
    """hospital_general (xubh-q36u) rows with the live column names."""
    states = ["AL", "AL", "TX", "TX", "CA"]
    return [{
        "facility_id": f"01000{i}",
        "facility_name": f"TEST MEDICAL CENTER {i}",
        "address": f"{100 + i} MAIN ST",
        "citytown": "DOTHAN",
        "state": states[i % len(states)],
        "zip_code": "36301",
        "countyparish": "HOUSTON",
        "telephone_number": "(334) 793-8701",
        "hospital_type": "Acute Care Hospitals",
        "hospital_ownership": "Government - Hospital District or Authority",
        "emergency_services": "Yes",
        "meets_criteria_for_birthing_friendly_designation": "Y",
        "hospital_overall_rating": str((i % 5) + 1),
        "hospital_overall_rating_footnote": "",
        "mort_group_measure_count": "7",
    } for i in range(n)]


def hcahps_rows() -> List[Dict[str, Any]]:
    """hcahps_hospital (dgck-syfz) rows with the live column names."""
    return [{
        "facility_id": "010001",
        "facility_name": "TEST MEDICAL CENTER 0",
        "address": "100 MAIN ST",
        "citytown": "DOTHAN",
        "state": "AL",
        "zip_code": "36301",
        "countyparish": "HOUSTON",
        "telephone_number": "(334) 793-8701",
        "hcahps_measure_id": mid,
        "hcahps_question": q,
        "hcahps_answer_description": desc,
        "patient_survey_star_rating": star,
        "patient_survey_star_rating_footnote": "",
        "hcahps_answer_percent": pct,
        "hcahps_answer_percent_footnote": "",
        "hcahps_linear_mean_value": "Not Applicable",
        "number_of_completed_surveys": "300",
        "number_of_completed_surveys_footnote": "",
        "survey_response_rate_percent": "22",
        "survey_response_rate_percent_footnote": "",
        "start_date": "01/01/2024",
        "end_date": "12/31/2024",
    } for mid, q, desc, star, pct in [
        ("H_COMP_1_A_P", "Nurses always communicated well",
         "Patients who reported that their nurses always communicated well",
         "Not Applicable", "81"),
        ("H_STAR_RATING", "Summary star rating", "Summary star rating", "4",
         "Not Applicable"),
    ]]


def clinician_rows() -> List[Dict[str, Any]]:
    """dac_national (mj5m-pzi6) rows with the live column names.

    Same NPI at two organizations — exercises the composed 4-field key.
    """
    base = {
        "npi": "1659447118",
        "ind_pac_id": "0143128082",
        "ind_enrl_id": "I20200729003366",
        "provider_last_name": "SMITH",
        "provider_first_name": "JANE",
        "provider_middle_name": "Q",
        "suff": "",
        "gndr": "F",
        "cred": "MD",
        "med_sch": "OTHER",
        "grd_yr": "2005",
        "pri_spec": "DIAGNOSTIC RADIOLOGY",
        "sec_spec_all": "",
        "telehlth": "Y",
        "num_org_mem": "12",
        "adr_ln_1": "715 GRAND AVE",
        "adr_ln_2": "",
        "ln_2_sprs": "",
        "citytown": "ALBUQUERQUE",
        "state": "NM",
        "zip_code": "871064814",
        "telephone_number": "5057274700",
        "ind_assgn": "Y",
        "grp_assgn": "Y",
    }
    a = dict(base, facility_name="RADIOLOGY ASSOCIATES OF ALBUQUERQUE PA",
             org_pac_id="2860304482", adrs_id="VI00840XXXXFRXXXXXXXXXX00")
    b = dict(base, facility_name="CENTRAL TEXAS RADIOLOGICAL ASSOCIATES PA",
             org_pac_id="4385740141", adrs_id="VI00840XXXXSTXXXXXXXXXX00")
    return [a, b]


def ich_cahps_facility_rows() -> List[Dict[str, Any]]:
    """ich_cahps_facility (59mq-zhts) rows with the live column names.

    Carries the doubled-underscore raw headers the live file really
    serves (``…communication_and__205e``) so the ``_snake`` hazard path
    is exercised end-to-end.
    """
    return [{
        "cms_certification_number_ccn": f"01230{i}",
        "network": "8",
        "facility_name": f"TEST DIALYSIS CENTER {i}",
        "address_line_1": "1600 7TH AVENUE SOUTH",
        "address_line_2": "",
        "citytown": "BIRMINGHAM",
        "state": "AL",
        "zip_code": "35233",
        "countyparish": "Jefferson",
        "telephone_number": "(205) 638-9275",
        "profit_or_nonprofit": "Non-profit",
        "chain_owned": "No",
        "chain_organization": "Independent",
        "ichcahps_date": "18Oct2024-11Jul2025",
        "ichcahps_data_availability_code": "001",
        "top_box_percent_of_patientsnephrologists_communication_and__205e": "75",
        "top_box_percent_of_patientsquality_of_dialysis_center_care__0710": "69",
        "star_rating_of_the_dialysis_facility": str((i % 5) + 1),
        "ich_cahps_survey_of_patients_experiences_star_rating": "4",
        "survey_response_rate": "22",
    } for i in range(3)]


def qip_tps_rows() -> List[Dict[str, Any]]:
    """esrd_qip_tps (slug identifier ``tps``) rows, live column names."""
    return [{
        "facility_name": f"03230{i} TEST DIALYSIS - {i}",
        "cms_certification_number_ccn": f"03230{i}",
        "alternate_ccn": f"03002{i}",
        "address": "2525 E ROOSEVELT ST",
        "city": "PHOENIX",
        "state": "AZ",
        "zip_code": "85008",
        "network": "Network 15",
        "total_performance_score": str(60 + i),
        "state_average_total_performance_score": "54",
        "national_average_total_performance_score": "54",
        "payment_reduction_percentage": "0.0%",
    } for i in range(3)]


def asc_facility_rows() -> List[Dict[str, Any]]:
    """asc_quality_facility (4jcv-atw7) rows with the live column names.

    Mirrors the two live key hazards: a row with an EMPTY facility_id
    (npi still populated — 3 such rows exist live) and two rows sharing
    one facility_id at different NPIs (98 such pairs live) — both must
    survive the npi-led composed key.
    """
    base = {
        "citytown": "PLANO", "state": "TX", "zip_code": "75093",
        "year": "2024", "asc1_rate": "N/A", "asc1_footnote": "5",
        "asc2_rate": "0.033", "asc2_footnote": "",
        "asc9_rate": "85.64", "asc9_footnote": "",
        "asc12_total_cases": "1343",
        "asc12_performance_category": "No Different Than the National Rate",
        "asc12_rshv_rate": "11.9", "asc12_interval_lower_limit": "9",
        "asc12_interval_upper_limit": "15.8", "asc12_footnote": "",
    }
    return [
        dict(base, facility_name="TEXAS ENDOSCOPY PLANO",
             facility_id="45C0001277", npi="1023420577"),
        dict(base, facility_name="DIGESTIVE HEALTH SPECIALISTS PA",
             facility_id="34C0001142", npi="1184976797"),
        dict(base, facility_name="DIGESTIVE HEALTH SPECIALISTS PA",
             facility_id="34C0001142", npi="1306005343"),
        dict(base, facility_name="SLENT SURGERY CENTER",
             facility_id="", npi="1134590912"),
    ]


def supplier_rows(n: int = 4) -> List[Dict[str, Any]]:
    """medical_equipment_suppliers (ct36-nrcq) rows, live column names."""
    return [{
        "provider_id": f"3436341{i}",
        "acceptsassignement": "True",
        "participationbegindate": "2026-02-27",
        "businessname": f"TEST SUPPLIER {i} INC",
        "practicename": f"TEST PHARMACY {i}",
        "practiceaddress1": f"{i} GRAND PKWY S",
        "practiceaddress2": "",
        "practicecity": "RICHMOND",
        "practicestate": "TX",
        "practicezip9code": "774078710",
        "telephonenumber": "3465704749",
        "specialitieslist": "Pharmacy",
        "providertypelist": "",
        "supplieslist": "Epoetin|Infusion Drugs",
        "latitude": "29.65170077032",
        "longitude": "-95.706947816399",
        "is_contracted_for_cba": "False",
    } for i in range(n)]


def generic_hai_rows(n: int = 4) -> List[Dict[str, Any]]:
    """Rows for a non-curated catalog dataset (77hc-ibv8, HAI - Hospital).

    Field names copied from the live datastore — proves any of the 234
    catalog datasets round-trips through the generic rows table.
    """
    return [{
        "facility_id": f"01000{i}",
        "facility_name": f"TEST MEDICAL CENTER {i}",
        "address": f"{i} ELM ST",
        "citytown": "DOTHAN",
        "state": "AL",
        "zip_code": "36301",
        "countyparish": "HOUSTON",
        "telephone_number": "(334) 793-8701",
        "measure_id": "HAI_1_CILOWER",
        "measure_name": "Central Line Associated Bloodstream Infection: Lower Confidence Limit",
        "compared_to_national": "Better than the National Benchmark",
        "score": "0.073",
        "footnote": "",
        "start_date": "07/01/2024",
        "end_date": "06/30/2025",
    } for i in range(n)]
