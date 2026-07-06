"""Enriched lookup handlers for the Care Compare provider families.

Seven nouns, all unique to this connector (the estate already owns
drug/device/company/document/contractor/provider/taxonomy/code/category):

    /v1/lookup/hospital/{facility_id}     hospital_general + star rating
    /v1/lookup/nursing-home/{ccn}         provider info + penalties summary
    /v1/lookup/home-health/{ccn}          HHA row
    /v1/lookup/hospice/{ccn}              hospice general + measure count
    /v1/lookup/dialysis/{ccn}             dialysis facility row
    /v1/lookup/clinician/{npi}            DAC national rows for one NPI
    /v1/lookup/pdc-dataset/{identifier}   catalog row + fetched-rows count

They are provided as **plain callables** plus a router-agnostic handler
map (:func:`v1_handlers`) so a router that supports plugin registration
can mount them *without editing its core*. If the core router can't
accept plugins, these stay usable directly (and via the CLI) and nothing
in the router is touched.

Each lookup fans one key out across the related canonical tables so the
caller gets the full picture in one call instead of stitching queries.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List

from .tables import ProviderDataStore

_ROWS_LIMIT = 100


def lookup_hospital(store: ProviderDataStore, facility_id: str) -> Dict[str, Any]:
    """Hospital General Information row + the overall star rating."""
    fid = str(facility_id).strip()
    rows = _rows(store,
                 "SELECT * FROM hospital_general WHERE facility_id = ?", (fid,))
    return {
        "facility_id": fid,
        "found": bool(rows),
        "hospital": rows[0] if rows else None,
        "overall_star_rating": rows[0]["hospital_overall_rating"] if rows else None,
    }


def lookup_nursing_home(store: ProviderDataStore, ccn: str) -> Dict[str, Any]:
    """Nursing home provider info + its penalty history summary."""
    key = str(ccn).strip()
    rows = _rows(store,
                 "SELECT * FROM nursing_home_provider_info "
                 "WHERE cms_certification_number_ccn = ?", (key,))
    penalties = _rows(store,
                      "SELECT * FROM nursing_home_penalties "
                      "WHERE cms_certification_number_ccn = ? "
                      "ORDER BY penalty_date DESC LIMIT ?", (key, _ROWS_LIMIT))
    return {
        "ccn": key,
        "found": bool(rows),
        "provider": rows[0] if rows else None,
        "overall_rating": rows[0]["overall_rating"] if rows else None,
        "penalties": {"count": store.count(
            "nursing_home_penalties", "cms_certification_number_ccn = ?", (key,)),
            "rows": penalties},
    }


def lookup_home_health(store: ProviderDataStore, ccn: str) -> Dict[str, Any]:
    """Home health agency row + its quality-of-care star rating."""
    key = str(ccn).strip()
    rows = _rows(store,
                 "SELECT * FROM home_health_agencies "
                 "WHERE cms_certification_number_ccn = ?", (key,))
    return {
        "ccn": key,
        "found": bool(rows),
        "agency": rows[0] if rows else None,
        "quality_star_rating": (rows[0]["quality_of_patient_care_star_rating"]
                                if rows else None),
    }


def lookup_hospice(store: ProviderDataStore, ccn: str) -> Dict[str, Any]:
    """Hospice general-information row + how many measures it reported."""
    key = str(ccn).strip()
    rows = _rows(store,
                 "SELECT * FROM hospice_general "
                 "WHERE cms_certification_number_ccn = ?", (key,))
    measures = store.count("hospice_provider",
                           "cms_certification_number_ccn = ?", (key,))
    return {
        "ccn": key,
        "found": bool(rows),
        "hospice": rows[0] if rows else None,
        "measure_rows": measures,
    }


def lookup_dialysis(store: ProviderDataStore, ccn: str) -> Dict[str, Any]:
    """Dialysis facility row (five-star + outcome summaries)."""
    key = str(ccn).strip()
    rows = _rows(store,
                 "SELECT * FROM dialysis_facilities "
                 "WHERE cms_certification_number_ccn = ?", (key,))
    return {
        "ccn": key,
        "found": bool(rows),
        "facility": rows[0] if rows else None,
        "five_star": rows[0]["five_star"] if rows else None,
    }


def lookup_clinician(store: ProviderDataStore, npi: str) -> Dict[str, Any]:
    """Every DAC national row for one NPI (clinician x org x address)."""
    key = str(npi).strip()
    rows = _rows(store,
                 "SELECT * FROM dac_national WHERE npi = ? "
                 "ORDER BY org_pac_id, adrs_id LIMIT ?", (key, _ROWS_LIMIT))
    return {
        "npi": key,
        "count": store.count("dac_national", "npi = ?", (key,)),
        "rows": rows,
        "organizations": sorted({r["facility_name"] for r in rows
                                 if r.get("facility_name") not in (None, "")}),
    }


def lookup_pdc_dataset(store: ProviderDataStore, identifier: str) -> Dict[str, Any]:
    """One catalog entry + how many generic rows we've pulled for it."""
    key = str(identifier).strip()
    rows = _rows(store,
                 "SELECT * FROM provider_data_catalog WHERE identifier = ?",
                 (key,))
    fetched = store.count("provider_data_rows", "dataset_key = ?", (key,))
    return {
        "identifier": key,
        "found": bool(rows),
        "dataset": rows[0] if rows else None,
        "fetched_rows": fetched,
    }


# ── router-agnostic plugin surface ────────────────────────────────────
def v1_handlers(store: ProviderDataStore) -> Dict[str, Callable[[str], Dict[str, Any]]]:
    """Return ``{route_template: handler}`` for plugin registration.

    A router that accepts plugins can mount these without core edits::

        for route, fn in v1_handlers(store).items():
            router.register(route, fn)

    Each handler takes the single path parameter and returns a JSON-able
    dict. Kept deliberately framework-free so it binds to any router shape.
    """
    return {
        "/v1/lookup/hospital/{facility_id}":
            lambda fid: lookup_hospital(store, fid),
        "/v1/lookup/nursing-home/{ccn}":
            lambda ccn: lookup_nursing_home(store, ccn),
        "/v1/lookup/home-health/{ccn}":
            lambda ccn: lookup_home_health(store, ccn),
        "/v1/lookup/hospice/{ccn}":
            lambda ccn: lookup_hospice(store, ccn),
        "/v1/lookup/dialysis/{ccn}":
            lambda ccn: lookup_dialysis(store, ccn),
        "/v1/lookup/clinician/{npi}":
            lambda npi: lookup_clinician(store, npi),
        "/v1/lookup/pdc-dataset/{identifier}":
            lambda ident: lookup_pdc_dataset(store, ident),
    }


def _rows(store: ProviderDataStore, sql: str, args: tuple) -> List[Dict[str, Any]]:
    return [dict(r) for r in store.fetchall(sql, args)]
