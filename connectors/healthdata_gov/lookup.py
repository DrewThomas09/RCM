"""Enriched lookup handlers: ``/v1/lookup/hhs-dataset/{dataset_uid}`` &
``/v1/lookup/hospital-capacity/{ccn}``.

These fan one key out across the canonical tables to return a full
picture. They are provided as **plain callables** plus a router-agnostic
handler map (:func:`v1_handlers`) so a router that supports plugin
registration can mount them without editing its core; until then they
stay usable directly (and via the CLI).

Nouns are deliberately new to the estate (taken elsewhere: drug, device,
company, document, contractor, provider, taxonomy, code, category,
practice, prescriber, facility-cost, ownership, cms-dataset, hospital,
nursing-home, home-health, hospice, dialysis, clinician, pdc-dataset,
physician-payments, manufacturer, op-dataset, ndc-cost, state-drug,
medicaid-dataset, marketplace-plan, county-plans, county-health,
cdc-dataset, shortage-area, health-center, grant, grantee-org,
county-demographics, state-demographics, exclusion, exclusion-name,
labor-market, industry-employment, facility-universe):

  hhs-dataset      — a catalog row for any 4x4 id on the HHS-wide
                     meta-catalog plus its hosting posture, VERIFIED
                     LIVE 2026-07-06: ``domain=datahub.hhs.gov`` marks
                     HHS's own hub records (whose *tabular* assets are
                     the ones that actually serve rows on
                     ``/resource/``; hub records with an ``attribution``
                     naming another portal — data.cdc.gov,
                     data.medicaid.gov, … — are href mirrors of
                     catalogs other estate connectors already cover),
                     while ``domain=healthdata.gov`` marks copies
                     federated in from state/city portals. Non-row
                     entries 403 on ``/resource/``. The lookup also
                     reports whether the id is one of this connector's
                     curated datasets and how many generic rows have
                     been pulled for it.
  hospital-capacity — one hospital's COVID-era capacity picture by CCN
                     (or HHS Protect hospital_pk): identity + HHS-ID
                     crosswalk rows from ``hhs_hospital_ids`` and the
                     most recent weekly utilization rows from
                     ``hhs_hospital_capacity_facility``.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List

from .registry import registry_rows
from .tables import HealthdataGovStore

_WEEKS_LIMIT = 26              # ~half a year of weekly capacity rows
_GENERIC_SAMPLE_LIMIT = 5


def lookup_hhs_dataset(store: HealthdataGovStore, dataset_uid: str) -> Dict[str, Any]:
    """A catalog row by 4x4 id + this connector's relationship to it."""
    uid = str(dataset_uid).strip()
    catalog = _rows(
        store, "SELECT * FROM healthdata_gov_catalog WHERE dataset_uid = ?",
        (uid,))
    cat = catalog[0] if catalog else None
    # Hosting posture (verified live): datahub.hhs.gov = HHS's own hub
    # record; healthdata.gov = a copy federated in from a state/city
    # portal. A hub record whose attribution names another portal is an
    # href mirror of that portal's dataset — the estate covers those
    # through their home connectors, and /resource/ 403s for them here.
    hhs_hub = bool(cat) and cat.get("domain") == "datahub.hhs.gov"
    attribution = cat.get("attribution") if cat else None
    # Is this 4x4 one of our curated first-class datasets?
    curated = [
        {"dataset_id": r.dataset_id, "target_table": r.target_table,
         "refresh_cadence": r.refresh_cadence}
        for r in registry_rows()
        if r.endpoint == f"/resource/{uid}.json"
    ]
    fetched = store.count("healthdata_gov_rows", "dataset_key = ?", (uid,))
    sample = _rows(
        store,
        "SELECT row_key, dataset_key, row_idx, row_json, fetched_at "
        "FROM healthdata_gov_rows WHERE dataset_key = ? ORDER BY row_idx "
        "LIMIT ?",
        (uid, _GENERIC_SAMPLE_LIMIT))
    return {
        "dataset_uid": uid,
        "catalog": cat,
        "hhs_hub": hhs_hub,
        "domain": cat.get("domain") if cat else None,
        "attribution": attribution,
        "curated_as": curated,
        "fetched_rows": {"count": fetched, "sample": sample},
    }


def lookup_hospital_capacity(store: HealthdataGovStore, ccn: str) -> Dict[str, Any]:
    """One hospital's COVID-era capacity picture by CCN / hospital_pk.

    hospital_pk in the facility file is the CCN for CMS-certified
    hospitals (and an HHS-assigned surrogate otherwise), so the lookup
    matches either column. The HHS-ID crosswalk rows bridge to every
    other CCN-keyed dataset in the estate.
    """
    code = str(ccn).strip()
    ids = _rows(
        store,
        "SELECT * FROM hhs_hospital_ids WHERE ccn = ? OR hhs_id = ? "
        "ORDER BY hhs_id",
        (code, code))
    weeks = _rows(
        store,
        "SELECT * FROM hhs_hospital_capacity_facility "
        "WHERE ccn = ? OR hospital_pk = ? "
        "ORDER BY collection_week DESC LIMIT ?",
        (code, code, _WEEKS_LIMIT))
    head = weeks[0] if weeks else (ids[0] if ids else None)
    name = head.get("hospital_name") or head.get("facility_name") if head else None
    return {
        "ccn": code,
        "hospital_name": name,
        "state": head.get("state") if head else None,
        "city": head.get("city") if head else None,
        "hhs_ids": {"count": len(ids), "rows": ids},
        "weekly_capacity": {"count": len(weeks), "rows": weeks},
    }


# ── router-agnostic plugin surface ────────────────────────────────────
def v1_handlers(store: HealthdataGovStore) -> Dict[str, Callable[[str], Dict[str, Any]]]:
    """Return ``{route_template: handler}`` for plugin registration.

    A router that accepts plugins can mount these without core edits::

        for route, fn in v1_handlers(store).items():
            router.register(route, fn)

    Each handler takes the single path parameter and returns a JSON-able
    dict. Kept deliberately framework-free so it binds to any router shape.
    """
    return {
        "/v1/lookup/hhs-dataset/{dataset_uid}":
            lambda uid: lookup_hhs_dataset(store, uid),
        "/v1/lookup/hospital-capacity/{ccn}":
            lambda ccn: lookup_hospital_capacity(store, ccn),
    }


def _rows(store: HealthdataGovStore, sql: str, args: tuple) -> List[Dict[str, Any]]:
    return [dict(r) for r in store.fetchall(sql, args)]
