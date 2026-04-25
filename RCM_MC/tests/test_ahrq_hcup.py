"""Tests for AHRQ HCUP discharge ingestion."""
from __future__ import annotations

import csv
import os
import tempfile
import unittest
from pathlib import Path


def _write_csv(path: Path, fieldnames, rows):
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


class TestNormalizers(unittest.TestCase):
    def test_region(self):
        from rcm_mc.data.ahrq_hcup import _normalize_region
        self.assertEqual(_normalize_region("Northeast"),
                         "northeast")
        self.assertEqual(_normalize_region("North Central"),
                         "midwest")
        self.assertEqual(_normalize_region("Midwest"),
                         "midwest")
        self.assertEqual(_normalize_region("South"), "south")
        self.assertEqual(_normalize_region("West"), "west")
        self.assertEqual(_normalize_region(""), "national")
        self.assertEqual(_normalize_region("US"), "national")
        self.assertEqual(_normalize_region("All Regions"),
                         "national")

    def test_payer(self):
        from rcm_mc.data.ahrq_hcup import _normalize_payer
        self.assertEqual(_normalize_payer("Medicare"),
                         "medicare")
        self.assertEqual(_normalize_payer("Medicaid"),
                         "medicaid")
        self.assertEqual(_normalize_payer(
            "Private Insurance"), "private")
        self.assertEqual(_normalize_payer("Commercial"),
                         "private")
        self.assertEqual(_normalize_payer("Self-Pay"),
                         "self_pay")
        self.assertEqual(_normalize_payer("Uninsured"),
                         "self_pay")
        self.assertEqual(_normalize_payer("All Payers"),
                         "all")
        self.assertEqual(_normalize_payer(""), "all")

    def test_age_group(self):
        from rcm_mc.data.ahrq_hcup import _normalize_age_group
        self.assertEqual(_normalize_age_group("0-17"), "0-17")
        self.assertEqual(_normalize_age_group("18-44"),
                         "18-44")
        self.assertEqual(_normalize_age_group("65-84"),
                         "65-84")
        self.assertEqual(_normalize_age_group("85+"), "85+")
        self.assertEqual(_normalize_age_group("All Ages"),
                         "all")

    def test_clinical_system(self):
        from rcm_mc.data.ahrq_hcup import (
            _normalize_clinical_system,
        )
        self.assertEqual(_normalize_clinical_system("DRG"),
                         "drg")
        self.assertEqual(_normalize_clinical_system(
            "MS-DRG"), "drg")
        self.assertEqual(_normalize_clinical_system(
            "CCS-DX"), "ccs_dx")
        self.assertEqual(_normalize_clinical_system(
            "CCS Diagnosis"), "ccs_dx")
        self.assertEqual(_normalize_clinical_system(
            "CCS-PR"), "ccs_pr")
        self.assertEqual(_normalize_clinical_system(
            "ICD-10-CM"), "icd10cm")
        self.assertEqual(_normalize_clinical_system(
            "ICD-10-PCS"), "icd10pcs")


class TestHCUPParser(unittest.TestCase):
    def test_hcupnet_friendly_columns(self):
        from rcm_mc.data.ahrq_hcup import parse_hcup_csv
        tmp = tempfile.TemporaryDirectory()
        try:
            csv_path = Path(tmp.name) / "hcup.csv"
            _write_csv(csv_path, [
                "DRG", "DRG Description",
                "Census Region", "Age Group",
                "Primary Payer",
                "Total Discharges", "Mean LOS",
                "Mean Charges", "In-Hospital Mortality",
            ], [{
                "DRG": "470",
                "DRG Description":
                    "Major hip/knee w/o MCC",
                "Census Region": "South",
                "Age Group": "65-84",
                "Primary Payer": "Medicare",
                "Total Discharges": "180000",
                "Mean LOS": "2.4",
                "Mean Charges": "$58,200",
                "In-Hospital Mortality": "0.18%",
            }])
            recs = list(parse_hcup_csv(
                csv_path, year=2023, source_db="NIS"))
            self.assertEqual(len(recs), 1)
            r = recs[0]
            self.assertEqual(r.clinical_code, "470")
            self.assertEqual(r.clinical_system, "drg")
            self.assertEqual(r.region, "south")
            self.assertEqual(r.age_group, "65-84")
            self.assertEqual(r.payer, "medicare")
            self.assertEqual(r.n_discharges, 180000)
            self.assertAlmostEqual(r.mean_los, 2.4)
            self.assertAlmostEqual(r.mean_charges, 58200.0)
            self.assertAlmostEqual(r.mortality_pct, 0.18)
            self.assertEqual(r.source_db, "NIS")
        finally:
            tmp.cleanup()

    def test_raw_nis_column_aliases(self):
        """NIS public-use file uses HOSPREGION / PAY1 / TOTCHG."""
        from rcm_mc.data.ahrq_hcup import parse_hcup_csv
        tmp = tempfile.TemporaryDirectory()
        try:
            csv_path = Path(tmp.name) / "nis.csv"
            _write_csv(csv_path, [
                "DRG", "HOSPREGION", "AGE_GROUP", "PAY1",
                "DISCWT", "LOS", "TOTCHG",
            ], [{
                "DRG": "871",
                "HOSPREGION": "Northeast",
                "AGE_GROUP": "85+",
                "PAY1": "Private Insurance",
                "DISCWT": "12500",
                "LOS": "5.8",
                "TOTCHG": "82500",
            }])
            recs = list(parse_hcup_csv(
                csv_path, year=2023, source_db="NIS"))
            self.assertEqual(len(recs), 1)
            r = recs[0]
            self.assertEqual(r.region, "northeast")
            self.assertEqual(r.age_group, "85+")
            self.assertEqual(r.payer, "private")
        finally:
            tmp.cleanup()

    def test_suppressed_cells(self):
        from rcm_mc.data.ahrq_hcup import parse_hcup_csv
        tmp = tempfile.TemporaryDirectory()
        try:
            csv_path = Path(tmp.name) / "hcup.csv"
            _write_csv(csv_path, [
                "DRG", "Total Discharges", "Mean LOS",
            ], [{
                "DRG": "470",
                "Total Discharges": "Suppressed",
                "Mean LOS": ".",
            }])
            recs = list(parse_hcup_csv(csv_path, year=2023))
            self.assertIsNone(recs[0].n_discharges)
            self.assertIsNone(recs[0].mean_los)
        finally:
            tmp.cleanup()

    def test_blank_code_skipped(self):
        from rcm_mc.data.ahrq_hcup import parse_hcup_csv
        tmp = tempfile.TemporaryDirectory()
        try:
            csv_path = Path(tmp.name) / "hcup.csv"
            _write_csv(csv_path, [
                "DRG", "Total Discharges",
            ], [
                {"DRG": "", "Total Discharges": "100"},
                {"DRG": "470", "Total Discharges": "180000"},
            ])
            recs = list(parse_hcup_csv(csv_path, year=2023))
            self.assertEqual(len(recs), 1)
        finally:
            tmp.cleanup()


class TestRoundTrip(unittest.TestCase):
    def test_load_lookup(self):
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.data.ahrq_hcup import (
            HCUPDischargeRecord,
            load_hcup_discharges,
            get_hcup_metrics,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PortfolioStore(db)
            store.init_db()
            recs = [
                HCUPDischargeRecord(
                    clinical_code="470",
                    clinical_system="drg",
                    region="south", age_group="all",
                    payer="all", year=2023,
                    n_discharges=180000, mean_los=2.4),
                HCUPDischargeRecord(
                    clinical_code="470",
                    clinical_system="drg",
                    region="northeast", age_group="all",
                    payer="all", year=2023,
                    n_discharges=85000, mean_los=2.8),
            ]
            n = load_hcup_discharges(store, recs)
            self.assertEqual(n, 2)

            rows = get_hcup_metrics(store, "470")
            self.assertEqual(len(rows), 2)

            south = get_hcup_metrics(
                store, "470", region="south")
            self.assertEqual(len(south), 1)
            self.assertEqual(south[0]["n_discharges"], 180000)
        finally:
            tmp.cleanup()


class TestRegionalVariation(unittest.TestCase):
    def test_low_variation(self):
        """All regions roughly equal → CoV near 0."""
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.data.ahrq_hcup import (
            HCUPDischargeRecord,
            load_hcup_discharges,
            compute_regional_variation_index,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PortfolioStore(db)
            store.init_db()
            load_hcup_discharges(store, [
                HCUPDischargeRecord(
                    clinical_code="100",
                    clinical_system="drg",
                    region=r, age_group="all",
                    payer="all", year=2023,
                    n_discharges=100000)
                for r in
                ("northeast", "midwest", "south", "west")
            ])
            cov = compute_regional_variation_index(
                store, "100")
            self.assertAlmostEqual(cov, 0.0, places=2)
        finally:
            tmp.cleanup()

    def test_high_variation(self):
        """Site-of-service shift signal: wide regional spread."""
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.data.ahrq_hcup import (
            HCUPDischargeRecord,
            load_hcup_discharges,
            compute_regional_variation_index,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PortfolioStore(db)
            store.init_db()
            load_hcup_discharges(store, [
                HCUPDischargeRecord(
                    clinical_code="200",
                    clinical_system="drg",
                    region="northeast", age_group="all",
                    payer="all", year=2023,
                    n_discharges=20000),
                HCUPDischargeRecord(
                    clinical_code="200",
                    clinical_system="drg",
                    region="midwest", age_group="all",
                    payer="all", year=2023,
                    n_discharges=50000),
                HCUPDischargeRecord(
                    clinical_code="200",
                    clinical_system="drg",
                    region="south", age_group="all",
                    payer="all", year=2023,
                    n_discharges=180000),
                HCUPDischargeRecord(
                    clinical_code="200",
                    clinical_system="drg",
                    region="west", age_group="all",
                    payer="all", year=2023,
                    n_discharges=40000),
            ])
            cov = compute_regional_variation_index(
                store, "200")
            self.assertGreater(cov, 0.7)
        finally:
            tmp.cleanup()

    def test_unknown_metric_rejected(self):
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.data.ahrq_hcup import (
            compute_regional_variation_index,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PortfolioStore(db)
            store.init_db()
            with self.assertRaises(ValueError):
                compute_regional_variation_index(
                    store, "100", metric="drop_table")
        finally:
            tmp.cleanup()

    def test_insufficient_data_returns_none(self):
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.data.ahrq_hcup import (
            HCUPDischargeRecord,
            load_hcup_discharges,
            compute_regional_variation_index,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PortfolioStore(db)
            store.init_db()
            load_hcup_discharges(store, [
                HCUPDischargeRecord(
                    clinical_code="300",
                    clinical_system="drg",
                    region="south", age_group="all",
                    payer="all", year=2023,
                    n_discharges=100000),
            ])
            self.assertIsNone(
                compute_regional_variation_index(
                    store, "300"))
        finally:
            tmp.cleanup()


class TestVolumeRanking(unittest.TestCase):
    def test_top_volume(self):
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.data.ahrq_hcup import (
            HCUPDischargeRecord,
            load_hcup_discharges,
            list_top_volume_procedures,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PortfolioStore(db)
            store.init_db()
            load_hcup_discharges(store, [
                HCUPDischargeRecord(
                    clinical_code="A",
                    clinical_system="drg",
                    region="national", age_group="all",
                    payer="all", year=2023,
                    n_discharges=500000),
                HCUPDischargeRecord(
                    clinical_code="B",
                    clinical_system="drg",
                    region="national", age_group="all",
                    payer="all", year=2023,
                    n_discharges=200000),
                # Filtered out: not 'all' payer
                HCUPDischargeRecord(
                    clinical_code="C",
                    clinical_system="drg",
                    region="national", age_group="all",
                    payer="medicare", year=2023,
                    n_discharges=900000),
            ])
            top = list_top_volume_procedures(store)
            codes = [r["clinical_code"] for r in top]
            self.assertEqual(codes, ["A", "B"])
        finally:
            tmp.cleanup()


class TestVolumeTrend(unittest.TestCase):
    def test_basic_cagr(self):
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.data.ahrq_hcup import (
            HCUPDischargeRecord,
            load_hcup_discharges,
            compute_volume_trend,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PortfolioStore(db)
            store.init_db()
            # 100K → 161K over 5 years = ~10% CAGR
            load_hcup_discharges(store, [
                HCUPDischargeRecord(
                    clinical_code="500",
                    clinical_system="drg",
                    region="national", age_group="all",
                    payer="all", year=2018,
                    n_discharges=100000),
                HCUPDischargeRecord(
                    clinical_code="500",
                    clinical_system="drg",
                    region="national", age_group="all",
                    payer="all", year=2023,
                    n_discharges=161051),
            ])
            cagr = compute_volume_trend(store, "500")
            self.assertAlmostEqual(cagr, 0.10, places=2)
        finally:
            tmp.cleanup()

    def test_decline_cagr_negative(self):
        """Volume migrating to outpatient → negative CAGR."""
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.data.ahrq_hcup import (
            HCUPDischargeRecord,
            load_hcup_discharges,
            compute_volume_trend,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PortfolioStore(db)
            store.init_db()
            # 200K → 154K over 4 years = ~-6.3%
            load_hcup_discharges(store, [
                HCUPDischargeRecord(
                    clinical_code="600",
                    clinical_system="drg",
                    region="national", age_group="all",
                    payer="all", year=2019,
                    n_discharges=200000),
                HCUPDischargeRecord(
                    clinical_code="600",
                    clinical_system="drg",
                    region="national", age_group="all",
                    payer="all", year=2023,
                    n_discharges=154000),
            ])
            cagr = compute_volume_trend(store, "600")
            self.assertLess(cagr, 0.0)
        finally:
            tmp.cleanup()

    def test_insufficient_history_returns_none(self):
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.data.ahrq_hcup import (
            HCUPDischargeRecord,
            load_hcup_discharges,
            compute_volume_trend,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PortfolioStore(db)
            store.init_db()
            load_hcup_discharges(store, [
                HCUPDischargeRecord(
                    clinical_code="700",
                    clinical_system="drg",
                    region="national", age_group="all",
                    payer="all", year=2023,
                    n_discharges=100000),
            ])
            self.assertIsNone(
                compute_volume_trend(store, "700"))
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
