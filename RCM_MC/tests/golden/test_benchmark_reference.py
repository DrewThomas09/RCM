"""Golden test for REF-01 through REF-06 granular benchmarking reference data.

Each domain is a registered reference Exhibit. The tests prove:
- the stated reconciliation identities tie out (hand-verified below),
- the provenance flags fire so estimates and projections are never mistaken for
  realized data,
- the partner render carries the core pack and leaks no internal nodes.

Hand-verified reconciliations:
    REF-01 patient experience weight: 4 minus 2 reduction equals 2.
    REF-02 top 10 Part B drugs: 4.9+3.5+2.0+1.9+1.9+1.0+0.9+0.8+0.8+0.7 = 18.4
        versus reported 18.5, gap 0.1 within tolerance 0.15.
    REF-03 family medicine: 218400 / 5200 = 42.0 dollars per wRVU.
    REF-04 340B uncompensated care: 42.0 * 0.68 = 28.56 billion dollars.
    REF-05 leading causes: (680909 + 613352) / 3090964 * 100 = 41.87 percent
        versus reported 41.9, gap 0.03 within tolerance 0.1.
    REF-06 NHE by payer: 1500 + 1029.8 + 871.7 + 505.7 = 3907.2, plus a
        residual of 992.8, sums to 4900.
"""
import unittest

from rcm_mc.cdd import registry
from rcm_mc.cdd.benchmark_reference import (
    code_frequency,
    disease_prevalence,
    hospital_cost_structure,
    national_expenditure,
    physician_compensation_supply,
    quality_measure_weights,
)

REF_IDS = ["REF-01", "REF-02", "REF-03", "REF-04", "REF-05", "REF-06"]


class TestBenchmarkReference(unittest.TestCase):
    def test_all_ref_features_registered(self):
        ids = set(registry.feature_ids())
        for fid in REF_IDS:
            self.assertIn(fid, ids, msg=f"{fid} not registered")

    def test_every_exhibit_reconciles(self):
        for fid in REF_IDS:
            ex = registry.get(fid).demo()
            self.assertTrue(ex.reconciled, msg=f"{fid} did not reconcile")

    def test_ref01_patient_experience_weight_cut(self):
        ex = quality_measure_weights()
        self.assertAlmostEqual(ex.meta["patient_experience_reduction"], 2.0, delta=1e-9)
        self.assertIn("star_patient_experience_weight_cut", ex.flag_codes())
        self.assertEqual(ex.meta["weights_2026"]["Patient experience, complaints, access"], 2.0)

    def test_ref02_part_b_top10_sum(self):
        ex = code_frequency()
        self.assertAlmostEqual(ex.meta["part_b_top10_sum_b"], 18.4, delta=1e-9)
        self.assertTrue(ex.reconciled)
        self.assertIn("part_b_ffs_only", ex.flag_codes())

    def test_ref03_dollars_per_wrvu(self):
        ex = physician_compensation_supply()
        self.assertAlmostEqual(
            ex.meta["family_medicine_comp"] / ex.meta["family_medicine_wrvu"],
            42.0,
            delta=0.05,
        )
        self.assertIn("mgma_proprietary", ex.flag_codes())

    def test_ref04_340b_uncompensated(self):
        ex = hospital_cost_structure()
        self.assertAlmostEqual(ex.meta["uncompensated_340b_b"], 28.56, delta=1e-9)
        self.assertIn("340b_rebate_pilot_vacated", ex.flag_codes())

    def test_ref05_heart_plus_cancer_share(self):
        ex = disease_prevalence()
        heart = ex.meta["leading_causes_2023"][0]["deaths"]
        cancer = ex.meta["leading_causes_2023"][1]["deaths"]
        total = ex.meta["total_deaths_2023"]
        self.assertAlmostEqual((heart + cancer) / total * 100.0, 41.9, delta=0.1)
        self.assertIn("diabetes_methodology_conflict", ex.flag_codes())

    def test_ref06_payer_residual_ties_to_total(self):
        ex = national_expenditure()
        named = sum(p["spend_b"] for p in ex.meta["nhe_by_payer"])
        self.assertAlmostEqual(named + ex.meta["payer_residual_b"], 4900.0, delta=1e-6)
        self.assertIn("medpac_all_payer_basis", ex.flag_codes())

    def test_partner_render_carries_core_pack(self):
        for fid in REF_IDS:
            partner = registry.run(fid, internal_mode=False)
            self.assertTrue(partner["title"])
            self.assertIsNotNone(partner["footnote"])
            self.assertGreaterEqual(len(partner["series"]), 1)
            self.assertNotIn("assumptions", partner)

    def test_footnotes_carry_source_and_vintage(self):
        for fid in REF_IDS:
            fn = registry.get(fid).demo().render(internal_mode=True)["footnote"]
            self.assertTrue(fn["source"], f"{fid} missing source")
            self.assertTrue(fn["vintage"], f"{fid} missing vintage")
            self.assertTrue(fn["assumptions"], f"{fid} missing assumptions")


if __name__ == "__main__":
    unittest.main()
