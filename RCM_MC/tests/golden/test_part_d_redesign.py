"""Golden test for NEW-29 Part D IRA redesign payer shares.

2025, 10,000 gross brand cost, deductible 590, cap 2,000:
    deductible phase gross 590 (enrollee 100 percent)
    initial-phase gross to cap = (2000 - 590) / 0.25 = 5,640
    catastrophic gross = 10000 - 590 - 5640 = 3,770
    enrollee 590 + 0.25*5640 = 2,000 (at cap)
    plan 0.65*5640 + 0.60*3770 = 3666 + 2262 = 5,928
    manufacturer 0.10*5640 + 0.20*3770 = 564 + 754 = 1,318
    Medicare 0.20*3770 = 754; total 10,000
"""
import unittest

from rcm_mc.cdd.part_d_redesign import allocate_part_d, part_d_redesign


class TestPartDRedesign(unittest.TestCase):
    def test_2025_allocation(self):
        a = allocate_part_d(10000.0, year=2025)
        p = a["payers"]
        self.assertAlmostEqual(p["enrollee"], 2000.0, delta=1e-9)
        self.assertAlmostEqual(p["plan"], 5928.0, delta=1e-9)
        self.assertAlmostEqual(p["manufacturer"], 1318.0, delta=1e-9)
        self.assertAlmostEqual(p["medicare"], 754.0, delta=1e-9)

    def test_phase_gross(self):
        ph = allocate_part_d(10000.0, year=2025)["phases"]
        self.assertAlmostEqual(ph["deductible"]["gross"], 590.0, delta=1e-9)
        self.assertAlmostEqual(ph["initial"]["gross"], 5640.0, delta=1e-9)
        self.assertAlmostEqual(ph["catastrophic"]["gross"], 3770.0, delta=1e-9)

    def test_cap_reached_and_oop(self):
        a = allocate_part_d(10000.0, year=2025)
        self.assertTrue(a["cap_reached"])
        self.assertAlmostEqual(a["enrollee_oop"], 2000.0, delta=1e-9)

    def test_2026_cap(self):
        a = allocate_part_d(10000.0, year=2026)
        self.assertAlmostEqual(a["oop_cap"], 2100.0, delta=1e-9)
        self.assertAlmostEqual(a["payers"]["enrollee"], 2100.0, delta=1e-9)
        self.assertAlmostEqual(a["payers"]["medicare"], 689.0, delta=1e-9)

    def test_below_deductible_no_cap(self):
        a = allocate_part_d(400.0, year=2025)
        self.assertFalse(a["cap_reached"])
        self.assertAlmostEqual(a["payers"]["enrollee"], 400.0, delta=1e-9)
        self.assertAlmostEqual(a["payers"]["plan"], 0.0, delta=1e-9)

    def test_reconciles_and_flags(self):
        ex = part_d_redesign(10000.0, year=2025, source="Golden", vintage="2025")
        self.assertTrue(ex.reconciled)
        self.assertIn("oop_cap_reached", ex.flag_codes())
        self.assertIn("catastrophic_reinsurance_shift", ex.flag_codes())

    def test_partner_hides_oop_detail(self):
        ex = part_d_redesign(10000.0, year=2025, source="Golden", vintage="2025")
        partner = {s["name"] for s in ex.render(internal_mode=False)["series"]}
        self.assertNotIn("Enrollee out-of-pocket vs cap", partner)

    def test_negative_raises(self):
        with self.assertRaises(ValueError):
            allocate_part_d(-1.0, year=2025)


if __name__ == "__main__":
    unittest.main()
