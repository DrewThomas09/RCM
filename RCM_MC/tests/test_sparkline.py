"""Tests for the dashboard sparkline helper + its wiring into pinned
deal cards.

The sparkline is a tiny inline SVG — no external render, no
framework. Coverage goal: ensure the helper rejects degenerate
input (empty / single-point), normalizes the y-range correctly so
a deal bouncing between 70 and 75 uses the full height instead of
looking flat, and that the pinned-deal card renders one when
history exists + degrades to no-spark when it doesn't.
"""
from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone


class TestSparklineHelper(unittest.TestCase):
    def test_empty_returns_empty(self):
        from rcm_mc.ui.dashboard_page import _sparkline_svg
        self.assertEqual(_sparkline_svg([]), "")

    def test_single_point_returns_empty(self):
        """One data point isn't a trend. Don't render a misleading
        dot-only SVG."""
        from rcm_mc.ui.dashboard_page import _sparkline_svg
        self.assertEqual(_sparkline_svg([75]), "")

    def test_two_points_renders(self):
        from rcm_mc.ui.dashboard_page import _sparkline_svg
        svg = _sparkline_svg([60, 70])
        self.assertIn("<svg", svg)
        self.assertIn("polyline", svg)
        self.assertIn("circle", svg)  # last-point marker

    def test_normalization_uses_observed_range(self):
        """Scores 70 and 75 should span the full chart height, not
        look flat against a 0-100 scale. Verify by checking that
        the two y-coordinates differ meaningfully."""
        from rcm_mc.ui.dashboard_page import _sparkline_svg
        import re
        svg = _sparkline_svg([70, 75], width=80, height=20)
        # Extract points attribute
        m = re.search(r'points="([^"]+)"', svg)
        self.assertIsNotNone(m)
        points = m.group(1).split()
        y_coords = [float(p.split(",")[1]) for p in points]
        # Full usable height is 20 - 2*2 = 16 px; the two points
        # should occupy the extremes (modulo padding).
        y_span = max(y_coords) - min(y_coords)
        self.assertGreater(y_span, 10,
                           msg="two-point chart should use most of "
                               "the vertical range")

    def test_stroke_color_threads_through(self):
        from rcm_mc.ui.dashboard_page import _sparkline_svg
        svg = _sparkline_svg([60, 70], stroke="#ff0000")
        self.assertIn('stroke="#ff0000"', svg)
        self.assertIn('fill="#ff0000"', svg)  # circle marker

    def test_flat_series_does_not_divide_by_zero(self):
        """All-equal scores → hi == lo → span=0 would divide by zero
        without the guard."""
        from rcm_mc.ui.dashboard_page import _sparkline_svg
        svg = _sparkline_svg([72, 72, 72])
        self.assertIn("<svg", svg)
        # Rendered; no ZeroDivisionError — implicit by running

    def test_aria_label_present(self):
        from rcm_mc.ui.dashboard_page import _sparkline_svg
        svg = _sparkline_svg([60, 65, 70, 68])
        self.assertIn("aria-label", svg)
        self.assertIn("4 points", svg)


class TestSparklineInPinnedCards(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "t.db")
        from rcm_mc.portfolio.store import PortfolioStore
        self.store = PortfolioStore(self.db)
        from rcm_mc.deals.watchlist import star_deal
        star_deal(self.store, "DEAL_TREND")

        # Seed 5 days of health history
        from rcm_mc.deals.health_score import _ensure_history_table
        _ensure_history_table(self.store)
        now = datetime.now(timezone.utc)
        with self.store.connect() as con:
            for i, score in enumerate([60, 65, 70, 68, 72]):
                dt = (now - timedelta(days=4 - i)).date().isoformat()
                # band isn't read by history_series (only score),
                # but it's NOT NULL in the schema — match what the
                # prod writer emits.
                band = "good" if score >= 70 else "fair"
                con.execute(
                    "INSERT INTO deal_health_history "
                    "(deal_id, at_date, score, band) VALUES (?, ?, ?, ?)",
                    ("DEAL_TREND", dt, score, band),
                )
            con.commit()

    def tearDown(self):
        self.tmp.cleanup()

    def test_card_includes_sparkline_svg(self):
        """A pinned deal with seeded history should render a
        sparkline next to the score chip."""
        from unittest.mock import patch
        with patch("rcm_mc.deals.health_score.compute_health",
                   return_value={"score": 72, "band": "good",
                                 "components": [{"label": "ok",
                                                 "impact": 0}]}):
            from rcm_mc.ui.dashboard_page import render_dashboard
            html = render_dashboard(self.db)

        self.assertIn("DEAL_TREND", html)
        # SVG present in the pinned-deals section
        section_start = html.find("Pinned deals")
        self.assertGreater(section_start, 0)
        section = html[section_start:section_start + 5000]
        self.assertIn("<svg", section,
                      msg="pinned card should include sparkline SVG")
        self.assertIn("polyline", section)

    def test_missing_history_degrades_to_no_sparkline(self):
        """A deal that's never been scored → empty series → no
        sparkline. The card still renders, just without the chart."""
        from unittest.mock import patch
        # Pin a different deal with no history seeded
        from rcm_mc.deals.watchlist import star_deal
        star_deal(self.store, "DEAL_NO_HISTORY")

        with patch("rcm_mc.deals.health_score.compute_health",
                   return_value={"score": 50, "band": "fair",
                                 "components": []}):
            from rcm_mc.ui.dashboard_page import render_dashboard
            html = render_dashboard(self.db)

        # Both deals render
        self.assertIn("DEAL_TREND", html)
        self.assertIn("DEAL_NO_HISTORY", html)
        # The card for the no-history deal still links out — it just
        # lacks a sparkline. Test doesn't assert SVG count because
        # DEAL_TREND still has one; the point is the page renders
        # cleanly with a mix.


if __name__ == "__main__":
    unittest.main()
