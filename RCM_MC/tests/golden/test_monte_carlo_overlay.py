"""Golden test for NEW-11 Monte Carlo overlay.

Base 1000, two normal fractional drivers:
    cms   ~ Normal(-0.05, 0.02)   -> dominant driver
    small ~ Normal( 0.00, 0.005)  -> minor driver
Default model output = base * (1 + cms + small) ~ Normal(950, ~20.6).
Theoretical median 950; P5/P50/P95 reproducible to 1e-9 on seed 42.
A CMS rate cut stress shifts cms by -0.10, dropping the median by 100.
"""
import unittest

from rcm_mc.cdd.monte_carlo_overlay import monte_carlo_overlay

DRIVERS = [
    {"name": "cms", "dist": "normal", "params": {"mean": -0.05, "sd": 0.02}},
    {"name": "small", "dist": "normal", "params": {"mean": 0.0, "sd": 0.005}},
]
STRESS = {"CMS rate cut": {"cms": -0.10}}


class TestMonteCarloOverlay(unittest.TestCase):
    def _build(self, seed=42):
        return monte_carlo_overlay(1000.0, DRIVERS, seed=seed,
                                   stress_scenarios=STRESS,
                                   source="Golden", vintage="2026")

    def test_p50_near_theory(self):
        m = self._build().meta
        self.assertAlmostEqual(m["p50"], 950.0, delta=1.0,
                               msg=f"P50 expected near 950, got {m['p50']}")
        self.assertLess(m["p5"], m["p50"])
        self.assertLess(m["p50"], m["p95"])

    def test_reproducible_to_1e9(self):
        a = self._build().meta
        b = self._build().meta
        for k in ("p5", "p50", "p95"):
            self.assertAlmostEqual(a[k], b[k], delta=1e-9,
                                   msg=f"{k} not reproducible: {a[k]} vs {b[k]}")

    def test_tornado_ranks_drivers(self):
        t = self._build().meta["tornado"]
        self.assertEqual(t[0]["driver"], "cms",
                         msg="cms must rank first by sensitivity")
        self.assertGreater(t[0]["sensitivity"], t[1]["sensitivity"])

    def test_cms_rate_cut_stress(self):
        m = self._build().meta
        stressed = m["stresses"]["CMS rate cut"]["p50"]
        # additive -0.10 shock on base 1000 shifts the median down by ~100.
        self.assertAlmostEqual(stressed, m["p50"] - 100.0, delta=1e-6)
        self.assertIn("downside_stress", self._build().flag_codes())

    def test_ordering_reconciles(self):
        self.assertTrue(self._build().reconciled)

    def test_n_sims_minimum_enforced(self):
        with self.assertRaises(ValueError):
            monte_carlo_overlay(1000.0, DRIVERS, n_sims=500)

    def test_distributions_supported(self):
        drivers = [
            {"name": "tri", "dist": "triangular", "params": {"left": -0.1, "mode": 0.0, "right": 0.1}},
            {"name": "beta", "dist": "beta", "params": {"a": 2, "b": 5, "scale": 0.1, "loc": -0.05}},
            {"name": "logn", "dist": "lognormal", "params": {"mean": -3.0, "sigma": 0.3}},
        ]
        ex = monte_carlo_overlay(1000.0, drivers, seed=7, source="Golden", vintage="2026")
        self.assertTrue(ex.meta["p5"] <= ex.meta["p50"] <= ex.meta["p95"])

    def test_different_seed_changes_draws(self):
        a = self._build(seed=1).meta["p50"]
        b = self._build(seed=2).meta["p50"]
        self.assertNotAlmostEqual(a, b, places=6)


if __name__ == "__main__":
    unittest.main()
