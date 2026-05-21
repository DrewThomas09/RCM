"""Pin for the median-MOIC-by-deal-type bars on /portfolio-analytics.

The deals-by-type table carries median MOIC alongside count/loss/HR; the
lead bar ranks types by realized median MOIC so the best-performing
archetype reads first. Tone matches the table coloring (>=2.5x positive,
>=1.5x warning, else negative).
"""
from __future__ import annotations

import unittest


class DealTypeMoicBarsTests(unittest.TestCase):
    _BAR = 'ck-bar-row-fill" style="width:'

    def _bars(self, by_type):
        from rcm_mc.ui.chartis.portfolio_analytics_page import _deal_type_moic_bars
        return _deal_type_moic_bars(by_type)

    def test_one_bar_per_type_with_moic(self):
        html = self._bars({
            "Platform": {"median_moic": 2.8, "count": 40},
            "Add-on": {"median_moic": 1.9, "count": 25},
            "Carve-out": {"median_moic": 1.2, "count": 10},
        })
        self.assertEqual(html.count(self._BAR), 3)

    def test_sorted_best_first_full_width(self):
        html = self._bars({
            "Low": {"median_moic": 1.5}, "High": {"median_moic": 3.0},
        })
        # Best (High, 3.0x) renders at full width.
        self.assertIn("width:100.0%", html)

    def test_tone_tiers(self):
        html = self._bars({
            "A": {"median_moic": 2.8},  # positive
            "B": {"median_moic": 1.8},  # warning
            "C": {"median_moic": 1.1},  # negative
        })
        self.assertIn("%;background:var(--sc-positive)", html)
        self.assertIn("%;background:var(--sc-warning)", html)
        self.assertIn("%;background:var(--sc-negative)", html)

    def test_skips_types_without_moic(self):
        html = self._bars({
            "A": {"median_moic": 2.0}, "B": {"median_moic": None},
            "C": {"median_moic": 1.5},
        })
        self.assertEqual(html.count(self._BAR), 2)

    def test_empty_below_two(self):
        self.assertEqual(self._bars({"Solo": {"median_moic": 2.0}}), "")


if __name__ == "__main__":
    unittest.main()
