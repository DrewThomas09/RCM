"""Enriched lookup handlers: ``/v1/lookup/county-health/{fips}`` &
``/v1/lookup/cdc-dataset/{dataset_uid}``.

These fan one key out across the canonical tables to return a full
picture. They are provided as **plain callables** plus a router-agnostic
handler map (:func:`v1_handlers`) so a router that supports plugin
registration can mount them without editing its core; until then they
stay usable directly (and via the CLI).

Nouns are deliberately new to the estate (taken elsewhere: drug, device,
company, document, contractor, provider, taxonomy, code, category):

  county-health — every PLACES measure for a 5-digit county FIPS, plus
                  the county's NCHS drug-poisoning and heart-disease
                  mortality slices when ingested (all three tables key
                  counties by the same FIPS).
  cdc-dataset   — a catalog row for any 4x4 id, plus whether it is one of
                  this connector's curated datasets and how many generic
                  rows have been pulled for it.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List

from .registry import registry_rows
from .tables import CdcDataStore

_MEASURES_LIMIT = 500
_MORTALITY_LIMIT = 100
_GENERIC_SAMPLE_LIMIT = 5


def lookup_county_health(store: CdcDataStore, fips: str) -> Dict[str, Any]:
    """The full local-health picture for one 5-digit county FIPS."""
    code = str(fips).strip()
    # Tolerate un-padded FIPS (1073 → 01073): PLACES stores 5 digits.
    if code.isdigit() and len(code) < 5:
        code = code.zfill(5)
    places = _rows(
        store,
        "SELECT * FROM cdc_places_county WHERE locationid = ? "
        "ORDER BY categoryid, measureid, datavaluetypeid LIMIT ?",
        (code, _MEASURES_LIMIT))
    county = places[0]["locationname"] if places else None
    state = places[0]["stateabbr"] if places else None
    drug = _rows(
        store,
        # NCHS county drug-poisoning rows key FIPS without a leading zero.
        "SELECT * FROM cdc_drug_poisoning_county "
        "WHERE fips = ? OR fips = ? ORDER BY year DESC LIMIT ?",
        (code, code.lstrip("0") or code, _MORTALITY_LIMIT))
    heart = _rows(
        store,
        "SELECT * FROM cdc_heart_disease_mortality WHERE locationid = ? "
        "ORDER BY year DESC LIMIT ?", (code, _MORTALITY_LIMIT))
    return {
        "fips": code,
        "county": county,
        "state": state,
        "places": {"count": len(places), "measures": places},
        "drug_poisoning": {"count": len(drug), "rows": drug},
        "heart_disease_mortality": {"count": len(heart), "rows": heart},
    }


def lookup_cdc_dataset(store: CdcDataStore, dataset_uid: str) -> Dict[str, Any]:
    """A catalog row by 4x4 id + this connector's relationship to it."""
    uid = str(dataset_uid).strip()
    catalog = _rows(
        store, "SELECT * FROM cdc_data_catalog WHERE dataset_uid = ?", (uid,))
    # Is this 4x4 one of our curated first-class datasets?
    curated = [
        {"dataset_id": r.dataset_id, "target_table": r.target_table,
         "refresh_cadence": r.refresh_cadence}
        for r in registry_rows()
        if r.endpoint == f"/resource/{uid}.json"
    ]
    fetched = store.count("cdc_data_rows", "dataset_key = ?", (uid,))
    sample = _rows(
        store,
        "SELECT row_key, dataset_key, row_idx, row_json, fetched_at "
        "FROM cdc_data_rows WHERE dataset_key = ? ORDER BY row_idx LIMIT ?",
        (uid, _GENERIC_SAMPLE_LIMIT))
    return {
        "dataset_uid": uid,
        "catalog": catalog[0] if catalog else None,
        "curated_as": curated,
        "fetched_rows": {"count": fetched, "sample": sample},
    }


# ── router-agnostic plugin surface ────────────────────────────────────
def v1_handlers(store: CdcDataStore) -> Dict[str, Callable[[str], Dict[str, Any]]]:
    """Return ``{route_template: handler}`` for plugin registration.

    A router that accepts plugins can mount these without core edits::

        for route, fn in v1_handlers(store).items():
            router.register(route, fn)

    Each handler takes the single path parameter and returns a JSON-able
    dict. Kept deliberately framework-free so it binds to any router shape.
    """
    return {
        "/v1/lookup/county-health/{fips}":
            lambda fips: lookup_county_health(store, fips),
        "/v1/lookup/cdc-dataset/{dataset_uid}":
            lambda uid: lookup_cdc_dataset(store, uid),
    }


def _rows(store: CdcDataStore, sql: str, args: tuple) -> List[Dict[str, Any]]:
    return [dict(r) for r in store.fetchall(sql, args)]
