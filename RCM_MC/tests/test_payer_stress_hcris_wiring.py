"""PR 4 — Payer Stress wires to the target's real HCRIS payer-day mix.

When a hospital is attached (?ccn=), the base mix is seeded from real HCRIS
day-share (LIVE/DERIVED) with an honest note that HCRIS 'other' = commercial +
self-pay. Without a (valid) CCN it degrades to the illustrative sensitivity
model. No fabricated payer mix.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.data_public.payer_stress_page import render_payer_stress


class PayerStressHcrisTests(unittest.TestCase):
    def test_no_ccn_is_illustrative(self):
        h = render_payer_stress({})
        self.assertIn("ILLUSTRATIVE", h)

    def test_attached_ccn_uses_real_hcris_mix(self):
        h = render_payer_stress({"ccn": "050100"})   # Sharp Memorial (HCRIS fixture)
        self.assertIn("HCRIS PUBLIC DATA", h)         # real source
        self.assertIn("DERIVED", h)
        self.assertIn("CCN 050100", h)                # source names the target
        # honest about the commercial/self-pay limitation
        self.assertIn("commercial + self-pay", h)

    def test_bad_ccn_degrades_honestly(self):
        h = render_payer_stress({"ccn": "ZZZZZZ"})
        self.assertIn("ILLUSTRATIVE", h)              # no fabricated target mix
        self.assertNotIn("HCRIS PUBLIC DATA", h)


if __name__ == "__main__":
    unittest.main()
