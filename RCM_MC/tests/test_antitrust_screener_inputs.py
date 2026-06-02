"""Antitrust screener — risk must respond to the inputs.

You flagged that switching deal sizes left the risk unchanged: the score was
built almost entirely from a fixed Texas-anesthesiology scenario, and deal size
only nudged one term above $500M. The score is now input-driven across deal
size, top-market combined share (the dominant concentration signal), acquirer
footprint (serial-acquisition theory), and the primary review state's AG
posture — so the page is actually a useful trigger gauge.
"""
from __future__ import annotations

import unittest

from rcm_mc.data_public.antitrust_screener import compute_antitrust_screener as c
from rcm_mc.ui.data_public.antitrust_screener_page import render_antitrust_screener


class RiskRespondsToInputsTests(unittest.TestCase):
    def test_combined_share_moves_risk(self) -> None:
        lo = c(485, combined_share_pct=20, state="TX").overall_risk_score
        hi = c(485, combined_share_pct=70, state="TX").overall_risk_score
        self.assertGreater(hi, lo + 15, "combined share should dominate risk")

    def test_state_posture_moves_risk(self) -> None:
        tx = c(485, combined_share_pct=50, state="TX").overall_risk_score
        ca = c(485, combined_share_pct=50, state="CA").overall_risk_score
        self.assertGreater(ca, tx, "active-scrutiny state should raise risk")

    def test_deal_size_and_acquirer_move_risk(self) -> None:
        small = c(150, combined_share_pct=40, acquirer_size_mm=300, state="TX").overall_risk_score
        big = c(1500, combined_share_pct=40, acquirer_size_mm=5000, state="TX").overall_risk_score
        self.assertGreater(big, small)

    def test_hsr_threshold_is_real(self) -> None:
        self.assertFalse(c(80).hsr_required)     # below $119.5M
        self.assertTrue(c(485).hsr_required)

    def test_risk_bounded_0_100(self) -> None:
        for ds, sh, st in [(50, 0, "FL"), (5000, 100, "CA")]:
            r = c(ds, combined_share_pct=sh, state=st).overall_risk_score
            self.assertGreaterEqual(r, 0)
            self.assertLessEqual(r, 100)


class PageExposesInputsTests(unittest.TestCase):
    def test_form_has_all_levers(self) -> None:
        html = render_antitrust_screener(
            {"deal_size": "900", "combined_share": "65",
             "state": "CA", "acquirer_size": "3000"})
        for field in ("deal_size", "acquirer_size", "combined_share", "state"):
            self.assertIn(f'name="{field}"', html)
        # the in-table data bar now explains itself
        self.assertIn("longer bar clears a bigger HSR tier", html)


if __name__ == "__main__":
    unittest.main()
