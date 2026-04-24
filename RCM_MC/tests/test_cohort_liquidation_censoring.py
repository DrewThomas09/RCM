"""Cohort liquidation with as_of censoring.

Using ``hospital_03_censoring`` which has a mature cohort (Dec 2025)
and a young cohort (Feb 2026) when as_of is 2026-03-15. The young
cohort's 90-day and 120-day windows MUST refuse to report a number.
"""
from __future__ import annotations

import unittest
from datetime import date
from pathlib import Path

from rcm_mc.diligence import ingest_dataset, compute_cohort_liquidation
from rcm_mc.diligence.benchmarks import CohortStatus


FIXTURE = Path(__file__).resolve().parent / "fixtures" / "kpi_truth" / "hospital_03_censoring"


class CohortCensoringTests(unittest.TestCase):

    def setUp(self):
        self.ds = ingest_dataset(FIXTURE)
        self.as_of = date(2026, 3, 15)

    def test_mature_cohort_reports_liquidation(self):
        """Dec 2025 cohort is 104 days old at as_of=2026-03-15, so
        30/60/90-day windows are mature but 120d is not (by design).
        Assert the 90d window."""
        rep = compute_cohort_liquidation(
            self.ds.claims, as_of_date=self.as_of,
        )
        mature_90d = [
            c for c in rep.cells
            if c.cohort_month == "2025-12" and c.days_since_dos == 90
        ]
        self.assertEqual(len(mature_90d), 1)
        self.assertEqual(mature_90d[0].status, CohortStatus.MATURE)
        # All claims paid at 25d after DOS → 100% liquidation by 90d.
        self.assertAlmostEqual(
            mature_90d[0].cumulative_liquidation_pct or 0.0, 1.0, places=6,
        )
        # And the 120d window for the same cohort IS censored (age<120d).
        censored_120d = [
            c for c in rep.cells
            if c.cohort_month == "2025-12" and c.days_since_dos == 120
        ]
        self.assertEqual(censored_120d[0].status, CohortStatus.INSUFFICIENT_DATA)

    def test_young_cohort_90d_censored(self):
        rep = compute_cohort_liquidation(
            self.ds.claims, as_of_date=self.as_of,
        )
        young_90d = [
            c for c in rep.cells
            if c.cohort_month == "2026-02" and c.days_since_dos == 90
        ]
        self.assertEqual(len(young_90d), 1)
        self.assertEqual(young_90d[0].status, CohortStatus.INSUFFICIENT_DATA)
        self.assertIsNone(young_90d[0].cumulative_liquidation_pct,
                          "young cohort 90d must NOT fabricate a number")
        self.assertIn("in-flight", young_90d[0].reason or "")

    def test_young_cohort_120d_also_censored(self):
        rep = compute_cohort_liquidation(
            self.ds.claims, as_of_date=self.as_of,
        )
        cells = [
            c for c in rep.cells
            if c.cohort_month == "2026-02" and c.days_since_dos == 120
        ]
        self.assertEqual(cells[0].status, CohortStatus.INSUFFICIENT_DATA)

    def test_no_fabrication_anywhere(self):
        """Global sweep: no CohortCell with status=INSUFFICIENT_DATA
        carries a non-None cumulative_liquidation_pct."""
        rep = compute_cohort_liquidation(
            self.ds.claims, as_of_date=self.as_of,
        )
        for c in rep.cells:
            if c.status == CohortStatus.INSUFFICIENT_DATA:
                self.assertIsNone(
                    c.cumulative_liquidation_pct,
                    msg=f"fabricated number on censored cell: {c}",
                )

    def test_mature_cohort_always_has_numerator(self):
        rep = compute_cohort_liquidation(
            self.ds.claims, as_of_date=self.as_of,
        )
        for c in rep.cells:
            if c.status == CohortStatus.MATURE and c.denominator_usd > 0:
                self.assertIsNotNone(c.cumulative_liquidation_pct)
                self.assertGreaterEqual(c.cumulative_liquidation_pct, 0.0)
                self.assertLessEqual(c.cumulative_liquidation_pct, 1.0 + 1e-6)


if __name__ == "__main__":
    unittest.main()
