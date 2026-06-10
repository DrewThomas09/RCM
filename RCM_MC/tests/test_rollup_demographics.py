"""Blended service-area demographics for a roll-up platform.

Population-weighted Census/ACS across the platform's home counties — the
combined demand backdrop the pro-forma payer mix has to live with. De-dups
counties; carries coverage; empty when nothing geocodes (never fabricated).
"""
from __future__ import annotations

import unittest

from rcm_mc.data.county_demographics import blended_demographics_for_ccns


class BlendTests(unittest.TestCase):
    def test_dedups_counties_and_weights_by_population(self):
        # 3 Harris-county + 1 Dallas-county facility → 2 unique counties.
        b = blended_demographics_for_ccns(["450358", "450068", "450076",
                                           "450021"])
        self.assertEqual(set(b["counties"]),
                         {"Harris County", "Dallas County"})
        self.assertGreaterEqual(b["covered"], 2)
        self.assertEqual(b["n"], 4)
        self.assertTrue(0 < b["pct_age_65_plus"] < 1)
        self.assertGreater(b["median_household_income"], 0)

    def test_empty_when_no_match(self):
        b = blended_demographics_for_ccns(["000000", "999999"])
        self.assertEqual(b["counties"], [])
        self.assertEqual(b["covered"], 0)

    def test_single_county_blend_equals_that_county(self):
        from rcm_mc.data.county_demographics import demographics_for_ccn
        one = demographics_for_ccn("450358")
        b = blended_demographics_for_ccns(["450358"])
        self.assertAlmostEqual(b["pct_age_65_plus"],
                               float(one["pct_age_65_plus"]), places=6)


class PanelTests(unittest.TestCase):
    def test_rollup_renders_blended_panel(self):
        from rcm_mc.ui.rollup_builder_page import render_rollup_builder
        h = render_rollup_builder({"ccns": ["450358,450068"]})
        self.assertIn("Blended service-area demographics", h)
        self.assertIn("Blended 65+", h)
        self.assertIn("population-weighted", h)
        self.assertIn("not the platform's patient", h.replace("&#39;", "'"))


if __name__ == "__main__":
    unittest.main()
