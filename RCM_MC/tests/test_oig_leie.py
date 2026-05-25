"""OIG LEIE excluded-provider aggregate loader — committed data + shape."""
import unittest

from rcm_mc.data import oig_leie as l


class OigLeieTests(unittest.TestCase):
    def test_summary_plausible(self):
        s = l.leie_summary()
        self.assertTrue(s, "summary missing — run scripts/ingest_oig_leie.py")
        self.assertGreater(s["total_exclusions"], 50_000)
        self.assertGreaterEqual(s["states"], 50)
        # PII must not be present in the committed data sections (the
        # pii_note legitimately names which fields were dropped).
        data_blob = str({k: v for k, v in s.items() if k != "pii_note"}).lower()
        for pii in ("lastname", "firstname", "dob", "npi", "address"):
            self.assertNotIn(pii, data_blob)

    def test_breakdowns(self):
        self.assertGreaterEqual(len(l.top_states(8)), 8)
        bt = l.by_exclusion_type(8)
        self.assertTrue(bt and bt[0]["count"] > 0)
        self.assertTrue(all("label" in r for r in bt))

    def test_registry(self):
        rows = l.leie_sources()
        self.assertTrue(rows)
        self.assertEqual(rows[0]["source_id"], "oig_leie")


if __name__ == "__main__":
    unittest.main()
