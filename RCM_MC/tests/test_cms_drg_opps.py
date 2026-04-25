"""Tests for CMS DRG weights + OPPS outpatient ingestion."""
from __future__ import annotations

import os
import tempfile
import unittest


# ── DRG weights + case-mix index ──────────────────────────────

class TestDRGWeights(unittest.TestCase):
    def test_default_lookup(self):
        from rcm_mc.data.cms_drg_weights import get_drg_weight
        # DRG 470 (major hip/knee w/o MCC) ≈ 1.8 weight
        self.assertEqual(get_drg_weight("470"), 1.8)
        # 3-digit-padding from numeric input
        self.assertEqual(get_drg_weight(470), 1.8)
        # Float-encoded int
        self.assertEqual(get_drg_weight("470.0"), 1.8)
        # Unknown → None
        self.assertIsNone(get_drg_weight("99999"))

    def test_load_weights_from_rows(self):
        from rcm_mc.data.cms_drg_weights import load_drg_weights
        weights = load_drg_weights([
            {"drg_code": "100", "relative_weight": 2.5},
            {"MS_DRG_Cd": "200", "Wt": 1.8},
        ])
        self.assertEqual(weights["100"], 2.5)
        self.assertEqual(weights["200"], 1.8)


class TestCaseMixIndex(unittest.TestCase):
    def test_basic_cmi_computation(self):
        from rcm_mc.data.cms_drg_weights import (
            compute_case_mix_index,
        )
        # DRG 470 (1.8 weight) × 100 discharges
        # DRG 871 (1.85 weight) × 50 discharges
        # CMI = (1.8*100 + 1.85*50) / 150 = 273 / 150 = 1.82
        cmi = compute_case_mix_index([
            {"drg_code": "470", "discharges": 100},
            {"drg_code": "871", "discharges": 50},
        ])
        self.assertAlmostEqual(cmi, 1.8167, places=3)

    def test_unknown_drgs_excluded(self):
        from rcm_mc.data.cms_drg_weights import (
            compute_case_mix_index,
        )
        # Mix of known + unknown DRGs — unknown excluded
        cmi = compute_case_mix_index([
            {"drg_code": "470", "discharges": 100},
            {"drg_code": "9999", "discharges": 1000},  # unknown
        ])
        # Only DRG 470 counts → CMI = 1.8
        self.assertAlmostEqual(cmi, 1.8, places=2)

    def test_no_known_drgs_returns_none(self):
        from rcm_mc.data.cms_drg_weights import (
            compute_case_mix_index,
        )
        cmi = compute_case_mix_index([
            {"drg_code": "9999", "discharges": 1000},
        ])
        self.assertIsNone(cmi)

    def test_custom_weights_override(self):
        from rcm_mc.data.cms_drg_weights import (
            compute_case_mix_index,
        )
        cmi = compute_case_mix_index(
            [{"drg_code": "100", "discharges": 50},
             {"drg_code": "200", "discharges": 50}],
            weights={"100": 3.0, "200": 1.0},
        )
        self.assertAlmostEqual(cmi, 2.0, places=3)


# ── OPPS outpatient ──────────────────────────────────────────

class TestOPPS(unittest.TestCase):
    def test_metrics_aggregate(self):
        from rcm_mc.data.cms_opps_outpatient import (
            OPPSRecord, compute_opps_metrics,
        )
        records = [
            OPPSRecord(
                ccn="450001", hcpcs_code="70551",
                hcpcs_description="MRI brain",
                total_services=200,
                avg_medicare_payment=500.0,
                is_offcampus=True),
            OPPSRecord(
                ccn="450001", hcpcs_code="71250",
                hcpcs_description="CT chest",
                total_services=150,
                avg_medicare_payment=400.0,
                is_offcampus=False),
            OPPSRecord(
                ccn="450001", hcpcs_code="99213",
                total_services=50,
                avg_medicare_payment=80.0,
                is_offcampus=False),
        ]
        metrics = compute_opps_metrics(records)
        m = metrics["450001"]
        # Total services = 200 + 150 + 50 = 400
        self.assertEqual(m.total_outpatient_services, 400)
        # Top HCPCS = 70551 (200 services)
        self.assertEqual(m.top_hcpcs_code, "70551")
        self.assertAlmostEqual(
            m.top_hcpcs_share, 0.50, places=2)
        # Off-campus share: 200 / 400 = 0.50
        self.assertAlmostEqual(
            m.offcampus_share, 0.50, places=2)
        # Total payment: 200*500 + 150*400 + 50*80 = 164,000
        self.assertAlmostEqual(
            m.total_medicare_outpatient_payment_mm,
            0.164, places=3)

    def test_round_trip_through_store(self):
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.data.cms_opps_outpatient import (
            OPPSRecord, compute_opps_metrics,
            load_opps_metrics, get_opps_metrics,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PortfolioStore(db)
            store.init_db()
            metrics = compute_opps_metrics([
                OPPSRecord(
                    ccn="450001", hcpcs_code="70551",
                    total_services=100,
                    avg_medicare_payment=500.0,
                    is_offcampus=True),
            ])
            n = load_opps_metrics(store, metrics)
            self.assertEqual(n, 1)
            row = get_opps_metrics(store, "450001")
            self.assertEqual(row["top_hcpcs_code"], "70551")
            self.assertAlmostEqual(
                row["offcampus_share"], 1.0, places=2)
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
