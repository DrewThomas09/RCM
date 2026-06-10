"""P4 — peer-percentile chip: rank math + honesty guards + quick-view wiring."""
from __future__ import annotations

import re
import unittest

import pandas as pd

from rcm_mc.ui._chartis_kit import ck_peer_percentile


def _p(html: str) -> int:
    m = re.search(r">p(\d+)<", html)
    assert m, html[:200]
    return int(m.group(1))


class RankMathTests(unittest.TestCase):
    def test_standard_percentile_rank(self):
        # value 75 among 0..100 step 10: 8 below, 0 ties, n=11 → 72.7 → p73
        self.assertEqual(_p(ck_peer_percentile(
            75, [10 * i for i in range(11)], peer_label="x")), 73)

    def test_ties_take_half_credit(self):
        # value 5 among [1,5,5,9,9,9,2,3,4,5]: below=4, ties=3, n=10
        # → (4 + 1.5)/10 = 55%
        self.assertEqual(_p(ck_peer_percentile(
            5, [1, 5, 5, 9, 9, 9, 2, 3, 4, 5], peer_label="x")), 55)

    def test_extremes(self):
        dist = list(range(20))
        self.assertEqual(_p(ck_peer_percentile(-1, dist, peer_label="x")), 0)
        self.assertEqual(_p(ck_peer_percentile(99, dist, peer_label="x")), 100)

    def test_nan_peers_excluded_from_n(self):
        h = ck_peer_percentile(5, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
                                   float("nan")], peer_label="x")
        self.assertIn("(n=10)", h)


class HonestyGuardTests(unittest.TestCase):
    def test_small_peer_set_refuses_percentile(self):
        h = ck_peer_percentile(5, [1, 2, 3, 4], peer_label="x")
        self.assertIn("peer set too small (n=4)", h)
        self.assertIsNone(re.search(r">p\d+<", h))

    def test_missing_value_renders_nothing(self):
        self.assertEqual(ck_peer_percentile(None, [1] * 20, peer_label="x"), "")
        self.assertEqual(
            ck_peer_percentile(float("nan"), [1] * 20, peer_label="x"), "")

    def test_tooltip_states_method(self):
        h = ck_peer_percentile(5, list(range(20)), peer_label="TX hospitals")
        self.assertIn("share of peers below + half of ties", h)
        self.assertIn("TX hospitals", h)


class QuickViewWiringTests(unittest.TestCase):
    def _peers(self, n=10):
        return pd.DataFrame([
            {"deal_id": f"d{i}", "denial_rate": 6 + i, "days_in_ar": 38 + 2 * i,
             "net_collection_rate": 97 - i, "clean_claim_rate": 95 - i,
             "cost_to_collect": 2.5 + 0.3 * i} for i in range(n)])

    _PROF = {"name": "Atlas", "denial_rate": 11.5, "days_in_ar": 48.0,
             "net_collection_rate": 94.5, "clean_claim_rate": 86.0,
             "cost_to_collect": 3.4, "net_revenue": 2.4e8}

    def test_chips_render_vs_book(self):
        from rcm_mc.ui.deal_quick_view import render_deal_quick_view
        h = render_deal_quick_view("atlas", self._PROF, peer_deals=self._peers())
        self.assertGreaterEqual(len(re.findall(r">p\d+<", h)), 4)
        self.assertIn("portfolio deals", h)

    def test_small_book_gets_honest_guard(self):
        from rcm_mc.ui.deal_quick_view import render_deal_quick_view
        h = render_deal_quick_view("atlas", self._PROF,
                                   peer_deals=self._peers(5))
        self.assertIn("peer set too small (n=5)", h)

    def test_no_peer_frame_no_chip_no_crash(self):
        from rcm_mc.ui.deal_quick_view import render_deal_quick_view
        h = render_deal_quick_view("atlas", self._PROF)
        self.assertNotIn("ck-pct-chip", h)


if __name__ == "__main__":
    unittest.main()
