"""CMS HCAHPS patient-experience aggregate loader — committed data + shape."""
import unittest

from rcm_mc.data import hcahps_data as h


class HcahpsDataTests(unittest.TestCase):
    def test_summary_present_and_plausible(self):
        s = h.hcahps_summary()
        self.assertTrue(s, "summary aggregate missing — run scripts/ingest_hcahps.py")
        self.assertGreaterEqual(s["states"], 50)
        nat = s["national_mean_pct"]
        # national "would definitely recommend" is ~71%; bound it.
        self.assertTrue(60.0 < nat["would_definitely_recommend"] < 80.0,
                        nat["would_definitely_recommend"])
        self.assertTrue(60.0 < nat["overall_rating_9_10"] < 82.0,
                        nat["overall_rating_9_10"])

    def test_state_lookup(self):
        ca = h.hcahps_state("CA")
        self.assertEqual(ca["state"], "CA")
        self.assertIn("would_definitely_recommend", ca)
        self.assertEqual(h.hcahps_state("ZZ"), {})

    def test_top_states_ranking(self):
        top = h.top_states_by("overall_rating_9_10", 5)
        self.assertEqual(len(top), 5)
        vals = [r["overall_rating_9_10"] for r in top]
        self.assertEqual(vals, sorted(vals, reverse=True))

    def test_registry_row(self):
        rows = h.hcahps_sources()
        self.assertTrue(rows, "cms_hcahps_state not registered")
        self.assertEqual(rows[0]["source_id"], "cms_hcahps_state")


if __name__ == "__main__":
    unittest.main()
