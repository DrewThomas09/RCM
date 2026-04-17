"""Large-portfolio performance sanity check.

Seeds 200 deals, then asserts two things:
1. The deals table read for the dashboard finishes in <1s.
2. The packet_renderer's LP-update roll-up over a sampled subset
   produces a valid HTML in a reasonable time budget.

Explicitly NOT a proper benchmark — wall-clock assertions are fragile
on slow CI. Budgets are generous (3×) so only truly pathological
regressions trip them.
"""
from __future__ import annotations

import os
import tempfile
import time
import unittest

from rcm_mc.analysis.analysis_store import get_or_build_packet, list_packets
from rcm_mc.exports import PacketRenderer
from rcm_mc.portfolio.store import PortfolioStore


def _seed_many(store: PortfolioStore, n: int) -> None:
    for i in range(n):
        store.upsert_deal(
            f"deal-{i:04d}", name=f"Deal {i:04d}",
            profile={
                "bed_count": 200 + (i % 8) * 50,
                "region": "midwest" if i % 2 == 0 else "south",
                "state": "IL" if i % 3 == 0 else "CA",
                "payer_mix": {"medicare": 0.4, "commercial": 0.45, "medicaid": 0.15},
            },
        )


class TestLargePortfolio(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.store = PortfolioStore(self.path)
        self.store.init_db()
        _seed_many(self.store, 200)

    def tearDown(self):
        try:
            os.unlink(self.path)
        except OSError:
            pass

    def test_list_deals_under_one_second(self):
        t0 = time.time()
        df = self.store.list_deals()
        elapsed = time.time() - t0
        self.assertEqual(len(df), 200)
        # 1s is the headline number in the spec; give CI 3× runway.
        self.assertLess(elapsed, 3.0, f"list_deals took {elapsed:.2f}s")

    def test_build_and_list_packets_scales(self):
        """Seed 20 packets (not 200 — each build is ~150ms so 200 is
        overkill for the scaling claim) and verify list_packets is
        O(n) and cheap."""
        for i in range(20):
            get_or_build_packet(
                self.store, f"deal-{i:04d}", skip_simulation=True,
            )
        t0 = time.time()
        rows = list_packets(self.store)
        elapsed = time.time() - t0
        self.assertGreaterEqual(len(rows), 20)
        self.assertLess(elapsed, 1.0, f"list_packets took {elapsed:.2f}s")

    def test_lp_update_render_scales(self):
        """Render the portfolio LP update from 10 cached packets.
        Keeps the test cheap; the shape of the render function is the
        contract, not the wall-clock on a CI box."""
        packets = []
        for i in range(10):
            packets.append(get_or_build_packet(
                self.store, f"deal-{i:04d}", skip_simulation=True,
            ))
        r = PacketRenderer()
        t0 = time.time()
        html = r.render_lp_update_html(packets)
        elapsed = time.time() - t0
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("10</span>", html)   # deal count
        self.assertLess(elapsed, 2.0, f"LP render took {elapsed:.2f}s")


if __name__ == "__main__":
    unittest.main()
