"""Universe profiling / data-room coverage view."""
from __future__ import annotations

import pytest

from connectors.nppes import api, profile, synth, pipeline
from connectors.nppes.store import NppesStore


@pytest.fixture(scope="module")
def store(tmp_path_factory):
    d = tmp_path_factory.mktemp("nppes_profile")
    m = synth.generate(str(d / "fx"), n_orgs=40, n_individuals=160, seed=31)
    s = NppesStore(str(d / "nppes.db"))
    pipeline.run(s, monthly_path=m["monthly_path"], nucc_path=m["nucc_path"],
                 monthly_version=m["monthly_version"],
                 monthly_header_count=m["monthly_header_count"],
                 othername_path=m["othername_path"],
                 endpoint_path=m["endpoint_path"],
                 landing_root=str(d / "landing"), write_journal=False)
    return s


def test_profile_structure(store):
    p = profile.profile_universe(store)
    for key in ("totals", "completeness_pct", "null_rates_pct",
                "top_specialties", "top_states"):
        assert key in p
    t = p["totals"]
    assert t["providers"] == t["type1_individual"] + t["type2_organization"]
    assert t["quarantined_invalid"] >= 2


def test_completeness_bounds(store):
    p = profile.profile_universe(store)
    for k, v in p["completeness_pct"].items():
        assert 0.0 <= v <= 100.0
    # every provider has a primary practice address in the synth universe
    assert p["completeness_pct"]["has_practice_address"] >= 90.0
    # geocode coverage is 0 until the Census geocoder lands (validates stub)
    assert p["completeness_pct"]["addresses_geocoded"] == 0.0


def test_top_specialties_sorted(store):
    p = profile.profile_universe(store)
    counts = [r["c"] for r in p["top_specialties"]]
    assert counts == sorted(counts, reverse=True)


def test_profile_markdown_renders(store):
    md = profile.profile_markdown(store)
    assert md.startswith("# NPPES Universe — Data-Room Profile")
    assert "## Completeness" in md
    assert "## Top specialties" in md


def test_profile_mounted_on_router(store):
    class _Router:
        def __init__(self): self.routes = {}
        def add_route(self, path, fn): self.routes[path] = fn
    r = _Router()
    api.mount_router(r, store)
    assert "/v1/lookup/universe/profile" in r.routes
    out = r.routes["/v1/lookup/universe/profile"]()
    assert "totals" in out
