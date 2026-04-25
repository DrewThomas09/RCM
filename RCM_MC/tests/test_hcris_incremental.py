"""Tests for the incremental HCRIS ingestion layer."""
from __future__ import annotations

import os
import tempfile
import unittest


def _filing(ccn, year, status="settled", revenue=100.0):
    return {
        "ccn": ccn, "fiscal_year": year,
        "status": status,
        "net_patient_revenue": revenue,
        "operating_expenses": revenue * 0.92,
        "beds": 200, "case_mix_index": 1.45,
        "total_inpatient_days": 65000,
        "medicare_days": 28000, "medicaid_days": 9000,
        "outpatient_revenue": revenue * 0.4,
    }


class TestIncrementalRefresh(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "hcris.db")

    def tearDown(self):
        self.tmp.cleanup()

    def test_initial_insert(self):
        from rcm_mc.data.hcris_incremental import (
            incremental_refresh,
        )
        def fetcher(year):
            yield _filing("450001", year, "submitted")
            yield _filing("450002", year, "submitted")
        report = incremental_refresh(
            self.db, years=[2022], fetcher=fetcher)
        self.assertEqual(report.filings_inserted, 2)
        self.assertEqual(report.filings_upgraded, 0)
        self.assertEqual(report.filings_skipped, 0)

    def test_skip_unchanged_filings(self):
        """Re-running with identical data → all skipped."""
        from rcm_mc.data.hcris_incremental import (
            incremental_refresh,
        )
        def fetcher(year):
            yield _filing("450001", year, "submitted")
        incremental_refresh(
            self.db, years=[2022], fetcher=fetcher)
        # Re-run with the SAME data
        report = incremental_refresh(
            self.db, years=[2022], fetcher=fetcher)
        self.assertEqual(report.filings_inserted, 0)
        self.assertEqual(report.filings_upgraded, 0)
        self.assertEqual(report.filings_skipped, 1)

    def test_upgrade_on_status_improvement(self):
        """submitted → settled → audited each upgrade the row."""
        from rcm_mc.data.hcris_incremental import (
            incremental_refresh,
        )
        # 1. Submit
        incremental_refresh(
            self.db, years=[2022],
            fetcher=lambda y: [
                _filing("450001", y, "submitted")])
        # 2. Settle — should UPGRADE (rank 1 → 2)
        r2 = incremental_refresh(
            self.db, years=[2022],
            fetcher=lambda y: [
                _filing("450001", y, "settled")])
        self.assertEqual(r2.filings_upgraded, 1)
        # 3. Audit — should UPGRADE (rank 2 → 3)
        r3 = incremental_refresh(
            self.db, years=[2022],
            fetcher=lambda y: [
                _filing("450001", y, "audited")])
        self.assertEqual(r3.filings_upgraded, 1)
        # 4. Re-audit with SAME data — skipped
        r4 = incremental_refresh(
            self.db, years=[2022],
            fetcher=lambda y: [
                _filing("450001", y, "audited")])
        self.assertEqual(r4.filings_skipped, 1)

    def test_no_downgrade_on_lower_status(self):
        """If we have an audited row and CMS re-publishes a
        submitted version of the SAME filing, don't downgrade."""
        from rcm_mc.data.hcris_incremental import (
            incremental_refresh,
        )
        incremental_refresh(
            self.db, years=[2022],
            fetcher=lambda y: [
                _filing("450001", y, "audited")])
        # Re-publish a submitted row — should be skipped
        report = incremental_refresh(
            self.db, years=[2022],
            fetcher=lambda y: [
                _filing("450001", y, "submitted")])
        self.assertEqual(report.filings_inserted, 0)
        self.assertEqual(report.filings_upgraded, 0)
        self.assertEqual(report.filings_skipped, 1)

    def test_amendment_upgrade_at_same_rank(self):
        """CMS sometimes re-issues an amended filing without
        bumping the status-rank. Hash-based detection should
        upgrade in that case."""
        from rcm_mc.data.hcris_incremental import (
            incremental_refresh,
        )
        # Initial settled filing
        incremental_refresh(
            self.db, years=[2022],
            fetcher=lambda y: [
                _filing("450001", y, "settled",
                        revenue=100.0)])
        # Amendment: same status, different revenue
        report = incremental_refresh(
            self.db, years=[2022],
            fetcher=lambda y: [
                _filing("450001", y, "settled",
                        revenue=105.0)])
        self.assertEqual(report.filings_upgraded, 1)


class TestIngestStatus(unittest.TestCase):
    def test_per_year_status_breakdown(self):
        from rcm_mc.data.hcris_incremental import (
            incremental_refresh, ingest_status,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "hcris.db")
            incremental_refresh(
                db, years=[2021, 2022],
                fetcher=lambda y: [
                    _filing("A", y, "audited"),
                    _filing("B", y, "settled"),
                    _filing("C", y, "submitted"),
                ])
            statuses = ingest_status(db)
            self.assertEqual(len(statuses), 2)
            for s in statuses:
                self.assertEqual(s.filings_loaded, 3)
                self.assertEqual(s.audited_count, 1)
                self.assertEqual(s.settled_count, 1)
                self.assertEqual(s.submitted_count, 1)
                self.assertTrue(s.last_refreshed)
        finally:
            tmp.cleanup()


class TestReset(unittest.TestCase):
    def test_reset_drops_all_rows(self):
        from rcm_mc.data.hcris_incremental import (
            incremental_refresh, ingest_status, reset_load_log,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "hcris.db")
            incremental_refresh(
                db, years=[2022],
                fetcher=lambda y: [
                    _filing("X", y, "settled")])
            self.assertEqual(len(ingest_status(db)), 1)
            dropped = reset_load_log(db)
            self.assertEqual(dropped, 1)
            self.assertEqual(len(ingest_status(db)), 0)
        finally:
            tmp.cleanup()


class TestNoneFetcher(unittest.TestCase):
    def test_default_fetcher_returns_empty(self):
        from rcm_mc.data.hcris_incremental import (
            incremental_refresh,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "h.db")
            # No fetcher → empty iterator → no rows inserted
            r = incremental_refresh(db, years=[2022])
            self.assertEqual(r.filings_inserted, 0)
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
