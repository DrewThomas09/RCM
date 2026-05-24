"""PR 8 — CMS APM Tracker honesty pass.

The /cms-apm page mixes a real, curated public CMS Innovation Center (CMMI)
program catalog with a fabricated portfolio-exposure overlay (the "Project ..."
deals are not this portfolio's live data). These tests lock in the honest
framing: a CMS source header, a curated-reference label on the program data,
and an explicit ILLUSTRATIVE marker on the portfolio/commercial-adjacency
halves.
"""
import unittest

from rcm_mc.ui.data_public.cms_apm_tracker_page import render_cms_apm_tracker


class TestCMSApmHonesty(unittest.TestCase):
    def setUp(self):
        self.html = render_cms_apm_tracker({})

    def test_source_purpose_header_present(self):
        self.assertIn("ck-sp", self.html)
        self.assertIn("CMMI", self.html)

    def test_program_catalog_labeled_curated_reference(self):
        self.assertIn("public reference", self.html.lower())

    def test_portfolio_overlay_marked_illustrative(self):
        # Both the calm marker and the section tag must be present.
        self.assertIn("ck-illus-note", self.html)
        self.assertIn("ILLUSTRATIVE", self.html)

    def test_no_unqualified_portfolio_at_risk_claim_in_title_meta(self):
        # The page title meta must not assert a live "portfolio APM revenue
        # at X% share at risk" — that figure is illustrative, not measured.
        head = self.html.split("Illustrative overlay")[0]
        self.assertNotIn("portfolio APM revenue at", head)

    def test_renders_without_error(self):
        self.assertGreater(len(self.html), 1000)


if __name__ == "__main__":
    unittest.main()
