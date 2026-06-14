"""Golden test for NEW-03 payer-mix analysis and waterfall.

Hand-computed fixture (totals 10000 each period):

    FY24: Medicare 4000, Medicaid 2000, Commercial 3000, Self-pay 500, Other 500
          shares  40,         20,          30,            5,           5  = 100
    FY25: Medicare 4500, Medicaid 2500, Commercial 2500, Self-pay 300, Other 200
          shares  45,         25,          25,            3,           2  = 100
    deltas:       +5,         +5,          -5,           -2,          -3  = 0

    margin weights Commercial 1.0, Medicare 0.6, Medicaid 0.4, Self-pay 0.2, Other 0.5
    score FY24 = .40*.6+.20*.4+.30*1+.05*.2+.05*.5 = .24+.08+.30+.01+.025 = 0.655
    score FY25 = .45*.6+.25*.4+.25*1+.03*.2+.02*.5 = .27+.10+.25+.006+.01 = 0.636
"""
import unittest

from rcm_mc.cdd.payer_mix import payer_mix

P1 = {"Medicare": 4000, "Medicaid": 2000, "Commercial": 3000, "Self-pay": 500, "Other": 500}
P2 = {"Medicare": 4500, "Medicaid": 2500, "Commercial": 2500, "Self-pay": 300, "Other": 200}


class TestPayerMix(unittest.TestCase):
    def _build(self):
        return payer_mix(P1, P2, period1_label="FY24", period2_label="FY25",
                         source="Golden", vintage="2026")

    def test_shares_sum_to_100(self):
        ex = self._build()
        s1 = ex.meta["shares_1"]
        s2 = ex.meta["shares_2"]
        self.assertAlmostEqual(sum(s1.values()), 100.0, delta=1e-9)
        self.assertAlmostEqual(sum(s2.values()), 100.0, delta=1e-9)
        self.assertAlmostEqual(s1["Medicare"], 40.0, delta=1e-9)
        self.assertAlmostEqual(s2["Commercial"], 25.0, delta=1e-9)

    def test_deltas_hand_verified_and_sum_zero(self):
        d = self._build().meta["deltas"]
        self.assertAlmostEqual(d["Medicare"], 5.0, delta=1e-9)
        self.assertAlmostEqual(d["Medicaid"], 5.0, delta=1e-9)
        self.assertAlmostEqual(d["Commercial"], -5.0, delta=1e-9)
        self.assertAlmostEqual(d["Self-pay"], -2.0, delta=1e-9)
        self.assertAlmostEqual(d["Other"], -3.0, delta=1e-9)
        self.assertAlmostEqual(sum(d.values()), 0.0, delta=1e-9)

    def test_weighted_score_and_dilution_flag(self):
        ex = self._build()
        self.assertAlmostEqual(ex.meta["weighted_score_1"], 0.655, delta=1e-9)
        self.assertAlmostEqual(ex.meta["weighted_score_2"], 0.636, delta=1e-9)
        self.assertIn("margin_dilutive_shift", ex.flag_codes())

    def test_reconciliations_emitted_and_ok(self):
        ex = self._build()
        self.assertTrue(ex.reconciled)
        ids = [r["identity"] for r in ex.render()["reconciliations"]]
        self.assertTrue(any("sum to zero" in i for i in ids))

    def test_single_period_shares(self):
        ex = payer_mix(P1, source="Golden", vintage="2026")
        self.assertAlmostEqual(sum(ex.meta["shares_1"].values()), 100.0, delta=1e-9)
        self.assertNotIn("deltas", ex.meta)

    def test_all_medicaid_degenerate(self):
        # Adversarial: 100% Medicaid. Shares still sum to 100, no crash.
        ex = payer_mix({"Medicaid": 5000, "Medicare": 0, "Commercial": 0},
                       source="Golden", vintage="2026")
        self.assertAlmostEqual(ex.meta["shares_1"]["Medicaid"], 100.0, delta=1e-9)

    def test_partner_view_hides_margin_weights(self):
        ex = self._build()
        partner = {s["name"] for s in ex.render(internal_mode=False)["series"]}
        internal = {s["name"] for s in ex.render(internal_mode=True)["series"]}
        self.assertNotIn("Margin-weight overlay", partner)
        self.assertIn("Margin-weight overlay", internal)


if __name__ == "__main__":
    unittest.main()
