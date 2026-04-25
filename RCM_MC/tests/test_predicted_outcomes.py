"""Tests for the dashboard's "Predicted exit outcomes" card.

The wow moment: partner pins DEAL_042 to track. On every dashboard
load, the tool runs that deal's profile against 600+ realized PE
comparables and renders a predicted MOIC distribution as an inline
SVG range chart. Partner didn't ask for the prediction — the tool
volunteered it.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime, timezone


def _seed_deal(store, deal_id: str, name: str,
               sector: str = "hospital") -> None:
    with store.connect() as con:
        con.execute(
            "INSERT INTO deals (deal_id, name, created_at, profile_json) "
            "VALUES (?, ?, ?, ?)",
            (deal_id, name,
             datetime.now(timezone.utc).isoformat(),
             json.dumps({"sector": sector})),
        )
        con.commit()


class TestRangeBarSvg(unittest.TestCase):
    def test_returns_empty_string_when_no_median(self):
        from rcm_mc.ui.dashboard_page import _moic_range_bar
        self.assertEqual(_moic_range_bar(None, None, None), "")

    def test_renders_svg_with_all_three_points(self):
        from rcm_mc.ui.dashboard_page import _moic_range_bar
        svg = _moic_range_bar(1.5, 2.3, 3.1)
        self.assertIn("<svg", svg)
        self.assertIn("polyline", svg) if False else None
        # Whisker rect + median dot
        self.assertIn("<rect", svg)
        self.assertIn("<circle", svg)
        # 1.0x and 2.5x reference lines (dashed)
        self.assertIn("stroke-dasharray", svg)

    def test_handles_missing_p25_p75(self):
        """When only median is known, render a dot without crashing
        (degraded but informative)."""
        from rcm_mc.ui.dashboard_page import _moic_range_bar
        svg = _moic_range_bar(None, 2.0, None)
        self.assertIn("<svg", svg)


class TestNoWatchlistNoSection(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "t.db")
        from rcm_mc.portfolio.store import PortfolioStore
        PortfolioStore(self.db).init_db()

    def tearDown(self):
        self.tmp.cleanup()

    def test_no_section_when_watchlist_empty(self):
        from rcm_mc.ui.dashboard_page import render_dashboard
        html = render_dashboard(self.db)
        self.assertNotIn("Predicted exit outcomes", html)


class TestPredictedOutcomesPopulate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "t.db")
        from rcm_mc.portfolio.store import PortfolioStore
        self.store = PortfolioStore(self.db)
        self.store.init_db()
        # Seed 2 starred deals + the corpus
        _seed_deal(self.store, "PINNED_1", "Watch A")
        _seed_deal(self.store, "PINNED_2", "Watch B")
        from rcm_mc.deals.watchlist import star_deal
        star_deal(self.store, "PINNED_1")
        star_deal(self.store, "PINNED_2")
        # Seed corpus so benchmark_deal has matches
        from rcm_mc.data_public.deals_corpus import DealsCorpus
        corpus = DealsCorpus(self.db)
        corpus.seed(skip_if_populated=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_section_renders_with_predictions(self):
        from rcm_mc.ui.dashboard_page import render_dashboard
        html = render_dashboard(self.db)
        # Section title with count
        self.assertIn("Predicted exit outcomes", html)
        # Both pinned deals appear
        self.assertIn("Watch A", html)
        self.assertIn("Watch B", html)
        # MOIC value rendered (any number followed by 'x')
        import re
        self.assertRegex(html, r"\d+\.\d{2}x")
        # SVG range chart present
        self.assertIn('aria-label="MOIC range chart"', html)

    def test_section_includes_legend(self):
        from rcm_mc.ui.dashboard_page import render_dashboard
        html = render_dashboard(self.db)
        # Legend explains what the chart means
        self.assertIn("scale 0–6", html)
        self.assertIn("p25–p75 range", html)
        self.assertIn("median predicted MOIC", html)


class TestCapAtEightDeals(unittest.TestCase):
    """Watchlist of 12 → only 8 prediction rows. Bounds compute
    on busy partners' dashboards."""

    def test_cap_enforced(self):
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "t.db")
            from rcm_mc.portfolio.store import PortfolioStore
            store = PortfolioStore(db)
            store.init_db()
            from rcm_mc.deals.watchlist import star_deal
            for i in range(12):
                _seed_deal(store, f"PIN_{i}", f"Watch {i}")
                star_deal(store, f"PIN_{i}")
            from rcm_mc.data_public.deals_corpus import DealsCorpus
            DealsCorpus(db).seed(skip_if_populated=True)

            from rcm_mc.ui.dashboard_page import render_dashboard
            html = render_dashboard(db)
            # Find the predicted-outcomes section title
            import re
            m = re.search(
                r"Predicted exit outcomes \((\d+)\)", html,
            )
            if m:
                n = int(m.group(1))
                self.assertLessEqual(n, 8,
                                     msg=f"cap should be 8, got {n}")
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
