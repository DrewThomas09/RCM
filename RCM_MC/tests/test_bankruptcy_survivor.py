"""Bankruptcy-survivor scan page visuals — the diligence upgrade wave.

The pattern strip renders the scan at a glance: one chip per pattern
check, fired chips lit in severity tone, passed chips muted.
"""
from __future__ import annotations

import unittest


class PatternStripTests(unittest.TestCase):
    def test_strip_renders_with_fired_patterns(self):
        from rcm_mc.diligence.screening import (
            ScanInput, run_bankruptcy_survivor_scan,
        )
        from rcm_mc.ui.bankruptcy_survivor_page import render_scan_result
        scan = run_bankruptcy_survivor_scan(ScanInput(
            target_name="Test", is_correctional_health=True,
            is_hospital_based_physician=True, oon_revenue_share=0.45,
            ebitdar_coverage=0.9, lease_rent_pct_revenue=0.12))
        self.assertGreater(scan.patterns_hit, 0)
        h = render_scan_result(scan)
        self.assertIn("patterns fired", h)
        self.assertIn("severity tone", h)

    def test_empty_checks_no_strip(self):
        from rcm_mc.diligence.screening.bankruptcy_survivor import (
            BankruptcySurvivorScan,
        )
        from rcm_mc.ui.bankruptcy_survivor_page import _pattern_strip
        empty = BankruptcySurvivorScan(target_name="X", computed_at="now")
        self.assertEqual(_pattern_strip(empty), "")


if __name__ == "__main__":
    unittest.main()
