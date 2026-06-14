"""Health-system (org→org) reconstruction heuristic."""
from __future__ import annotations

import pytest

from connectors.nppes import systems, synth, pipeline
from connectors.nppes.store import NppesStore


@pytest.fixture(scope="module")
def store(tmp_path_factory):
    d = tmp_path_factory.mktemp("nppes_sys")
    m = synth.generate(str(d / "fx"), n_orgs=60, n_individuals=200, seed=23)
    s = NppesStore(str(d / "nppes.db"))
    pipeline.run(s, monthly_path=m["monthly_path"], nucc_path=m["nucc_path"],
                 monthly_version=m["monthly_version"],
                 monthly_header_count=m["monthly_header_count"],
                 othername_path=m["othername_path"],
                 landing_root=str(d / "landing"), write_journal=False)
    return s


def test_systems_cluster_by_brand(store):
    sys = systems.health_systems(store, min_members=2, limit=50)
    assert sys
    for s in sys:
        assert s["member_count"] >= 2
        assert 0.0 <= s["cohesion"] <= 1.0
        assert len(s["member_npis"]) >= 1
        # the anchor token must be a real distinctive token, not a stopword
        assert s["system_name"] not in systems.SYSTEM_STOPWORDS
    # ranked by member count
    counts = [s["member_count"] for s in sys]
    assert counts == sorted(counts, reverse=True)


def test_specialty_words_do_not_anchor_systems(store):
    """Regression: 'MEDICINE'/'CARDIOLOGY' must never form a mega-system."""
    sys = systems.health_systems(store, min_members=2, limit=100)
    names = {s["system_name"] for s in sys}
    assert "MEDICINE" not in names
    assert "CARDIOLOGY" not in names
    # no single cluster should swallow the whole org universe
    if sys:
        with store.connect() as con:
            total_orgs = con.execute(
                "SELECT COUNT(*) c FROM dim_provider "
                "WHERE entity_type=2 AND status='active'").fetchone()["c"]
        assert max(s["member_count"] for s in sys) < total_orgs * 0.5


def test_members_are_active_orgs(store):
    sys = systems.health_systems(store, min_members=2, limit=20)
    npis = [n for s in sys for n in s["member_npis"]]
    with store.connect() as con:
        ph = ",".join("?" * len(npis))
        bad = con.execute(
            f"SELECT COUNT(*) c FROM dim_provider WHERE npi IN ({ph}) "
            f"AND (entity_type<>2 OR status<>'active')", npis).fetchone()["c"]
    assert bad == 0
