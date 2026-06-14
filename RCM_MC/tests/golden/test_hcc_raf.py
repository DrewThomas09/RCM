"""Golden test for NEW-12 HCC/RAF (CMS-HCC V28).

Synthetic member: 72yo male, community non-dual aged.
    demographic factor M 70-74 = 0.395
    diagnoses E11.9  -> HCC38 (diabetes w/o complications, 0.105)
              E11.22 -> HCC37 (diabetes with chronic complications, 0.300)
              I50.9  -> HCC226 (heart failure, 0.330)
    hierarchy: HCC37 trumps HCC38, so HCC38 is dropped.
    RAF = 0.395 + 0.300 + 0.330 = 1.025
"""
import unittest

from rcm_mc.cdd import v28_data
from rcm_mc.cdd.hcc_raf import compute_raf

MEMBER = {"age": 72, "sex": "M", "eligibility": "CNA",
          "icd10": ["E11.9", "E11.22", "I50.9"]}


class TestHccRaf(unittest.TestCase):
    def _build(self, member=None):
        return compute_raf(member or MEMBER, source="Golden", vintage="")

    def test_raf_exact(self):
        m = self._build().meta
        self.assertAlmostEqual(m["demographic_factor"], 0.395, delta=1e-12)
        self.assertAlmostEqual(m["raf"], 1.025, delta=1e-12,
                               msg=f"RAF expected 1.025 got {m['raf']}")

    def test_hierarchy_drops_less_severe(self):
        m = self._build().meta
        self.assertIn("HCC37", m["surviving_hccs"])
        self.assertIn("HCC226", m["surviving_hccs"])
        self.assertNotIn("HCC38", m["surviving_hccs"])
        self.assertIn("HCC38", m["dropped_by_hierarchy"])

    def test_raf_reconciles_to_components(self):
        ex = self._build()
        self.assertTrue(ex.reconciled)
        m = ex.meta
        self.assertAlmostEqual(m["raf"], m["demographic_factor"] + m["hcc_sum"], delta=1e-12)

    def test_trajectory_and_compression(self):
        m = self._build().meta
        traj = m["trajectory"]
        comp = m["compressed_trajectory"]
        self.assertEqual(traj[0]["raf"], m["raf"])  # year 0 equals RAF
        # year 1 base = raf * 1.02
        self.assertAlmostEqual(traj[1]["raf"], m["raf"] * 1.02, delta=1e-12)
        # compression pulls year 1 below the uncompressed value
        self.assertLess(comp[1]["raf"], traj[1]["raf"])
        self.assertAlmostEqual(comp[1]["raf"], m["raf"] * 1.02 * (1 - 0.059), delta=1e-12)

    def test_vintage_labeled(self):
        ex = self._build()
        self.assertIn("V28", ex.render()["footnote"]["vintage"])
        self.assertIn("V28", ex.meta["vintage"])

    def test_unmapped_code_flagged(self):
        member = dict(MEMBER)
        member["icd10"] = ["E11.9", "E11.22", "I50.9", "Z00.00"]  # Z00.00 unmapped
        ex = self._build(member)
        self.assertIn("unmapped_codes", ex.flag_codes())
        self.assertIn("Z0000", ex.meta["unmapped_codes"])
        # RAF unchanged by the unmapped code.
        self.assertAlmostEqual(ex.meta["raf"], 1.025, delta=1e-12)

    def test_demographic_only_member(self):
        ex = self._build({"age": 68, "sex": "F", "icd10": []})
        self.assertAlmostEqual(ex.meta["raf"], v28_data.demographic_factor("F", 68), delta=1e-12)
        self.assertAlmostEqual(ex.meta["hcc_sum"], 0.0, delta=1e-12)

    def test_partner_hides_mapping_detail(self):
        ex = self._build()
        partner = {s["name"] for s in ex.render(internal_mode=False)["series"]}
        self.assertNotIn("HCC mapping detail", partner)

    def test_mapping_is_pure_lookup(self):
        # Same input twice yields identical RAF (deterministic, no model state).
        a = self._build().meta["raf"]
        b = self._build().meta["raf"]
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
