"""Tests for State All-Payer Claims Database (APCD) ingestion."""
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


class TestPayerNormalization(unittest.TestCase):
    def test_canonical_buckets(self):
        from rcm_mc.data.state_apcd import _normalize_payer_type
        self.assertEqual(
            _normalize_payer_type("Commercial"), "commercial")
        self.assertEqual(
            _normalize_payer_type("Private Insurance"),
            "commercial")
        self.assertEqual(
            _normalize_payer_type("HMO"), "commercial")
        self.assertEqual(
            _normalize_payer_type("Medicare Advantage"),
            "medicare_advantage")
        self.assertEqual(
            _normalize_payer_type("MA Plan"),
            "medicare_advantage")
        self.assertEqual(
            _normalize_payer_type("Medicaid Managed Care"),
            "medicaid_managed_care")
        self.assertEqual(
            _normalize_payer_type("Medicaid MCO"),
            "medicaid_managed_care")
        self.assertEqual(
            _normalize_payer_type("Medicaid"),
            "medicaid_ffs")
        self.assertEqual(
            _normalize_payer_type("Medicare"),
            "medicare_ffs")
        self.assertEqual(
            _normalize_payer_type(""), "commercial")


class TestAPCDParser(unittest.TestCase):
    def test_co_style_columns(self):
        """CO APCD: 'Procedure Code' + 'Median Allowed'."""
        from rcm_mc.data.state_apcd import parse_apcd_csv
        tmp = tempfile.TemporaryDirectory()
        try:
            csv_path = Path(tmp.name) / "co.csv"
            _write_csv(csv_path, [
                "Procedure Code", "Description",
                "Region", "Payer Type",
                "Number of Claims",
                "P25 Allowed", "Median Allowed",
                "P75 Allowed", "P95 Allowed",
            ], [{
                "Procedure Code": "70551",
                "Description": "MRI brain w/o contrast",
                "Region": "Denver",
                "Payer Type": "Commercial",
                "Number of Claims": "1240",
                "P25 Allowed": "$680.00",
                "Median Allowed": "$1,180.00",
                "P75 Allowed": "$1,820.00",
                "P95 Allowed": "$2,950.00",
            }])
            recs = list(parse_apcd_csv(
                csv_path, state="CO", year=2023))
            self.assertEqual(len(recs), 1)
            r = recs[0]
            self.assertEqual(r.state, "CO")
            self.assertEqual(r.cpt_code, "70551")
            self.assertEqual(r.payer_type, "commercial")
            self.assertEqual(r.region, "Denver")
            self.assertEqual(r.n_claims, 1240)
            self.assertAlmostEqual(r.allowed_p50, 1180.0)
            self.assertAlmostEqual(r.allowed_p95, 2950.0)
        finally:
            tmp.cleanup()

    def test_ma_style_columns(self):
        """MA APCD-style: snake_case with payer_type."""
        from rcm_mc.data.state_apcd import parse_apcd_csv
        tmp = tempfile.TemporaryDirectory()
        try:
            csv_path = Path(tmp.name) / "ma.csv"
            _write_csv(csv_path, [
                "state", "region", "cpt", "year",
                "payer_type", "claim_count",
                "allowed_p25", "allowed_p50",
                "allowed_p75", "allowed_p95",
                "avg_member_oop",
            ], [{
                "state": "MA", "region": "Boston-HSA",
                "cpt": "27447", "year": "2023",
                "payer_type": "Medicare Advantage",
                "claim_count": "85",
                "allowed_p25": "18000",
                "allowed_p50": "22500",
                "allowed_p75": "28000",
                "allowed_p95": "38000",
                "avg_member_oop": "1240",
            }])
            recs = list(parse_apcd_csv(csv_path))
            self.assertEqual(len(recs), 1)
            r = recs[0]
            self.assertEqual(r.payer_type,
                             "medicare_advantage")
            self.assertEqual(r.cpt_code, "27447")
            self.assertAlmostEqual(r.allowed_p50, 22500.0)
            self.assertAlmostEqual(r.avg_member_oop, 1240.0)
        finally:
            tmp.cleanup()

    def test_suppressed_small_cells(self):
        """APCDs suppress cells with <11 claims for privacy."""
        from rcm_mc.data.state_apcd import parse_apcd_csv
        tmp = tempfile.TemporaryDirectory()
        try:
            csv_path = Path(tmp.name) / "apcd.csv"
            _write_csv(csv_path, [
                "state", "cpt_code", "payer_type",
                "n_claims", "allowed_p50",
            ], [{
                "state": "OR", "cpt_code": "99213",
                "payer_type": "Commercial",
                "n_claims": "<11",
                "allowed_p50": "Suppressed",
            }])
            recs = list(parse_apcd_csv(csv_path, year=2023))
            self.assertEqual(len(recs), 1)
            self.assertIsNone(recs[0].n_claims)
            self.assertIsNone(recs[0].allowed_p50)
        finally:
            tmp.cleanup()

    def test_blank_cpt_skipped(self):
        from rcm_mc.data.state_apcd import parse_apcd_csv
        tmp = tempfile.TemporaryDirectory()
        try:
            csv_path = Path(tmp.name) / "apcd.csv"
            _write_csv(csv_path, [
                "state", "cpt_code", "allowed_p50",
            ], [
                {"state": "WA", "cpt_code": "",
                 "allowed_p50": "100"},
                {"state": "WA", "cpt_code": "99213",
                 "allowed_p50": "100"},
            ])
            recs = list(parse_apcd_csv(csv_path, year=2023))
            self.assertEqual(len(recs), 1)
        finally:
            tmp.cleanup()


class TestRoundTrip(unittest.TestCase):
    def test_load_and_lookup(self):
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.data.state_apcd import (
            APCDPriceRecord,
            load_apcd_prices,
            get_apcd_prices_for_cpt,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PortfolioStore(db)
            store.init_db()
            recs = [
                APCDPriceRecord(
                    state="CO", region="Denver",
                    cpt_code="70551",
                    payer_type="commercial", year=2023,
                    n_claims=1240, allowed_p50=1180.0),
                APCDPriceRecord(
                    state="CO", region="Denver",
                    cpt_code="70551",
                    payer_type="medicare_ffs", year=2023,
                    n_claims=2400, allowed_p50=420.0),
                APCDPriceRecord(
                    state="MA", region="Boston",
                    cpt_code="70551",
                    payer_type="commercial", year=2023,
                    n_claims=890, allowed_p50=1280.0),
            ]
            n = load_apcd_prices(store, recs)
            self.assertEqual(n, 3)

            # All matching
            rows = get_apcd_prices_for_cpt(store, "70551")
            self.assertEqual(len(rows), 3)

            # Filter by state
            co = get_apcd_prices_for_cpt(
                store, "70551", state="CO")
            self.assertEqual(len(co), 2)

            # Filter by state + payer
            co_com = get_apcd_prices_for_cpt(
                store, "70551",
                state="CO", payer_type="commercial")
            self.assertEqual(len(co_com), 1)
            self.assertAlmostEqual(
                co_com[0]["allowed_p50"], 1180.0)
        finally:
            tmp.cleanup()

    def test_idempotent_upsert(self):
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.data.state_apcd import (
            APCDPriceRecord,
            load_apcd_prices,
            get_apcd_prices_for_cpt,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PortfolioStore(db)
            store.init_db()
            base = APCDPriceRecord(
                state="CO", region="Denver",
                cpt_code="70551",
                payer_type="commercial", year=2023,
                n_claims=1240, allowed_p50=1180.0)
            load_apcd_prices(store, [base])
            # Re-load with revised number — should overwrite
            base.allowed_p50 = 1200.0
            load_apcd_prices(store, [base])
            rows = get_apcd_prices_for_cpt(store, "70551")
            self.assertEqual(len(rows), 1)
            self.assertAlmostEqual(rows[0]["allowed_p50"],
                                   1200.0)
        finally:
            tmp.cleanup()


class TestCommercialMedicareRatio(unittest.TestCase):
    def test_basic_ratio(self):
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.data.state_apcd import (
            APCDPriceRecord,
            load_apcd_prices,
            compute_commercial_medicare_ratio,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PortfolioStore(db)
            store.init_db()
            load_apcd_prices(store, [
                APCDPriceRecord(
                    state="CO", region="Denver",
                    cpt_code="70551",
                    payer_type="commercial", year=2023,
                    n_claims=1000, allowed_p50=1200.0),
                APCDPriceRecord(
                    state="CO", region="Denver",
                    cpt_code="70551",
                    payer_type="medicare_ffs", year=2023,
                    n_claims=1000, allowed_p50=400.0),
            ])
            ratio = compute_commercial_medicare_ratio(
                store, "70551", state="CO")
            self.assertAlmostEqual(ratio, 3.0, places=2)
        finally:
            tmp.cleanup()

    def test_volume_weighted_across_regions(self):
        """Multi-region ratios should be claim-volume-weighted,
        not simple-averaged."""
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.data.state_apcd import (
            APCDPriceRecord,
            load_apcd_prices,
            compute_commercial_medicare_ratio,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PortfolioStore(db)
            store.init_db()
            load_apcd_prices(store, [
                # Denver: 1000 claims @ $1500 commercial,
                # 1000 @ $500 medicare → 3.0x
                APCDPriceRecord(
                    state="CO", region="Denver",
                    cpt_code="X", payer_type="commercial",
                    year=2023, n_claims=1000,
                    allowed_p50=1500.0),
                APCDPriceRecord(
                    state="CO", region="Denver",
                    cpt_code="X", payer_type="medicare_ffs",
                    year=2023, n_claims=1000,
                    allowed_p50=500.0),
                # Pueblo: 100 claims @ $1000 commercial,
                # 100 @ $400 medicare → 2.5x
                APCDPriceRecord(
                    state="CO", region="Pueblo",
                    cpt_code="X", payer_type="commercial",
                    year=2023, n_claims=100,
                    allowed_p50=1000.0),
                APCDPriceRecord(
                    state="CO", region="Pueblo",
                    cpt_code="X", payer_type="medicare_ffs",
                    year=2023, n_claims=100,
                    allowed_p50=400.0),
            ])
            # Weighted commercial:
            #   (1000*1500 + 100*1000)/1100 = 1454.55
            # Weighted medicare:
            #   (1000*500 + 100*400)/1100   = 490.91
            # Ratio: 1454.55 / 490.91 = 2.963
            ratio = compute_commercial_medicare_ratio(
                store, "X", state="CO")
            self.assertAlmostEqual(ratio, 2.963, places=2)
        finally:
            tmp.cleanup()

    def test_ma_fallback_when_no_medicare_ffs(self):
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.data.state_apcd import (
            APCDPriceRecord,
            load_apcd_prices,
            compute_commercial_medicare_ratio,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PortfolioStore(db)
            store.init_db()
            load_apcd_prices(store, [
                APCDPriceRecord(
                    state="MA", region="Boston",
                    cpt_code="99213",
                    payer_type="commercial", year=2023,
                    n_claims=1000, allowed_p50=120.0),
                APCDPriceRecord(
                    state="MA", region="Boston",
                    cpt_code="99213",
                    payer_type="medicare_advantage",
                    year=2023, n_claims=1000,
                    allowed_p50=80.0),
            ])
            ratio = compute_commercial_medicare_ratio(
                store, "99213", state="MA")
            self.assertAlmostEqual(ratio, 1.5, places=2)
        finally:
            tmp.cleanup()

    def test_missing_side_returns_none(self):
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.data.state_apcd import (
            APCDPriceRecord,
            load_apcd_prices,
            compute_commercial_medicare_ratio,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PortfolioStore(db)
            store.init_db()
            load_apcd_prices(store, [
                APCDPriceRecord(
                    state="CO", region="Denver",
                    cpt_code="9999",
                    payer_type="commercial", year=2023,
                    n_claims=1000, allowed_p50=100.0),
            ])
            self.assertIsNone(
                compute_commercial_medicare_ratio(
                    store, "9999"))
        finally:
            tmp.cleanup()


class TestHighDispersion(unittest.TestCase):
    def test_dispersion_ranking(self):
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.data.state_apcd import (
            APCDPriceRecord,
            load_apcd_prices,
            list_high_dispersion_procedures,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PortfolioStore(db)
            store.init_db()
            load_apcd_prices(store, [
                # Tight distribution: p95/p25 = 1.5
                APCDPriceRecord(
                    state="CO", region="A",
                    cpt_code="A", payer_type="commercial",
                    year=2023, n_claims=200,
                    allowed_p25=100.0, allowed_p95=150.0),
                # Wide: p95/p25 = 6.0
                APCDPriceRecord(
                    state="CO", region="A",
                    cpt_code="B", payer_type="commercial",
                    year=2023, n_claims=200,
                    allowed_p25=100.0, allowed_p95=600.0),
                # Below min_claims threshold — excluded
                APCDPriceRecord(
                    state="CO", region="A",
                    cpt_code="C", payer_type="commercial",
                    year=2023, n_claims=10,
                    allowed_p25=100.0, allowed_p95=2000.0),
            ])
            top = list_high_dispersion_procedures(
                store, state="CO")
            cpts = [r["cpt_code"] for r in top]
            self.assertEqual(cpts, ["B", "A"])
            self.assertAlmostEqual(top[0]["dispersion"], 6.0)
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
