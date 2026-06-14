"""Golden test for BOLSTER-07 data-ingestion reconciliation.

CCN join fixture:
    HCRIS:       CCN 1,2,3        (3 rows, unique)
    POS:         CCN 1,2,3,4      (4 rows)
    CareCompare: CCN 1,2          (2 rows; CCN 3 is an orphan from HCRIS)
    HCRIS->POS integrity         = 3/3 = 1.0
    HCRIS->CareCompare integrity = 2/3 (CCN 3 orphan)
Suppression: CareCompare CCN 2 has cases=8 (<=11) -> suppressed.
Vintage stamp required on every load.
"""
import unittest

from rcm_mc.cdd.ingestion import (
    apply_suppression,
    ingestion_reconciliation,
    reconcile_join,
)


def _datasets():
    return {
        "HCRIS": {"rows": [{"CCN": "1"}, {"CCN": "2"}, {"CCN": "3"}], "key": "CCN", "vintage": "2023"},
        "POS": {"rows": [{"CCN": "1"}, {"CCN": "2"}, {"CCN": "3"}, {"CCN": "4"}], "key": "CCN", "vintage": "2024Q4"},
        "CareCompare": {"rows": [{"CCN": "1", "cases": 40}, {"CCN": "2", "cases": 8}], "key": "CCN", "vintage": "2024"},
    }


class TestIngestionReconciliation(unittest.TestCase):
    def test_join_integrity(self):
        ds = _datasets()
        full = reconcile_join(ds["HCRIS"]["rows"], ds["POS"]["rows"], "CCN")
        self.assertAlmostEqual(full["join_integrity"], 1.0, delta=1e-9)
        partial = reconcile_join(ds["HCRIS"]["rows"], ds["CareCompare"]["rows"], "CCN")
        self.assertAlmostEqual(partial["join_integrity"], 2.0 / 3.0, delta=1e-9)
        self.assertEqual(partial["orphans_left"], ["3"])

    def test_key_uniqueness_detected(self):
        rows = [{"CCN": "1"}, {"CCN": "1"}]
        res = reconcile_join(rows, rows, "CCN")
        self.assertFalse(res["left_unique"])

    def test_suppression(self):
        ds = _datasets()
        rows, n = apply_suppression(ds["CareCompare"]["rows"], "cases", threshold=11)
        self.assertEqual(n, 1)
        by_ccn = {r["CCN"]: r for r in rows}
        self.assertIsNone(by_ccn["2"]["cases"])
        self.assertTrue(by_ccn["2"]["suppressed"])
        self.assertEqual(by_ccn["1"]["cases"], 40)
        self.assertFalse(by_ccn["1"]["suppressed"])

    def test_full_reconciliation_exhibit(self):
        ds = _datasets()
        ex = ingestion_reconciliation(
            ds, [("HCRIS", "POS", "CCN"), ("HCRIS", "CareCompare", "CCN")],
            suppression=[("CareCompare", "cases")],
            integrity_tolerance=0.5, source="Golden", vintage="2024",
        )
        self.assertIn("join_orphans", ex.flag_codes())
        self.assertIn("cells_suppressed", ex.flag_codes())
        self.assertEqual(ex.meta["suppression"]["CareCompare.cases"], 1)

    def test_missing_vintage_flagged(self):
        ds = _datasets()
        ds["HCRIS"]["vintage"] = ""
        ex = ingestion_reconciliation(ds, [("HCRIS", "POS", "CCN")],
                                      integrity_tolerance=0.0, source="Golden", vintage="2024")
        self.assertIn("missing_vintage", ex.flag_codes())
        self.assertIn("HCRIS", ex.meta["missing_vintage"])

    def test_npi_and_fips_joins(self):
        ds = {
            "NPPES": {"rows": [{"NPI": "a"}, {"NPI": "b"}], "key": "NPI", "vintage": "2026-05"},
            "Physician": {"rows": [{"NPI": "a"}, {"NPI": "b"}], "key": "NPI", "vintage": "2024"},
            "GeoVar": {"rows": [{"FIPS": "06037"}], "key": "FIPS", "vintage": "2022"},
            "MarketSat": {"rows": [{"FIPS": "06037"}], "key": "FIPS", "vintage": "2024"},
        }
        ex = ingestion_reconciliation(
            ds, [("NPPES", "Physician", "NPI"), ("GeoVar", "MarketSat", "FIPS")],
            integrity_tolerance=0.0, source="Golden", vintage="2024",
        )
        # Perfect joins -> reconciles.
        self.assertTrue(ex.reconciled)

    def test_clean_run_reconciles(self):
        ds = {
            "A": {"rows": [{"k": 1}, {"k": 2}], "key": "k", "vintage": "2024"},
            "B": {"rows": [{"k": 1}, {"k": 2}], "key": "k", "vintage": "2024"},
        }
        ex = ingestion_reconciliation(ds, [("A", "B", "k")], integrity_tolerance=0.0,
                                      source="Golden", vintage="2024")
        self.assertTrue(ex.reconciled)


if __name__ == "__main__":
    unittest.main()
