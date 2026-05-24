"""Home Health + Hospice market-intelligence layer (Phase 2D).

Covers the pure analytics (ownership mix, quality distribution/quartiles,
percentile rank, locality competition) and the rendered surfaces: the
screener state view's market summary + locality competition + locality
filter, and the provider profile's same-locality peers + per-metric state
percentile. CCNs/states are drawn from the live loaders so tests survive a
data re-vendor. No external calls; honest degradation on empty input.
"""
from __future__ import annotations

import unittest

from rcm_mc.data.home_health import load_home_health_providers
from rcm_mc.data.hospice import load_hospice_providers
from rcm_mc.ui import sector_market_intel as smi
from rcm_mc.ui.home_health_page import (
    render_home_health,
    render_home_health_profile,
)
from rcm_mc.ui.hospice_page import render_hospice, render_hospice_profile


def _busy_state(providers, locality_attr):
    """A state with the most providers (so competition/peers are non-trivial)."""
    from collections import Counter
    c = Counter(getattr(p, "state", "") for p in providers.values()
                if getattr(p, "state", ""))
    return c.most_common(1)[0][0]


class MarketIntelAnalyticsTests(unittest.TestCase):
    def test_ownership_mix_folds_unknowns(self):
        class P:
            def __init__(self, o): self.ownership = o
        mix = dict(smi.ownership_mix([P("PROPRIETARY"), P("PROPRIETARY"),
                                      P("-"), P(""), P("NON-PROFIT")]))
        self.assertEqual(mix["PROPRIETARY"], 2)
        self.assertEqual(mix["Not reported"], 2)      # "-" and "" folded
        self.assertEqual(mix["NON-PROFIT"], 1)

    def test_quality_distribution_quartiles(self):
        q = {str(i): {"m": float(i)} for i in range(1, 6)}  # 1..5
        d = smi.quality_distribution(q, list(q), "m")
        self.assertEqual(d["n"], 5)
        self.assertEqual((d["min"], d["median"], d["max"]), (1, 3, 5))
        self.assertIsNone(smi.quality_distribution({}, [], "m"))

    def test_percentile_rank(self):
        vals = [1.0, 2.0, 3.0, 4.0]
        self.assertEqual(smi.percentile_rank(vals, 4.0), 88)   # top
        self.assertEqual(smi.percentile_rank(vals, 1.0), 12)   # bottom
        self.assertIsNone(smi.percentile_rank(vals, None))
        self.assertIsNone(smi.percentile_rank([], 3.0))

    def test_locality_competition_groups_and_sorts(self):
        class P:
            def __init__(self, state, loc, own): self.state, self.loc, self.ownership = state, loc, own
        providers = {
            "a": P("CA", "LA", "PROPRIETARY"), "b": P("CA", "LA", "NON-PROFIT"),
            "c": P("CA", "SF", "PROPRIETARY"), "d": P("NY", "NYC", "PROPRIETARY"),
        }
        quality = {"a": {"h": 4.0}, "b": {"h": 2.0}, "c": {"h": 5.0}}
        rows = smi.locality_competition(providers, quality, "CA", "loc", "h")
        self.assertEqual(rows[0]["locality"], "LA")     # most providers first
        self.assertEqual(rows[0]["count"], 2)
        self.assertEqual(rows[0]["avg"], 3.0)           # (4+2)/2
        self.assertEqual([r["locality"] for r in rows], ["LA", "SF"])  # NY excluded

    def test_filter_by_locality_case_insensitive(self):
        class P:
            def __init__(self, c): self.city = c
        rows = [P("Los Angeles"), P("SF"), P("los angeles")]
        self.assertEqual(len(smi.filter_by_locality(rows, "city", "LOS ANGELES")), 2)
        self.assertEqual(len(smi.filter_by_locality(rows, "city", "")), 3)  # no-op


class HomeHealthMarketViewTests(unittest.TestCase):
    def setUp(self):
        self.providers = load_home_health_providers()
        self.state = _busy_state(self.providers, "city")
        self.html = render_home_health({"state": [self.state]})

    def test_state_market_summary_renders(self):
        self.assertIn("market summary", self.html)
        self.assertIn("distribution", self.html)
        self.assertIn("Ownership mix", self.html)

    def test_city_competition_table_renders(self):
        # HH locality is city (CMS HH file has no county).
        self.assertIn("City competition", self.html)
        self.assertIn("locality=", self.html)        # rows filter the list

    def test_market_caveats_present(self):
        flat = " ".join(self.html.split())
        self.assertIn("cannot tell you", flat)
        self.assertIn("private-pay", flat)
        self.assertIn("not an investment recommendation", flat.lower())
        self.assertIn("city, not county", flat.lower())

    def test_locality_filter_narrows_list(self):
        city = next(p.city for c, p in self.providers.items()
                    if p.state == self.state and p.city)
        filt = render_home_health({"state": [self.state], "locality": [city]})
        self.assertIn("clear", filt.lower())
        self.assertIn(f", {self.state}.", filt)       # scope line shows city, state

    def test_no_external_calls(self):
        low = self.html.lower()
        for bad in ("mapbox", "maps.googleapis", "leaflet", "unpkg"):
            self.assertNotIn(bad, low)


class HospiceMarketViewTests(unittest.TestCase):
    def setUp(self):
        self.providers = load_hospice_providers()
        self.state = _busy_state(self.providers, "county")
        self.html = render_hospice({"state": [self.state]})

    def test_state_market_and_county_competition(self):
        self.assertIn("market summary", self.html)
        self.assertIn("County competition", self.html)   # hospice has county

    def test_caveats_present(self):
        flat = " ".join(self.html.split())
        self.assertIn("cannot tell you", flat)
        self.assertIn("not an investment recommendation", flat.lower())


class ProfileMarketContextTests(unittest.TestCase):
    def test_home_health_profile_peers_and_percentile(self):
        providers = load_home_health_providers()
        ccn = next(c for c, p in providers.items() if p.state and p.city)
        html = render_home_health_profile(ccn)
        self.assertIn("%ile", html)                       # per-metric percentile
        self.assertIn(f"Peers in {providers[ccn].state}", html)
        self.assertIn(f"Peers in {providers[ccn].city}", html)  # same-city peers

    def test_hospice_profile_peers_and_percentile(self):
        providers = load_hospice_providers()
        ccn = next(c for c, p in providers.items() if p.state and p.county)
        html = render_hospice_profile(ccn)
        self.assertIn("%ile", html)
        self.assertIn(f"Peers in {providers[ccn].county}", html)  # same-county


class HonestDegradationTests(unittest.TestCase):
    def test_unknown_state_degrades_without_market_panels(self):
        # A bogus state has no providers — page still renders, no market panels.
        html = render_home_health({"state": ["ZZ"]})
        self.assertIn("ck-page-title", html)
        self.assertNotIn("market summary", html)

    def test_existing_routes_unaffected(self):
        # National screener + provider profiles still render.
        self.assertIn("ck-page-title", render_home_health())
        self.assertIn("ck-page-title", render_hospice())
        providers = load_home_health_providers()
        ccn = next(iter(providers))
        self.assertIsNotNone(render_home_health_profile(ccn))


if __name__ == "__main__":
    unittest.main()
