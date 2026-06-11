"""Wave-26 visual: escalations aging chart.

The escalations list printed "Nd open" per row; nothing drew the
relative staleness or separated live from acknowledged alerts
visually. Pins the aging SVG: oldest-first bars, live vs acked
tones, the 20-row cap, and the empty states.
"""
from __future__ import annotations

import unittest

import pandas as pd

from rcm_mc.ui.escalations_page import _aging_svg


def _df(rows):
    return pd.DataFrame(rows)


class EscalationsAgingChartTests(unittest.TestCase):
    def test_renders_bars_with_live_and_acked_tones(self):
        svg = _aging_svg(_df([
            {"deal_id": "d1", "title": "Covenant trip", "days_open": 90,
             "acked": False},
            {"deal_id": "d2", "title": "Stale snapshot", "days_open": 45,
             "acked": True},
        ]), min_days=30)
        self.assertIn("<svg", svg)
        self.assertIn("ck-escalation-aging", svg)
        self.assertIn("#b5321e", svg)        # live brick
        self.assertIn("#9b9382", svg)        # acked gray
        self.assertIn("90d", svg)
        self.assertIn("45d ACKED", svg)
        self.assertIn("30-DAY THRESHOLD", svg)

    def test_oldest_first(self):
        svg = _aging_svg(_df([
            {"deal_id": "young", "title": "t", "days_open": 31,
             "acked": False},
            {"deal_id": "ancient", "title": "t", "days_open": 200,
             "acked": False},
        ]), min_days=30)
        self.assertLess(svg.index("ancient"), svg.index("young"))

    def test_capped_at_twenty_rows(self):
        rows = [{"deal_id": f"d{i}", "title": "t", "days_open": 30 + i,
                 "acked": False} for i in range(30)]
        svg = _aging_svg(_df(rows), min_days=30)
        self.assertEqual(svg.count("<rect"), 20)
        self.assertIn("20 OLDEST SHOWN", svg)

    def test_empty_renders_nothing(self):
        self.assertEqual(_aging_svg(None, 30), "")
        self.assertEqual(_aging_svg(pd.DataFrame(), 30), "")


if __name__ == "__main__":
    unittest.main()
