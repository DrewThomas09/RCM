"""Bankruptcy-survivor named-case replay analysis.

The fired patterns are matches to real public-record healthcare
bankruptcies, not abstract risk scores. The fingerprint analysis
ranks them by severity, de-dupes by named case, and is a pure
function of the scan's fired checks.
"""
from __future__ import annotations

import unittest

from rcm_mc.diligence.screening import (
    ScanInput, analyze_distress_fingerprint, run_bankruptcy_survivor_scan,
)


class DistressFingerprintTests(unittest.TestCase):
    def test_clean_deal_replays_nothing(self):
        scan = run_bankruptcy_survivor_scan(ScanInput(target_name="Clean"))
        fp = analyze_distress_fingerprint(scan)
        self.assertEqual(fp.replays, [])
        self.assertEqual(fp.distinct_cases, [])
        self.assertEqual(fp.weighted_severity, 0)
        self.assertIn("does not", fp.headline)

    def test_replays_only_fired_checks(self):
        scan = run_bankruptcy_survivor_scan(ScanInput(
            target_name="T", lease_rent_pct_revenue=0.18,
            ebitdar_coverage=1.0, is_correctional_health=True))
        fp = analyze_distress_fingerprint(scan)
        self.assertEqual(len(fp.replays), scan.patterns_hit)
        self.assertTrue(all(r.severity for r in fp.replays))

    def test_ranked_by_severity_weight(self):
        scan = run_bankruptcy_survivor_scan(ScanInput(
            target_name="T", lease_rent_pct_revenue=0.20,
            ebitdar_coverage=0.9, is_correctional_health=True,
            is_hospital_based_physician=True, oon_revenue_share=0.45))
        fp = analyze_distress_fingerprint(scan)
        weights = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
        seq = [weights[r.severity] for r in fp.replays]
        self.assertEqual(seq, sorted(seq, reverse=True))

    def test_distinct_cases_deduped(self):
        scan = run_bankruptcy_survivor_scan(ScanInput(
            target_name="T", lease_rent_pct_revenue=0.18,
            ebitdar_coverage=1.0, is_correctional_health=True,
            is_hospital_based_physician=True, oon_revenue_share=0.45))
        fp = analyze_distress_fingerprint(scan)
        # No duplicate named cases.
        self.assertEqual(len(fp.distinct_cases), len(set(fp.distinct_cases)))
        # Weighted severity equals sum over fired checks.
        weights = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
        expect = sum(weights[c.severity] for c in scan.checks if c.fired)
        self.assertEqual(fp.weighted_severity, expect)

    def test_to_dict_round_trips(self):
        scan = run_bankruptcy_survivor_scan(ScanInput(
            target_name="T", is_correctional_health=True))
        d = analyze_distress_fingerprint(scan).to_dict()
        self.assertIn("replays", d)
        self.assertIn("distinct_cases", d)
        self.assertIn("weighted_severity", d)

    def test_renders_in_page(self):
        from rcm_mc.ui.bankruptcy_survivor_page import render_scan_result
        scan = run_bankruptcy_survivor_scan(ScanInput(
            target_name="T", lease_rent_pct_revenue=0.18,
            ebitdar_coverage=1.0, is_correctional_health=True))
        h = render_scan_result(scan)
        self.assertIn("NAMED-CASE REPLAY", h)

    def test_clean_page_shows_no_replay_note(self):
        from rcm_mc.ui.bankruptcy_survivor_page import render_scan_result
        scan = run_bankruptcy_survivor_scan(ScanInput(target_name="Clean"))
        h = render_scan_result(scan)
        self.assertIn("does not replay", h)


if __name__ == "__main__":
    unittest.main()
