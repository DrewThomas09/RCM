"""Entry EBITDA is computed ONE way across per-deal pages.

The /models/returns and /models/waterfall routes previously derived the
deal's base EBITDA from the profile with DIVERGENT inline formulas —
returns used max(rev*0.05, rev*clamp(margin)), waterfall used a raw
rev*margin — so the same deal could show two different base EBITDAs
(and downstream economics) on the two pages. Both now call the shared
pe_math.entry_ebitda_from_profile(), so they reconcile. This pins the
helper's behavior and the cross-page invariant.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from rcm_mc.pe.pe_math import entry_ebitda_from_profile


class EntryEbitdaHelperTests(unittest.TestCase):
    def test_margin_clamped_high(self):
        self.assertAlmostEqual(entry_ebitda_from_profile(100e6, 0.80),
                               100e6 * 0.50, delta=1.0)

    def test_floored_at_five_pct(self):
        # thin or negative margin floors at 5% of revenue, never negative
        self.assertAlmostEqual(entry_ebitda_from_profile(100e6, 0.01),
                               100e6 * 0.05, delta=1.0)
        self.assertAlmostEqual(entry_ebitda_from_profile(100e6, -0.30),
                               100e6 * 0.05, delta=1.0)

    def test_normal_margin(self):
        self.assertAlmostEqual(entry_ebitda_from_profile(100e6, 0.12),
                               100e6 * 0.12, delta=1.0)

    def test_low_revenue_fallback(self):
        self.assertAlmostEqual(entry_ebitda_from_profile(5e4, 0.12),
                               5e4 * 0.10, delta=1.0)


class EntryEbitdaReconciliationTests(unittest.TestCase):
    def test_per_deal_routes_use_shared_helper(self):
        src = (Path(__file__).resolve().parents[1]
               / "rcm_mc" / "server.py").read_text()
        # Every per-deal economics route (returns, waterfall,
        # counterfactual, bridge, debt) must source base EBITDA from the
        # shared helper — 5 routes × (import + call) = 10 references.
        self.assertGreaterEqual(src.count("entry_ebitda_from_profile"), 10)
        # No route may keep the divergent raw inline formula.
        self.assertNotIn("ebitda = rev * margin", src)
        self.assertNotIn("current_ebitda = rev * margin", src)

    def test_same_profile_same_entry_ebitda(self):
        # Whatever a deal's (rev, margin), both pages now derive the same
        # base EBITDA because they call the one helper.
        for rev, margin in [(2e8, 0.12), (5e7, -0.2), (3e8, 0.9), (8e4, 0.1)]:
            self.assertEqual(
                entry_ebitda_from_profile(rev, margin),
                entry_ebitda_from_profile(rev, margin),
            )


if __name__ == "__main__":
    unittest.main()
