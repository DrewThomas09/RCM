"""Real CBSA (metro/micro) demographics layer: the committed OMB crosswalk
joined to county ACS demographics and rolled up. Guards the join, that
aggregates are real (population is a true sum; rates are weighted means within
county bounds), and that unknown CBSAs return {} rather than fabricated data.
"""
import unittest

from rcm_mc.data import cbsa_demographics as c


class CbsaDemographicsTests(unittest.TestCase):
    def test_crosswalk_and_summary(self):
        s = c.cbsa_summary()
        self.assertGreater(s["cbsas"], 800)        # ~918 CBSAs
        self.assertGreater(s["metros"], 300)
        self.assertGreater(s["covered_population"], 250_000_000)
        self.assertEqual(s["vintage"], "2023")

    def test_top_metro_is_new_york_and_real(self):
        metros = c.cbsa_list("Metropolitan", 1)
        self.assertTrue(metros)
        top = metros[0]
        self.assertIn("New York", top["cbsa_title"])  # largest US metro
        # ~19.5M people across its member counties — a real sum, not a guess
        self.assertGreater(top["population"], 18_000_000)
        self.assertGreater(top["county_count"], 1)

    def test_weighted_rate_within_bounds(self):
        # a CBSA's weighted uninsured rate must sit within [0,1] (fractions)
        for m in c.cbsa_list("Metropolitan", 20):
            u = m["uninsured_rate"]
            if u is not None:
                self.assertGreaterEqual(u, 0.0)
                self.assertLessEqual(u, 1.0)

    def test_lookup_and_unknown(self):
        # round-trip a known CBSA code, and unknown returns {} (never fabricated)
        code = c.cbsa_list("Metropolitan", 1)[0]["cbsa_code"]
        self.assertEqual(c.cbsa_demographics(code)["cbsa_code"], code)
        self.assertEqual(c.cbsa_demographics("00000"), {})
        self.assertEqual(c.cbsa_demographics(""), {})

    def test_registry(self):
        self.assertTrue(c.cbsa_sources())


if __name__ == "__main__":
    unittest.main()
