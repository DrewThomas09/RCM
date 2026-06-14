"""Tests for back-of-pipe ingest validation.

Pure functions, no DB/network. See SECOND_AGENT_BUILD_PROMPT.md
Appendix A (suppression, reconciliation, sign, format-drift).
"""
from __future__ import annotations

import unittest

from rcm_mc.data import ingest_validation as iv


class SuppressionSentinelTests(unittest.TestCase):
    def test_sentinels_recognized(self):
        for raw in ("*", ".", "", "(x)", "N/A", "na", "Suppressed", None):
            self.assertTrue(iv.is_suppressed(raw), raw)

    def test_numbers_never_suppressed(self):
        self.assertFalse(iv.is_suppressed(0))
        self.assertFalse(iv.is_suppressed(5))
        self.assertFalse(iv.is_suppressed(3.14))

    def test_real_string_value_not_suppressed(self):
        self.assertFalse(iv.is_suppressed("420"))
        self.assertFalse(iv.is_suppressed("IL"))


class SuppressionValidationTests(unittest.TestCase):
    def test_suppressed_stored_as_zero_is_flagged(self):
        rep = iv.ValidationReport("ma_enrollment")
        records = [
            {"raw_enroll": "*", "enroll": 0},   # bug: blank → 0
            {"raw_enroll": "100", "enroll": 100},
        ]
        iv.validate_suppression(rep, records,
                                raw_field="raw_enroll", parsed_field="enroll")
        self.assertFalse(rep.ok)
        self.assertIn("suppression", rep.issues[0])

    def test_suppressed_stored_as_none_is_ok(self):
        rep = iv.ValidationReport("ma_enrollment")
        records = [
            {"raw_enroll": "*", "enroll": None},   # correct handling
            {"raw_enroll": "100", "enroll": 100},
        ]
        iv.validate_suppression(rep, records,
                                raw_field="raw_enroll", parsed_field="enroll")
        self.assertTrue(rep.ok)

    def test_real_zero_is_not_flagged(self):
        rep = iv.ValidationReport("s")
        records = [{"raw_enroll": "0", "enroll": 0}]
        iv.validate_suppression(rep, records,
                                raw_field="raw_enroll", parsed_field="enroll")
        self.assertTrue(rep.ok)


class ReconciliationTests(unittest.TestCase):
    def test_exact_match_ok(self):
        rep = iv.ValidationReport("hcris")
        iv.reconcile_counts(rep, loaded=1000, expected=1000)
        self.assertTrue(rep.ok)

    def test_mismatch_flagged_at_zero_tolerance(self):
        rep = iv.ValidationReport("hcris")
        iv.reconcile_counts(rep, loaded=999, expected=1000)
        self.assertFalse(rep.ok)
        self.assertIn("reconciliation", rep.issues[0])

    def test_within_tolerance_ok(self):
        rep = iv.ValidationReport("hcris")
        iv.reconcile_counts(rep, loaded=990, expected=1000, tolerance=0.02)
        self.assertTrue(rep.ok)

    def test_outside_tolerance_flagged(self):
        rep = iv.ValidationReport("hcris")
        iv.reconcile_counts(rep, loaded=950, expected=1000, tolerance=0.02)
        self.assertFalse(rep.ok)

    def test_negative_expected_flagged(self):
        rep = iv.ValidationReport("hcris")
        iv.reconcile_counts(rep, loaded=0, expected=-1)
        self.assertFalse(rep.ok)


class SignConventionTests(unittest.TestCase):
    def test_negative_in_non_negative_field_flagged(self):
        rep = iv.ValidationReport("hcris")
        records = [{"beds": 200}, {"beds": -5}, {"beds": None}]
        iv.check_non_negative(rep, records, fields=["beds"])
        self.assertFalse(rep.ok)
        self.assertIn("sign", rep.issues[0])

    def test_all_non_negative_ok(self):
        rep = iv.ValidationReport("hcris")
        records = [{"beds": 200}, {"beds": 0}, {"beds": None}]
        iv.check_non_negative(rep, records, fields=["beds"])
        self.assertTrue(rep.ok)


class FormatDriftTests(unittest.TestCase):
    def test_unknown_key_flagged(self):
        rep = iv.ValidationReport("hcris")
        known = {("G300000", "00100", "00100"), ("G300000", "00200", "00100")}
        observed = [
            ("G300000", "00100", "00100"),
            ("S999999", "00500", "00300"),  # not in crosswalk → drift
        ]
        iv.detect_unknown_keys(rep, observed, known)
        self.assertFalse(rep.ok)
        self.assertIn("format_drift", rep.issues[0])

    def test_all_known_ok(self):
        rep = iv.ValidationReport("hcris")
        known = {("G300000", "00100", "00100")}
        iv.detect_unknown_keys(rep, [("G300000", "00100", "00100")], known)
        self.assertTrue(rep.ok)

    def test_sample_truncation_reports_overflow(self):
        rep = iv.ValidationReport("hcris")
        observed = [("X", str(i), "1") for i in range(10)]
        iv.detect_unknown_keys(rep, observed, set(), sample=3)
        self.assertFalse(rep.ok)
        self.assertIn("more", rep.issues[0])


class ReportTests(unittest.TestCase):
    def test_raise_for_issues_raises_when_bad(self):
        rep = iv.ValidationReport("s")
        rep.add("boom")
        with self.assertRaises(iv.IngestValidationError):
            rep.raise_for_issues()

    def test_raise_for_issues_passthrough_when_ok(self):
        rep = iv.ValidationReport("s")
        self.assertIs(rep.raise_for_issues(), rep)

    def test_to_dict_shape(self):
        rep = iv.ValidationReport("s")
        rep.ran("reconciliation")
        d = rep.to_dict()
        self.assertEqual(d["source"], "s")
        self.assertTrue(d["ok"])
        self.assertEqual(d["checks_run"], ["reconciliation"])


if __name__ == "__main__":
    unittest.main()
