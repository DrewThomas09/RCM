"""CDD market-structure brief generator + market API exposure."""
from __future__ import annotations

import pytest

from connectors.nppes import api, report, synth, pipeline
from connectors.nppes.store import NppesStore


@pytest.fixture(scope="module")
def store(tmp_path_factory):
    d = tmp_path_factory.mktemp("nppes_report")
    m = synth.generate(str(d / "fx"), n_orgs=50, n_individuals=250, seed=17)
    s = NppesStore(str(d / "nppes.db"))
    pipeline.run(s, monthly_path=m["monthly_path"], nucc_path=m["nucc_path"],
                 monthly_version=m["monthly_version"],
                 monthly_header_count=m["monthly_header_count"],
                 othername_path=m["othername_path"],
                 landing_root=str(d / "landing"), write_journal=False)
    return s


def test_brief_data_has_all_sections(store):
    d = report.market_brief_data(store, geo="TX")
    for key in ("scope", "tam", "concentration", "fragmentation",
                "platforms", "rollup_targets", "roster"):
        assert key in d
    assert d["tam"]["total_providers"] >= 0
    # scoped to TX
    for r in d["concentration"]["markets"]:
        assert r["geo"] == "TX"


def test_brief_markdown_renders(store):
    md = report.market_brief_markdown(store, geo="TX",
                                      classification="Internal Medicine")
    assert md.startswith("# Market-Structure Brief — TX · Internal Medicine")
    # the six analyst sections are present
    assert "## 1. Market size (TAM spine)" in md
    assert "## 2. Concentration (HHI)" in md
    assert "## 3. Fragmentation & roll-up runway" in md
    assert "## 4. Incumbent platforms" in md
    assert "## 5. Roll-up candidates" in md
    assert "## 6. Roster integrity" in md
    # markdown tables are well-formed (header + separator)
    assert "|---|" in md or "|---:|" in md


def test_brief_unscoped_aggregates(store):
    md = report.market_brief_markdown(store)
    assert "all states" in md


def test_market_handler_mounts_and_dispatches(store):
    class _Router:
        def __init__(self):
            self.routes = {}
        def add_route(self, path, fn):
            self.routes[path] = fn
    r = _Router()
    assert api.mount_router(r, store) is True
    assert "/v1/lookup/market/{metric}" in r.routes
    handler = r.routes["/v1/lookup/market/{metric}"]
    tam = handler("tam", limit=5)
    assert isinstance(tam, list)
    roster = handler("roster")
    assert "total_providers" in roster
    brief = handler("brief", geo="TX")
    assert "concentration" in brief
    with pytest.raises(Exception):
        handler("nonsense_metric")
