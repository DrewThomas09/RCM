"""Cash Waterfall / Quality of Revenue regression tests.

One session's work: add a claim-level cash waterfall as a first-
class Phase 2 deliverable. Tests cover:

- The hand-computed truth on ``hospital_06_waterfall_truth``:
  every step of the cascade matches the fixture's expected.json
  within 0.01 USD. This is the truth-table lock — if the formula
  drifts, this test fails loud.
- Censoring: a cohort too young for the realization window (120d)
  returns ``status=INSUFFICIENT_DATA`` with no numeric fields.
  Never fabricated.
- Front-end vs clinical denial routing: CARC 27 (coverage
  terminated) lands in ``front_end_leakage``, CARC 50 (medical
  necessity) lands in ``initial_denials_gross``. Distinct buckets,
  no double-count.
- QoR divergence flag: when ``management_reported_revenue`` diverges
  by more than the 5% threshold, the cohort's ``qor_flag`` is True
  and the divergence percentage carries the signed direction.
- Provenance: every ``WaterfallStep`` carries the ``claim_ids`` that
  contributed; no step is missing its drill-through set.
- Totals roll-up: the report's ``total_realized_cash_usd`` equals
  the sum of mature cohorts' realized cash.
"""
from __future__ import annotations

import json
import unittest
from datetime import date
from pathlib import Path

from rcm_mc.diligence import ingest_dataset
from rcm_mc.diligence.benchmarks import (
    CashWaterfallReport,
    CohortStatus,
    compute_cash_waterfall,
)


FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "kpi_truth"


class CashWaterfallTruthTests(unittest.TestCase):
    """Lock the math against ``hospital_06_waterfall_truth``."""

    def setUp(self):
        self.ccd = ingest_dataset(
            FIXTURE_ROOT / "hospital_06_waterfall_truth",
        )
        self.expected = json.loads(
            (FIXTURE_ROOT / "hospital_06_waterfall_truth"
             / "expected.json").read_text("utf-8")
        )
        self.as_of = date.fromisoformat(self.expected["as_of_date"])
        self.report = compute_cash_waterfall(
            self.ccd.claims, as_of_date=self.as_of,
        )

    def test_exactly_one_cohort_mature(self):
        mature = self.report.mature_cohorts()
        self.assertEqual(len(mature), 1,
                         msg=f"expected 1 mature cohort, got {len(mature)}")
        self.assertEqual(mature[0].cohort_month, "2024-02")
        self.assertEqual(mature[0].payer_class, "ALL")
        self.assertEqual(mature[0].claim_count, 10)

    def test_each_waterfall_step_matches_expected(self):
        cohort = self.report.mature_cohorts()[0]
        steps = {s.name: s for s in cohort.steps}
        ew = self.expected["expected_waterfall"]

        # Every step in the spec appears in the cohort.
        for key in (
            "gross_charges", "contractual_adjustments", "front_end_leakage",
            "initial_denials_gross", "appeals_recovered", "bad_debt",
            "realized_cash",
        ):
            self.assertIn(key, steps, msg=f"missing step {key!r}")
            self.assertAlmostEqual(
                steps[key].amount_usd, ew[key], places=2,
                msg=f"step {key!r} amount mismatch",
            )

    def test_realization_rate_is_42_percent(self):
        cohort = self.report.mature_cohorts()[0]
        self.assertIsNotNone(cohort.realization_rate)
        self.assertAlmostEqual(
            cohort.realization_rate,
            self.expected["expected_waterfall"]["realization_rate"],
            places=4,
        )

    def test_running_balance_walks_down_to_realized_cash(self):
        """The cascade must close: after every step, running_balance
        equals the expected balance at that point."""
        cohort = self.report.mature_cohorts()[0]
        steps = {s.name: s for s in cohort.steps}
        # gross (10,000) - contractual (2,000) = 8,000
        self.assertAlmostEqual(steps["contractual_adjustments"].running_balance_usd, 8_000.0, places=2)
        # - front_end (1,600) = 6,400
        self.assertAlmostEqual(steps["front_end_leakage"].running_balance_usd, 6_400.0, places=2)
        # - initial_denials (1,600) = 4,800
        self.assertAlmostEqual(steps["initial_denials_gross"].running_balance_usd, 4_800.0, places=2)
        # + appeals (0) = 4,800
        self.assertAlmostEqual(steps["appeals_recovered"].running_balance_usd, 4_800.0, places=2)
        # - bad_debt (600) = 4,200
        self.assertAlmostEqual(steps["bad_debt"].running_balance_usd, 4_200.0, places=2)
        # realized_cash step carries 4,200 as both amount + balance
        self.assertAlmostEqual(steps["realized_cash"].running_balance_usd, 4_200.0, places=2)
        self.assertAlmostEqual(steps["realized_cash"].amount_usd, 4_200.0, places=2)

    # ── Denial-routing invariants ───────────────────────────────────

    def test_front_end_and_initial_denials_do_not_double_count(self):
        cohort = self.report.mature_cohorts()[0]
        steps = {s.name: s for s in cohort.steps}
        front_ids = set(steps["front_end_leakage"].claim_ids)
        initial_ids = set(steps["initial_denials_gross"].claim_ids)
        self.assertEqual(front_ids & initial_ids, set(),
                         msg=f"claim in both buckets: {front_ids & initial_ids}")
        # Front-end catches the two CARC-27 claims.
        self.assertEqual(len(front_ids), 2)
        # Clinical catches the two CARC-50 claims.
        self.assertEqual(len(initial_ids), 2)

    def test_bad_debt_catches_only_aged_open_balance(self):
        cohort = self.report.mature_cohorts()[0]
        steps = {s.name: s for s in cohort.steps}
        # Exactly one claim in the bad-debt bucket — the aged
        # $200-paid-on-$800-allowed row.
        self.assertEqual(steps["bad_debt"].claim_count, 1)
        self.assertEqual(steps["bad_debt"].claim_ids[0], "H6-B000")
        self.assertAlmostEqual(steps["bad_debt"].amount_usd, 600.0, places=2)


class CashWaterfallCensoringTests(unittest.TestCase):
    """A cohort whose age < realization_window_days must refuse to
    emit numbers. Uses a post-dated as_of so hospital_06 is censored."""

    def test_cohort_younger_than_window_is_censored(self):
        ccd = ingest_dataset(FIXTURE_ROOT / "hospital_06_waterfall_truth")
        # hospital_06 DOS is 2024-02-01..2024-02-10. Setting as_of to
        # 2024-03-15 gives cohort age ~42 days — well below the
        # 120-day realization window.
        report = compute_cash_waterfall(
            ccd.claims, as_of_date=date(2024, 3, 15),
            realization_window_days=120,
        )
        self.assertEqual(len(report.mature_cohorts()), 0)
        censored = report.censored_cohorts()
        self.assertEqual(len(censored), 1)
        cell = censored[0]
        self.assertEqual(cell.status, CohortStatus.INSUFFICIENT_DATA)
        self.assertEqual(cell.steps, [])
        self.assertEqual(cell.realized_cash_usd, 0.0)
        self.assertEqual(cell.gross_charges_usd, 0.0)
        self.assertIsNone(cell.realization_rate)
        self.assertIn("in-flight", cell.reason)

    def test_custom_window_respected(self):
        """A 30-day window lets hospital_06 mature at as_of 2024-04-01."""
        ccd = ingest_dataset(FIXTURE_ROOT / "hospital_06_waterfall_truth")
        report = compute_cash_waterfall(
            ccd.claims, as_of_date=date(2024, 4, 1),
            realization_window_days=30,
        )
        mature = report.mature_cohorts()
        self.assertEqual(len(mature), 1)
        self.assertAlmostEqual(
            mature[0].gross_charges_usd, 10_000.0, places=2,
        )


class CashWaterfallQoRDivergenceTests(unittest.TestCase):

    def setUp(self):
        self.ccd = ingest_dataset(
            FIXTURE_ROOT / "hospital_06_waterfall_truth",
        )
        self.expected = json.loads(
            (FIXTURE_ROOT / "hospital_06_waterfall_truth"
             / "expected.json").read_text("utf-8")
        )
        self.as_of = date.fromisoformat(self.expected["as_of_date"])

    def test_qor_flag_fires_when_divergence_exceeds_threshold(self):
        spec = self.expected["management_reported_revenue_for_qor_test"]
        report = compute_cash_waterfall(
            self.ccd.claims, as_of_date=self.as_of,
            management_reported_revenue_by_cohort_month={
                spec["cohort_month"]: spec["management_reported_revenue_usd"],
            },
        )
        cohort = report.mature_cohorts()[0]
        self.assertAlmostEqual(
            cohort.qor_divergence_usd,
            spec["expected_qor_divergence_usd"], places=2,
        )
        # Accrual ($5,800) − management ($5,000) = +$800 → +16% → CRITICAL
        self.assertGreater(cohort.qor_divergence_pct, 0.0)
        self.assertEqual(cohort.qor_flag, spec["expected_qor_flag"])
        self.assertEqual(
            cohort.divergence_status, spec["expected_divergence_status"],
        )

    def test_no_qor_fields_when_management_revenue_absent(self):
        from rcm_mc.diligence.benchmarks import DivergenceStatus
        report = compute_cash_waterfall(
            self.ccd.claims, as_of_date=self.as_of,
        )
        cohort = report.mature_cohorts()[0]
        self.assertIsNone(cohort.management_reported_revenue_usd)
        self.assertIsNone(cohort.qor_divergence_usd)
        self.assertIsNone(cohort.qor_divergence_pct)
        self.assertFalse(cohort.qor_flag)
        self.assertEqual(cohort.divergence_status,
                         DivergenceStatus.UNKNOWN.value)

    def test_small_divergence_does_not_flag(self):
        """Accrual $5,800 vs mgmt $5,750 → +0.87% divergence → IMMATERIAL."""
        from rcm_mc.diligence.benchmarks import DivergenceStatus
        report = compute_cash_waterfall(
            self.ccd.claims, as_of_date=self.as_of,
            management_reported_revenue_by_cohort_month={"2024-02": 5_750.0},
        )
        cohort = report.mature_cohorts()[0]
        self.assertFalse(cohort.qor_flag)
        self.assertIsNotNone(cohort.qor_divergence_pct)
        self.assertLess(abs(cohort.qor_divergence_pct), 0.02)
        self.assertEqual(cohort.divergence_status,
                         DivergenceStatus.IMMATERIAL.value)

    def test_watch_tier_bands_between_2_and_5_percent(self):
        """Accrual $5,800 vs mgmt $5,600 → +3.57% → WATCH (2-5% band)."""
        from rcm_mc.diligence.benchmarks import DivergenceStatus
        report = compute_cash_waterfall(
            self.ccd.claims, as_of_date=self.as_of,
            management_reported_revenue_by_cohort_month={"2024-02": 5_600.0},
        )
        cohort = report.mature_cohorts()[0]
        pct = cohort.qor_divergence_pct
        self.assertIsNotNone(pct)
        self.assertGreaterEqual(abs(pct), 0.02)
        self.assertLess(abs(pct), 0.05)
        self.assertEqual(cohort.divergence_status,
                         DivergenceStatus.WATCH.value)
        # flag is reserved for >= 5% so WATCH does not flag
        self.assertFalse(cohort.qor_flag)

    def test_accrual_revenue_matches_formula(self):
        """accrual = gross − contractuals − final_denials_net − bad_debt."""
        report = compute_cash_waterfall(
            self.ccd.claims, as_of_date=self.as_of,
        )
        cohort = report.mature_cohorts()[0]
        expected_accrual = self.expected[
            "expected_waterfall"
        ]["accrual_revenue"]
        self.assertIsNotNone(cohort.accrual_revenue_usd)
        self.assertAlmostEqual(
            cohort.accrual_revenue_usd, expected_accrual, places=2,
        )

    def test_report_rolls_up_accrual_and_status(self):
        """Top-line accrual + divergence_status roll-up match per-cohort."""
        from rcm_mc.diligence.benchmarks import DivergenceStatus
        spec = self.expected["management_reported_revenue_for_qor_test"]
        report = compute_cash_waterfall(
            self.ccd.claims, as_of_date=self.as_of,
            management_reported_revenue_by_cohort_month={
                spec["cohort_month"]: spec["management_reported_revenue_usd"],
            },
        )
        self.assertAlmostEqual(
            report.total_accrual_revenue_usd,
            self.expected["expected_waterfall"]["accrual_revenue"],
            places=2,
        )
        self.assertEqual(
            report.total_divergence_status,
            DivergenceStatus.CRITICAL.value,
        )
        self.assertTrue(report.total_qor_flag)


class DivergenceClassifierTests(unittest.TestCase):
    """Pure-function banding tests — no CCD needed."""

    def test_none_returns_unknown(self):
        from rcm_mc.diligence.benchmarks import (
            DivergenceStatus, classify_divergence,
        )
        self.assertEqual(classify_divergence(None),
                         DivergenceStatus.UNKNOWN)

    def test_under_two_percent_is_immaterial(self):
        from rcm_mc.diligence.benchmarks import (
            DivergenceStatus, classify_divergence,
        )
        self.assertEqual(classify_divergence(0.0),
                         DivergenceStatus.IMMATERIAL)
        self.assertEqual(classify_divergence(0.0199),
                         DivergenceStatus.IMMATERIAL)
        self.assertEqual(classify_divergence(-0.0199),
                         DivergenceStatus.IMMATERIAL)

    def test_between_two_and_five_percent_is_watch(self):
        from rcm_mc.diligence.benchmarks import (
            DivergenceStatus, classify_divergence,
        )
        self.assertEqual(classify_divergence(0.02),
                         DivergenceStatus.WATCH)
        self.assertEqual(classify_divergence(0.03),
                         DivergenceStatus.WATCH)
        self.assertEqual(classify_divergence(-0.0499),
                         DivergenceStatus.WATCH)

    def test_five_percent_or_more_is_critical(self):
        from rcm_mc.diligence.benchmarks import (
            DivergenceStatus, classify_divergence,
        )
        self.assertEqual(classify_divergence(0.05),
                         DivergenceStatus.CRITICAL)
        self.assertEqual(classify_divergence(-0.16),
                         DivergenceStatus.CRITICAL)
        self.assertEqual(classify_divergence(1.5),
                         DivergenceStatus.CRITICAL)


class CashWaterfallProvenanceTests(unittest.TestCase):

    def test_every_step_carries_claim_ids(self):
        ccd = ingest_dataset(FIXTURE_ROOT / "hospital_06_waterfall_truth")
        report = compute_cash_waterfall(
            ccd.claims, as_of_date=date(2025, 1, 1),
        )
        cohort = report.mature_cohorts()[0]
        for s in cohort.steps:
            # Every step with a non-zero amount must name the claims
            # that contributed. Zero-amount steps can have empty lists.
            if s.amount_usd > 0:
                self.assertEqual(
                    len(s.claim_ids), s.claim_count,
                    msg=f"step {s.name}: claim_ids len {len(s.claim_ids)} != "
                        f"claim_count {s.claim_count}",
                )
                # IDs should be valid (non-empty strings).
                for cid in s.claim_ids:
                    self.assertIsInstance(cid, str)
                    self.assertTrue(cid, msg=f"empty claim_id in step {s.name}")


class CashWaterfallRollUpTests(unittest.TestCase):

    def test_totals_match_sum_over_mature_cohorts(self):
        ccd = ingest_dataset(FIXTURE_ROOT / "hospital_02_denial_heavy")
        report = compute_cash_waterfall(
            ccd.claims, as_of_date=date(2025, 1, 1),
        )
        expected_gross = sum(c.gross_charges_usd for c in report.mature_cohorts())
        expected_cash = sum(c.realized_cash_usd for c in report.mature_cohorts())
        self.assertAlmostEqual(
            report.total_gross_charges_usd, expected_gross, places=2,
        )
        self.assertAlmostEqual(
            report.total_realized_cash_usd, expected_cash, places=2,
        )
        self.assertAlmostEqual(
            report.total_realization_rate,
            expected_cash / expected_gross, places=4,
        )

    def test_json_round_trip_shape(self):
        ccd = ingest_dataset(FIXTURE_ROOT / "hospital_06_waterfall_truth")
        report = compute_cash_waterfall(
            ccd.claims, as_of_date=date(2025, 1, 1),
        )
        d = report.to_dict()
        self.assertIn("cohorts_all_payers", d)
        self.assertIn("cohorts_by_payer_class", d)
        self.assertIn("total_realized_cash_usd", d)
        self.assertIn("total_realization_rate", d)
        # QoR headline round-trip: accrual + divergence status travel
        # through to_dict so exports/packets can surface the banding.
        self.assertIn("total_accrual_revenue_usd", d)
        self.assertIn("total_divergence_status", d)
        first_cohort = d["cohorts_all_payers"][0]
        self.assertIn("accrual_revenue_usd", first_cohort)
        self.assertIn("divergence_status", first_cohort)
        # Cohort dict has the full step list.
        first_cohort = d["cohorts_all_payers"][0]
        self.assertIn("steps", first_cohort)
        self.assertEqual(
            [s["name"] for s in first_cohort["steps"]],
            ["gross_charges", "contractual_adjustments", "front_end_leakage",
             "initial_denials_gross", "appeals_recovered", "bad_debt",
             "realized_cash"],
        )


class CashWaterfallFixtureConcordantTests(unittest.TestCase):
    """Lock the math against ``hospital_07_waterfall_concordant``.

    Purpose: a hand-built reconciled hospital. 10 clean paid Medicare
    claims. Waterfall accrual $8,000 vs management $7,920 → +1.01%
    → IMMATERIAL banding. Tests the happy-path: no denials, no bad
    debt, divergence below the 2% threshold.
    """

    def setUp(self):
        self.ccd = ingest_dataset(
            FIXTURE_ROOT / "hospital_07_waterfall_concordant",
        )
        self.expected = json.loads(
            (FIXTURE_ROOT / "hospital_07_waterfall_concordant"
             / "expected.json").read_text("utf-8")
        )
        self.as_of = date.fromisoformat(self.expected["as_of_date"])

    def test_waterfall_steps_match_expected(self):
        report = compute_cash_waterfall(
            self.ccd.claims, as_of_date=self.as_of,
        )
        cohort = report.mature_cohorts()[0]
        steps = {s.name: s for s in cohort.steps}
        ew = self.expected["expected_waterfall"]
        for key in ("gross_charges", "contractual_adjustments",
                    "front_end_leakage", "initial_denials_gross",
                    "appeals_recovered", "bad_debt", "realized_cash"):
            self.assertAlmostEqual(steps[key].amount_usd, ew[key], places=2,
                                   msg=f"step {key!r} amount mismatch")
        self.assertAlmostEqual(cohort.accrual_revenue_usd,
                               ew["accrual_revenue"], places=2)

    def test_management_reconciliation_is_immaterial(self):
        from rcm_mc.diligence.benchmarks import DivergenceStatus
        spec = self.expected["management_reported_revenue_for_qor_test"]
        report = compute_cash_waterfall(
            self.ccd.claims, as_of_date=self.as_of,
            management_reported_revenue_by_cohort_month={
                spec["cohort_month"]: spec["management_reported_revenue_usd"],
            },
        )
        cohort = report.mature_cohorts()[0]
        self.assertAlmostEqual(cohort.qor_divergence_usd,
                               spec["expected_qor_divergence_usd"], places=2)
        self.assertAlmostEqual(cohort.qor_divergence_pct,
                               spec["expected_qor_divergence_pct"], places=5)
        self.assertFalse(cohort.qor_flag)
        self.assertEqual(cohort.divergence_status,
                         DivergenceStatus.IMMATERIAL.value)
        # Top-line status rolls up to IMMATERIAL too.
        self.assertEqual(report.total_divergence_status,
                         DivergenceStatus.IMMATERIAL.value)


class CashWaterfallFixtureCriticalTests(unittest.TestCase):
    """Lock the math against ``hospital_08_waterfall_critical``.

    Purpose: a hand-built over-reporting hospital. 8 paid + 2 clinical
    denials. Waterfall accrual $6,400; management over-reports at
    $6,850 → -6.57% → CRITICAL. Tests the failure-path: mgmt OVER
    what the claims-side reconstruction supports, by more than the
    5% threshold.
    """

    def setUp(self):
        self.ccd = ingest_dataset(
            FIXTURE_ROOT / "hospital_08_waterfall_critical",
        )
        self.expected = json.loads(
            (FIXTURE_ROOT / "hospital_08_waterfall_critical"
             / "expected.json").read_text("utf-8")
        )
        self.as_of = date.fromisoformat(self.expected["as_of_date"])

    def test_waterfall_steps_match_expected(self):
        report = compute_cash_waterfall(
            self.ccd.claims, as_of_date=self.as_of,
        )
        cohort = report.mature_cohorts()[0]
        steps = {s.name: s for s in cohort.steps}
        ew = self.expected["expected_waterfall"]
        for key in ("gross_charges", "contractual_adjustments",
                    "front_end_leakage", "initial_denials_gross",
                    "appeals_recovered", "bad_debt", "realized_cash"):
            self.assertAlmostEqual(steps[key].amount_usd, ew[key], places=2,
                                   msg=f"step {key!r} amount mismatch")
        self.assertAlmostEqual(cohort.accrual_revenue_usd,
                               ew["accrual_revenue"], places=2)

    def test_management_reconciliation_is_critical(self):
        from rcm_mc.diligence.benchmarks import DivergenceStatus
        spec = self.expected["management_reported_revenue_for_qor_test"]
        report = compute_cash_waterfall(
            self.ccd.claims, as_of_date=self.as_of,
            management_reported_revenue_by_cohort_month={
                spec["cohort_month"]: spec["management_reported_revenue_usd"],
            },
        )
        cohort = report.mature_cohorts()[0]
        self.assertAlmostEqual(cohort.qor_divergence_usd,
                               spec["expected_qor_divergence_usd"], places=2)
        self.assertAlmostEqual(cohort.qor_divergence_pct,
                               spec["expected_qor_divergence_pct"], places=5)
        self.assertLess(cohort.qor_divergence_pct, 0.0,
                        msg="critical case: mgmt over-reports → negative delta")
        self.assertTrue(cohort.qor_flag)
        self.assertEqual(cohort.divergence_status,
                         DivergenceStatus.CRITICAL.value)
        self.assertEqual(report.total_divergence_status,
                         DivergenceStatus.CRITICAL.value)


class CashWaterfallPayerSliceTests(unittest.TestCase):

    def test_per_payer_class_cohorts_produced(self):
        ccd = ingest_dataset(FIXTURE_ROOT / "hospital_04_mixed_payer")
        report = compute_cash_waterfall(
            ccd.claims, as_of_date=date(2025, 1, 1), by_payer_class=True,
        )
        # hospital_04 has 4 payer classes: MEDICARE, MEDICAID, COMMERCIAL, SELF_PAY
        self.assertIn("MEDICARE", report.cohorts_by_payer_class)
        self.assertIn("COMMERCIAL", report.cohorts_by_payer_class)
        # Each class's gross charges should be <= the all-payers total.
        total_gross_all = sum(
            c.gross_charges_usd for c in report.cohorts_all_payers
        )
        for pc, cohorts in report.cohorts_by_payer_class.items():
            pc_gross = sum(c.gross_charges_usd for c in cohorts)
            self.assertLessEqual(pc_gross, total_gross_all + 0.01)


if __name__ == "__main__":
    unittest.main()
