"""CMS SNF Change-of-Ownership loader — real consolidation signal by state x year.

Data is the committed aggregate of CMS's SNF CHOW file (identifiers dropped).
Tests assert real totals, the national year trend, per-state counts, no
identifier columns in the committed aggregate, and source registration.
No runtime network.
"""
from __future__ import annotations

import csv
import unittest
from pathlib import Path

from rcm_mc.data import snf_chow as c


class SnfChowTests(unittest.TestCase):
    def test_summary_real(self):
        s = c.chow_summary()
        self.assertGreater(s["total_chows"], 1000)      # ~5.1k CHOWs
        self.assertGreaterEqual(s["states"], 40)
        self.assertLessEqual(s["year_min"], s["year_max"])

    def test_national_trend(self):
        rows = c.chow_by_year()
        self.assertTrue(rows)
        years = [r["year"] for r in rows]
        self.assertEqual(years, sorted(years))
        self.assertTrue(all(r["chow_count"] >= 0 for r in rows))

    def test_state_counts(self):
        tx = c.total_chows_for_state("TX")
        self.assertGreater(tx, 0)
        self.assertEqual(c.total_chows_for_state("ZZ"), 0)
        top = c.top_chow_states(5)
        counts = [r["chow_count"] for r in top]
        self.assertEqual(counts, sorted(counts, reverse=True))

    def test_no_identifiers_committed(self):
        vendor = Path(c.__file__).resolve().parent / "vendor" / "snf_chow"
        banned = {"npi", "enrollment id - buyer", "ccn - buyer", "associate id - buyer",
                  "organization name - buyer"}
        for f in vendor.glob("*.csv"):
            with f.open(newline="") as fh:
                header = {x.strip().lower() for x in next(csv.reader(fh))}
            self.assertEqual(header & banned, set(), f"{f.name} leaked identifiers")

    def test_source_registered(self):
        src = c.chow_sources()
        ids = {s["source_id"] for s in src}
        self.assertIn("cms_snf_chow", ids)
        self.assertIn("cms_hospital_chow", ids)

    def test_hospital_chow_real(self):
        s = c.hospital_chow_summary()
        self.assertGreater(s["total_chows"], 100)       # ~755 hospital CHOWs
        self.assertGreaterEqual(s["states"], 30)
        self.assertGreater(c.total_hospital_chows_for_state("TX"), 0)
        self.assertEqual(c.total_hospital_chows_for_state("ZZ"), 0)


if __name__ == "__main__":
    unittest.main()
