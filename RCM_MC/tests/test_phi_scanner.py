"""PHI scanner regression tests.

The scanner is a pre-commit / CI guardrail; false positives here
block legitimate commits, false negatives let PHI into git. Both
cases have tests.

Pattern coverage:
- SSN (with + without dashes)
- Phone (multiple formats)
- Email
- DOB (keyed, not every date)
- MRN, NPI
- Street address

False-positive avoidance:
- Synthetic claim IDs used in kpi_truth fixtures (``H6-P000`` etc.)
  do NOT trigger any finding
- A bare 9-digit number without SSN keyword is NOT flagged
- A date without a DOB keyword is NOT flagged
- A 10-digit number without NPI keyword is NOT flagged as NPI
"""
from __future__ import annotations

import unittest

from rcm_mc.compliance.phi_scanner import (
    PHIScanReport, redact_phi, scan_text,
)


class SSNPatternTests(unittest.TestCase):

    def test_dashed_ssn_is_flagged(self):
        r = scan_text("SSN: 123-45-6789 is on the form")
        self.assertTrue(any(f.pattern == "ssn" for f in r.findings))
        self.assertEqual(r.highest_severity, "HIGH")

    def test_forbidden_area_codes_do_not_flag(self):
        # SSA reserves 000, 666, 900-999 — synthetic numbers with
        # these prefixes are common in test data; scanner must
        # tolerate them.
        r = scan_text("000-12-3456  666-12-3456  900-12-3456")
        self.assertEqual([f for f in r.findings if f.pattern == "ssn"], [])

    def test_keyword_required_for_bare_9_digits(self):
        # A random 9-digit number is NOT an SSN by itself.
        r = scan_text("invoice 123456789 pending")
        self.assertEqual([f for f in r.findings
                          if f.pattern == "ssn_nodash"], [])
        # With the keyword, it flags.
        r2 = scan_text("SSN: 123456789")
        self.assertTrue(any(f.pattern == "ssn_nodash" for f in r2.findings))


class PhonePatternTests(unittest.TestCase):

    def test_common_phone_formats_flag(self):
        for phone in (
            "(415) 555-1234",
            "415-555-1234",
            "415.555.1234",
            "+1 415 555 1234",
        ):
            r = scan_text(f"call {phone} today")
            hits = [f for f in r.findings if f.pattern == "phone"]
            self.assertTrue(hits, msg=f"phone {phone!r} missed")


class EmailPatternTests(unittest.TestCase):

    def test_email_flags(self):
        r = scan_text("contact jane.doe@example.com")
        self.assertTrue(any(f.pattern == "email" for f in r.findings))

    def test_email_severity_medium(self):
        r = scan_text("contact jane.doe@example.com")
        email = next(f for f in r.findings if f.pattern == "email")
        self.assertEqual(email.severity, "MEDIUM")


class DOBPatternTests(unittest.TestCase):

    def test_dob_with_keyword_flags(self):
        for text in (
            "DOB: 03/14/1955",
            "Date of Birth: 1955-03-14",
            "Born March 14, 1955",
            "d.o.b. 03/14/1955",
        ):
            r = scan_text(text)
            self.assertTrue(any(f.pattern == "dob" for f in r.findings),
                            msg=f"dob {text!r} missed")

    def test_date_without_keyword_does_not_flag(self):
        # A claim date of service is not PHI on its own — we don't
        # flag dates that aren't keyed as DOB.
        r = scan_text("date_of_service: 2024-03-14  paid_date: 2024-04-02")
        self.assertEqual([f for f in r.findings if f.pattern == "dob"], [])


class MRNAndNPIPatternTests(unittest.TestCase):

    def test_mrn_flags_with_keyword(self):
        r = scan_text("MRN: A7892345 arrived")
        self.assertTrue(any(f.pattern == "mrn" for f in r.findings))

    def test_npi_flags_only_with_keyword(self):
        # Keyword required — bare 10-digit number does not flag NPI.
        r1 = scan_text("4155551234")          # a phone / bare number
        self.assertEqual([f for f in r1.findings if f.pattern == "npi"], [])
        r2 = scan_text("NPI: 1234567890")
        self.assertTrue(any(f.pattern == "npi" for f in r2.findings))


class SyntheticFixtureFalsePositiveTests(unittest.TestCase):
    """The kpi_truth fixtures use synthetic patient/claim IDs like
    ``H6-P000``, ``P-000``, ``H8-C001``. The scanner must not flag
    any of them — test fixtures would otherwise become permanently
    dirty."""

    def test_synthetic_claim_ids_do_not_flag(self):
        text = (
            "claim_id,patient_id,date_of_service\n"
            "H6-P000,P-000,2024-02-01\n"
            "H8-C001,P-C001,2024-03-09\n"
        )
        r = scan_text(text)
        self.assertEqual(
            r.findings, [],
            msg=f"synthetic fixture IDs should not flag, got "
                f"{[f.to_dict() for f in r.findings]}",
        )


class RedactTests(unittest.TestCase):

    def test_redact_preserves_non_phi_text(self):
        text = "Patient SSN: 123-45-6789. Call (415) 555-1234."
        redacted, report = redact_phi(text)
        self.assertIn("Patient SSN: ", redacted)
        self.assertIn("Call ", redacted)
        self.assertNotIn("123-45-6789", redacted)
        self.assertNotIn("555-1234", redacted)
        self.assertEqual(len(report.findings), 2)

    def test_redaction_is_idempotent(self):
        text = "DOB: 03/14/1955  DOB: 04/01/1960"
        redacted1, _ = redact_phi(text)
        redacted2, report = redact_phi(redacted1)
        self.assertEqual(redacted1, redacted2)
        self.assertEqual(report.findings, [])


class ReportMetadataTests(unittest.TestCase):

    def test_count_by_pattern_aggregates_correctly(self):
        r = scan_text(
            "SSN: 111-22-3333 and SSN: 444-55-6666. "
            "Email: a@b.co"
        )
        counts = r.count_by_pattern
        self.assertEqual(counts.get("ssn"), 2)
        self.assertEqual(counts.get("email"), 1)

    def test_highest_severity_picks_the_worst_tier(self):
        # MEDIUM-only input
        r1 = scan_text("Email: a@b.co")
        self.assertEqual(r1.highest_severity, "MEDIUM")
        # HIGH wins over MEDIUM
        r2 = scan_text("Email: a@b.co SSN: 111-22-3333")
        self.assertEqual(r2.highest_severity, "HIGH")
        # None when empty
        r3 = scan_text("plain text with no PHI")
        self.assertIsNone(r3.highest_severity)

    def test_allowed_patterns_skips_requested_categories(self):
        text = "contact a@b.co, SSN: 111-22-3333"
        r = scan_text(text, allowed_patterns={"email"})
        self.assertFalse(any(f.pattern == "email" for f in r.findings))
        # SSN still flags.
        self.assertTrue(any(f.pattern == "ssn" for f in r.findings))


if __name__ == "__main__":
    unittest.main()
