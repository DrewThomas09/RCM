"""Enriched lookup handlers for the CMS Open Data slice.

Six domain nouns, none taken by other connectors (checked against every
``lookup.py`` in the estate, 2026-07-06):

    /v1/lookup/practice/{npi}        — a practitioner's Medicare practice
                                       profile (utilization/payment) plus
                                       enrollment, ordering/referring
                                       privileges and opt-out status
    /v1/lookup/prescriber/{npi}      — Part D prescriber profile + top
                                       drugs by claim count
    /v1/lookup/facility-cost/{ccn}   — HCRIS cost-report rows for a CCN
                                       across hospital / SNF / HHA
    /v1/lookup/ownership/{key}       — PECOS all-owners rows for an
                                       enrollment id or a hospital CCN
    /v1/lookup/cms-dataset/{key}     — a catalog entry + what of it is
                                       already ingested locally
    /v1/lookup/facility-universe/{state}
                                     — certified-facility counts by
                                       provider category for one state,
                                       aggregated over both Provider of
                                       Services files (QIES + iQIES)

They fan one key out across the canonical tables to return the full
picture in one call. Provided as **plain callables** plus a
router-agnostic handler map (:func:`v1_handlers`) so a router that
supports plugin registration can mount them *without editing its core*;
they stay usable directly (and via the CLI) regardless.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from .endpoints import CATALOG_TABLE, ENDPOINTS, GENERIC_TABLE, find_endpoint
from .normalize import slugify
from .tables import CmsOpenDataStore

_TOP_DRUGS_LIMIT = 25
_ROWS_LIMIT = 100


def lookup_practice(store: CmsOpenDataStore, npi: str) -> Dict[str, Any]:
    """One NPI's Medicare practice picture across the provider tables."""
    key = str(npi).strip()
    practice = _rows(
        store,
        "SELECT * FROM cms_open_data_mup_physician_by_provider "
        "WHERE rndrng_npi = ?", (key,))
    enrollment = _rows(
        store,
        "SELECT * FROM cms_open_data_ffs_provider_enrollment "
        "WHERE npi = ? LIMIT ?", (key, _ROWS_LIMIT))
    ordering = _rows(
        store,
        "SELECT * FROM cms_open_data_order_and_referring WHERE npi = ?",
        (key,))
    opt_out = _rows(
        store,
        "SELECT * FROM cms_open_data_opt_out_affidavits WHERE npi = ?",
        (key,))
    return {
        "npi": key,
        "count": len(practice),
        "practice": practice,
        "enrollment": enrollment,
        "order_and_referring": ordering[0] if ordering else None,
        "opt_out": opt_out,
    }


def lookup_prescriber(store: CmsOpenDataStore, npi: str) -> Dict[str, Any]:
    """A Part D prescriber's profile plus their top drugs by claims."""
    key = str(npi).strip()
    profile = _rows(
        store,
        "SELECT * FROM cms_open_data_mup_partd_prescriber_by_provider "
        "WHERE prscrbr_npi = ?", (key,))
    top_drugs = _rows(
        store,
        "SELECT prscrbr_npi, brnd_name, gnrc_name, tot_clms, tot_benes, "
        "tot_drug_cst, tot_day_suply "
        "FROM cms_open_data_mup_partd_prescriber_by_provider_drug "
        "WHERE prscrbr_npi = ? "
        "ORDER BY CAST(tot_clms AS REAL) DESC LIMIT ?",
        (key, _TOP_DRUGS_LIMIT))
    return {
        "npi": key,
        "count": len(profile),
        "prescriber": profile,
        "top_drugs": {"count": len(top_drugs), "by_claims": top_drugs},
    }


def lookup_facility_cost(store: CmsOpenDataStore, ccn: str) -> Dict[str, Any]:
    """HCRIS cost-report rows for a CCN across all three facility types.

    CCN spaces don't overlap across hospital / SNF / HHA, so scanning all
    three tables costs three indexed probes and spares the caller from
    knowing the facility type up front.
    """
    key = str(ccn).strip()
    out: Dict[str, Any] = {"ccn": key}
    total = 0
    for label, table in (("hospital", "cms_open_data_hospital_cost_report"),
                         ("snf", "cms_open_data_snf_cost_report"),
                         ("hha", "cms_open_data_hha_cost_report")):
        rows = _rows(
            store,
            f"SELECT * FROM {table} WHERE provider_ccn = ? "
            f"ORDER BY fiscal_year_end_date DESC LIMIT ?",
            (key, _ROWS_LIMIT))
        out[label] = rows
        total += len(rows)
    out["count"] = total
    return out


def lookup_ownership(store: CmsOpenDataStore, ccn_or_enrollment_id: str
                     ) -> Dict[str, Any]:
    """PECOS all-owners rows for an enrollment id — or a hospital CCN.

    A CCN is translated to enrollment ids through the hospital/FQHC/RHC
    enrollment tables first, then both all-owners tables are fanned out
    over the resolved ids (plus the raw key, so a direct enrollment id
    needs no enrollment row to resolve).
    """
    key = str(ccn_or_enrollment_id).strip()
    enrollment_ids = {key}
    for table in ("cms_open_data_hospital_enrollments",
                  "cms_open_data_fqhc_enrollments",
                  "cms_open_data_rhc_enrollments"):
        for r in _rows(store,
                       f"SELECT enrollment_id FROM {table} WHERE ccn = ?",
                       (key,)):
            if r.get("enrollment_id"):
                enrollment_ids.add(str(r["enrollment_id"]))
    ids = sorted(enrollment_ids)
    placeholders = ", ".join("?" for _ in ids)
    out: Dict[str, Any] = {"key": key, "enrollment_ids": ids}
    total = 0
    for label, table in (("hospital_owners", "cms_open_data_hospital_all_owners"),
                         ("snf_owners", "cms_open_data_snf_all_owners")):
        rows = _rows(
            store,
            f"SELECT * FROM {table} WHERE enrollment_id IN ({placeholders}) "
            f"ORDER BY enrollment_id LIMIT ?",
            (*ids, _ROWS_LIMIT))
        out[label] = rows
        total += len(rows)
    out["count"] = total
    return out


def lookup_cms_dataset(store: CmsOpenDataStore, dataset_key: str
                       ) -> Dict[str, Any]:
    """A catalog entry + how much of it is ingested locally.

    Accepts a catalog title slug, a curated short key, or a dataset UUID.
    Reports the curated table's row count when the dataset is a curated
    flagship, and the generic ``cms_open_data_rows`` slice count either
    way.
    """
    raw = str(dataset_key).strip()
    spec = find_endpoint(raw)
    slug = slugify(spec.title) if spec is not None and spec.kind == "curated" \
        else slugify(raw)
    catalog = _rows(
        store,
        f"SELECT * FROM {CATALOG_TABLE} WHERE dataset_key = ? OR uuid = ?",
        (slug, raw))
    entry = catalog[0] if catalog else None
    # Map a catalog entry back to a curated spec (by title slug) so the
    # caller sees the canonical table even when they passed the slug/UUID.
    if spec is None or spec.kind != "curated":
        title_slug = entry["dataset_key"] if entry else slug
        for s in ENDPOINTS.values():
            if s.kind == "curated" and slugify(s.title) == title_slug:
                spec = s
                break
    curated: Optional[Dict[str, Any]] = None
    if spec is not None and spec.kind == "curated":
        curated = {
            "dataset_id": spec.dataset_id,
            "table": spec.target_table,
            "rows": store.count(spec.target_table),
        }
    generic_key = entry["dataset_key"] if entry else slug
    generic_rows = store.count(
        GENERIC_TABLE, "dataset_key = ?", (generic_key,))
    return {
        "dataset_key": generic_key,
        "catalog": entry,
        "curated": curated,
        "generic_rows": generic_rows,
        "ingested": bool((curated and curated["rows"]) or generic_rows),
    }


# Provider category labels for the two Provider of Services files.
# VERIFIED from live samples (facility names per code, 2026-07-06): the
# legacy QIES file carries hospitals + the clinic categories; everything
# certified through iQIES (post-2023) lands in the Internet QIES file
# under its own type-id scheme. Unknown codes pass through label-less
# rather than guessing.
_POS_QIES_CATEGORIES: Dict[str, str] = {
    "01": "Hospital",
    "06": "Psychiatric Residential Treatment Facility",
    "12": "Rural Health Clinic",
    "19": "Community Mental Health Center",
    "21": "Federally Qualified Health Center",
}

_POS_IQIES_TYPES: Dict[str, str] = {
    "3": "Home Health Agency",
    "5": "Portable X-Ray Supplier",
    "6": "Comprehensive Outpatient Rehabilitation Facility",
    "7": "ESRD Facility (dialysis)",
    "8": "ICF/IID",
    "10": "Outpatient Physical Therapy/Speech Pathology",
    "11": "Ambulatory Surgical Center",
    "12": "Hospice",
    "13": "Organ Procurement Organization",
    "20": "Skilled Nursing Facility / Nursing Facility",
}


def lookup_facility_universe(store: CmsOpenDataStore, state: str
                             ) -> Dict[str, Any]:
    """Certified-facility counts by provider category for one state.

    Aggregates BOTH Provider of Services files — the legacy QIES file
    (hospitals, RHCs, FQHCs, CMHCs, PRTFs) and the Internet QIES file
    (HHAs, SNF/NFs, hospices, ASCs, ESRD, CORFs, OPTs, OPOs, …) — because
    together they are the certified-facility universe. ``facilities``
    counts every record (the files retain terminated providers);
    ``active`` counts rows whose program termination code is ``00``
    (active). Served straight from the ingested tables, no API calls.
    """
    key = str(state).strip().upper()
    qies = _rows(
        store,
        "SELECT prvdr_ctgry_cd, COUNT(*) AS facilities, "
        "SUM(CASE WHEN pgm_trmntn_cd = '00' THEN 1 ELSE 0 END) AS active "
        "FROM cms_open_data_pos_qies WHERE state_cd = ? "
        "GROUP BY prvdr_ctgry_cd ORDER BY facilities DESC", (key,))
    for r in qies:
        r["category"] = _POS_QIES_CATEGORIES.get(str(r["prvdr_ctgry_cd"]), "")
    iqies = _rows(
        store,
        "SELECT prvdr_type_id, COUNT(*) AS facilities, "
        "SUM(CASE WHEN pgm_trmntn_cd = '00' THEN 1 ELSE 0 END) AS active "
        "FROM cms_open_data_pos_internet_qies WHERE state_cd = ? "
        "GROUP BY prvdr_type_id ORDER BY facilities DESC", (key,))
    for r in iqies:
        r["category"] = _POS_IQIES_TYPES.get(str(r["prvdr_type_id"]), "")
    return {
        "state": key,
        "qies": qies,
        "internet_qies": iqies,
        "count": sum(int(r["facilities"] or 0) for r in qies + iqies),
        "active": sum(int(r["active"] or 0) for r in qies + iqies),
    }


# ── router-agnostic plugin surface ────────────────────────────────────
def v1_handlers(store: CmsOpenDataStore) -> Dict[str, Callable[[str], Dict[str, Any]]]:
    """Return ``{route_template: handler}`` for plugin registration.

    A router that accepts plugins can mount these without core edits::

        for route, fn in v1_handlers(store).items():
            router.register(route, fn)

    Each handler takes the single path parameter and returns a JSON-able
    dict. Kept deliberately framework-free so it binds to any router shape.
    """
    return {
        "/v1/lookup/practice/{npi}":
            lambda npi: lookup_practice(store, npi),
        "/v1/lookup/prescriber/{npi}":
            lambda npi: lookup_prescriber(store, npi),
        "/v1/lookup/facility-cost/{ccn}":
            lambda ccn: lookup_facility_cost(store, ccn),
        "/v1/lookup/ownership/{ccn_or_enrollment_id}":
            lambda key: lookup_ownership(store, key),
        "/v1/lookup/cms-dataset/{dataset_key}":
            lambda key: lookup_cms_dataset(store, key),
        "/v1/lookup/facility-universe/{state}":
            lambda state: lookup_facility_universe(store, state),
    }


def _rows(store: CmsOpenDataStore, sql: str, args: tuple) -> List[Dict[str, Any]]:
    return [dict(r) for r in store.fetchall(sql, args)]
