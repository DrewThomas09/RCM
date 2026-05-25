"""CMS FFS provider-supply loader — real PII-free supply counts by state x type.

Data is the committed aggregate of CMS's FFS Public Provider Enrollment extract
(NPIs/names dropped at ingest). Tests assert real national totals, state and
primary-care supply, NO PII columns in the committed aggregate, and the source
is registered. No runtime network.
"""
from __future__ import annotations

import csv
import unittest
from pathlib import Path

from rcm_mc.data import provider_supply as ps


class ProviderSupplyTests(unittest.TestCase):
    def test_summary_real_and_sane(self):
        s = ps.supply_summary()
        self.assertGreater(s["total_enrollments"], 1_000_000)   # ~3M enrollees
        self.assertGreaterEqual(s["states"], 50)
        self.assertGreater(s["provider_types"], 100)

    def test_state_and_primary_care(self):
        ca = ps.total_supply_for_state("CA")
        self.assertGreater(ca, 10_000)
        pc = ps.primary_care_supply_for_state("CA")
        self.assertTrue(0 < pc < ca)        # primary care is a subset
        self.assertEqual(ps.total_supply_for_state("ZZ"), 0)

    def test_national_by_type_sorted(self):
        rows = ps.supply_national_by_type(5)
        self.assertEqual(len(rows), 5)
        counts = [r["enrolled_count"] for r in rows]
        self.assertEqual(counts, sorted(counts, reverse=True))

    def test_no_pii_in_committed_aggregate(self):
        vendor = Path(ps.__file__).resolve().parent / "vendor" / "provider_supply"
        banned = {"npi", "first_name", "last_name", "mdl_name", "org_name",
                  "pecos_asct_cntl_id", "enrlmt_id"}
        for f in vendor.glob("*.csv"):
            with f.open(newline="") as fh:
                header = {c.strip().lower() for c in next(csv.reader(fh))}
            self.assertEqual(header & banned, set(), f"{f.name} leaked PII")

    def test_source_registered(self):
        src = ps.provider_supply_sources()
        self.assertTrue(src)
        self.assertEqual(src[0]["source_id"], "cms_ffs_provider_enrollment")


if __name__ == "__main__":
    unittest.main()
