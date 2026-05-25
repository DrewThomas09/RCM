"""CDC PLACES health-equity aggregate loader — committed data + shape."""
import unittest

from rcm_mc.data import cdc_places_agg as c


class CdcPlacesEquityTests(unittest.TestCase):
    def test_summary_present_and_plausible(self):
        s = c.places_equity_summary()
        self.assertTrue(s, "summary aggregate missing — run scripts/ingest_cdc_places.py")
        self.assertGreaterEqual(s["counties"], 3000)
        self.assertGreaterEqual(s["states"], 50)
        nat = s["national_prevalence_pct"]
        # national uninsured 18-64 is ~11% — sanity-bound it.
        self.assertTrue(5.0 < nat["uninsured_18_64"] < 20.0, nat["uninsured_18_64"])
        # obesity ~33% nationally
        self.assertTrue(20.0 < nat["obesity"] < 45.0, nat["obesity"])

    def test_state_lookup(self):
        ca = c.places_equity_state("CA")
        self.assertEqual(ca["state"], "CA")
        self.assertIn("food_insecurity", ca)
        self.assertGreater(ca["population"], 1_000_000)
        # unknown state returns empty
        self.assertEqual(c.places_equity_state("ZZ"), {})

    def test_top_states_ranking(self):
        top = c.top_states_by("uninsured_18_64", 5)
        self.assertEqual(len(top), 5)
        # descending by default — highest-burden first
        vals = [r["uninsured_18_64"] for r in top]
        self.assertEqual(vals, sorted(vals, reverse=True))
        # TX is the canonical highest-uninsured state
        self.assertEqual(top[0]["state"], "TX")

    def test_registry_row(self):
        rows = c.places_equity_sources()
        self.assertTrue(rows, "cdc_places_equity not registered in source_registry.csv")
        self.assertEqual(rows[0]["source_id"], "cdc_places_equity")


if __name__ == "__main__":
    unittest.main()
