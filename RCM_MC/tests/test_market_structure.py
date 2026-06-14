"""Two-source market-structure reconciliation (NPPES supply × Census CBP).

Pure over already-fetched inputs — no network. Covers: both sides present,
each side missing, CBP suppression handling, and the no-divide-by-zero ratio.
"""
from __future__ import annotations

import unittest

from rcm_mc.data_public import market_structure as ms
from rcm_mc.data_public import nucc_taxonomy as nt


def _cbp(*estabs):
    return [{"establishments": e} for e in estabs]


class ReconcileTests(unittest.TestCase):
    def test_both_sides_present_computes_ratio(self):
        out = ms.reconcile_vertical(
            "home_health",
            nppes_supply={"live": True, "count": 120},
            cbp_rows=_cbp(40, 20))
        self.assertEqual(out["providers"], 120)
        self.assertEqual(out["establishments"], 60)
        self.assertEqual(out["providers_per_estab"], 2.0)
        self.assertEqual(out["naics"], "621610")

    def test_missing_nppes_leaves_providers_none(self):
        out = ms.reconcile_vertical(
            "snf", nppes_supply={"live": False}, cbp_rows=_cbp(10))
        self.assertIsNone(out["providers"])
        self.assertEqual(out["establishments"], 10)
        self.assertIsNone(out["providers_per_estab"])

    def test_missing_cbp_leaves_establishments_none(self):
        out = ms.reconcile_vertical(
            "snf", nppes_supply={"live": True, "count": 5}, cbp_rows=[])
        self.assertEqual(out["providers"], 5)
        self.assertIsNone(out["establishments"])
        self.assertIsNone(out["providers_per_estab"])

    def test_all_suppressed_cbp_is_none_not_zero(self):
        out = ms.reconcile_vertical(
            "dialysis",
            nppes_supply={"live": True, "count": 8},
            cbp_rows=[{"establishments": None}, {"establishments": None}])
        self.assertIsNone(out["establishments"])
        self.assertIsNone(out["providers_per_estab"])  # no divide by None

    def test_zero_establishments_no_divide_by_zero(self):
        out = ms.reconcile_vertical(
            "dialysis",
            nppes_supply={"live": True, "count": 8},
            cbp_rows=_cbp(0))
        self.assertEqual(out["establishments"], 0)
        self.assertIsNone(out["providers_per_estab"])

    def test_unmapped_vertical_has_empty_naics(self):
        out = ms.reconcile_vertical("hospice",
                                    nppes_supply={"live": True, "count": 3})
        self.assertEqual(out["naics"], "")
        self.assertEqual(out["providers"], 3)


class NaicsMapTests(unittest.TestCase):
    def test_naics_for_known_and_unknown(self):
        self.assertEqual(nt.naics_for("dental"), "621210")
        self.assertEqual(nt.naics_for("hospice"), "")        # intentional gap
        self.assertEqual(nt.naics_for("not_a_vertical"), "")


if __name__ == "__main__":
    unittest.main()
