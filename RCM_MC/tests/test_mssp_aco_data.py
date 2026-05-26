"""CMS MSSP ACO participants — loader + LIVE section on the CMS APM tracker.

Public CMS snapshot (PII dropped); no runtime network. National participation
directory, not savings/performance.
"""
import inspect
import unittest

from rcm_mc.data import mssp_aco_data as m
from rcm_mc.ui.data_public.cms_apm_tracker_page import render_cms_apm_tracker


class TestMsspLoader(unittest.TestCase):
    def test_loads_and_summary(self):
        s = m.mssp_summary()
        self.assertGreater(s["acos"], 100)
        self.assertGreater(s["enhanced_track_acos"], 0)
        self.assertTrue(s["snapshot_date"])

    def test_no_pii_columns(self):
        df = m.load_mssp_aco()
        cols = set(df.columns)
        for bad in ("email", "phone", "exec", "contact"):
            self.assertFalse(any(bad in c.lower() for c in cols), bad)

    def test_no_runtime_network(self):
        src = inspect.getsource(m)
        self.assertNotIn("urllib", src)
        self.assertNotIn("requests", src)

    def test_track_breakdown_and_top(self):
        self.assertTrue(any(t["track"] == "ENHANCED" for t in m.mssp_track_breakdown()))
        top = m.top_acos_by_participants(5)
        self.assertEqual([t["participants"] for t in top],
                         sorted([t["participants"] for t in top], reverse=True))

    def test_registry(self):
        self.assertTrue(m.mssp_sources())

    def test_acos_for_state(self):
        # real per-state ACO counts parsed from service_area; large states lead
        ca = m.acos_for_state("CA")
        wy = m.acos_for_state("WY")
        self.assertGreater(ca, wy)
        self.assertGreater(ca, 0)
        # sum of distinct-per-state counts >= the 511 distinct ACOs (multi-state)
        self.assertEqual(m.acos_for_state("ZZ"), 0)  # unknown → 0, never fabricated
        self.assertEqual(m.acos_for_state(""), 0)


class TestCmsApmMsspSection(unittest.TestCase):
    def test_live_section_and_caveat(self):
        h = render_cms_apm_tracker({})
        self.assertIn("National MSSP ACO Landscape · LIVE (CMS)", h)
        self.assertIn("not</b> savings/performance", h)
        # both real sections + illustrative overlay coexist, honestly labeled
        self.assertIn("Colorado APM Adoption", h)
        self.assertIn("ILLUSTRATIVE", h)


if __name__ == "__main__":
    unittest.main()
