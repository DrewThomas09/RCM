"""Golden test for NEW-08 market saturation / white-space mapping.

Hand-computed fixture (100000 beneficiaries each, per 1000):
    CBSA-A: 50 providers  -> 0.5 / 1000
    CBSA-B: 10 providers  -> 0.1 / 1000  (most white space, rank 1)
    CBSA-C: 200 providers -> 2.0 / 1000  (most saturated, rank 3)
White-space ranking ascending saturation: B, A, C.
Serve rule: provider_claims > 10 counts as serving.
"""
import unittest

from rcm_mc.cdd.market_saturation import market_saturation

AREAS = [
    {"area": "CBSA-A", "providers": 50, "beneficiaries": 100000},
    {"area": "CBSA-B", "providers": 10, "beneficiaries": 100000},
    {"area": "CBSA-C", "providers": 200, "beneficiaries": 100000},
]


class TestMarketSaturation(unittest.TestCase):
    def test_saturation_values(self):
        ex = market_saturation(AREAS, source="Golden", vintage="2026")
        byarea = {r["area"]: r for r in ex.meta["rows"]}
        self.assertAlmostEqual(byarea["CBSA-A"]["saturation_per_n"], 0.5, delta=1e-9)
        self.assertAlmostEqual(byarea["CBSA-B"]["saturation_per_n"], 0.1, delta=1e-9)
        self.assertAlmostEqual(byarea["CBSA-C"]["saturation_per_n"], 2.0, delta=1e-9)

    def test_white_space_ranking(self):
        ex = market_saturation(AREAS, source="Golden", vintage="2026")
        self.assertEqual(ex.meta["ranking"], ["CBSA-B", "CBSA-A", "CBSA-C"])
        byarea = {r["area"]: r for r in ex.meta["rows"]}
        self.assertEqual(byarea["CBSA-B"]["white_space_rank"], 1)
        self.assertEqual(byarea["CBSA-C"]["white_space_rank"], 3)
        self.assertTrue(ex.reconciled)

    def test_serve_rule_counts_over_threshold(self):
        areas = [{"area": "X", "providers": 5, "beneficiaries": 1000,
                  "provider_claims": [15, 8, 20, 3, 11]}]  # >10: 15,20,11 = 3
        ex = market_saturation(areas, source="Golden", vintage="2026")
        self.assertEqual(ex.meta["rows"][0]["serving_providers"], 3)
        self.assertAlmostEqual(ex.meta["rows"][0]["saturation_per_n"], 3.0, delta=1e-9)

    def test_ffs_only_noted(self):
        ex = market_saturation(AREAS, source="Golden", vintage="2026")
        self.assertTrue(ex.meta["ffs_only"])
        self.assertIn("ffs_only", ex.flag_codes())
        fn = ex.render()["footnote"]
        self.assertTrue(any("Fee-for-service" in a for a in fn["assumptions"]))

    def test_single_area(self):
        ex = market_saturation([{"area": "solo", "providers": 1, "beneficiaries": 1000}],
                               source="Golden", vintage="2026")
        self.assertEqual(ex.meta["ranking"], ["solo"])
        self.assertTrue(ex.reconciled)


if __name__ == "__main__":
    unittest.main()
