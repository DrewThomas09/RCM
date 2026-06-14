"""CDD analytics over the NPPES universe: TAM, HHI concentration,
fragmentation / roll-up, roster integrity, affiliation footprint."""
from __future__ import annotations

import pytest

from connectors.nppes import cdd, synth, pipeline
from connectors.nppes.store import NppesStore


@pytest.fixture(scope="module")
def store(tmp_path_factory):
    d = tmp_path_factory.mktemp("nppes_cdd")
    m = synth.generate(str(d / "fx"), n_orgs=60, n_individuals=300, seed=13)
    s = NppesStore(str(d / "nppes.db"))
    pipeline.run(s, monthly_path=m["monthly_path"], nucc_path=m["nucc_path"],
                 monthly_version=m["monthly_version"],
                 monthly_header_count=m["monthly_header_count"],
                 othername_path=m["othername_path"],
                 landing_root=str(d / "landing"), write_journal=False)
    return s


def test_tam_by_taxonomy_geography(store):
    rows = cdd.tam_by_taxonomy_geography(store, geo_level="state", limit=20)
    assert rows
    for r in rows:
        assert {"geo", "classification", "provider_count"} <= set(r)
        assert r["provider_count"] >= 1
    # sorted densest-first
    counts = [r["provider_count"] for r in rows]
    assert counts == sorted(counts, reverse=True)


def test_tam_filter_classification(store):
    rows = cdd.tam_by_taxonomy_geography(
        store, classification="Internal Medicine", limit=20)
    assert all(r["classification"] == "Internal Medicine" for r in rows)


def test_hhi_in_range_and_banded(store):
    rows = cdd.market_concentration(store, min_providers=3, limit=200)
    assert rows
    for r in rows:
        assert 0.0 <= r["hhi"] <= 10000.0
        assert r["concentration_band"] in (
            "unconcentrated", "moderately_concentrated", "highly_concentrated")
        # HHI band consistency
        if r["hhi"] < cdd.HHI_UNCONCENTRATED:
            assert r["concentration_band"] == "unconcentrated"
        elif r["hhi"] >= cdd.HHI_MODERATE:
            assert r["concentration_band"] == "highly_concentrated"
        # top firm share never exceeds 100
        assert 0.0 <= r["top_firm_share_pct"] <= 100.0
    # ranked most-concentrated first
    hhis = [r["hhi"] for r in rows]
    assert hhis == sorted(hhis, reverse=True)


def test_hhi_singletons_are_competitive():
    """A market of all-independent providers should be near-perfectly
    competitive (low HHI)."""
    import tempfile
    d = tempfile.mkdtemp()
    m = synth.generate(d, n_orgs=5, n_individuals=200, seed=21)
    s = NppesStore(d + "/n.db")
    pipeline.run(s, monthly_path=m["monthly_path"], nucc_path=m["nucc_path"],
                 monthly_version=m["monthly_version"],
                 monthly_header_count=m["monthly_header_count"],
                 landing_root=d + "/landing", write_journal=False)
    rows = cdd.market_concentration(s, min_providers=20, limit=50)
    # at least one sizeable market should be unconcentrated
    if rows:
        assert min(r["hhi"] for r in rows) < cdd.HHI_MODERATE


def test_fragmentation_scan_produces_rollup_scores(store):
    rows = cdd.fragmentation_scan(store, min_providers=5, limit=20)
    assert rows
    for r in rows:
        assert 0.0 <= r["independent_share_pct"] <= 100.0
        assert r["rollup_score"] >= 0.0
    scores = [r["rollup_score"] for r in rows]
    assert scores == sorted(scores, reverse=True)


def test_enumeration_trend(store):
    rows = cdd.enumeration_trend(store, geo="TX")
    assert rows
    years = [r["year"] for r in rows]
    assert years == sorted(years)  # oldest-first
    cum = 0
    for r in rows:
        assert r["net_growth"] == r["new_providers"] - r["deactivated"]
        cum += r["net_growth"]
        assert r["cumulative_net"] == cum
        assert r["year"].isdigit() and len(r["year"]) == 4


def test_enumeration_trend_handles_slash_dates(store):
    """Year extraction must tolerate the file's native MM/DD/YYYY too."""
    # inject a provider with an NPPES-style slash date directly
    with store.connect() as con:
        con.execute(
            "INSERT OR REPLACE INTO dim_provider "
            "(npi, entity_type, enumeration_date, status, loaded_at) "
            "VALUES ('1999999999', 1, '03/14/2009', 'active', '2026-01-01')")
        con.execute(
            "INSERT OR REPLACE INTO dim_provider_address "
            "(npi, address_purpose, address_seq, state, geocode_status, loaded_at) "
            "VALUES ('1999999999','practice',0,'ZZ','pending','2026-01-01')")
        con.commit()
    rows = cdd.enumeration_trend(store, geo="ZZ")
    assert any(r["year"] == "2009" for r in rows)


def test_referral_hubs(store):
    rows = cdd.referral_hubs(store, min_providers=3, limit=20)
    assert rows
    counts = [r["providers"] for r in rows]
    assert counts == sorted(counts, reverse=True)
    for r in rows:
        assert r["providers"] >= 3
        # individuals + organizations should account for the provider total
        assert r["individuals"] + r["organizations"] == r["providers"]
        assert r["address"]


def test_roster_integrity(store):
    rep = cdd.roster_integrity(store, geo_level="state")
    assert rep["total_providers"] > 0
    assert 0.0 <= rep["deactivation_rate_pct"] <= 100.0
    assert rep["deactivated"] >= 1   # synth seeds deactivations
    assert isinstance(rep["by_geo"], list)
    for g in rep["by_geo"]:
        assert 0.0 <= g["deactivation_rate_pct"] <= 100.0


def test_affiliation_footprint_ranked(store):
    rows = cdd.affiliation_footprint(store, min_confidence=0.4, limit=10)
    assert rows
    counts = [r["captive_providers"] for r in rows]
    assert counts == sorted(counts, reverse=True)
    for r in rows:
        assert r["captive_providers"] >= 1
        assert r["avg_confidence"] >= 0.4


def test_rollup_targets_are_subscale_orgs(store):
    rows = cdd.rollup_targets(store, max_captive=3, limit=50)
    assert rows  # the realistic universe carries a solo-practice tail
    for r in rows:
        assert r["captive_providers"] <= 3
        assert r["npi"]
    # confirm they are Type-2 orgs
    npis = tuple(r["npi"] for r in rows)
    with store.connect() as con:
        ph = ",".join("?" * len(npis))
        bad = con.execute(
            f"SELECT COUNT(*) c FROM dim_provider "
            f"WHERE npi IN ({ph}) AND entity_type<>2", npis).fetchone()["c"]
    assert bad == 0
