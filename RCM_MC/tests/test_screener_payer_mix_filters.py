"""Target Screener payer-mix filters (Medicaid ceiling / Medicare floor).

The Hospital Target Screener gained two payer-mix range filters so a partner
can screen on reimbursement risk: a Medicaid-share ceiling (high Medicaid =
reimbursement-rate risk) and a Medicare-share floor (stable-payer cushion).
The existing screener-clarity guard pins the size/margin/revenue range fields
and sort, but not these two, so they could silently drop out of the control
rail. Pin the fields and their active-criteria chips here.

Renderer-level (no server / no HCRIS read needed): exercises render_screen_page
directly, like test_hospital_screener_clarity.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.deal_comparison import render_screen_page


class PayerMixFilterChrome(unittest.TestCase):
    def test_payer_mix_fields_present(self) -> None:
        html = render_screen_page(total_scanned=6123)
        # Both payer-mix controls must be in the filter rail.
        self.assertIn('name="max_medicaid"', html)
        self.assertIn('name="min_medicare"', html)
        # And labelled so intent is explicit (ceiling vs floor).
        self.assertIn("Medicaid % (max)", html)
        self.assertIn("Medicare % (min)", html)

    def test_active_payer_mix_chips(self) -> None:
        html = render_screen_page(
            filters={"max_medicaid": "25", "min_medicare": "30"},
            total_scanned=6123,
        )
        # Active criteria surface as chips with the threshold + direction.
        self.assertIn("Medicaid ≤25%", html)   # Medicaid <= 25%
        self.assertIn("Medicare ≥30%", html)   # Medicare >= 30%

    def test_one_sided_payer_filter_chip(self) -> None:
        # Only the set filter shows a chip; the unset one stays absent.
        html = render_screen_page(
            filters={"max_medicaid": "40"}, total_scanned=6123,
        )
        self.assertIn("Medicaid ≤40%", html)
        self.assertNotIn("Medicare ≥", html)


if __name__ == "__main__":
    unittest.main()
