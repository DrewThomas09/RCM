"""Portfolio Analytics dossier redesign — filter bar, vintage toggle, and
statistical-honesty guardrails (z-score insufficient sample, HHI labeled as
composition not market share).

The filter bar is server-side: it filters the corpus list before every
analytics function, so the scorecard never desyncs from the visible rows.
All numbers come from the real corpus; honest empty states throughout.
"""
from __future__ import annotations

import os
import tempfile
import unittest

from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.ui.chartis.portfolio_analytics_page import (
    _hhi,
    _outlier_panel,
    _vintage_chart,
    _vintage_chart_toggle,
    render_portfolio_analytics,
)


def _store():
    return PortfolioStore(os.path.join(tempfile.mkdtemp(), "pa.db"))


class HHITests(unittest.TestCase):
    def test_hhi_single_category_is_one(self):
        self.assertEqual(_hhi([10.0]), 1.0)

    def test_hhi_even_split_is_low(self):
        # Four equal categories → HHI 0.25.
        self.assertEqual(_hhi([5, 5, 5, 5]), 0.25)

    def test_hhi_none_on_empty(self):
        self.assertIsNone(_hhi([]))
        self.assertIsNone(_hhi([0]))


class ZScoreGuardrailTests(unittest.TestCase):
    def test_insufficient_sample_under_three_realized(self):
        corpus = [{"realized_moic": 2.0, "deal_name": "A", "year": 2020},
                  {"realized_moic": 1.5, "deal_name": "B", "year": 2021}]
        html = _outlier_panel(corpus)
        self.assertIn("Insufficient peer sample", html)
        self.assertNotIn("Z-score", html)   # no outlier table rendered

    def test_zero_variance_is_insufficient(self):
        corpus = [{"realized_moic": 2.0, "deal_name": str(i), "year": 2020 + i}
                  for i in range(5)]   # ≥3 deals but all identical → sd 0
        html = _outlier_panel(corpus)
        self.assertIn("Insufficient variance", html)


class AnalyticsPageTests(unittest.TestCase):
    def setUp(self):
        self.html = render_portfolio_analytics(store=_store())

    def test_filter_bar_renders(self):
        self.assertIn("pa-filterbar", self.html)
        self.assertIn("Subsector", self.html)
        self.assertIn("Vintage", self.html)
        self.assertIn("pa-seg-btn", self.html)

    def test_vintage_toggle_moic_count_ev(self):
        self.assertIn("pa-vint-toggle", self.html)
        self.assertIn('data-pa-vint="moic"', self.html)
        self.assertIn('data-pa-vint="count"', self.html)
        self.assertIn('data-pa-vint="ev"', self.html)

    def test_hhi_composition_not_market_share(self):
        self.assertIn("HHI", self.html)
        self.assertIn("composition", self.html.lower())
        self.assertIn("not market share", self.html.lower())

    def test_core_sections_present(self):
        for label in ("Corpus scorecard", "Vintage cohort summary",
                      "Deals by type", "concentration", "Outlier"):
            self.assertIn(label, self.html)
        self.assertIn("Sponsor", self.html)

    def test_no_external_cdn(self):
        low = self.html.lower()
        for bad in ("unpkg", "babel", "react-dom", "portfolio-analytics.html",
                    "chart.js", "d3.min"):
            self.assertNotIn(bad, low)


class ServerSideFilterTests(unittest.TestCase):
    def test_subsector_filter_recomputes_and_marks_active(self):
        full = render_portfolio_analytics(store=_store())
        # Pull a real subsector option from the rendered filter bar.
        import re
        m = re.search(r"subsector=([^\"&]+)", full)
        self.assertIsNotNone(m, "no subsector option in filter bar")
        import urllib.parse
        sub = urllib.parse.unquote(m.group(1))
        filtered = render_portfolio_analytics(store=_store(), subsector=sub)
        self.assertIn("Filtered to", filtered)
        self.assertIn("recomputed on this universe", filtered)
        self.assertIn("clear filters", filtered)

    def test_bogus_filter_falls_back_to_full_corpus(self):
        html = render_portfolio_analytics(store=_store(), subsector="ZZZ-NOPE")
        # Invalid filter ignored → no active scope note, full page renders.
        self.assertNotIn("Filtered to", html)
        self.assertIn("Corpus scorecard", html)


class VintageChartMetricTests(unittest.TestCase):
    def test_chart_handles_each_metric_without_crash(self):
        cohorts = [
            {"year": 2019, "median_moic": 2.1, "count": 8, "total_ev_mm": 420,
             "realized_count": 5},
            {"year": 2020, "median_moic": 1.4, "count": 12, "total_ev_mm": 610,
             "realized_count": 7},
        ]
        for metric in ("moic", "count", "ev"):
            svg = _vintage_chart(cohorts, metric)
            self.assertIn("<svg", svg)

    def test_empty_cohorts_degrade(self):
        # The low-level SVG renderer returns "" for no plottable data (the
        # caller owns the empty-state — see test_portfolio_analytics_vintage_chart).
        self.assertEqual(_vintage_chart([], "moic"), "")
        # The MOIC/Count/EV toggle wrapper degrades gracefully with an honest
        # per-metric note so a partner toggling to an empty metric sees why.
        self.assertIn("No vintage data", _vintage_chart_toggle([]))


if __name__ == "__main__":
    unittest.main()
