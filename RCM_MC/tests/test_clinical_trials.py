"""ClinicalTrials.gov trial-landscape loader — committed data + shape."""
import unittest

from rcm_mc.data import clinical_trials as ct


class ClinicalTrialsTests(unittest.TestCase):
    def test_summary_plausible(self):
        s = ct.clinical_trials_summary()
        self.assertTrue(s, "summary missing — run scripts/ingest_clinical_trials.py")
        self.assertGreater(s["total_studies"], 400_000)
        self.assertGreater(s["recruiting"], 10_000)
        self.assertLess(s["recruiting"], s["total_studies"])
        self.assertGreater(s["interventional"], 100_000)

    def test_phase_breakdown(self):
        ph = ct.phase_breakdown()
        self.assertEqual(len(ph), 4)
        self.assertTrue(all(p["count"] > 0 for p in ph))
        self.assertTrue(any(p["phase"] == "Phase 3" for p in ph))

    def test_registry(self):
        rows = ct.clinical_trials_sources()
        self.assertTrue(rows)
        self.assertEqual(rows[0]["source_id"], "clinicaltrials_gov")


if __name__ == "__main__":
    unittest.main()
