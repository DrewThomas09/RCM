"""NPPES API surface: registry shape, /v1/query uniform engine, and the
/v1/lookup/provider handlers."""
from __future__ import annotations

import pytest

from connectors.nppes import api, registry, synth, pipeline
from connectors.nppes.api import QueryError
from connectors.nppes.store import NppesStore


@pytest.fixture(scope="module")
def store(tmp_path_factory):
    d = tmp_path_factory.mktemp("nppes_api")
    m = synth.generate(str(d / "fx"), n_orgs=30, n_individuals=90, seed=5)
    s = NppesStore(str(d / "nppes.db"))
    pipeline.run(s, monthly_path=m["monthly_path"], nucc_path=m["nucc_path"],
                 monthly_version=m["monthly_version"],
                 monthly_header_count=m["monthly_header_count"],
                 weekly_paths=m["weekly_paths"],
                 othername_path=m["othername_path"],
                 endpoint_path=m["endpoint_path"],
                 practice_location_path=m["practice_location_path"],
                 landing_root=str(d / "landing"), write_journal=False)
    return s


# ── registry ────────────────────────────────────────────────────────
def test_registry_rows_have_contract_schema():
    required = {"dataset_id", "connector", "base_url", "endpoint",
                "default_params", "refresh_cadence", "join_keys",
                "target_table", "source"}
    for row in registry.registry_rows():
        assert required <= set(row)
        assert row["source"] == "nppes"
        assert isinstance(row["join_keys"], list)


def test_registry_dataset_by_id():
    ds = registry.dataset_by_id("nppes_monthly_full")
    assert ds["target_table"] == "dim_provider"
    with pytest.raises(KeyError):
        registry.dataset_by_id("does_not_exist")


# ── query engine ────────────────────────────────────────────────────
def test_query_filter_select_sort_paginate(store):
    res = api.query_dataset(
        store, "dim_provider",
        filters={"entity_type": 2},
        select=["npi", "organization_name", "entity_type"],
        sort=["-npi"], limit=5, offset=0)
    assert res["target_table"] == "dim_provider"
    assert res["total"] >= 1
    assert len(res["data"]) <= 5
    assert set(res["data"][0]) == {"npi", "organization_name", "entity_type"}
    npis = [r["npi"] for r in res["data"]]
    assert npis == sorted(npis, reverse=True)


def test_query_operators(store):
    res = api.query_dataset(
        store, "dim_provider",
        filters={"organization_name__like": "%MEDICINE%", "entity_type__eq": 2},
        limit=10)
    assert all("MEDICINE" in (r["organization_name"] or "") for r in res["data"])


def test_query_in_operator(store):
    res = api.query_dataset(
        store, "bridge_provider_taxonomy",
        filters={"taxonomy_code__in": ["207Q00000X", "207R00000X"]}, limit=50)
    assert all(r["taxonomy_code"] in ("207Q00000X", "207R00000X")
               for r in res["data"])


def test_query_pagination_cursor(store):
    p1 = api.query_dataset(store, "dim_provider", limit=10, offset=0)
    assert p1["next_offset"] == 10
    p2 = api.query_dataset(store, "dim_provider", limit=10,
                           offset=p1["next_offset"])
    assert {r["npi"] for r in p1["data"]} != {r["npi"] for r in p2["data"]}


def test_query_rejects_forbidden_columns(store):
    with pytest.raises(QueryError):
        api.query_dataset(store, "dim_provider", filters={"npi); DROP TABLE": 1})
    with pytest.raises(QueryError):
        api.query_dataset(store, "dim_provider", select=["evil_col"])
    with pytest.raises(QueryError):
        api.query_dataset(store, "dim_provider", sort=["nope"])


def test_query_unknown_dataset(store):
    with pytest.raises(QueryError):
        api.query_dataset(store, "not_a_dataset")


def test_query_by_registry_dataset_id(store):
    res = api.query_dataset(store, "nppes_provider_affiliation", limit=3)
    assert res["target_table"] == "bridge_provider_affiliation"


# ── lookup / search ─────────────────────────────────────────────────
def test_lookup_provider_full_view(store):
    # grab a known org NPI
    with store.connect() as con:
        npi = con.execute(
            "SELECT npi FROM dim_provider WHERE entity_type=2 LIMIT 1").fetchone()["npi"]
    view = api.lookup_provider(store, npi)
    assert view["provider"]["npi"] == npi
    assert "taxonomies" in view and "addresses" in view
    assert "affiliations" in view and "endpoints" in view
    # taxonomy joined to NUCC crosswalk
    if view["taxonomies"]:
        assert "classification" in view["taxonomies"][0]


def test_lookup_missing_returns_none(store):
    assert api.lookup_provider(store, "0000000000") is None


def test_search_by_state_and_entity(store):
    res = api.search_providers(store, state="TX", entity_type=2, limit=5)
    assert res["total"] >= 0
    assert len(res["data"]) <= 5


def test_search_by_taxonomy(store):
    res = api.search_providers(store, taxonomy_code="207Q00000X", limit=5)
    for r in res["data"]:
        assert r["npi"]


def test_mount_router_plugin_registration(store):
    class _Router:
        def __init__(self):
            self.routes = []
        def add_route(self, path, fn):
            self.routes.append((path, fn))
    r = _Router()
    assert api.mount_router(r, store) is True
    paths = {p for p, _ in r.routes}
    assert "/v1/lookup/provider/{npi}" in paths
    assert "/v1/query/{dataset}" in paths

    # a router with no hook → not mounted, but functions still callable
    class _Bare:
        pass
    assert api.mount_router(_Bare(), store) is False
