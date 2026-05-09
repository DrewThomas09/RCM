"""tests for ``rcm_mc.diligence.cim_paste`` (P85)."""
from __future__ import annotations

import unittest

from rcm_mc.diligence.cim_paste import extract_from_cim


SAMPLE_CIM = """
Project Aurora — Confidential

Target: Meadowbrook Regional Health System
Sector: Hospital, multi-site rural

Revenue: $450M (FY2024)
Adjusted EBITDA: $67.5M
Enterprise Value: $600M
Equity check: $250M
Debt financing: $350M

Payer mix:
  Medicare: 38%
  Commercial: 35%
  Medicaid: 17%
  Other: 10%

Real estate:
  Lease term: 15 years
  Annual rent: $4.2M
"""


class FieldExtraction(unittest.TestCase):

    def test_revenue_extracted(self) -> None:
        out = extract_from_cim(SAMPLE_CIM)
        self.assertEqual(out.get("revenue_year0_usd"), 450_000_000)

    def test_ebitda_extracted(self) -> None:
        out = extract_from_cim(SAMPLE_CIM)
        self.assertEqual(out.get("ebitda_year0_usd"), 67_500_000)

    def test_enterprise_value_extracted(self) -> None:
        out = extract_from_cim(SAMPLE_CIM)
        self.assertEqual(out.get("enterprise_value_usd"), 600_000_000)

    def test_equity_check_extracted(self) -> None:
        out = extract_from_cim(SAMPLE_CIM)
        self.assertEqual(out.get("equity_check_usd"), 250_000_000)

    def test_debt_extracted(self) -> None:
        out = extract_from_cim(SAMPLE_CIM)
        self.assertEqual(out.get("debt_usd"), 350_000_000)

    def test_lease_term_extracted(self) -> None:
        out = extract_from_cim(SAMPLE_CIM)
        self.assertEqual(out.get("lease_term_years"), 15)


class PercentageExtraction(unittest.TestCase):

    def test_medicare_share(self) -> None:
        out = extract_from_cim(SAMPLE_CIM)
        self.assertAlmostEqual(out.get("medicare_share"), 0.38, places=2)

    def test_commercial_share(self) -> None:
        out = extract_from_cim(SAMPLE_CIM)
        self.assertAlmostEqual(out.get("commercial_share"), 0.35, places=2)

    def test_medicaid_share(self) -> None:
        out = extract_from_cim(SAMPLE_CIM)
        self.assertAlmostEqual(out.get("medicaid_share"), 0.17, places=2)


class GracefulInput(unittest.TestCase):

    def test_empty_text_returns_empty_dict(self) -> None:
        self.assertEqual(extract_from_cim(""), {})

    def test_unrecognised_format_returns_partial(self) -> None:
        # Random prose with no canonical keywords → no extractions.
        out = extract_from_cim(
            "This deal is interesting because of the team."
        )
        self.assertEqual(out, {})

    def test_handles_alt_phrasings(self) -> None:
        out = extract_from_cim(
            "TEV: $500M\nNet Revenue: 200M\nAdjusted EBITDA: 30M"
        )
        self.assertEqual(out.get("enterprise_value_usd"), 500_000_000)
        self.assertEqual(out.get("revenue_year0_usd"), 200_000_000)
        self.assertEqual(out.get("ebitda_year0_usd"), 30_000_000)

    def test_partner_can_edit_wrong_values(self) -> None:
        # Bad data shouldn't crash — the parser returns whatever
        # matched. Caller treats this as a starting point.
        out = extract_from_cim("Revenue: garbled")
        self.assertNotIn("revenue_year0_usd", out)


if __name__ == "__main__":
    unittest.main()
