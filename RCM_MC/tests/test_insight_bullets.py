"""P13 — honest insight bullets: guards suppress trivia, figures trace."""
from __future__ import annotations

import unittest

import pandas as pd

from rcm_mc.ui._chartis_kit import ck_insight_bullets


class PrimitiveTests(unittest.TestCase):
    def test_renders_significant_only(self):
        h = ck_insight_bullets([("big move", True), ("trivia", False)])
        self.assertIn("big move", h)
        self.assertNotIn("trivia", h)

    def test_silence_when_nothing_significant(self):
        self.assertEqual(ck_insight_bullets([("trivia", False)]), "")
        self.assertEqual(ck_insight_bullets([]), "")

    def test_caps_at_four(self):
        h = ck_insight_bullets([(f"b{i}", True) for i in range(7)])
        self.assertEqual(h.count("<li"), 4)

    def test_copy_payload_is_tag_stripped(self):
        h = ck_insight_bullets([("a <strong>5.0pp</strong> gap", True)])
        self.assertIn('data-t="a 5.0pp gap"', h)
        self.assertIn("computed from the figures on this page", h)


class PortfolioBulletsTests(unittest.TestCase):
    def _render(self, rows):
        from rcm_mc.ui.portfolio_overview import render_portfolio_overview
        return render_portfolio_overview(pd.DataFrame(rows), None)

    def test_spread_bullet_fires_and_matches_stats(self):
        rows = [
            {"deal_id": "a", "name": "Alpha", "created_at": "2026-01-01",
             "denial_rate": 6.0, "days_in_ar": 40.0, "net_collection_rate": 96.0},
            {"deal_id": "b", "name": "Bravo", "created_at": "2026-01-01",
             "denial_rate": 14.0, "days_in_ar": 42.0, "net_collection_rate": 95.8},
        ]
        h = self._render(rows)
        self.assertIn("8.0pp", h)           # 14 − 6, the page's own numbers
        self.assertIn("Bravo", h)
        self.assertIn("Alpha", h)

    def test_tiny_spread_suppressed(self):
        rows = [
            {"deal_id": "a", "name": "Alpha", "created_at": "2026-01-01",
             "denial_rate": 8.0, "days_in_ar": 40.0},
            {"deal_id": "b", "name": "Bravo", "created_at": "2026-01-01",
             "denial_rate": 9.0, "days_in_ar": 41.0},
        ]
        h = self._render(rows)
        self.assertNotIn("Denial-rate spread", h)   # 1.0pp < 2.0 guard

    def test_ncr_guard_half_point(self):
        rows = [
            {"deal_id": "a", "name": "A", "created_at": "2026-01-01",
             "denial_rate": 6.0, "net_collection_rate": 94.8},
            {"deal_id": "b", "name": "B", "created_at": "2026-01-01",
             "denial_rate": 13.0, "net_collection_rate": 94.9},
        ]
        h = self._render(rows)
        # avg 94.85 → 0.15pp from the 95% floor → suppressed
        self.assertNotIn("underwriting floor", h)


if __name__ == "__main__":
    unittest.main()
