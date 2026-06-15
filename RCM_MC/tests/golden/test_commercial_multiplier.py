"""Golden test for NEW-24 commercial-to-Medicare multiplier.

Applying RAND Round 5.1 ratios to four 2026 Medicare anchors:
    inpatient discharge 6752.61 * 2.54 = 17151.6294
    outpatient service   91.415 * 2.79 = 255.04785
    physician RVU        33.5675 * 1.84 = 61.7642
    ASC case             56.322 * 1.71 = 96.31062
"""
import unittest

from rcm_mc.cdd.commercial_multiplier import commercial_multiplier


class TestCommercialMultiplier(unittest.TestCase):
    def _build(self):
        return commercial_multiplier([
            {"label": "Inpatient hospital discharge", "service_type": "inpatient facility",
             "medicare_amount": 6752.61},
            {"label": "Hospital outpatient service", "service_type": "outpatient facility",
             "medicare_amount": 91.415},
            {"label": "Physician RVU", "service_type": "professional",
             "medicare_amount": 33.5675},
            {"label": "ASC case", "service_type": "asc outpatient",
             "medicare_amount": 56.322},
        ])

    def test_repricing(self):
        pts = {p["label"]: p for p in self._build().meta["anchors"]}
        self.assertAlmostEqual(pts["Inpatient hospital discharge"]["commercial_estimate"],
                               17151.6294, delta=1e-6)
        self.assertAlmostEqual(pts["Hospital outpatient service"]["commercial_estimate"],
                               255.04785, delta=1e-6)
        self.assertAlmostEqual(pts["Physician RVU"]["commercial_estimate"],
                               61.7642, delta=1e-6)
        self.assertAlmostEqual(pts["ASC case"]["commercial_estimate"],
                               96.31062, delta=1e-6)

    def test_reconciles(self):
        self.assertTrue(self._build().reconciled)
        self.assertIn("benchmark_not_price", self._build().flag_codes())

    def test_unknown_service_type_flagged(self):
        ex = commercial_multiplier([
            {"label": "Lab test", "service_type": "lab", "medicare_amount": 20.0},
            {"label": "RVU", "service_type": "professional", "medicare_amount": 33.5675},
        ])
        self.assertIn("unknown_service_type", ex.flag_codes())
        labels = [p["label"] for p in ex.meta["anchors"]]
        self.assertNotIn("Lab test", labels)
        self.assertIn("RVU", labels)

    def test_all_unknown_raises(self):
        with self.assertRaises(ValueError):
            commercial_multiplier([
                {"label": "Lab", "service_type": "lab", "medicare_amount": 20.0},
            ])

    def test_state_spread(self):
        m = self._build().meta
        self.assertEqual(m["state_low"]["state"], "Arkansas")
        self.assertEqual(m["state_high"]["pct"], 346.0)

    def test_rejects_empty(self):
        with self.assertRaises(ValueError):
            commercial_multiplier([])


if __name__ == "__main__":
    unittest.main()
