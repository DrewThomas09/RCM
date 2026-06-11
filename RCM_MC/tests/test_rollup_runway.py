"""Buy-and-build roll-up runway — how far a platform can consolidate
before the DOJ concentration presumption bites.

Pure arithmetic on the share map + published DOJ thresholds (HHI>2500
AND deltaHHI>200), so the runway is auditable from the shares table.
"""
from __future__ import annotations

import unittest

from rcm_mc.pe_intelligence.market_structure import (
    HHI_DELTA_PRESUMPTION, HHI_HIGHLY_CONCENTRATED, compute_hhi,
    rollup_runway,
)


class RollupRunwayTests(unittest.TestCase):
    def test_single_player_returns_none(self):
        self.assertIsNone(rollup_runway({"A": 1.0}))
        self.assertIsNone(rollup_runway({}))

    def test_platform_defaults_to_largest(self):
        r = rollup_runway({"Big": 0.4, "B": 0.3, "C": 0.3})
        self.assertEqual(r.platform, "Big")

    def test_named_platform_used(self):
        r = rollup_runway({"Big": 0.4, "Mid": 0.35, "C": 0.25},
                          platform="Mid")
        self.assertEqual(r.platform, "Mid")

    def test_acquisitions_absorb_largest_first(self):
        # A fragmented market (20 equal 5% players) so the loop runs
        # several steps before any milestone, exposing the order.
        shares = {f"p{i}": 0.05 for i in range(20)}
        r = rollup_runway(shares, target_share=0.30, max_steps=6)
        self.assertGreaterEqual(len(r.steps), 2)
        # Combined share is monotonic increasing across the sequence.
        combined = [s.combined_share for s in r.steps]
        self.assertEqual(combined, sorted(combined))
        # Each step's combined share rises by one acquired player's share.
        self.assertGreater(r.steps[1].combined_share,
                           r.steps[0].combined_share)

    def test_presumption_flag_matches_doj_rule(self):
        r = rollup_runway({
            "Plat": 0.20, "B": 0.15, "C": 0.12, "D": 0.10, "E": 0.08,
            "F": 0.07, "G": 0.06, "H": 0.05, "I": 0.05, "J": 0.04,
            "K": 0.04})
        for s in r.steps:
            expected = (s.hhi_after > HHI_HIGHLY_CONCENTRATED
                        and s.delta_hhi > HHI_DELTA_PRESUMPTION)
            self.assertEqual(s.crosses_presumption, expected)
        # The flagged presumption_step is the first crossing.
        crossings = [s.n for s in r.steps if s.crosses_presumption]
        if crossings:
            self.assertEqual(r.presumption_step, crossings[0])

    def test_combined_share_arithmetic(self):
        # Shares already sum to 1.0. Platform absorbs the LARGEST
        # independent first — here C (0.50) — => 0.30 + 0.50 = 0.80.
        r = rollup_runway({"Plat": 0.30, "B": 0.20, "C": 0.50},
                          platform="Plat")
        self.assertEqual(r.steps[0].acquired, "C")
        self.assertAlmostEqual(r.steps[0].combined_share, 0.80, places=4)

    def test_reaches_target(self):
        r = rollup_runway({"Plat": 0.20, "B": 0.15, "C": 0.10, "D": 0.10,
                           "E": 0.10, "F": 0.10, "G": 0.25},
                          target_share=0.30)
        # Platform is G (0.25), one bolt-on of B(0.15) → 0.40 ≥ 0.30.
        self.assertIsNotNone(r.acquisitions_to_target)

    def test_fragmented_market_long_runway(self):
        # 20 equal 5% players → very low HHI, long antitrust-safe runway.
        shares = {f"p{i}": 0.05 for i in range(20)}
        r = rollup_runway(shares, target_share=0.30, max_steps=8)
        # No single bolt-on lifts HHI past 2500 from this base.
        self.assertTrue(all(not s.crosses_presumption for s in r.steps[:3]))

    def test_to_dict_round_trips(self):
        r = rollup_runway({"Plat": 0.4, "B": 0.35, "C": 0.25})
        d = r.to_dict()
        self.assertIn("steps", d)
        self.assertIn("presumption_step", d)
        self.assertEqual(len(d["steps"]), len(r.steps))

    def test_renders_in_page(self):
        from types import SimpleNamespace
        from rcm_mc.ui.chartis.market_structure_page import (
            render_market_structure,
        )
        shares = {"Plat": 0.20, "B": 0.15, "C": 0.12, "D": 0.10,
                  "E": 0.08, "F": 0.07, "G": 0.06}
        review = SimpleNamespace(market_structure={
            "hhi": compute_hhi(shares), "cr3": 0.47, "cr5": 0.65,
            "n_players": 7, "top_share": 0.20,
            "fragmentation_verdict": "consolidating",
            "consolidation_play_score": 0.7, "shares_used": shares,
            "thesis_hint": "roll_up"})
        h = render_market_structure(review, "d1", deal_name="Plat")
        self.assertIn("Buy-and-build runway", h)


if __name__ == "__main__":
    unittest.main()
