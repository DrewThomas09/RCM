"""Tests for the CMS Part B + Part D utilization loaders."""
from __future__ import annotations

import os
import tempfile
import unittest


# ── Part B ──────────────────────────────────────────────────────

class TestPartB(unittest.TestCase):
    def test_metrics_aggregate_correctly(self):
        from rcm_mc.data.cms_part_b import (
            PartBRecord, compute_part_b_provider_metrics,
        )
        records = [
            # NPI A — orthopedist; 27447 (knee replacement) heavy
            PartBRecord(
                npi="A", hcpcs_code="27447",
                hcpcs_description="TKA",
                n_services=80,
                avg_medicare_payment=1200.0,
                avg_medicare_allowed=1500.0,
                provider_specialty="Orthopedic Surgery"),
            PartBRecord(
                npi="A", hcpcs_code="27130",
                hcpcs_description="THA",
                n_services=20,
                avg_medicare_payment=1300.0,
                avg_medicare_allowed=1600.0,
                provider_specialty="Orthopedic Surgery"),
            # NPI B — generalist
            PartBRecord(
                npi="B", hcpcs_code="99213",
                n_services=300,
                avg_medicare_payment=80.0,
                avg_medicare_allowed=100.0,
                provider_specialty="Internal Medicine"),
            PartBRecord(
                npi="B", hcpcs_code="99214",
                n_services=200,
                avg_medicare_payment=110.0,
                avg_medicare_allowed=140.0,
                provider_specialty="Internal Medicine"),
            PartBRecord(
                npi="B", hcpcs_code="99215",
                n_services=100,
                avg_medicare_payment=140.0,
                avg_medicare_allowed=180.0,
                provider_specialty="Internal Medicine"),
        ]
        metrics = compute_part_b_provider_metrics(records)
        self.assertEqual(len(metrics), 2)

        # NPI A — concentrated (80/100 = 80% on top procedure)
        a = metrics["A"]
        self.assertEqual(a.total_services_billed, 100)
        self.assertEqual(a.top_hcpcs_code, "27447")
        self.assertEqual(a.top_hcpcs_share, 0.80)
        # Herfindahl: 0.80^2 + 0.20^2 = 0.68
        self.assertAlmostEqual(
            a.procedure_concentration, 0.68, places=2)
        # Total payment: 80*1200 + 20*1300 = 96000 + 26000 = 122000
        self.assertAlmostEqual(
            a.total_medicare_payment_mm, 0.122, places=3)

        # NPI B — diversified
        b = metrics["B"]
        self.assertEqual(b.total_services_billed, 600)
        # Herfindahl: 0.5^2 + 0.333^2 + 0.166^2 ≈ 0.389
        self.assertLess(b.procedure_concentration,
                        a.procedure_concentration)

    def test_skip_zero_service_rows(self):
        from rcm_mc.data.cms_part_b import (
            PartBRecord, compute_part_b_provider_metrics,
        )
        records = [
            PartBRecord(npi="X", hcpcs_code="99213",
                        n_services=0,
                        avg_medicare_payment=80.0),
            PartBRecord(npi="X", hcpcs_code="99214",
                        n_services=None,
                        avg_medicare_payment=110.0),
        ]
        metrics = compute_part_b_provider_metrics(records)
        self.assertEqual(len(metrics), 0)

    def test_round_trip_through_store(self):
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.data.cms_part_b import (
            PartBRecord, compute_part_b_provider_metrics,
            load_part_b_metrics, get_part_b_metrics,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PortfolioStore(db)
            store.init_db()
            metrics = compute_part_b_provider_metrics([
                PartBRecord(npi="N1", hcpcs_code="99213",
                            n_services=100,
                            avg_medicare_payment=80.0,
                            provider_specialty="IM"),
            ])
            n = load_part_b_metrics(store, metrics)
            self.assertEqual(n, 1)
            row = get_part_b_metrics(store, "N1")
            self.assertEqual(row["specialty"], "IM")
            self.assertEqual(row["total_services_billed"], 100)
        finally:
            tmp.cleanup()


# ── Part D ──────────────────────────────────────────────────────

class TestPartD(unittest.TestCase):
    def test_metrics_aggregate_correctly(self):
        from rcm_mc.data.cms_part_d import (
            PartDRecord, compute_part_d_metrics,
        )
        records = [
            # NPI A — pain specialist, heavy oxycodone
            PartDRecord(
                npi="A", drug_name="Oxycodone",
                drug_generic_name="oxycodone",
                n_claims=120,
                total_drug_cost=24000.0),
            PartDRecord(
                npi="A", drug_name="Hydrocodone",
                drug_generic_name="hydrocodone",
                n_claims=80,
                total_drug_cost=12000.0),
            PartDRecord(
                npi="A", drug_name="Lipitor",
                drug_generic_name="atorvastatin",
                n_claims=20,
                total_drug_cost=2000.0),
            # NPI B — primary care, no opioid concentration
            PartDRecord(
                npi="B", drug_name="Lisinopril",
                drug_generic_name="lisinopril",
                n_claims=300,
                total_drug_cost=3000.0),
            PartDRecord(
                npi="B", drug_name="Atorvastatin",
                drug_generic_name="atorvastatin",
                n_claims=200,
                total_drug_cost=2400.0),
        ]
        metrics = compute_part_d_metrics(records)
        # NPI A — opioid share = (120 + 80) / 220 = 90.9%
        a = metrics["A"]
        self.assertGreater(a.opioid_claim_share, 0.85)
        self.assertTrue(a.opioid_prescriber_flag)
        # NPI B — no opioids, flag off
        b = metrics["B"]
        self.assertEqual(b.opioid_claim_share, 0.0)
        self.assertFalse(b.opioid_prescriber_flag)

    def test_brand_vs_generic_share(self):
        from rcm_mc.data.cms_part_d import (
            PartDRecord, compute_part_d_metrics,
        )
        records = [
            # Brand: drug_name differs from generic_name
            PartDRecord(npi="X", drug_name="Lipitor",
                        drug_generic_name="atorvastatin",
                        n_claims=50,
                        total_drug_cost=10000.0),
            PartDRecord(npi="X",
                        drug_name="atorvastatin",
                        drug_generic_name="atorvastatin",
                        n_claims=50,
                        total_drug_cost=500.0),
        ]
        metrics = compute_part_d_metrics(records)
        x = metrics["X"]
        self.assertEqual(x.total_claims_filled, 100)
        # 50 brand / 100 total = 0.50
        self.assertAlmostEqual(x.brand_share, 0.50, places=2)

    def test_round_trip_through_store(self):
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.data.cms_part_d import (
            PartDRecord, compute_part_d_metrics,
            load_part_d_metrics, get_part_d_metrics,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PortfolioStore(db)
            store.init_db()
            metrics = compute_part_d_metrics([
                PartDRecord(npi="N1",
                            drug_name="Oxycodone",
                            drug_generic_name="oxycodone",
                            n_claims=100,
                            total_drug_cost=20000.0,
                            provider_specialty="Pain Mgmt"),
            ])
            load_part_d_metrics(store, metrics)
            row = get_part_d_metrics(store, "N1")
            self.assertEqual(row["specialty"], "Pain Mgmt")
            self.assertTrue(row["opioid_prescriber_flag"])
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
