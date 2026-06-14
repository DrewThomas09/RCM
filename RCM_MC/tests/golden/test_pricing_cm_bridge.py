"""Golden test for NEW-16 pricing waterfall + contribution-margin bridge.

Hand-computed:
    gross 100 - discount 15 - rebate 5 = net 80
    revenue = 80 * 1000 = 80000
    variable = supplies 20000 + labor 25000 = 45000
    contribution margin = 80000 - 45000 = 35000  (43.75% of revenue)
    EBITDA proxy = 35000 - fixed 15000 = 20000
"""
import unittest

from rcm_mc.cdd.pricing_cm_bridge import pricing_cm_bridge


class TestPricingCmBridge(unittest.TestCase):
    def _build(self):
        return pricing_cm_bridge(
            gross_price=100.0, volume=1000,
            discounts=[{"name": "Volume discount", "amount": 15}],
            rebates=[{"name": "Payer rebate", "amount": 5}],
            variable_costs=[{"name": "Supplies", "amount": 20000}, {"name": "Labor", "amount": 25000}],
            fixed_costs=15000.0, source="Golden", vintage="2026",
        )

    def test_price_waterfall(self):
        m = self._build().meta
        self.assertAlmostEqual(m["net_price"], 80.0, delta=1e-6)
        self.assertAlmostEqual(m["discount_total"], 15.0, delta=1e-6)
        self.assertAlmostEqual(m["rebate_total"], 5.0, delta=1e-6)

    def test_cm_bridge(self):
        m = self._build().meta
        self.assertAlmostEqual(m["revenue"], 80000.0, delta=1e-6)
        self.assertAlmostEqual(m["variable_cost_total"], 45000.0, delta=1e-6)
        self.assertAlmostEqual(m["contribution_margin"], 35000.0, delta=1e-6)
        self.assertAlmostEqual(m["cm_margin"], 0.4375, delta=1e-9)

    def test_ebitda_handoff(self):
        m = self._build().meta
        self.assertAlmostEqual(m["ebitda_proxy"], 20000.0, delta=1e-6)
        self.assertIn("QoE EBITDA bridge", m["ebitda_handoff"])

    def test_both_waterfalls_reconcile(self):
        self.assertTrue(self._build().reconciled)

    def test_per_unit_variable_cost(self):
        ex = pricing_cm_bridge(
            gross_price=10.0, volume=100,
            variable_costs=[{"name": "unit cost", "per_unit": 4.0}],  # 400 total
            source="Golden", vintage="2026",
        )
        self.assertAlmostEqual(ex.meta["variable_cost_total"], 400.0, delta=1e-6)
        self.assertAlmostEqual(ex.meta["contribution_margin"], 1000.0 - 400.0, delta=1e-6)

    def test_partner_hides_ebitda_handoff(self):
        ex = self._build()
        partner = {s["name"] for s in ex.render(internal_mode=False)["series"]}
        self.assertNotIn("EBITDA-bridge handoff", partner)

    def test_no_discounts_net_equals_gross(self):
        ex = pricing_cm_bridge(gross_price=50.0, volume=10, source="Golden", vintage="2026")
        self.assertAlmostEqual(ex.meta["net_price"], 50.0, delta=1e-6)
        self.assertTrue(ex.reconciled)


if __name__ == "__main__":
    unittest.main()
