"""b174 — the deal-page EBITDA trend chart didn't fill its panel.

The inline SVG (_render_ebitda_sparkline) was 600px wide with
``max-width: 600px``, so on the full-width deal-detail card (~1200px) it
rendered ~600px and floated centered with large empty margins — looked tiny in
a too-big area. Widened the native canvas (960x220) and changed the cap to
``max-width: 100%`` so it fills the card (verified against real screenshots:
588px -> 1213px in a 1278px card). This guards the fill so it can't regress to
a fixed-width island again.
"""
from __future__ import annotations

import unittest


class TestEbitdaTrendFillsWidth(unittest.TestCase):
    def _svg(self):
        import pandas as pd
        from rcm_mc.server import _render_ebitda_sparkline
        df = pd.DataFrame([
            {"kpi": "ebitda", "quarter": "2025Q1", "actual": 100.0,
             "plan": 110.0, "severity": "lagging"},
            {"kpi": "ebitda", "quarter": "2025Q2", "actual": 95.0,
             "plan": 112.0, "severity": "off_track"},
            {"kpi": "ebitda", "quarter": "2025Q3", "actual": 88.0,
             "plan": 114.0, "severity": "off_track"},
        ])
        return _render_ebitda_sparkline(df)

    def test_chart_fills_container(self):
        svg = self._svg()
        self.assertIn("<svg", svg)
        # Fills the card, not capped at a fixed pixel width.
        self.assertIn("max-width: 100%", svg)
        self.assertNotIn("max-width: 600px", svg)
        # Wide native canvas + proportional scaling (no distortion).
        self.assertIn('viewBox="0 0 960 220"', svg)
        self.assertIn("height: auto", svg)


if __name__ == "__main__":
    unittest.main()
