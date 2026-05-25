"""Reference-Based-Pricing page now leads with REAL Colorado CIVHC RBP data.

The provider % of Medicare comes from the vendored CIVHC dataset (LIVE), with
the prior CPT/contract calculator clearly scoped as illustrative below it.
"""
import unittest

from rcm_mc.ui.data_public.ref_pricing_page import render_ref_pricing
from rcm_mc.data import payer_data as pdt


class TestRefPricingRealData(unittest.TestCase):
    def test_live_colorado_section_present(self):
        html = render_ref_pricing({})
        self.assertIn("LIVE (CIVHC)", html)
        self.assertIn("ck-sp", html)                     # source-purpose header
        self.assertIn("% of Medicare", html)
        self.assertIn("Colorado providers", html)

    def test_real_provider_rows_rendered(self):
        html = render_ref_pricing({})
        # a real provider from the dataset must appear
        top = pdt.reference_pricing_summary().iloc[0]["organization_name"]
        self.assertIn(str(top)[:12], html)

    def test_provider_search_filters(self):
        html = render_ref_pricing({"org": "adventhealth"})
        self.assertIn("AdventHealth", html)

    def test_illustrative_model_clearly_scoped(self):
        html = render_ref_pricing({})
        self.assertIn("Illustrative rate-negotiation model", html)
        self.assertIn("ck-illus-note", html)

    def test_no_crash_without_params(self):
        self.assertGreater(len(render_ref_pricing()), 1000)


if __name__ == "__main__":
    unittest.main()
