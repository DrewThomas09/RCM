"""P8b — facility→rule exposure join: correct mapping + state scoping."""
from __future__ import annotations

import unittest

from rcm_mc.diligence.regulatory_calendar.exposure import (
    applicable_events, exposure_summary,
)


class JoinTests(unittest.TestCase):
    def test_hospital_matches_hospital_tagged_rules(self):
        ids = {m.event.event_id for m in applicable_events("hospital", "TX")}
        self.assertIn("cms_opps_site_neutral_cy2026", ids)
        self.assertIn("cms_team_cy2026_live", ids)
        # v28 carries a literal HOSPITAL tag in the curated library
        self.assertIn("cms_v28_final_cy2027", ids)

    def test_state_scoped_rule_fires_only_in_its_state(self):
        tx = {m.event.event_id for m in applicable_events("hospital", "TX")}
        ct = {m.event.event_id for m in applicable_events("hospital", "CT")}
        self.assertNotIn("ct_hb_5316_sale_leaseback_phaseout", tx)
        self.assertIn("ct_hb_5316_sale_leaseback_phaseout", ct)
        # the match reason names the scoping
        m = [m for m in applicable_events("hospital", "CT")
             if m.event.event_id == "ct_hb_5316_sale_leaseback_phaseout"][0]
        self.assertIn("CT-scoped", m.reason)

    def test_dialysis_maps_to_esrd_pps(self):
        ids = {m.event.event_id for m in applicable_events("dialysis")}
        self.assertEqual(ids, {"cms_esrd_pps_cy2027"})

    def test_unknown_provider_type_matches_nothing(self):
        self.assertEqual(applicable_events("hcit_vendor"), [])

    def test_sorted_soonest_effective_first(self):
        ms = applicable_events("hospital", "CT")
        eff = [m.event.effective_date for m in ms if m.event.effective_date]
        self.assertEqual(eff, sorted(eff))

    def test_summary_sums_curated_impacts(self):
        ms = applicable_events("hospital", "TX")
        rev, mgn = exposure_summary(ms)
        self.assertAlmostEqual(
            rev, sum(m.event.expected_revenue_impact_pct for m in ms))
        self.assertAlmostEqual(
            mgn, sum(m.event.expected_margin_impact_pp for m in ms))


class XrayPanelTests(unittest.TestCase):
    def test_panel_renders_with_sourced_rules(self):
        from rcm_mc.ui.hcris_xray_page import render_hcris_xray_page
        h = render_hcris_xray_page({"ccn": ["450358"]})   # TX hospital
        self.assertIn("Regulatory exposure", h)
        self.assertIn("rule ↗", h)                  # source links present
        self.assertIn("not an exhaustive regulatory inventory", h)
        self.assertNotIn("Sale-Leaseback", h)       # CT rule must not leak


if __name__ == "__main__":
    unittest.main()
