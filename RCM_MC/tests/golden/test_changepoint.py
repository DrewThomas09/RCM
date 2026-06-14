"""Golden test for BOLSTER-03 changepoint detection (ruptures).

Fixtures:
- Break series [10]*10 + [50]*10: one changepoint at index 10, direction up,
  magnitude +40.
- Flat series [5]*20: zero changepoints.
- Downward break [50]*10 + [10]*10: changepoint at 10, direction down.
"""
import unittest

import numpy as np

from rcm_mc.cdd.changepoint import detect_changepoints


class TestChangepoint(unittest.TestCase):
    def test_known_break_detected(self):
        ex = detect_changepoints([10.0] * 10 + [50.0] * 10, model="l2",
                                 source="Golden", vintage="2026")
        cps = ex.meta["changepoints"]
        self.assertEqual(len(cps), 1)
        self.assertEqual(cps[0]["index"], 10)
        self.assertEqual(cps[0]["direction"], "up")
        self.assertAlmostEqual(cps[0]["magnitude"], 40.0, delta=1e-9)

    def test_flat_series_no_changepoints(self):
        ex = detect_changepoints([5.0] * 20, model="l2", source="Golden", vintage="2026")
        self.assertEqual(ex.meta["changepoints"], [])
        self.assertNotIn("changepoint_detected", ex.flag_codes())

    def test_downward_break(self):
        ex = detect_changepoints([50.0] * 10 + [10.0] * 10, model="l2",
                                 source="Golden", vintage="2026")
        cps = ex.meta["changepoints"]
        self.assertEqual(len(cps), 1)
        self.assertEqual(cps[0]["index"], 10)
        self.assertEqual(cps[0]["direction"], "down")
        self.assertAlmostEqual(cps[0]["magnitude"], -40.0, delta=1e-9)

    def test_date_mapping(self):
        dates = [f"2024-{i+1:02d}" for i in range(20)]
        ex = detect_changepoints([10.0] * 10 + [50.0] * 10, dates=dates,
                                 model="l2", source="Golden", vintage="2026")
        self.assertEqual(ex.meta["changepoints"][0]["date"], "2024-11")

    def test_noisy_break_default_penalty(self):
        rng = np.random.default_rng(1)
        sig = np.concatenate([rng.normal(0, 1, 30), rng.normal(6, 1, 30)]).tolist()
        ex = detect_changepoints(sig, model="l2", source="Golden", vintage="2026")
        cps = ex.meta["changepoints"]
        self.assertEqual(len(cps), 1)
        self.assertTrue(28 <= cps[0]["index"] <= 32, msg=f"break index {cps[0]['index']}")

    def test_reconciles(self):
        ex = detect_changepoints([10.0] * 10 + [50.0] * 10, source="Golden", vintage="2026")
        self.assertTrue(ex.reconciled)

    def test_flag_fires_on_break(self):
        ex = detect_changepoints([10.0] * 10 + [50.0] * 10, source="Golden", vintage="2026")
        self.assertIn("changepoint_detected", ex.flag_codes())

    def test_invalid_model_raises(self):
        with self.assertRaises(ValueError):
            detect_changepoints([1.0, 2.0, 3.0], model="poly")

    def test_partner_hides_detail(self):
        ex = detect_changepoints([10.0] * 10 + [50.0] * 10, source="Golden", vintage="2026")
        partner = {s["name"] for s in ex.render(internal_mode=False)["series"]}
        self.assertNotIn("Changepoint detail", partner)


if __name__ == "__main__":
    unittest.main()
