"""Tests for the CMS Open Payments (Sunshine Act) ingestion."""
from __future__ import annotations

import os
import tempfile
import unittest


def _record(npi, mfr, amount, nature="Consulting Fee",
            payment_type="general", year=2024,
            specialty="Cardiology"):
    from rcm_mc.data.cms_open_payments import OpenPaymentRecord
    return OpenPaymentRecord(
        npi=npi,
        physician_name="Dr. Test",
        specialty=specialty,
        payment_type=payment_type,
        nature_of_payment=nature,
        manufacturer_name=mfr,
        amount_usd=amount,
        program_year=year,
    )


class TestAggregation(unittest.TestCase):
    def test_total_and_per_category_buckets(self):
        from rcm_mc.data.cms_open_payments import (
            compute_npi_aggregates,
        )
        records = [
            _record("A", "Pfizer", 25_000.0,
                    nature="Consulting Fee"),
            _record("A", "Pfizer", 15_000.0,
                    nature="Speaking Fee"),
            _record("A", "Merck", 800.0, nature="Food and Beverage"),
            _record("A", "Pfizer", 1_200.0, nature="Travel"),
        ]
        agg = compute_npi_aggregates(records)["A"]
        self.assertEqual(agg.n_payments, 4)
        self.assertAlmostEqual(
            agg.total_payment_usd, 42_000.0, places=2)
        self.assertAlmostEqual(
            agg.consulting_payment_usd, 25_000.0, places=2)
        self.assertAlmostEqual(
            agg.speaker_payment_usd, 15_000.0, places=2)
        self.assertAlmostEqual(
            agg.meals_travel_usd, 2_000.0, places=2)
        self.assertEqual(agg.top_manufacturer, "Pfizer")
        self.assertAlmostEqual(
            agg.top_manufacturer_share,
            41_200 / 42_000, places=3)
        # Below the $50K consulting threshold and total $250K → no flag
        self.assertFalse(agg.conflict_flag)

    def test_consulting_threshold_fires_flag(self):
        from rcm_mc.data.cms_open_payments import (
            compute_npi_aggregates,
        )
        records = [
            _record("A", "Pfizer", 75_000.0,
                    nature="Consulting Fee"),
        ]
        agg = compute_npi_aggregates(records)["A"]
        self.assertTrue(agg.conflict_flag)
        self.assertTrue(any("Consulting" in r
                            for r in agg.conflict_reasons))

    def test_total_threshold_fires_flag(self):
        from rcm_mc.data.cms_open_payments import (
            compute_npi_aggregates,
        )
        records = [
            _record("A", "Pfizer", 30_000.0,
                    nature="Consulting Fee"),
            _record("A", "Merck", 30_000.0,
                    nature="Speaking Fee"),
            _record("A", "Lilly", 200_000.0,
                    nature="Food and Beverage"),
        ]
        agg = compute_npi_aggregates(records)["A"]
        self.assertTrue(agg.conflict_flag)
        self.assertTrue(any("Total industry" in r
                            for r in agg.conflict_reasons))

    def test_ownership_threshold_fires_flag(self):
        from rcm_mc.data.cms_open_payments import (
            compute_npi_aggregates,
        )
        records = [
            _record("A", "DeviceCo", 200_000.0,
                    nature="Stock or stock option",
                    payment_type="ownership"),
        ]
        agg = compute_npi_aggregates(records)["A"]
        self.assertTrue(agg.conflict_flag)
        self.assertAlmostEqual(
            agg.ownership_value_usd, 200_000.0, places=2)

    def test_single_manufacturer_concentration(self):
        from rcm_mc.data.cms_open_payments import (
            compute_npi_aggregates,
        )
        # 95% of the partner's $60K total comes from one mfr —
        # alignment risk
        records = [
            _record("A", "Pfizer", 57_000.0,
                    nature="Consulting Fee"),
            _record("A", "Merck", 3_000.0,
                    nature="Food and Beverage"),
        ]
        agg = compute_npi_aggregates(records)["A"]
        self.assertTrue(any("concentration" in r
                            for r in agg.conflict_reasons))

    def test_below_thresholds_no_flag(self):
        from rcm_mc.data.cms_open_payments import (
            compute_npi_aggregates,
        )
        records = [
            _record("A", "Pfizer", 1_000.0,
                    nature="Food and Beverage"),
            _record("A", "Merck", 500.0,
                    nature="Travel"),
        ]
        agg = compute_npi_aggregates(records)["A"]
        self.assertFalse(agg.conflict_flag)


class TestStoreRoundTrip(unittest.TestCase):
    def test_insert_and_lookup(self):
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.data.cms_open_payments import (
            compute_npi_aggregates, load_npi_aggregates,
            get_payments_for_npi, list_top_recipients,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PortfolioStore(db)
            store.init_db()
            agg = compute_npi_aggregates([
                _record("HIGH", "Pfizer", 80_000.0,
                        nature="Consulting Fee"),
                _record("MED", "Pfizer", 30_000.0,
                        nature="Consulting Fee"),
                _record("LOW", "Pfizer", 500.0,
                        nature="Food and Beverage"),
            ])
            n = load_npi_aggregates(store, agg)
            self.assertEqual(n, 3)

            # Lookup HIGH
            row = get_payments_for_npi(store, "HIGH")
            self.assertEqual(row["npi"], "HIGH")
            self.assertTrue(row["conflict_flag"])

            # Top 2 recipients ordered by total descending
            top = list_top_recipients(store, limit=2)
            self.assertEqual(len(top), 2)
            self.assertEqual(top[0]["npi"], "HIGH")
            self.assertEqual(top[1]["npi"], "MED")
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
