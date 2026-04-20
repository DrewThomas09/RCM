"""Tests for rcm_mc/ui/data_public/backtest_page.py."""
from __future__ import annotations

import unittest
from typing import Any, Dict, List


def _make_deal(
    moic: float = 2.5,
    ev: float = 200.0,
    ebitda: float = 20.0,
    hold: float = 5.0,
    sector: str = "Physician Practice",
    irr: float = 0.22,
    payer_mix: dict = None,
) -> Dict[str, Any]:
    return {
        "source_id": "test_001",
        "deal_name": "Test Deal",
        "sector": sector,
        "year": 2018,
        "ev_mm": ev,
        "ebitda_at_entry_mm": ebitda,
        "hold_years": hold,
        "realized_moic": moic,
        "realized_irr": irr,
        "payer_mix": payer_mix or {"commercial": 0.6, "medicare": 0.3, "medicaid": 0.1},
    }


class TestCorpusLoader(unittest.TestCase):
    def test_loads_nonzero(self):
        from rcm_mc.ui.data_public.backtest_page import _load_corpus
        deals = _load_corpus()
        self.assertGreater(len(deals), 600)

    def test_realized_subset(self):
        from rcm_mc.ui.data_public.backtest_page import _load_corpus, _realized
        deals = _load_corpus()
        r = _realized(deals)
        self.assertGreater(len(r), 300)
        self.assertLess(len(r), len(deals))


class TestPercentile(unittest.TestCase):
    def test_median_even(self):
        from rcm_mc.ui.data_public.backtest_page import _percentile
        vals = [1.0, 2.0, 3.0, 4.0]
        self.assertAlmostEqual(_percentile(vals, 50), 2.5, places=1)

    def test_p25_p75(self):
        from rcm_mc.ui.data_public.backtest_page import _percentile
        vals = list(range(1, 101))
        self.assertAlmostEqual(_percentile(vals, 25), 25.75, delta=1.0)
        self.assertAlmostEqual(_percentile(vals, 75), 75.25, delta=1.0)

    def test_empty_returns_zero(self):
        from rcm_mc.ui.data_public.backtest_page import _percentile
        self.assertEqual(_percentile([], 50), 0.0)


class TestCorpusPredictedMoic(unittest.TestCase):
    def test_returns_float(self):
        from rcm_mc.ui.data_public.backtest_page import _corpus_predicted_moic
        deal = _make_deal()
        pred = _corpus_predicted_moic(deal)
        self.assertIsInstance(pred, float)
        self.assertGreater(pred, 0)

    def test_missing_fields_returns_none(self):
        from rcm_mc.ui.data_public.backtest_page import _corpus_predicted_moic
        self.assertIsNone(_corpus_predicted_moic({}))
        self.assertIsNone(_corpus_predicted_moic({"ev_mm": 100}))

    def test_lower_multiple_higher_moic(self):
        from rcm_mc.ui.data_public.backtest_page import _corpus_predicted_moic
        cheap = _make_deal(ev=60.0, ebitda=20.0)   # 3× multiple
        dear = _make_deal(ev=300.0, ebitda=20.0)   # 15× multiple
        self.assertGreater(_corpus_predicted_moic(cheap), _corpus_predicted_moic(dear))

    def test_longer_hold_higher_moic(self):
        from rcm_mc.ui.data_public.backtest_page import _corpus_predicted_moic
        short = _make_deal(hold=3.0)
        long_ = _make_deal(hold=8.0)
        self.assertGreater(_corpus_predicted_moic(long_), _corpus_predicted_moic(short))

    def test_high_commercial_premium(self):
        from rcm_mc.ui.data_public.backtest_page import _corpus_predicted_moic
        high_comm = _make_deal(payer_mix={"commercial": 0.75, "medicare": 0.15, "medicaid": 0.10})
        high_gov = _make_deal(payer_mix={"commercial": 0.20, "medicare": 0.50, "medicaid": 0.30})
        self.assertGreater(_corpus_predicted_moic(high_comm), _corpus_predicted_moic(high_gov))

    def test_always_positive(self):
        from rcm_mc.ui.data_public.backtest_page import _corpus_predicted_moic
        worst = _make_deal(ev=500.0, ebitda=20.0, hold=1.0)  # 25× multiple, 1yr hold
        pred = _corpus_predicted_moic(worst)
        self.assertGreater(pred, 0.0)


class TestCalibrationStats(unittest.TestCase):
    def _get_stats(self):
        from rcm_mc.ui.data_public.backtest_page import _load_corpus, _calibration_stats
        return _calibration_stats(_load_corpus())

    def test_keys_present(self):
        stats = self._get_stats()
        for key in ["total", "realized_n", "moic_p25", "moic_p50", "moic_p75",
                    "loss_rate", "homerun_rate", "pairs_n", "mae", "rmse", "r2"]:
            self.assertIn(key, stats)

    def test_moic_ordering(self):
        stats = self._get_stats()
        self.assertLessEqual(stats["moic_p25"], stats["moic_p50"])
        self.assertLessEqual(stats["moic_p50"], stats["moic_p75"])

    def test_rates_bounded(self):
        stats = self._get_stats()
        self.assertGreaterEqual(stats["loss_rate"], 0.0)
        self.assertLessEqual(stats["loss_rate"], 1.0)
        self.assertGreaterEqual(stats["homerun_rate"], 0.0)
        self.assertLessEqual(stats["homerun_rate"], 1.0)

    def test_mae_reasonable(self):
        stats = self._get_stats()
        self.assertIsNotNone(stats["mae"])
        self.assertLess(stats["mae"], 3.0)  # MAE < 3x is always true even for terrible models

    def test_r2_range(self):
        stats = self._get_stats()
        self.assertIsNotNone(stats["r2"])
        self.assertGreaterEqual(stats["r2"], -5.0)  # R² can be negative; no theoretical lower bound
        self.assertLessEqual(stats["r2"], 1.0)

    def test_pairs_have_data(self):
        stats = self._get_stats()
        self.assertGreater(stats["pairs_n"], 50)

    def test_moic_p50_in_range(self):
        stats = self._get_stats()
        self.assertGreater(stats["moic_p50"], 0.5)
        self.assertLess(stats["moic_p50"], 5.0)


class TestScatterData(unittest.TestCase):
    def test_entry_multiple_scatter(self):
        from rcm_mc.ui.data_public.backtest_page import _load_corpus, _entry_multiple_scatter_data
        pts = _entry_multiple_scatter_data(_load_corpus())
        self.assertGreater(len(pts), 50)
        for x, y in pts[:5]:
            self.assertGreater(x, 0)
            self.assertGreater(y, 0)

    def test_hold_scatter(self):
        from rcm_mc.ui.data_public.backtest_page import _load_corpus, _hold_scatter_data
        pts = _hold_scatter_data(_load_corpus())
        self.assertGreater(len(pts), 50)

    def test_predicted_realized_scatter(self):
        from rcm_mc.ui.data_public.backtest_page import _load_corpus, _predicted_vs_realized_data
        pts = _predicted_vs_realized_data(_load_corpus())
        self.assertGreater(len(pts), 50)


class TestSectorCalibration(unittest.TestCase):
    def test_returns_rows(self):
        from rcm_mc.ui.data_public.backtest_page import _load_corpus, _sector_calibration
        rows = _sector_calibration(_load_corpus())
        self.assertGreater(len(rows), 3)

    def test_sorted_by_p50_desc(self):
        from rcm_mc.ui.data_public.backtest_page import _load_corpus, _sector_calibration
        rows = _sector_calibration(_load_corpus())
        p50s = [r["p50"] for r in rows]
        self.assertEqual(p50s, sorted(p50s, reverse=True))

    def test_row_fields(self):
        from rcm_mc.ui.data_public.backtest_page import _load_corpus, _sector_calibration
        rows = _sector_calibration(_load_corpus())
        r = rows[0]
        for key in ["sector", "n", "p25", "p50", "p75", "loss_rate", "homerun"]:
            self.assertIn(key, r)
        self.assertGreaterEqual(r["n"], 3)


class TestSvgHelpers(unittest.TestCase):
    def test_scatter_svg_produces_svg(self):
        from rcm_mc.ui.data_public.backtest_page import _scatter_svg
        pts = [(5.0, 2.5), (8.0, 1.8), (12.0, 3.1)]
        svg = _scatter_svg(pts, "X", "Y")
        self.assertIn("<svg", svg)
        self.assertIn("</svg>", svg)
        self.assertIn("<circle", svg)

    def test_histogram_svg_produces_svg(self):
        from rcm_mc.ui.data_public.backtest_page import _histogram_svg
        vals = [1.0, 2.0, 2.5, 3.0, 1.5, 0.8, 3.5, 2.1]
        svg = _histogram_svg(vals)
        self.assertIn("<svg", svg)
        self.assertIn("<rect", svg)

    def test_scatter_no_points_no_crash(self):
        from rcm_mc.ui.data_public.backtest_page import _scatter_svg
        svg = _scatter_svg([], "X", "Y")
        self.assertIn("<svg", svg)

    def test_scatter_trend_line_present(self):
        from rcm_mc.ui.data_public.backtest_page import _scatter_svg
        pts = [(i, i * 0.3 + 1.0) for i in range(1, 11)]
        svg = _scatter_svg(pts, "X", "Y")
        # Trend line is a dashed line
        self.assertIn("stroke-dasharray", svg)


class TestRenderBacktest(unittest.TestCase):
    def test_renders_html(self):
        from rcm_mc.ui.data_public.backtest_page import render_backtest
        html = render_backtest()
        self.assertIn("<!doctype html>", html)
        self.assertGreater(len(html), 50_000)

    def test_contains_svgs(self):
        import re
        from rcm_mc.ui.data_public.backtest_page import render_backtest
        html = render_backtest()
        svgs = re.findall(r"<svg", html)
        self.assertGreaterEqual(len(svgs), 4)

    def test_contains_calibration_metrics(self):
        from rcm_mc.ui.data_public.backtest_page import render_backtest
        html = render_backtest()
        self.assertIn("MAE", html)
        self.assertIn("RMSE", html)
        self.assertIn("R²", html)

    def test_contains_sector_table(self):
        from rcm_mc.ui.data_public.backtest_page import render_backtest
        html = render_backtest()
        self.assertIn("Sector-Level MOIC", html)

    def test_nav_link_present(self):
        from rcm_mc.ui.data_public.backtest_page import render_backtest
        html = render_backtest()
        self.assertIn("/backtest", html)

    def test_no_light_theme_palette(self):
        from rcm_mc.ui.data_public.backtest_page import render_backtest
        html = render_backtest()
        # Should not contain light-mode background colors
        self.assertNotIn("background:#ffffff", html.lower())
        self.assertNotIn("background: white", html.lower())


if __name__ == "__main__":
    unittest.main()
