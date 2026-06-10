"""P11 — Data Quality dashboard: numbers must match independent computation.

The dashboard's claim is that it cannot drift from the product because it
computes from the same loaders at render. These tests hold it to that: the
displayed row counts equal the loaders' own counts, and the gap rows equal
the gap registry's census.
"""
from __future__ import annotations

import re
import unittest


class DataQualityNumbersTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from rcm_mc.ui.data_quality_page import render_data_quality
        cls.html = render_data_quality()

    def test_hcris_row_count_matches_loader(self):
        from rcm_mc.data.hcris import _get_latest_per_ccn
        n = len(_get_latest_per_ccn())
        self.assertIn(f"{n:,}", self.html)

    def test_vertical_count_matches_loader(self):
        from rcm_mc.data.home_health import load_home_health_providers
        n = len(load_home_health_providers())
        self.assertIn(f"{n:,}", self.html)

    def test_gap_census_matches_registry(self):
        from rcm_mc.data.gap_fill_registry import gap_report
        from rcm_mc.diligence.hcris_xray import load_all_metrics
        rep = gap_report(load_all_metrics())
        top = rep[0]  # largest gap (medicaid day share)
        self.assertIn(top["label"], self.html)
        self.assertIn(f'{top["gaps"]:,}', self.html)

    def test_unwired_catalog_present(self):
        self.assertIn("Registered, not yet wired", self.html)
        self.assertIn("source_registry.csv", self.html)

    def test_no_loader_failures_on_healthy_tree(self):
        self.assertNotIn("LOADER FAILED", self.html)
        self.assertNotIn("gap census failed", self.html)


if __name__ == "__main__":
    unittest.main()
