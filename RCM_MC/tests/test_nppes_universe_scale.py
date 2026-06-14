"""Robustness + scale guards for the NPPES slice.

Two concerns:
  • empty/degenerate universe — every analytics surface must return a sane
    empty rather than crash (a fresh store, a store with no affiliations).
  • scale — the pipeline + the heaviest CDD analytics must stay comfortably
    bounded on a larger universe, guarding against an accidental O(n²)
    regression in the window-function / join SQL.
"""
from __future__ import annotations

import time

import pytest

from connectors.nppes import cdd, systems, screen, profile, report, synth, pipeline
from connectors.nppes.store import NppesStore


# ── empty-universe robustness ───────────────────────────────────────
def test_analytics_on_empty_store(tmp_path):
    s = NppesStore(str(tmp_path / "empty.db"))
    s.init_db()
    assert cdd.tam_by_taxonomy_geography(s) == []
    assert cdd.market_concentration(s) == []
    assert cdd.fragmentation_scan(s) == []
    assert cdd.enumeration_trend(s) == []
    assert cdd.referral_hubs(s) == []
    assert cdd.affiliation_footprint(s) == []
    assert cdd.rollup_targets(s) == []
    assert systems.health_systems(s) == []
    assert screen.screen_targets(s) == []
    rep = cdd.roster_integrity(s)
    assert rep["total_providers"] == 0 and rep["deactivation_rate_pct"] == 0.0
    prof = profile.profile_universe(s)
    assert prof["totals"]["providers"] == 0
    # the brief must render even with nothing loaded
    md = report.market_brief_markdown(s)
    assert md.startswith("# Market-Structure Brief")


def test_analytics_with_no_affiliations(tmp_path):
    """A universe with providers but no affiliation bridge still produces
    HHI (all singletons) and an empty platform/system list — no crash."""
    m = synth.generate(str(tmp_path / "fx"), n_orgs=5, n_individuals=40, seed=2)
    s = NppesStore(str(tmp_path / "n.db"))
    pipeline.run(s, monthly_path=m["monthly_path"], nucc_path=m["nucc_path"],
                 monthly_version=m["monthly_version"],
                 monthly_header_count=m["monthly_header_count"],
                 landing_root=str(tmp_path / "l"), write_journal=False)
    with s.connect() as con:
        con.execute("DELETE FROM bridge_provider_affiliation")
        con.commit()
    assert cdd.affiliation_footprint(s) == []
    assert systems.health_systems(s) == [] or all(
        x["captive_providers"] == 0 for x in systems.health_systems(s))
    conc = cdd.market_concentration(s, min_providers=2)
    # with no affiliations every provider is its own firm → low HHI possible
    for r in conc:
        assert 0.0 <= r["hhi"] <= 10000.0


# ── scale guard ─────────────────────────────────────────────────────
@pytest.mark.slow
def test_pipeline_and_analytics_scale(tmp_path):
    """~1.6k-provider universe: full pipeline + the heaviest analytics must
    complete well within a generous budget."""
    m = synth.generate(str(tmp_path / "fx"), n_orgs=300, n_individuals=1200, seed=4)
    s = NppesStore(str(tmp_path / "scale.db"))

    t0 = time.monotonic()
    rep = pipeline.run(
        s, monthly_path=m["monthly_path"], nucc_path=m["nucc_path"],
        monthly_version=m["monthly_version"],
        monthly_header_count=m["monthly_header_count"],
        weekly_paths=m["weekly_paths"], othername_path=m["othername_path"],
        landing_root=str(tmp_path / "l"), write_journal=False)
    pipeline_s = time.monotonic() - t0
    assert rep["dq_all_passed"]

    with s.connect() as con:
        n = con.execute("SELECT COUNT(*) c FROM dim_provider").fetchone()["c"]
    assert n >= 1500

    t1 = time.monotonic()
    cdd.market_concentration(s, min_providers=2, limit=1000)
    cdd.fragmentation_scan(s, min_providers=2, limit=1000)
    systems.health_systems(s, limit=200)
    screen.screen_targets(s, limit=100)
    report.market_brief_data(s)
    analytics_s = time.monotonic() - t1

    # Generous budgets — these guard against O(n^2) blowups, not micro-perf.
    assert pipeline_s < 30.0, f"pipeline took {pipeline_s:.1f}s"
    assert analytics_s < 15.0, f"analytics took {analytics_s:.1f}s"
