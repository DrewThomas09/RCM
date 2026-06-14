"""Target-screen synthesizer: ranked acquisition long-list."""
from __future__ import annotations

import pytest

from connectors.nppes import screen, synth, pipeline
from connectors.nppes.store import NppesStore


@pytest.fixture(scope="module")
def store(tmp_path_factory):
    d = tmp_path_factory.mktemp("nppes_screen")
    m = synth.generate(str(d / "fx"), n_orgs=60, n_individuals=250, seed=29)
    s = NppesStore(str(d / "nppes.db"))
    pipeline.run(s, monthly_path=m["monthly_path"], nucc_path=m["nucc_path"],
                 monthly_version=m["monthly_version"],
                 monthly_header_count=m["monthly_header_count"],
                 othername_path=m["othername_path"],
                 landing_root=str(d / "landing"), write_journal=False)
    return s


def test_screen_ranks_and_scores(store):
    rows = screen.screen_targets(store, thesis="platform", limit=20)
    assert rows
    scores = [r["score"] for r in rows]
    assert scores == sorted(scores, reverse=True)
    for r in rows:
        assert 0.0 <= r["score"] <= 100.0
        c = r["components"]
        assert {"market_growth", "fragmentation", "scale_fit"} == set(c)
        for v in c.values():
            assert 0.0 <= v <= 1.0
        assert r["rationale"]


def test_platform_vs_addon_scale_fit_invert(store):
    """A high-captive org scores better as a platform; a sub-scale org scores
    better as an add-on (scale_fit inverts between theses)."""
    plat = {r["npi"]: r for r in screen.screen_targets(store, thesis="platform", limit=1000)}
    addon = {r["npi"]: r for r in screen.screen_targets(store, thesis="addon", limit=1000)}
    # find an org with the largest captive footprint
    big = max(plat.values(), key=lambda r: r["captive_providers"])
    if big["captive_providers"] > 0:
        assert plat[big["npi"]]["components"]["scale_fit"] >= \
            addon[big["npi"]]["components"]["scale_fit"]


def test_screen_candidates_are_active_orgs(store):
    rows = screen.screen_targets(store, limit=30)
    npis = tuple(r["npi"] for r in rows)
    with store.connect() as con:
        ph = ",".join("?" * len(npis))
        bad = con.execute(
            f"SELECT COUNT(*) c FROM dim_provider WHERE npi IN ({ph}) "
            f"AND (entity_type<>2 OR status<>'active')", npis).fetchone()["c"]
    assert bad == 0


def test_scope_filter(store):
    rows = screen.screen_targets(store, geo="TX", limit=50)
    assert all(r["geo"] == "TX" for r in rows)
