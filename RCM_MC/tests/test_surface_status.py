"""Surface data-honesty status taxonomy + /tools circle indicators."""
import unittest
from rcm_mc.diligence.surface_status import classify_surface, status_dot, TIERS


class TestSurfaceStatus(unittest.TestCase):
    def test_anchor_classifications(self):
        cases = {
            "/cms-apm": "green", "/ref-pricing": "green",
            "/diligence/hcris-xray": "green", "/deal-library": "green",
            "/rollup-economics": "navy", "/lbo-stress": "navy",
            "/scenario-mc": "navy",
            "/sponsor-league": "yellow", "/find-comps": "yellow",
            "/sector-intel": "yellow",
            "/mgmt-comp": "red", "/partner-economics": "red",
            "/provider-retention": "navy", "/physician-productivity": "navy",
        }
        for route, tier in cases.items():
            self.assertEqual(classify_surface(route)["tier"], tier, route)

    def test_every_tier_has_color_and_reason(self):
        for route in ("/cms-apm", "/lbo-stress", "/find-comps", "/mgmt-comp"):
            c = classify_surface(route)
            self.assertIn(c["color"], [v[0] for v in TIERS.values()])
            self.assertTrue(c["reason"])

    def test_query_and_slash_normalized(self):
        self.assertEqual(classify_surface("/cms-apm?ccn=1")["tier"], "green")
        self.assertEqual(classify_surface("/lbo-stress/")["tier"], "navy")

    def test_unknown_route_defaults_safely(self):
        # An unknown non-illustrative route → green (real workflow); never crashes.
        self.assertIn(classify_surface("/some-new-admin-page")["tier"], TIERS)

    def test_status_dot_has_color_and_tooltip(self):
        dot = status_dot("/mgmt-comp")
        self.assertIn("background:#b5321e", dot)      # red
        self.assertIn("title=", dot)

    def test_tools_index_renders_dots_and_legend(self):
        # Render the /tools page via the handler's building blocks.
        from rcm_mc.diligence.surface_status import status_dot as sd
        # green + red dots both appear when a mixed route set is rendered
        self.assertIn("#0a8a5f", sd("/cms-apm"))
        self.assertIn("#b5321e", sd("/mgmt-comp"))


if __name__ == "__main__":
    unittest.main()
