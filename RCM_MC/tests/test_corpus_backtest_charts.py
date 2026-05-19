"""Pin for the vintage-MOIC bar chart + sector median horizontal
bars on /corpus-backtest. Replaces 2 bland tables with a visual
shape view above each."""
from __future__ import annotations

import unittest


class VintageChartTests(unittest.TestCase):
    def test_renders_bars_per_year(self):
        from rcm_mc.ui.chartis.corpus_backtest_page import (
            _vintage_moic_chart,
        )
        by_year = {
            2018: [1.5, 2.2, 2.8],
            2019: [2.0, 2.5, 3.1, 2.4],
            2020: [1.1, 1.4, 1.6],
        }
        svg = _vintage_moic_chart(by_year)
        self.assertTrue(svg.startswith("<svg"))
        self.assertEqual(svg.count("<rect"), 3)
        # Year labels
        self.assertIn("2018", svg)
        self.assertIn("2019", svg)
        # Axis label
        self.assertIn("Median realized MOIC", svg)

    def test_returns_empty_for_no_data(self):
        from rcm_mc.ui.chartis.corpus_backtest_page import (
            _vintage_moic_chart,
        )
        self.assertEqual(_vintage_moic_chart({}), "")

    def test_band_colors_per_year(self):
        from rcm_mc.ui.chartis.corpus_backtest_page import (
            _vintage_moic_chart,
        )
        svg = _vintage_moic_chart({
            2018: [3.0, 3.5, 2.8],  # green band
            2019: [2.0, 1.9, 2.0],  # amber band
            2020: [1.0, 1.2, 0.8],  # red band
        })
        self.assertIn("#0a8a5f", svg)
        self.assertIn("#b8732a", svg)
        self.assertIn("#b5321e", svg)


class SectorBarsTests(unittest.TestCase):
    def test_renders_bar_per_sector_with_enough_data(self):
        from rcm_mc.ui.chartis.corpus_backtest_page import (
            _sector_median_bars,
        )
        secs = [
            ("Hospital", [2.5, 2.8, 2.4, 2.6]),
            ("Dental",   [1.4, 1.6, 1.7]),
            ("Vet",      [3.0, 3.5, 2.8]),
        ]
        svg = _sector_median_bars(secs)
        self.assertEqual(svg.count("<rect"), 3)
        self.assertIn("Hospital", svg)
        self.assertIn("Dental", svg)
        self.assertIn("Vet", svg)

    def test_skips_thin_cohorts(self):
        # < 3 deals → skipped (same threshold as the table)
        from rcm_mc.ui.chartis.corpus_backtest_page import (
            _sector_median_bars,
        )
        svg = _sector_median_bars([
            ("Big",    [2.0, 2.2, 2.4]),  # plot
            ("Small",  [2.5, 3.0]),       # skip (n=2)
            ("Tiny",   [1.5]),            # skip (n=1)
        ])
        self.assertEqual(svg.count("<rect"), 1)
        self.assertIn("Big", svg)
        self.assertNotIn(">Small<", svg)

    def test_returns_empty_for_no_data(self):
        from rcm_mc.ui.chartis.corpus_backtest_page import (
            _sector_median_bars,
        )
        self.assertEqual(_sector_median_bars([]), "")


if __name__ == "__main__":
    unittest.main()
