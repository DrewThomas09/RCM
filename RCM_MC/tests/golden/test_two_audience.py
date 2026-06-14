"""Golden test for BOLSTER-04 two-audience UI layer.

Sweeps every registered CDD feature and asserts:
- the partner render leaks no internal assumption nodes or internal-only series,
- both the partner and internal views render the core chart pack,
- the partner view is branded; the internal view is labeled internal,
- features that carry assumptions expose them only in the internal view.
"""
import unittest

from rcm_mc.cdd import registry
from rcm_mc.cdd.audience import (
    PARTNER_BRAND,
    audit_registry,
    find_leaks,
    render_for_audience,
)


class TestTwoAudience(unittest.TestCase):
    def test_no_partner_leakage_across_registry(self):
        report = audit_registry()
        self.assertTrue(report, "registry must have features to audit")
        for fid, r in report.items():
            self.assertEqual(r["partner_leaks"], [],
                             msg=f"{fid} leaked internal nodes to partner: {r['partner_leaks']}")

    def test_both_views_render_core_pack(self):
        report = audit_registry()
        for fid, r in report.items():
            self.assertTrue(r["partner_core"], msg=f"{fid} partner missing core pack")
            self.assertTrue(r["internal_core"], msg=f"{fid} internal missing core pack")

    def test_partner_branded_internal_labeled(self):
        ex = registry.get("NEW-01").demo()
        partner = render_for_audience(ex, internal_mode=False)
        internal = render_for_audience(ex, internal_mode=True)
        self.assertEqual(partner["view"], "partner")
        self.assertEqual(partner["brand"], PARTNER_BRAND)
        self.assertEqual(internal["view"], "internal")
        self.assertNotIn("brand", internal)

    def test_assumptions_internal_only(self):
        # NEW-01 has assumption nodes: present internal, absent partner.
        ex = registry.get("NEW-01").demo()
        self.assertNotIn("assumptions", render_for_audience(ex, internal_mode=False))
        self.assertIn("assumptions", render_for_audience(ex, internal_mode=True))

    def test_find_leaks_detects_injected_leak(self):
        # A hand-built partner payload with an internal-only series must be caught.
        leaky = {
            "internal_mode": False,
            "series": [{"name": "secret", "internal_only": True, "points": []}],
        }
        self.assertIn("series:secret", find_leaks(leaky))
        # And an assumptions key.
        self.assertIn("key:assumptions", find_leaks({"internal_mode": False, "assumptions": []}))

    def test_internal_view_never_flagged_as_leak(self):
        internal = {"internal_mode": True, "assumptions": [], "series": []}
        self.assertEqual(find_leaks(internal), [])


if __name__ == "__main__":
    unittest.main()
