"""The screener's Min-MOIC return floor must actually gate the decision.

deal_screening_engine.ScreeningConfig exposed `min_moic_threshold` and the
module docstring promised "MOIC below threshold -> FAIL", but the check was
never wired — so the /deal-screening "Min MOIC" control changed the URL but
not the PASS/WATCH/FAIL mix (a looks-functional-does-nothing filter). These
guard that a realized MOIC below the floor now fails, one above it clears,
and an unrealized deal (no realized MOIC) is left ungated.
"""

import unittest

from rcm_mc.data_public.deal_screening_engine import ScreeningConfig, screen_deal

_BASE = {
    "source_id": "x", "deal_name": "Test", "ev_mm": 300.0, "ebitda_mm": 30.0,
    "ev_ebitda": 10.0, "year": 2018,
    "payer_mix": {"medicare": 0.40, "medicaid": 0.20, "commercial": 0.36, "self_pay": 0.04},
}


def _deal(**kw):
    return {**_BASE, **kw}


class TestScreeningMoicFloor(unittest.TestCase):
    def test_below_floor_fails_with_reason(self):
        r = screen_deal(_deal(realized_moic=1.2), ScreeningConfig(min_moic_threshold=1.5))
        self.assertEqual(r.decision, "FAIL")
        self.assertTrue(any("MOIC" in x for x in r.fail_reasons))

    def test_above_floor_no_moic_fail(self):
        r = screen_deal(_deal(realized_moic=2.5), ScreeningConfig(min_moic_threshold=1.5))
        self.assertFalse(any("MOIC" in x and "below" in x for x in r.fail_reasons))

    def test_raising_floor_changes_outcome(self):
        """The control must bite: a 2.0x deal clears a 1.5x floor but fails a
        3.0x floor."""
        d = _deal(realized_moic=2.0)
        self.assertNotIn("FAIL", (screen_deal(d, ScreeningConfig(min_moic_threshold=1.5)).decision,))
        r_high = screen_deal(d, ScreeningConfig(min_moic_threshold=3.0))
        self.assertEqual(r_high.decision, "FAIL")
        self.assertTrue(any("MOIC" in x for x in r_high.fail_reasons))

    def test_unrealized_deal_is_not_gated_on_moic(self):
        r = screen_deal(_deal(realized_moic=None), ScreeningConfig(min_moic_threshold=3.0))
        self.assertFalse(any("MOIC" in x for x in r.fail_reasons))


if __name__ == "__main__":
    unittest.main()
