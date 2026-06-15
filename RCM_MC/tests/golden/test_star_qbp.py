"""Golden test for NEW-28 star-rating QBP sensitivity.

Held fixed: FFS 1000, quartile 1 (115 percent), bid 830, quality bonus on.
    5.0 stars: benchmark 1200, 70 percent, rebate 259, payment 1089
    4.5 stars: benchmark 1200, 70 percent, rebate 259, payment 1089
    4.0 stars: benchmark 1200, 65 percent, rebate 240.5, payment 1070.5
    3.5 stars: benchmark 1150 (no bonus), 65 percent, rebate 208, payment 1038
    3.0 stars: benchmark 1150 (no bonus), 50 percent, rebate 160, payment 990
    swing 1089 - 990 = 99; 4.5 -> 4.0 downgrade loss 1089 - 1070.5 = 18.5
"""
import unittest

from rcm_mc.cdd.star_qbp import star_qbp_sensitivity


class TestStarQbp(unittest.TestCase):
    def _build(self):
        return star_qbp_sensitivity(
            ffs_percapita=1000.0, quartile=1, bid=830.0, current_stars=4.5,
            source="Golden", vintage="2025",
        )

    def test_payment_by_star(self):
        by = self._build().meta["by_star"]
        self.assertAlmostEqual(by[5.0]["plan_payment"], 1089.0, delta=1e-9)
        self.assertAlmostEqual(by[4.0]["plan_payment"], 1070.5, delta=1e-9)
        self.assertAlmostEqual(by[3.5]["plan_payment"], 1038.0, delta=1e-9)
        self.assertAlmostEqual(by[3.0]["plan_payment"], 990.0, delta=1e-9)

    def test_benchmark_drops_below_4_stars(self):
        by = self._build().meta["by_star"]
        self.assertAlmostEqual(by[4.0]["benchmark"], 1200.0, delta=1e-9)
        self.assertAlmostEqual(by[3.5]["benchmark"], 1150.0, delta=1e-9)

    def test_swing(self):
        ex = self._build()
        self.assertAlmostEqual(ex.meta["best_payment"], 1089.0, delta=1e-9)
        self.assertAlmostEqual(ex.meta["worst_payment"], 990.0, delta=1e-9)
        self.assertAlmostEqual(ex.meta["swing"], 99.0, delta=1e-9)
        self.assertTrue(ex.reconciled)

    def test_cliff_flag(self):
        self.assertIn("crosses_4star_cliff", self._build().flag_codes())

    def test_downgrade_loss(self):
        ex = self._build()
        self.assertAlmostEqual(ex.meta["downgrade_loss"], 18.5, delta=1e-9)
        self.assertIn("downgrade_payment_loss", ex.flag_codes())

    def test_no_cliff_when_all_above_4(self):
        ex = star_qbp_sensitivity(
            ffs_percapita=1000.0, quartile=1, bid=830.0, scenarios=(5.0, 4.5, 4.0),
            source="Golden", vintage="2025",
        )
        self.assertNotIn("crosses_4star_cliff", ex.flag_codes())

    def test_partner_hides_retention_series(self):
        partner = {s["name"] for s in self._build().render(internal_mode=False)["series"]}
        self.assertNotIn("Retention share by star tier", partner)

    def test_empty_scenarios_raises(self):
        with self.assertRaises(ValueError):
            star_qbp_sensitivity(ffs_percapita=1000.0, quartile=1, bid=830.0, scenarios=())


if __name__ == "__main__":
    unittest.main()
