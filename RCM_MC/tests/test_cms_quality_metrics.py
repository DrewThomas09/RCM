"""Tests for the CMS Quality Metrics ingestion."""
from __future__ import annotations

import os
import tempfile
import unittest


class TestReadmissionLoader(unittest.TestCase):
    def setUp(self):
        from rcm_mc.portfolio.store import PortfolioStore
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "p.db")
        self.store = PortfolioStore(self.db)
        self.store.init_db()

    def tearDown(self):
        self.tmp.cleanup()

    def test_load_readmission_rates(self):
        from rcm_mc.data.cms_quality_metrics import (
            load_readmission_rates,
        )
        rows = [
            {"ccn": "450001", "metric_id": "READM_30_AMI",
             "value": 1.05, "denominator": 250,
             "period": "2023-2025"},
            {"ccn": "450001", "metric_id": "READM_30_HF",
             "value": 0.92, "denominator": 410,
             "period": "2023-2025"},
        ]
        n = load_readmission_rates(self.store, rows)
        self.assertEqual(n, 2)

    def test_handles_not_available_values(self):
        from rcm_mc.data.cms_quality_metrics import (
            load_readmission_rates, get_quality_features,
        )
        rows = [
            {"ccn": "450001", "metric_id": "READM_30_AMI",
             "value": "Not Available"},
            {"ccn": "450001", "metric_id": "READM_30_HF",
             "value": 0.92},
        ]
        load_readmission_rates(self.store, rows)
        feat = get_quality_features(self.store, "450001")
        # Not Available filtered out
        self.assertNotIn("READM_30_AMI", feat)
        self.assertIn("READM_30_HF", feat)


class TestMortalityLoader(unittest.TestCase):
    def test_load_with_default_label_lookup(self):
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.data.cms_quality_metrics import (
            load_mortality_rates,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PortfolioStore(db)
            store.init_db()
            n = load_mortality_rates(store, [
                {"ccn": "450001",
                 "metric_id": "MORT_30_HF",
                 "value": 0.118},
            ])
            self.assertEqual(n, 1)
            with store.connect() as con:
                row = con.execute(
                    "SELECT metric_label FROM "
                    "cms_quality_metrics "
                    "WHERE metric_id='MORT_30_HF'"
                ).fetchone()
            # Default label populated from the lookup
            self.assertIn("Heart failure", row["metric_label"])
        finally:
            tmp.cleanup()


class TestHCAHPSLoader(unittest.TestCase):
    def test_load_top_box_scores(self):
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.data.cms_quality_metrics import (
            load_hcahps_scores, get_quality_features,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PortfolioStore(db)
            store.init_db()
            rows = [
                {"ccn": "450001",
                 "metric_id": "HCAHPS_OVERALL",
                 "value": 0.72},
                {"ccn": "450001",
                 "metric_id": "HCAHPS_RECOMMEND",
                 "value": 0.78},
                {"ccn": "450001",
                 "metric_id": "HCAHPS_NURSE",
                 "value": 0.81},
            ]
            n = load_hcahps_scores(store, rows)
            self.assertEqual(n, 3)
            feat = get_quality_features(store, "450001")
            self.assertEqual(len(feat), 3)
        finally:
            tmp.cleanup()


class TestHAILoader(unittest.TestCase):
    def test_load_hai_rates(self):
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.data.cms_quality_metrics import (
            load_hai_rates, get_quality_summary,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PortfolioStore(db)
            store.init_db()
            rows = [
                {"ccn": "450001", "metric_id": "HAI_CAUTI",
                 "value": 0.85},
                {"ccn": "450001", "metric_id": "HAI_CLABSI",
                 "value": 0.62},
                {"ccn": "450001", "metric_id": "HAI_MRSA",
                 "value": 1.10},
            ]
            n = load_hai_rates(store, rows)
            self.assertEqual(n, 3)
            summary = get_quality_summary(store, "450001")
            self.assertEqual(
                summary["by_family"]["hai"]["n_metrics"], 3)
            # 0.85 + 0.62 + 1.10 / 3 ≈ 0.857
            self.assertAlmostEqual(
                summary["by_family"]["hai"]["mean"],
                (0.85 + 0.62 + 1.10) / 3, places=3)
        finally:
            tmp.cleanup()


class TestCrossFamily(unittest.TestCase):
    def test_summary_aggregates_all_families(self):
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.data.cms_quality_metrics import (
            load_readmission_rates, load_mortality_rates,
            load_hcahps_scores, load_hai_rates,
            get_quality_summary,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PortfolioStore(db)
            store.init_db()
            load_readmission_rates(store, [
                {"ccn": "450001", "metric_id": "READM_30_AMI",
                 "value": 1.05}])
            load_mortality_rates(store, [
                {"ccn": "450001", "metric_id": "MORT_30_HF",
                 "value": 0.12}])
            load_hcahps_scores(store, [
                {"ccn": "450001", "metric_id": "HCAHPS_OVERALL",
                 "value": 0.72}])
            load_hai_rates(store, [
                {"ccn": "450001", "metric_id": "HAI_CAUTI",
                 "value": 0.85}])
            summary = get_quality_summary(store, "450001")
            self.assertEqual(
                set(summary["by_family"].keys()),
                {"readmission", "mortality", "hcahps", "hai"})
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
