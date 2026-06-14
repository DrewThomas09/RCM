"""NPPES derived affiliation bridge: heuristic correctness, confidence
bounds, method tagging, and idempotent rebuild."""
from __future__ import annotations

import pytest

from connectors.nppes import affiliation, synth, pipeline
from connectors.nppes.store import NppesStore


@pytest.fixture(scope="module")
def store(tmp_path_factory):
    d = tmp_path_factory.mktemp("nppes_affil")
    m = synth.generate(str(d / "fx"), n_orgs=40, n_individuals=200, seed=9)
    s = NppesStore(str(d / "nppes.db"))
    pipeline.run(s, monthly_path=m["monthly_path"], nucc_path=m["nucc_path"],
                 monthly_version=m["monthly_version"],
                 monthly_header_count=m["monthly_header_count"],
                 othername_path=m["othername_path"],
                 landing_root=str(d / "landing"), write_journal=False)
    return s


def test_affiliations_exist_with_confidence_bounds(store):
    with store.connect() as con:
        rows = con.execute(
            "SELECT individual_npi, organization_npi, method, confidence, evidence "
            "FROM bridge_provider_affiliation").fetchall()
    assert rows, "expected derived affiliations"
    for r in rows:
        assert 0.0 <= r["confidence"] <= 1.0
        assert r["method"] in ("shared_practice_address", "shared_address+name")
        assert r["evidence"]


def test_name_overlap_boosts_confidence(store):
    with store.connect() as con:
        named = con.execute(
            "SELECT MIN(confidence) lo FROM bridge_provider_affiliation "
            "WHERE method='shared_address+name'").fetchone()["lo"]
        addr_only = con.execute(
            "SELECT MAX(confidence) hi FROM bridge_provider_affiliation "
            "WHERE method='shared_practice_address'").fetchone()["hi"]
    if named is not None and addr_only is not None:
        # name+address evidence should be able to outrank address-only
        assert named >= addr_only


def test_links_are_individual_to_organization(store):
    """Every affiliation links a Type-1 individual to a Type-2 org."""
    with store.connect() as con:
        bad = con.execute(
            "SELECT COUNT(*) c FROM bridge_provider_affiliation b "
            "JOIN dim_provider i ON i.npi=b.individual_npi "
            "JOIN dim_provider o ON o.npi=b.organization_npi "
            "WHERE i.entity_type<>1 OR o.entity_type<>2").fetchone()["c"]
    assert bad == 0


def test_rebuild_is_idempotent(store):
    with store.connect() as con:
        before = con.execute(
            "SELECT COUNT(*) c FROM bridge_provider_affiliation").fetchone()["c"]
    affiliation.build_affiliations(store)
    with store.connect() as con:
        after = con.execute(
            "SELECT COUNT(*) c FROM bridge_provider_affiliation").fetchone()["c"]
    assert after == before
