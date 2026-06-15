"""Golden test for NEW-21 unit-economics spine.

The default master spine carries 26 verticals: 14 verified 2026 final-rule
anchors, 2 sourced list-price ranges (CAR-T, gene therapy), and 10 secondary
source estimates. The log axis uses the geometric mean of the bounds, so a point
value charts at its own value and a range at sqrt(low*high).

Hand-checked anchors:
    hospice routine home care days 61 plus = 181.94 per diem (point)
    CAR-T representative = sqrt(400000 * 475000)
    span from ABA (sqrt(15*30) = 21.21) to gene therapy (sqrt(2.125M*4.25M))
        = log10(3,005,203.7 / 21.213) about 5.15 orders of magnitude
"""
import math
import unittest

from rcm_mc.cdd.unit_economics_spine import SPINE, unit_economics_spine


class TestUnitEconomicsSpine(unittest.TestCase):
    def test_row_counts(self):
        m = unit_economics_spine().meta
        self.assertEqual(m["n_rows"], 26)
        self.assertEqual(m["n_estimates"], 10)
        self.assertEqual(m["n_ranges"], 11)

    def test_point_anchor_value(self):
        pts = {p["label"]: p for p in unit_economics_spine().meta["table"]}
        row = pts["Hospice routine home care days 61 plus"]
        self.assertAlmostEqual(row["value"], 181.94, delta=1e-9)
        self.assertFalse(row["is_range"])
        self.assertFalse(row["est_verify"])

    def test_range_uses_geometric_mean(self):
        pts = {p["label"]: p for p in unit_economics_spine().meta["table"]}
        cart = pts["CAR-T cell therapy"]
        self.assertAlmostEqual(cart["value"], math.sqrt(400000.0 * 475000.0), delta=1e-6)
        self.assertTrue(cart["is_range"])

    def test_span_and_log_flag(self):
        ex = unit_economics_spine()
        self.assertGreaterEqual(ex.meta["orders_of_magnitude"], 4.0)
        self.assertIn("log_scale_required", ex.flag_codes())
        self.assertIn("estimates_present", ex.flag_codes())

    def test_points_sorted_ascending(self):
        vals = [p["value"] for p in unit_economics_spine().meta["table"]]
        self.assertEqual(vals, sorted(vals))

    def test_exclude_estimates(self):
        ex = unit_economics_spine(include_estimates=False)
        self.assertEqual(ex.meta["n_rows"], 16)
        self.assertEqual(ex.meta["n_estimates"], 0)
        self.assertNotIn("estimates_present", ex.flag_codes())

    def test_reconciles(self):
        self.assertTrue(unit_economics_spine().reconciled)

    def test_rejects_empty(self):
        with self.assertRaises(ValueError):
            unit_economics_spine(rows=[])

    def test_spine_rows_valid(self):
        for r in SPINE:
            r.validate()
            self.assertLessEqual(r.low, r.high)


if __name__ == "__main__":
    unittest.main()
