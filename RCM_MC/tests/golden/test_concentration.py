"""Golden test for NEW-10 customer concentration.

Fixture A (must flag): A 45, B 30, C 15, D 10 (total 100)
    largest = 45% > 40% -> single_account_over_40pct
Fixture B (must not flag): A 30, B 25, C 25, D 20 (total 100)
    largest = 30% -> no flag
"""
import unittest

from rcm_mc.cdd.concentration import customer_concentration

FLAGGED = [
    {"account": "A", "revenue": 45},
    {"account": "B", "revenue": 30},
    {"account": "C", "revenue": 15},
    {"account": "D", "revenue": 10},
]
CLEAN = [
    {"account": "A", "revenue": 30},
    {"account": "B", "revenue": 25},
    {"account": "C", "revenue": 25},
    {"account": "D", "revenue": 20},
]


class TestConcentration(unittest.TestCase):
    def test_shares_and_topn(self):
        ex = customer_concentration(FLAGGED, top_ns=(1, 2, 5), source="Golden", vintage="2026")
        self.assertAlmostEqual(ex.meta["max_share"], 0.45, delta=1e-9)
        self.assertAlmostEqual(ex.meta["top_n_shares"][1], 0.45, delta=1e-9)
        self.assertAlmostEqual(ex.meta["top_n_shares"][2], 0.75, delta=1e-9)
        self.assertAlmostEqual(ex.meta["top_n_shares"][5], 1.0, delta=1e-9)  # only 4 accounts
        self.assertTrue(ex.reconciled)

    def test_over_40_flags(self):
        ex = customer_concentration(FLAGGED, source="Golden", vintage="2026")
        self.assertIn("single_account_over_40pct", ex.flag_codes())

    def test_under_40_no_flag(self):
        ex = customer_concentration(CLEAN, source="Golden", vintage="2026")
        self.assertNotIn("single_account_over_40pct", ex.flag_codes())
        self.assertAlmostEqual(ex.meta["max_share"], 0.30, delta=1e-9)

    def test_partner_ranks_internal_names(self):
        ex = customer_concentration(FLAGGED, source="Golden", vintage="2026")
        partner = {s["name"] for s in ex.render(internal_mode=False)["series"]}
        internal = {s["name"] for s in ex.render(internal_mode=True)["series"]}
        self.assertIn("Top accounts by rank", partner)
        self.assertNotIn("Top accounts by name", partner)
        self.assertIn("Top accounts by name", internal)
        # Partner ranked points carry ranks, not names.
        ranked = next(s for s in ex.render(internal_mode=False)["series"]
                      if s["name"] == "Top accounts by rank")
        self.assertEqual([p["label"] for p in ranked["points"]], ["#1", "#2", "#3", "#4"])

    def test_pareto_monotone_to_one(self):
        ex = customer_concentration(FLAGGED, source="Golden", vintage="2026")
        cum = [p["cumulative_share"] for p in ex.meta["pareto"]]
        self.assertEqual(cum, sorted(cum))
        self.assertAlmostEqual(cum[-1], 1.0, delta=1e-9)

    def test_hhi(self):
        # HHI for 45/30/15/10 = .2025+.09+.0225+.01 = 0.325
        ex = customer_concentration(FLAGGED, source="Golden", vintage="2026")
        self.assertAlmostEqual(ex.meta["hhi"], 0.325, delta=1e-9)

    def test_single_account_100pct(self):
        ex = customer_concentration([{"account": "solo", "revenue": 500}],
                                    source="Golden", vintage="2026")
        self.assertAlmostEqual(ex.meta["max_share"], 1.0, delta=1e-9)
        self.assertIn("single_account_over_40pct", ex.flag_codes())


if __name__ == "__main__":
    unittest.main()
