"""Tests for the IRS 990 multi-year trend analytics."""
from __future__ import annotations

import os
import tempfile
import unittest


def _filing(ein, year, name="Memorial",
            revenue=100_000_000, expenses=92_000_000,
            net_assets=50_000_000, exec_comp=4_000_000,
            state="TX", ccn=""):
    from rcm_mc.data.irs990_trends import FilingRecord
    return FilingRecord(
        ein=ein, tax_year=year,
        organization_name=name, state=state, ccn=ccn,
        total_revenue=revenue,
        total_expenses=expenses,
        net_assets_end_of_year=net_assets,
        net_assets_beginning=net_assets * 0.95,
        top5_exec_comp_total=exec_comp,
        program_service_revenue=revenue * 0.92,
        contributions_revenue=revenue * 0.05,
        investment_income=revenue * 0.03,
        employee_count=2500,
        volunteer_count=200,
    )


class TestStorage(unittest.TestCase):
    def setUp(self):
        from rcm_mc.portfolio.store import PortfolioStore
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "p.db")
        self.store = PortfolioStore(self.db)
        self.store.init_db()

    def tearDown(self):
        self.tmp.cleanup()

    def test_store_filing_inserts(self):
        from rcm_mc.data.irs990_trends import store_filing
        ok = store_filing(
            self.store, _filing("123456789", 2023))
        self.assertTrue(ok)

    def test_bulk_store(self):
        from rcm_mc.data.irs990_trends import store_filings_bulk
        n = store_filings_bulk(self.store, [
            _filing("111", 2021),
            _filing("111", 2022),
            _filing("111", 2023),
        ])
        self.assertEqual(n, 3)

    def test_upsert_overwrites(self):
        """Same (ein, tax_year) inserted twice → upsert."""
        from rcm_mc.data.irs990_trends import store_filing
        store_filing(
            self.store,
            _filing("111", 2023, revenue=100_000_000))
        store_filing(
            self.store,
            _filing("111", 2023, revenue=110_000_000))
        with self.store.connect() as con:
            rows = con.execute(
                "SELECT total_revenue FROM irs990_filings "
                "WHERE ein='111'").fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["total_revenue"],
                         110_000_000)


class TestTrendComputation(unittest.TestCase):
    def setUp(self):
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.data.irs990_trends import store_filings_bulk
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "p.db")
        self.store = PortfolioStore(self.db)
        self.store.init_db()
        # Healthy hospital — 8% revenue CAGR, stable margin
        store_filings_bulk(self.store, [
            _filing("111", 2020, revenue=100_000_000,
                    expenses=92_000_000,
                    net_assets=50_000_000,
                    exec_comp=4_000_000),
            _filing("111", 2021, revenue=108_000_000,
                    expenses=99_000_000,
                    net_assets=55_000_000,
                    exec_comp=4_200_000),
            _filing("111", 2022, revenue=117_000_000,
                    expenses=107_000_000,
                    net_assets=60_000_000,
                    exec_comp=4_400_000),
            _filing("111", 2023, revenue=126_000_000,
                    expenses=115_000_000,
                    net_assets=65_000_000,
                    exec_comp=4_600_000),
        ])

    def tearDown(self):
        self.tmp.cleanup()

    def test_compute_trends_healthy_no_flags(self):
        from rcm_mc.data.irs990_trends import (
            compute_financial_trends,
        )
        t = compute_financial_trends(self.store, "111")
        self.assertEqual(t.n_years, 4)
        # Revenue CAGR over 3 years from 100M → 126M ≈ 8.0%
        self.assertAlmostEqual(
            t.revenue_cagr_3y, 0.080, places=2)
        # Healthy → no flags
        self.assertEqual(t.concerning_flags, [])

    def test_returns_none_for_single_filing(self):
        from rcm_mc.data.irs990_trends import (
            compute_financial_trends, store_filing,
        )
        store_filing(self.store, _filing("999", 2023))
        t = compute_financial_trends(self.store, "999")
        self.assertIsNone(t)


class TestConcerningFlags(unittest.TestCase):
    def test_eroding_net_assets_flagged(self):
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.data.irs990_trends import (
            store_filings_bulk, compute_financial_trends,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PortfolioStore(db)
            store.init_db()
            store_filings_bulk(store, [
                _filing("X", 2020, net_assets=50_000_000),
                _filing("X", 2021, net_assets=42_000_000),
                _filing("X", 2022, net_assets=35_000_000),
                _filing("X", 2023, net_assets=29_000_000),
            ])
            t = compute_financial_trends(store, "X")
            self.assertTrue(any("Net assets eroding" in f
                                for f in t.concerning_flags))
        finally:
            tmp.cleanup()

    def test_exec_comp_outpacing_revenue_flagged(self):
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.data.irs990_trends import (
            store_filings_bulk, compute_financial_trends,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PortfolioStore(db)
            store.init_db()
            store_filings_bulk(store, [
                # Revenue flat, exec comp growing 15% / year
                _filing("E", 2020, revenue=100_000_000,
                        exec_comp=3_000_000),
                _filing("E", 2021, revenue=101_000_000,
                        exec_comp=3_450_000),
                _filing("E", 2022, revenue=102_000_000,
                        exec_comp=3_970_000),
                _filing("E", 2023, revenue=103_000_000,
                        exec_comp=4_565_000),
            ])
            t = compute_financial_trends(store, "E")
            self.assertTrue(any("Executive comp" in f
                                for f in t.concerning_flags))
        finally:
            tmp.cleanup()

    def test_operating_loss_flagged(self):
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.data.irs990_trends import (
            store_filings_bulk, compute_financial_trends,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PortfolioStore(db)
            store.init_db()
            store_filings_bulk(store, [
                _filing("L", 2022, revenue=100_000_000,
                        expenses=98_000_000),
                _filing("L", 2023, revenue=100_000_000,
                        expenses=110_000_000),
            ])
            t = compute_financial_trends(store, "L")
            self.assertTrue(any("operating losses" in f.lower()
                                for f in t.concerning_flags))
        finally:
            tmp.cleanup()


class TestCohortSummary(unittest.TestCase):
    def test_state_filter_summary(self):
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.data.irs990_trends import (
            store_filings_bulk, cohort_trend_summary,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PortfolioStore(db)
            store.init_db()
            # 2 hospitals in TX, 1 in IL
            for ein, st in (("A", "TX"), ("B", "TX"),
                            ("C", "IL")):
                store_filings_bulk(store, [
                    _filing(ein, 2020, state=st,
                            revenue=100_000_000),
                    _filing(ein, 2023, state=st,
                            revenue=120_000_000),
                ])
            tx = cohort_trend_summary(store, state="TX")
            self.assertEqual(tx["n_eins"], 2)
            il = cohort_trend_summary(store, state="IL")
            self.assertEqual(il["n_eins"], 1)
            # All should report a positive median revenue CAGR
            self.assertGreater(tx["median_revenue_cagr"], 0)
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
