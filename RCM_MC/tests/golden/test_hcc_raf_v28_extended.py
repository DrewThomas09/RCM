"""Golden test for the extended CMS-HCC V28 engine (NEW-12).

Covers the additions beyond the base reference subset:
- disease-interaction terms (fire only when every required HCC survives),
- community segments (CNA / CND / CFA) selecting the demographic table,
- CSV loaders for the crosswalk and coefficients.

Interaction member (72yo M): I50.9 -> HCC226 (HF 0.330), N18.6 -> HCC329
(ESRD 0.435), J44.9 -> HCC280 (COPD 0.290). Demographic CNA 0.395.
Interactions HF_KIDNEY 0.10 (HF+ESRD) and HF_COPD 0.08 (HF+COPD) both fire.
    RAF = 0.395 + 0.330 + 0.435 + 0.290 + 0.10 + 0.08 = 1.630
"""
import os
import tempfile
import unittest

from rcm_mc.cdd import v28_data
from rcm_mc.cdd.hcc_raf import compute_raf

INTERACTION_MEMBER = {"age": 72, "sex": "M", "icd10": ["I50.9", "N18.6", "J44.9"]}


class TestHccRafExtended(unittest.TestCase):
    def test_interactions_fire_and_sum(self):
        ex = compute_raf(INTERACTION_MEMBER, source="Golden", vintage="")
        ic = ex.meta["interaction_contributions"]
        self.assertIn("HF_KIDNEY", ic)
        self.assertIn("HF_COPD", ic)
        self.assertAlmostEqual(ex.meta["interaction_sum"], 0.18, delta=1e-12)
        self.assertAlmostEqual(ex.meta["raf"], 1.630, delta=1e-12)
        self.assertTrue(ex.reconciled)

    def test_interaction_requires_all_hccs(self):
        # HF only (no ESRD, no COPD): no interaction fires.
        ex = compute_raf({"age": 72, "sex": "M", "icd10": ["I50.9"]},
                         source="Golden", vintage="")
        self.assertEqual(ex.meta["interaction_contributions"], {})
        self.assertAlmostEqual(ex.meta["raf"], 0.395 + 0.330, delta=1e-12)

    def test_segments_select_demographic_table(self):
        empty = {"age": 72, "sex": "M", "icd10": []}
        self.assertAlmostEqual(compute_raf(empty, segment="CNA").meta["raf"], 0.395, delta=1e-12)
        self.assertAlmostEqual(compute_raf(empty, segment="CFA").meta["raf"], 0.495, delta=1e-12)
        self.assertEqual(compute_raf(empty, segment="CFA").meta["segment"], "CFA")

    def test_base_member_unchanged_with_interactions_present(self):
        # The original golden member (diabetes + HF) triggers no interaction.
        ex = compute_raf({"age": 72, "sex": "M", "icd10": ["E11.9", "E11.22", "I50.9"]},
                         source="Golden", vintage="")
        self.assertEqual(ex.meta["interaction_contributions"], {})
        self.assertAlmostEqual(ex.meta["raf"], 1.025, delta=1e-12)

    def test_csv_loaders_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            xwalk = os.path.join(d, "xwalk.csv")
            coefs = os.path.join(d, "coefs.csv")
            with open(xwalk, "w") as fh:
                fh.write("icd10,hcc\nE11.9,HCC38\nI50.9,HCC226\n")
            with open(coefs, "w") as fh:
                fh.write("hcc,label,coef\nHCC38,Diabetes,0.105\nHCC226,Heart failure,0.330\n")
            icd_map = v28_data.load_crosswalk_csv(xwalk)
            coef_map = v28_data.load_coefficients_csv(coefs)
            # Code normalization: dots stripped.
            self.assertEqual(icd_map["E119"], "HCC38")
            self.assertAlmostEqual(coef_map["HCC226"]["coef"], 0.330, delta=1e-12)
            # Use the loaded tables in a RAF computation.
            ex = compute_raf({"age": 72, "sex": "M", "icd10": ["I50.9"]},
                             icd_to_hcc=icd_map, hcc_coefficients=coef_map,
                             interactions=[], source="Golden", vintage="")
            self.assertAlmostEqual(ex.meta["raf"], 0.395 + 0.330, delta=1e-12)

    def test_interactions_can_be_disabled(self):
        ex = compute_raf(INTERACTION_MEMBER, interactions=[], source="Golden", vintage="")
        self.assertEqual(ex.meta["interaction_contributions"], {})
        # Without interactions: 0.395 + 0.330 + 0.435 + 0.290 = 1.450
        self.assertAlmostEqual(ex.meta["raf"], 1.450, delta=1e-12)


if __name__ == "__main__":
    unittest.main()
