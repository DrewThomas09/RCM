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


class StalenessTierTests(unittest.TestCase):
    """The freshness chip compares snapshot age to the source's own cadence —
    deterministic from (snapshot_date, cadence_days), not a hand-set colour."""

    def setUp(self):
        from datetime import date
        from rcm_mc.ui.data_quality_page import _staleness_tier
        self._tier = _staleness_tier
        self._today = date(2026, 6, 10)

    def test_monthly_two_month_old_reads_aging(self):
        # The backlog's worked example: SNF (monthly cadence, Apr-2026
        # snapshot) shows amber by the Jun-2026 clock.
        color, label, age = self._tier("2026-04-01", 31, False, self._today)
        self.assertEqual(label, "AGING")
        self.assertIn("b8732a", color)        # warning amber
        self.assertEqual(age, 70)

    def test_quarterly_recent_reads_current(self):
        color, label, _ = self._tier("2026-03-01", 92, False, self._today)
        self.assertEqual(label, "CURRENT")
        self.assertIn("0a8a5f", color)        # positive green

    def test_very_old_reads_stale(self):
        color, label, _ = self._tier("2025-01-01", 31, False, self._today)
        self.assertEqual(label, "STALE")
        self.assertIn("b5321e", color)        # negative red

    def test_lag_tolerant_hcris_never_stale(self):
        # HCRIS' ~18-month publication lag is the current normal.
        _, label, age = self._tier(None, 365, True, self._today)
        self.assertEqual(label, "CURRENT NORMAL")
        self.assertIsNone(age)

    def test_missing_date_is_honest_not_green(self):
        _, label, _ = self._tier(None, 92, False, self._today)
        self.assertEqual(label, "DATE UNSTATED")

    def test_dashboard_renders_chips_and_legend(self):
        from rcm_mc.ui.data_quality_page import render_data_quality
        h = render_data_quality()
        # at least the SNF amber chip and HCRIS current-normal chip render
        self.assertIn(">AGING<", h)
        self.assertIn(">CURRENT NORMAL<", h)
        self.assertIn("publication cadence", h)   # legend present


if __name__ == "__main__":
    unittest.main()
