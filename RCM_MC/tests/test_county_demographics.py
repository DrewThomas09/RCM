"""County demographics (Census/ACS via CHR) loader — committed data + shape."""
import unittest

from rcm_mc.data import county_demographics as c


class CountyDemographicsTests(unittest.TestCase):
    def test_summary_present_and_plausible(self):
        s = c.demographics_summary()
        self.assertTrue(s, "summary missing — run scripts/ingest_county_demographics.py")
        self.assertGreaterEqual(s["counties"], 3000)
        self.assertGreaterEqual(s["states"], 50)
        nat = s["national"]
        self.assertGreater(nat["population"], 300_000_000)         # US pop ~333M
        self.assertTrue(0.10 < nat["pct_age_65_plus"] < 0.25, nat["pct_age_65_plus"])
        self.assertTrue(0.04 < nat["uninsured_rate"] < 0.20, nat["uninsured_rate"])

    def test_state_lookup_fractions(self):
        ca = c.demographics_state("CA")
        self.assertEqual(ca["state"], "CA")
        self.assertGreater(ca["population"], 30_000_000)
        # rates are fractions, not 0–100 percents
        self.assertTrue(0 < ca["uninsured_rate"] < 1, ca["uninsured_rate"])
        self.assertEqual(c.demographics_state("ZZ"), {})

    def test_county_fips_preserved(self):
        # Los Angeles County = 06037
        la = c.demographics_county("06037")
        self.assertEqual(la["county_fips"], "06037")
        self.assertEqual(la["state"], "CA")
        self.assertGreater(la["population"], 1_000_000)

    def test_top_states_uninsured(self):
        top = c.top_states_by("uninsured_rate", 5)
        self.assertEqual(len(top), 5)
        vals = [r["uninsured_rate"] for r in top]
        self.assertEqual(vals, sorted(vals, reverse=True))
        self.assertEqual(top[0]["state"], "TX")  # TX = highest uninsured

    def test_registry_row(self):
        rows = c.demographics_sources()
        self.assertTrue(rows, "chr_county_demographics not registered")
        self.assertEqual(rows[0]["source_id"], "chr_county_demographics")


if __name__ == "__main__":
    unittest.main()
