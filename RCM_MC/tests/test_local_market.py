"""Local competitive context — radius scan on the geocode crosswalk.

The state-proxy screens can't answer "who actually competes with this
facility"; this joins the one-time Census-geocoded CMS addresses with HCRIS
filings. Honesty: straight-line distance stated, ungeocoded target → None
(never an approximated location), share denominator = reporting set only.
"""
from __future__ import annotations

import unittest

import pandas as pd

from rcm_mc.data.local_market import (
    LocalMarket, NearbyHospital, haversine_miles, local_market,
)


class HaversineTests(unittest.TestCase):
    def test_known_distance_nyc_la(self):
        d = haversine_miles(40.7128, -74.0060, 34.0522, -118.2437)
        self.assertAlmostEqual(d, 2445, delta=15)   # great-circle ~2,445 mi

    def test_zero_distance(self):
        self.assertEqual(haversine_miles(29.7, -95.4, 29.7, -95.4), 0.0)


class LocalMarketRealDataTests(unittest.TestCase):
    def test_methodist_houston_finds_texas_medical_center(self):
        # Ground truth: Methodist sits IN the Texas Medical Center —
        # Memorial Hermann TMC must appear within a mile.
        lm = local_market("450358", 25.0)
        self.assertIsNotNone(lm)
        self.assertGreater(lm.n_competitors, 10)     # metro Houston
        nearest_ccns = {c.ccn for c in lm.competitors[:5]}
        self.assertIn("450068", nearest_ccns)        # Memorial Hermann TMC
        self.assertLess(lm.competitors[0].distance_mi, 1.0)
        # sorted nearest-first
        dists = [c.distance_mi for c in lm.competitors]
        self.assertEqual(dists, sorted(dists))

    def test_unknown_ccn_returns_none(self):
        self.assertIsNone(local_market("000000", 25.0))


class ShareMathTests(unittest.TestCase):
    def test_share_uses_reporting_set_only(self):
        lm = LocalMarket(target_ccn="x", radius_miles=25, target_npr=100.0)
        lm.competitors = [
            NearbyHospital("a", "A", "C", "TX", 1.0, 100, 300.0),
            NearbyHospital("b", "B", "C", "TX", 2.0, 100, None),   # no NPR
        ]
        self.assertEqual(lm.npr_reported, 1)
        self.assertEqual(lm.combined_competitor_npr, 300.0)
        self.assertAlmostEqual(lm.target_share_of_radius, 0.25)   # 100/400

    def test_no_target_npr_means_no_share(self):
        lm = LocalMarket(target_ccn="x", radius_miles=25, target_npr=None)
        lm.competitors = [NearbyHospital("a", "A", "C", "TX", 1.0, 100, 300.0)]
        self.assertIsNone(lm.target_share_of_radius)


class XrayPanelTests(unittest.TestCase):
    def test_panel_renders_on_xray_with_honesty_notes(self):
        from rcm_mc.ui.hcris_xray_page import render_hcris_xray_page
        h = render_hcris_xray_page({"ccn": ["450358"]})
        self.assertIn("Local competitive context", h)
        self.assertIn("Straight-line distance", h)
        self.assertIn("not a relevant", h)        # antitrust caveat stated
        self.assertIn("MEMORIAL HERMANN", h)


if __name__ == "__main__":
    unittest.main()


class LocalRollupLinkTests(unittest.TestCase):
    def test_xray_offers_local_rollup_with_nearest_three(self):
        # One click from "who's nearby" to the Roll-Up Builder, seeded with
        # target + 3 nearest (which already carries HHI screen/save-to-deal).
        import re
        from rcm_mc.ui.hcris_xray_page import render_hcris_xray_page
        h = render_hcris_xray_page({"ccn": ["450358"]})
        m = re.search(r'rollup\?ccns=([0-9,]+)', h)
        self.assertIsNotNone(m)
        ccns = m.group(1).split(",")
        self.assertEqual(ccns[0], "450358")        # target leads the basket
        self.assertEqual(len(ccns), 4)             # + 3 nearest
        self.assertIn("Model a local roll-up", h)


class RadiusHHITests(unittest.TestCase):
    def test_hhi_two_equal_facilities_is_5000(self):
        lm = LocalMarket(target_ccn="x", radius_miles=25, target_npr=100.0)
        lm.competitors = [NearbyHospital("a", "A", "C", "TX", 1.0, 100, 100.0)]
        # two 50% shares → 50²+50² = 5000
        self.assertAlmostEqual(lm.radius_hhi(), 5000.0, places=0)

    def test_hhi_none_without_target_npr(self):
        lm = LocalMarket(target_ccn="x", radius_miles=25, target_npr=None)
        lm.competitors = [NearbyHospital("a", "A", "C", "TX", 1.0, 100, 100.0)]
        self.assertIsNone(lm.radius_hhi())

    def test_hhi_none_when_alone(self):
        lm = LocalMarket(target_ccn="x", radius_miles=25, target_npr=100.0)
        self.assertIsNone(lm.radius_hhi())   # <2 reporting → no index

    def test_methodist_radius_hhi_unconcentrated(self):
        lm = local_market("450358", 25.0)
        h = lm.radius_hhi()
        self.assertIsNotNone(h)
        self.assertLess(h, 1500)   # dense Houston metro

    def test_panel_shows_radius_hhi_kpi(self):
        from rcm_mc.ui.hcris_xray_page import render_hcris_xray_page
        h = render_hcris_xray_page({"ccn": ["450358"]})
        self.assertIn("RADIUS HHI", h)
        self.assertIn("DOJ/FTC scale", h)
