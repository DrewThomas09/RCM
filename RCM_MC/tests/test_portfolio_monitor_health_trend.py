"""Wave-27: portfolio monitor health-history fix + trend chart.

Two things pinned here. First, a real bug: the monitor queried
``ORDER BY date`` against ``deal_health_history`` whose column is
``at_date`` — the bare except swallowed the OperationalError, so
health scores NEVER rendered on /portfolio/monitor. Second, the new
trend chart drawn from the same (now-working) history.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.portfolio_monitor_page import _health_trend_svg


class HealthQueryRegressionTests(unittest.TestCase):
    def test_health_query_matches_real_schema(self):
        """The exact query the page runs must work on the real DDL."""
        import re
        import sqlite3

        src = open("rcm_mc/ui/portfolio_monitor_page.py").read()
        m = re.search(
            r'"(SELECT deal_id, at_date[^"]*)"\s*\n\s*"([^"]*)"', src)
        self.assertIsNotNone(m, "health query not found in source")
        query = m.group(1) + m.group(2)
        con = sqlite3.connect(":memory:")
        con.execute(
            """CREATE TABLE deal_health_history (
                deal_id TEXT NOT NULL, at_date TEXT NOT NULL,
                score INTEGER NOT NULL, band TEXT NOT NULL,
                PRIMARY KEY (deal_id, at_date))"""
        )
        con.execute("INSERT INTO deal_health_history VALUES "
                    "('d1','2026-06-01',72,'amber')")
        rows = con.execute(query).fetchall()  # must not raise
        self.assertEqual(rows[0][2], 72)


class HealthTrendChartTests(unittest.TestCase):
    def test_renders_lines_with_band_guides(self):
        svg = _health_trend_svg({
            "Riverbend": [("2026-06-01", 62), ("2026-05-01", 70),
                          ("2026-04-01", 78)],
            "Lakeside": [("2026-06-01", 85), ("2026-05-01", 82)],
        })
        self.assertIn("<svg", svg)
        self.assertIn("Health Score Trend", svg)
        self.assertIn("Riverbend 62", svg)   # label carries latest score
        self.assertIn("Lakeside 85", svg)
        self.assertIn("GREEN ≥80", svg)
        self.assertIn("AMBER ≥50", svg)
        self.assertIn("2 DEALS WITH ≥2 SCORES", svg)

    def test_single_score_deals_counted_not_drawn(self):
        svg = _health_trend_svg({
            "Trended": [("2026-06-01", 60), ("2026-05-01", 65)],
            "OneShot": [("2026-06-01", 90)],
        })
        self.assertNotIn("OneShot", svg)
        self.assertIn("1 DEAL WITH A SINGLE SCORE NOT DRAWN", svg)

    def test_empty_renders_nothing(self):
        self.assertEqual(_health_trend_svg({}), "")
        self.assertEqual(
            _health_trend_svg({"Solo": [("2026-06-01", 50)]}), "")


if __name__ == "__main__":
    unittest.main()
