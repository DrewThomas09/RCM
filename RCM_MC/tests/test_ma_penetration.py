"""Tests for the MA penetration intelligence layer (/ma-penetration):
fixture integrity, banding, footprint scoring, and registration."""
from __future__ import annotations

import unittest

from rcm_mc.market_intel.ma_penetration import (
    band_counts, footprint_exposure, get_state, list_state_penetration,
    national_penetration_pct,
)
from rcm_mc.ui.ma_penetration_page import render_ma_penetration


class FixtureTests(unittest.TestCase):
    def test_covers_50_states_plus_dc(self):
        states = list_state_penetration()
        self.assertEqual(len(states), 51)
        self.assertEqual(len({s.state for s in states}), 51)

    def test_sorted_descending(self):
        vals = [s.penetration_pct for s in list_state_penetration()]
        self.assertEqual(vals, sorted(vals, reverse=True))

    def test_national_in_plausible_range(self):
        self.assertTrue(40 <= national_penetration_pct() <= 70)

    def test_bands_match_thresholds(self):
        for s in list_state_penetration():
            if s.penetration_pct >= 55:
                self.assertEqual(s.band, "SATURATED", s.state)
            elif s.penetration_pct >= 45:
                self.assertEqual(s.band, "HIGH", s.state)
            elif s.penetration_pct >= 30:
                self.assertEqual(s.band, "MODERATE", s.state)
            else:
                self.assertEqual(s.band, "LOW", s.state)

    def test_band_counts_sum_to_states(self):
        self.assertEqual(sum(band_counts().values()), 51)

    def test_get_state_case_insensitive(self):
        self.assertIsNotNone(get_state("tx"))
        self.assertIsNone(get_state("ZZ"))


class FootprintTests(unittest.TestCase):
    def test_average_and_delta(self):
        tx = get_state("TX").penetration_pct
        fl = get_state("FL").penetration_pct
        fp = footprint_exposure(["TX", "FL"])
        self.assertAlmostEqual(fp["avg_penetration_pct"],
                               round((tx + fl) / 2, 1))
        self.assertAlmostEqual(
            fp["vs_national_pp"],
            round((tx + fl) / 2 - national_penetration_pct(), 1))

    def test_unknown_codes_dropped(self):
        fp = footprint_exposure(["TX", "ZZ", ""])
        self.assertEqual(len(fp["states"]), 1)

    def test_empty_footprint_safe(self):
        fp = footprint_exposure([])
        self.assertEqual(fp["avg_penetration_pct"], 0.0)


class MaPenetrationPageTests(unittest.TestCase):
    def test_renders_with_identity_and_map(self):
        html = render_ma_penetration({})
        self.assertIn("Medicare Advantage Penetration", html)
        self.assertIn("US state choropleth", html)
        self.assertIn("State exposure table", html)

    def test_footprint_param_scores(self):
        html = render_ma_penetration({"footprint": "TX FL GA"})
        self.assertIn("Footprint read", html)
        self.assertIn("3-state footprint", html)

    def test_malicious_footprint_is_neutralized(self):
        html = render_ma_penetration({"footprint": "<script>x()</script>"})
        self.assertNotIn("<script>x()</script>", html)

    def test_registered_in_palette_and_breadcrumbs(self):
        from rcm_mc.ui._chartis_kit import (
            _DEFAULT_PALETTE_MODULES, _SUB_SECTION_MAP,
        )
        routes = {m["route"] for m in _DEFAULT_PALETTE_MODULES}
        self.assertIn("/ma-penetration", routes)
        self.assertEqual(_SUB_SECTION_MAP.get("/ma-penetration"), "research")


if __name__ == "__main__":
    unittest.main()
