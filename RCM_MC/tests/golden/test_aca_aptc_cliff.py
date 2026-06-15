"""Golden test for NEW-30 ACA enhanced-APTC subsidy cliff.

FPL base 15,060 (single, 2024). Benchmark premium 7,000.
    400 pct FPL: income 60,240.
        enhanced 8.5 pct -> required 5,120.40, net 5,120.40
        sunset 9.83 pct  -> required 5,921.592, net 5,921.592
    450 pct FPL: income 67,770.
        enhanced 8.5 pct -> required 5,760.45, net 5,760.45
        sunset above 400 pct -> cliff, no credit, net 7,000
"""
import unittest

from rcm_mc.cdd.aca_aptc_cliff import aca_aptc_cliff, applicable_percent, compute_aptc


class TestAcaAptcCliff(unittest.TestCase):
    def _build(self):
        enrollees = [
            {"label": "400 pct FPL", "fpl_pct": 400.0, "benchmark_premium": 7000.0},
            {"label": "450 pct FPL", "fpl_pct": 450.0, "benchmark_premium": 7000.0},
        ]
        return aca_aptc_cliff(enrollees, source="Golden", vintage="2025")

    def test_enhanced_net_premium(self):
        a = compute_aptc(400.0, 7000.0, "enhanced")
        self.assertAlmostEqual(a["net_premium"], 5120.40, delta=1e-6)
        b = compute_aptc(450.0, 7000.0, "enhanced")
        self.assertAlmostEqual(b["net_premium"], 5760.45, delta=1e-6)

    def test_sunset_cliff(self):
        b = compute_aptc(450.0, 7000.0, "sunset")
        self.assertFalse(b["eligible"])
        self.assertAlmostEqual(b["aptc"], 0.0, delta=1e-9)
        self.assertAlmostEqual(b["net_premium"], 7000.0, delta=1e-9)

    def test_sunset_at_boundary_keeps_credit(self):
        a = compute_aptc(400.0, 7000.0, "sunset")
        self.assertTrue(a["eligible"])
        self.assertAlmostEqual(a["net_premium"], 5921.592, delta=1e-6)

    def test_applicable_percent_tails(self):
        self.assertAlmostEqual(applicable_percent(120.0, "enhanced"), 0.0, delta=1e-12)
        self.assertAlmostEqual(applicable_percent(500.0, "enhanced"), 0.085, delta=1e-12)
        self.assertIsNone(applicable_percent(401.0, "sunset"))

    def test_flags_and_reconcile(self):
        ex = self._build()
        self.assertIn("subsidy_cliff", ex.flag_codes())
        self.assertIn("premium_shock", ex.flag_codes())
        self.assertEqual(ex.meta["cliff_hits"], 1)
        self.assertTrue(ex.reconciled)

    def test_totals(self):
        ex = self._build()
        self.assertAlmostEqual(ex.meta["total_enhanced_net"], 10880.85, delta=1e-6)
        self.assertAlmostEqual(ex.meta["total_sunset_net"], 12921.592, delta=1e-6)

    def test_partner_hides_contribution_line(self):
        partner = {s["name"] for s in self._build().render(internal_mode=False)["series"]}
        self.assertNotIn("Required contribution percent by income", partner)

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            aca_aptc_cliff([])


if __name__ == "__main__":
    unittest.main()
