"""CMS Open Payments (staged) loader — real industry-payments aggregates.

Data is the committed PII-free summary aggregate (no recipient identifiers).
Tests assert real national totals, top-entity ranking, no recipient-PII columns,
and source registration. No runtime network.
"""
from __future__ import annotations

import csv
import unittest
from pathlib import Path

from rcm_mc.data import open_payments as op


class OpenPaymentsTests(unittest.TestCase):
    def test_summary_real(self):
        s = op.open_payments_summary()
        self.assertGreater(s["total_payments_usd"], 1e9)        # ~$3.3bn 2023
        self.assertGreater(s["total_transactions"], 1_000_000)
        self.assertGreater(s["reporting_entities"], 500)
        self.assertEqual(s["program_year"], 2023)

    def test_top_entities_sorted(self):
        rows = op.top_reporting_entities(10)
        self.assertEqual(len(rows), 10)
        amts = [float(r["total_amount"]) for r in rows]
        self.assertEqual(amts, sorted(amts, reverse=True))
        self.assertTrue(all(r["AMGPO_Name"] for r in rows))

    def test_no_recipient_pii(self):
        vendor = Path(op.__file__).resolve().parent / "vendor" / "open_payments"
        banned = {"physician_npi", "covered_recipient_npi", "recipient_first_name",
                  "recipient_last_name", "physician_first_name", "physician_last_name"}
        for f in vendor.glob("*.csv"):
            with f.open(newline="") as fh:
                header = {c.strip().lower() for c in next(csv.reader(fh))}
            self.assertEqual(header & banned, set(), f"{f.name} leaked recipient PII")

    def test_source_registered(self):
        src = op.open_payments_sources()
        self.assertTrue(src)
        self.assertEqual(src[0]["source_id"], "cms_open_payments_2023")


if __name__ == "__main__":
    unittest.main()
