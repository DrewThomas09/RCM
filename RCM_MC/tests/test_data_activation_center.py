"""Data Activation Center hub: registry stays in sync with the DATA REQUIRED
tier, and the page renders every analysis with an actionable activation path."""
import unittest

from rcm_mc.diligence.activation_registry import ACTIVATION_BY_ROUTE, ACTIVATIONS
from rcm_mc.diligence.surface_status import _DATA_REQUIRED, classify_surface
from rcm_mc.ui.data_public.data_activation_page import render_data_activation


class DataActivationCenterTests(unittest.TestCase):
    def test_registry_matches_data_required_tier(self):
        # the hub must cover exactly the DATA REQUIRED surfaces — no drift
        self.assertEqual(set(ACTIVATION_BY_ROUTE), set(_DATA_REQUIRED))

    def test_each_activation_is_complete(self):
        for a in ACTIVATIONS:
            for field in (a.title, a.upload, a.request_from, a.activates, a.template):
                self.assertTrue(field and field.strip(), f"{a.route}: empty field")
            self.assertTrue(a.template.endswith(".csv"), a.route)

    def test_page_renders_all_with_import_path(self):
        h = render_data_activation()
        self.assertIn("Data Activation Center", h)
        # one card + import link per DATA REQUIRED analysis
        self.assertGreaterEqual(h.count("go to import"), len(ACTIVATIONS))
        for a in ACTIVATIONS:
            self.assertIn(a.route, h)

    def test_hub_is_green_real_index(self):
        self.assertEqual(classify_surface("/data-activation")["tier"], "green")


if __name__ == "__main__":
    unittest.main()
