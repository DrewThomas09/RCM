"""Golden test for NEW-23 payer economics.

Four segments, 2024 gross margin per enrollee:
    Medicare Advantage 1655 (2023: 1986, yoy -331)
    Individual 987 (1048)
    Fully-insured group 846 (910)
    Medicaid managed care 608 (753)
Medicare Advantage leads; year-over-year change ties to 2024 minus 2023.
"""
import unittest

from rcm_mc.cdd.payer_economics import payer_economics


class TestPayerEconomics(unittest.TestCase):
    def test_leader_is_ma(self):
        ex = payer_economics()
        self.assertEqual(ex.meta["leader"], "Medicare Advantage")
        self.assertEqual(ex.meta["leader_margin"], 1655.0)
        self.assertIn("highest_margin_segment", ex.flag_codes())

    def test_sorted_descending(self):
        vals = [p["value"] for p in payer_economics().series[0].points]
        self.assertEqual(vals, sorted(vals, reverse=True))
        self.assertEqual(vals, [1655.0, 987.0, 846.0, 608.0])

    def test_yoy_change(self):
        pts = {p["label"]: p for p in payer_economics().series[0].points}
        self.assertAlmostEqual(pts["Medicare Advantage"]["yoy_change"], -331.0, delta=1e-9)
        self.assertAlmostEqual(pts["Medicaid managed care"]["yoy_change"], -145.0, delta=1e-9)

    def test_mlr_series_present(self):
        names = [s.name for s in payer_economics().series]
        self.assertIn("Medical loss ratio percent", names)

    def test_reconciles(self):
        self.assertTrue(payer_economics().reconciled)

    def test_rejects_empty(self):
        with self.assertRaises(ValueError):
            payer_economics([])


if __name__ == "__main__":
    unittest.main()
