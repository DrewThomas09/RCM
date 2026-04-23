"""Contract Re-Pricer regression tests.

Session N+2 session deliverable: an engine that accepts a structured
ContractSchedule and re-prices historical claims against it,
producing derived per-payer leverage that drops into the v2
bridge's ``BridgeAssumptions.payer_revenue_leverage`` hook.

Tests cover, in order:

- Construction + validation of ``ContractRate`` (mutually-exclusive
  primitive fields).
- Per-claim re-pricing on every reason path: matched, carve-out,
  stop-loss, withhold, no-contract, missing-data.
- Roll-up math on a synthetic CCD: per-payer totals, recovery
  ratios, JSON round-trip.
- Derived payer leverage: baseline normalisation to Commercial,
  drop-in shape for ``BridgeAssumptions.payer_revenue_leverage``.
- CCD ↔ bridge PayerClass vocabulary mapping: MEDICARE →
  medicare_ffs, TRICARE → managed_government, etc.

Fixtures are built inline as ``CanonicalClaim`` dataclass instances
— no new kpi_truth directory. Keeps the re-pricer's tests hermetic
from the Phase 2 KPI fixtures.
"""
from __future__ import annotations

import unittest
from dataclasses import replace

from rcm_mc.diligence.benchmarks import (
    CCD_TO_BRIDGE_PAYER_CLASS,
    REASON_CARVE_OUT,
    REASON_MATCHED,
    REASON_MISSING_DATA,
    REASON_NO_CONTRACT,
    REASON_STOP_LOSS_APPLIED,
    REASON_WITHHOLD_APPLIED,
    ContractRate,
    ContractSchedule,
    payer_leverage_for_bridge,
    reprice_claim,
    reprice_claims,
)
from rcm_mc.diligence.ingest.ccd import CanonicalClaim, PayerClass


def _claim(
    *, claim_id: str, cpt: str, payer: PayerClass,
    charge: float, allowed: float,
) -> CanonicalClaim:
    """Tiny factory for test claims. Only the fields the re-pricer
    touches — everything else takes the dataclass defaults."""
    return CanonicalClaim(
        claim_id=claim_id, line_number=1, source_system="test",
        source_file="inline.csv", source_row=1,
        ccd_row_id=f"r-{claim_id}",
        patient_id=f"P-{claim_id}",
        cpt_code=cpt, payer_class=payer,
        charge_amount=charge, allowed_amount=allowed,
        paid_amount=allowed,
    )


class ContractRateValidationTests(unittest.TestCase):

    def test_flat_fee_rate_accepted(self):
        r = ContractRate(payer_class="MEDICARE", cpt_code="99213",
                         allowed_amount_usd=75.0)
        self.assertEqual(r.allowed_amount_usd, 75.0)

    def test_pct_of_charge_rate_accepted(self):
        r = ContractRate(payer_class="COMMERCIAL", cpt_code="99214",
                         allowed_pct_of_charge=0.65)
        self.assertEqual(r.allowed_pct_of_charge, 0.65)

    def test_both_amount_and_pct_raises(self):
        with self.assertRaises(ValueError):
            ContractRate(payer_class="MEDICARE", cpt_code="99213",
                         allowed_amount_usd=75.0,
                         allowed_pct_of_charge=0.5)

    def test_neither_amount_nor_pct_nor_carve_out_raises(self):
        with self.assertRaises(ValueError):
            ContractRate(payer_class="MEDICARE", cpt_code="99213")

    def test_carve_out_accepted_without_amount(self):
        r = ContractRate(payer_class="COMMERCIAL", cpt_code="97110",
                         is_carve_out=True)
        self.assertTrue(r.is_carve_out)

    def test_invalid_withhold_raises(self):
        with self.assertRaises(ValueError):
            ContractRate(payer_class="MEDICARE", cpt_code="99213",
                         allowed_amount_usd=75.0, withhold_pct=1.5)


class PerClaimRepricingTests(unittest.TestCase):

    def test_flat_fee_match(self):
        sched = ContractSchedule(rates=[
            ContractRate(payer_class="MEDICARE", cpt_code="99213",
                         allowed_amount_usd=75.0),
        ])
        c = _claim(claim_id="C1", cpt="99213", payer=PayerClass.MEDICARE,
                   charge=150.0, allowed=72.0)
        r = reprice_claim(c, sched)
        self.assertEqual(r.reason, REASON_MATCHED)
        self.assertAlmostEqual(r.repriced_allowed_usd, 75.0)
        self.assertAlmostEqual(r.delta_usd, 3.0)   # under-collection of $3
        self.assertEqual(r.payer_class_bridge, "medicare_ffs")

    def test_pct_of_charge_match(self):
        sched = ContractSchedule(rates=[
            ContractRate(payer_class="COMMERCIAL", cpt_code="99214",
                         allowed_pct_of_charge=0.65),
        ])
        c = _claim(claim_id="C2", cpt="99214", payer=PayerClass.COMMERCIAL,
                   charge=200.0, allowed=120.0)
        r = reprice_claim(c, sched)
        self.assertEqual(r.reason, REASON_MATCHED)
        self.assertAlmostEqual(r.repriced_allowed_usd, 130.0)   # 0.65 × 200
        self.assertAlmostEqual(r.delta_usd, 10.0)

    def test_carve_out_uses_schedule_default(self):
        sched = ContractSchedule(
            rates=[ContractRate(payer_class="COMMERCIAL", cpt_code="97110",
                                is_carve_out=True,
                                note="PT/OT carved out")],
            default_carve_out_rate_pct=0.40,
        )
        c = _claim(claim_id="C3", cpt="97110", payer=PayerClass.COMMERCIAL,
                   charge=100.0, allowed=50.0)
        r = reprice_claim(c, sched)
        self.assertEqual(r.reason, REASON_CARVE_OUT)
        self.assertAlmostEqual(r.repriced_allowed_usd, 40.0)   # 0.40 × 100
        self.assertEqual(r.contract_note, "PT/OT carved out")

    def test_stop_loss_applies_on_high_charge(self):
        sched = ContractSchedule(rates=[
            ContractRate(payer_class="COMMERCIAL", cpt_code="99223",
                         allowed_amount_usd=800.0,
                         stop_loss_threshold_usd=50_000.0,
                         stop_loss_rate_pct_of_charge=0.75),
        ])
        # Charge of 60k > 50k threshold → 75% of 60k = 45k
        c = _claim(claim_id="C4", cpt="99223", payer=PayerClass.COMMERCIAL,
                   charge=60_000.0, allowed=20_000.0)
        r = reprice_claim(c, sched)
        self.assertEqual(r.reason, REASON_STOP_LOSS_APPLIED)
        self.assertAlmostEqual(r.repriced_allowed_usd, 45_000.0)

    def test_stop_loss_does_not_apply_below_threshold(self):
        sched = ContractSchedule(rates=[
            ContractRate(payer_class="COMMERCIAL", cpt_code="99223",
                         allowed_amount_usd=800.0,
                         stop_loss_threshold_usd=50_000.0,
                         stop_loss_rate_pct_of_charge=0.75),
        ])
        c = _claim(claim_id="C4b", cpt="99223", payer=PayerClass.COMMERCIAL,
                   charge=40_000.0, allowed=800.0)
        r = reprice_claim(c, sched)
        self.assertEqual(r.reason, REASON_MATCHED)
        self.assertAlmostEqual(r.repriced_allowed_usd, 800.0)

    def test_withhold_reduces_matched_amount(self):
        # 2% withhold — repriced = 100 × 0.98 = 98
        sched = ContractSchedule(rates=[
            ContractRate(payer_class="MEDICARE_ADVANTAGE", cpt_code="99213",
                         allowed_amount_usd=100.0, withhold_pct=0.02),
        ])
        c = _claim(claim_id="C5", cpt="99213",
                   payer=PayerClass.MEDICARE_ADVANTAGE,
                   charge=150.0, allowed=98.0)
        r = reprice_claim(c, sched)
        self.assertEqual(r.reason, REASON_WITHHOLD_APPLIED)
        self.assertAlmostEqual(r.repriced_allowed_usd, 98.0)

    def test_no_contract_keeps_observed(self):
        sched = ContractSchedule(rates=[
            ContractRate(payer_class="MEDICARE", cpt_code="99213",
                         allowed_amount_usd=75.0),
        ])
        # CPT 99214 is not in the schedule.
        c = _claim(claim_id="C6", cpt="99214", payer=PayerClass.MEDICARE,
                   charge=200.0, allowed=110.0)
        r = reprice_claim(c, sched)
        self.assertEqual(r.reason, REASON_NO_CONTRACT)
        self.assertAlmostEqual(r.repriced_allowed_usd, 110.0)
        self.assertAlmostEqual(r.delta_usd, 0.0)

    def test_missing_cpt_or_payer_flagged(self):
        sched = ContractSchedule(rates=[
            ContractRate(payer_class="MEDICARE", cpt_code="99213",
                         allowed_amount_usd=75.0),
        ])
        c = _claim(claim_id="C7", cpt="", payer=PayerClass.MEDICARE,
                   charge=150.0, allowed=72.0)
        r = reprice_claim(c, sched)
        self.assertEqual(r.reason, REASON_MISSING_DATA)

    # ── Vocabulary mapping ──────────────────────────────────────────

    def test_ccd_medicare_maps_to_medicare_ffs(self):
        sched = ContractSchedule(rates=[
            ContractRate(payer_class="MEDICARE", cpt_code="99213",
                         allowed_amount_usd=75.0),
        ])
        c = _claim(claim_id="C8", cpt="99213", payer=PayerClass.MEDICARE,
                   charge=150.0, allowed=72.0)
        r = reprice_claim(c, sched)
        self.assertEqual(r.payer_class_bridge, "medicare_ffs")

    def test_tricare_maps_to_managed_government(self):
        sched = ContractSchedule(rates=[
            ContractRate(payer_class="TRICARE", cpt_code="99213",
                         allowed_amount_usd=80.0),
        ])
        c = _claim(claim_id="C9", cpt="99213", payer=PayerClass.TRICARE,
                   charge=150.0, allowed=78.0)
        r = reprice_claim(c, sched)
        self.assertEqual(r.payer_class_bridge, "managed_government")

    def test_medicare_advantage_maps_correctly(self):
        self.assertEqual(
            CCD_TO_BRIDGE_PAYER_CLASS["MEDICARE_ADVANTAGE"],
            "medicare_advantage",
        )

    def test_workers_comp_maps_to_managed_government(self):
        self.assertEqual(
            CCD_TO_BRIDGE_PAYER_CLASS["WORKERS_COMP"],
            "managed_government",
        )


class RepricingRollUpTests(unittest.TestCase):

    def setUp(self):
        self.sched = ContractSchedule(
            rates=[
                ContractRate(payer_class="COMMERCIAL", cpt_code="99213",
                             allowed_amount_usd=100.0),
                ContractRate(payer_class="MEDICARE", cpt_code="99213",
                             allowed_amount_usd=75.0),
                ContractRate(payer_class="MEDICAID", cpt_code="99213",
                             allowed_amount_usd=50.0),
            ],
            name="test_schedule",
        )

    def test_total_claims_accounted_for(self):
        claims = [
            _claim(claim_id="A", cpt="99213", payer=PayerClass.COMMERCIAL,
                   charge=150, allowed=95),
            _claim(claim_id="B", cpt="99213", payer=PayerClass.MEDICARE,
                   charge=150, allowed=72),
            _claim(claim_id="C", cpt="99213", payer=PayerClass.MEDICAID,
                   charge=150, allowed=48),
            # Unmatched — no contract for 99214.
            _claim(claim_id="D", cpt="99214", payer=PayerClass.COMMERCIAL,
                   charge=200, allowed=130),
        ]
        report = reprice_claims(claims, self.sched)
        self.assertEqual(report.total_claims, 4)
        self.assertEqual(report.matched_claims, 3)
        self.assertEqual(report.unmatched_claims, 1)

    def test_per_payer_rollup_totals(self):
        claims = [
            _claim(claim_id="A1", cpt="99213", payer=PayerClass.COMMERCIAL,
                   charge=150, allowed=95),
            _claim(claim_id="A2", cpt="99213", payer=PayerClass.COMMERCIAL,
                   charge=150, allowed=98),
            _claim(claim_id="M1", cpt="99213", payer=PayerClass.MEDICARE,
                   charge=150, allowed=72),
        ]
        report = reprice_claims(claims, self.sched)
        self.assertIn("commercial", report.by_payer_class)
        self.assertIn("medicare_ffs", report.by_payer_class)
        comm = report.by_payer_class["commercial"]
        self.assertEqual(comm.claim_count, 2)
        self.assertAlmostEqual(comm.total_observed_allowed_usd, 193.0)
        self.assertAlmostEqual(comm.total_repriced_allowed_usd, 200.0)
        self.assertAlmostEqual(comm.recovery_ratio, 193.0 / 200.0, places=4)
        mcr = report.by_payer_class["medicare_ffs"]
        self.assertEqual(mcr.claim_count, 1)
        self.assertAlmostEqual(mcr.avg_repriced_per_claim, 75.0)
        self.assertAlmostEqual(mcr.avg_observed_per_claim, 72.0)

    def test_unmatched_claims_do_not_bias_rollup(self):
        """An unmatched claim must not appear in any payer roll-up
        — doing so would set recovery_ratio = 1.0 (observed ==
        repriced) and corrupt the derived leverage."""
        claims = [
            _claim(claim_id="M1", cpt="99213", payer=PayerClass.MEDICARE,
                   charge=150, allowed=72),
            # Unmatched but same payer class — must not be in roll-up.
            _claim(claim_id="M2", cpt="99999", payer=PayerClass.MEDICARE,
                   charge=200, allowed=150),
        ]
        report = reprice_claims(claims, self.sched)
        mcr = report.by_payer_class["medicare_ffs"]
        # Only the matched claim.
        self.assertEqual(mcr.claim_count, 1)
        self.assertAlmostEqual(mcr.total_repriced_allowed_usd, 75.0)


class DerivedPayerLeverageTests(unittest.TestCase):
    """The output of derived_payer_leverage() must drop into
    ``BridgeAssumptions.payer_revenue_leverage`` directly."""

    def test_baseline_commercial_is_one(self):
        sched = ContractSchedule(rates=[
            ContractRate(payer_class="COMMERCIAL", cpt_code="99213",
                         allowed_amount_usd=100.0),
            ContractRate(payer_class="MEDICARE", cpt_code="99213",
                         allowed_amount_usd=75.0),
        ])
        claims = [
            _claim(claim_id="C1", cpt="99213", payer=PayerClass.COMMERCIAL,
                   charge=150, allowed=100),
            _claim(claim_id="M1", cpt="99213", payer=PayerClass.MEDICARE,
                   charge=150, allowed=75),
        ]
        report = reprice_claims(claims, sched)
        leverage = payer_leverage_for_bridge(report)
        self.assertAlmostEqual(leverage["commercial"], 1.0, places=4)
        self.assertAlmostEqual(leverage["medicare_ffs"], 0.75, places=4)

    def test_output_keys_match_bridge_vocabulary(self):
        """The dict keys must be the v2 bridge's PayerClass values
        (lowercase strings) so ``BridgeAssumptions.payer_revenue_leverage``
        consumes them directly. No translation needed."""
        sched = ContractSchedule(rates=[
            ContractRate(payer_class="COMMERCIAL", cpt_code="99213",
                         allowed_amount_usd=100.0),
            ContractRate(payer_class="MEDICARE", cpt_code="99213",
                         allowed_amount_usd=75.0),
            ContractRate(payer_class="MEDICARE_ADVANTAGE", cpt_code="99213",
                         allowed_amount_usd=80.0),
            ContractRate(payer_class="MEDICAID", cpt_code="99213",
                         allowed_amount_usd=50.0),
        ])
        claims = [
            _claim(claim_id="C1", cpt="99213", payer=PayerClass.COMMERCIAL,
                   charge=150, allowed=100),
            _claim(claim_id="M1", cpt="99213", payer=PayerClass.MEDICARE,
                   charge=150, allowed=75),
            _claim(claim_id="MA1", cpt="99213",
                   payer=PayerClass.MEDICARE_ADVANTAGE,
                   charge=150, allowed=80),
            _claim(claim_id="D1", cpt="99213", payer=PayerClass.MEDICAID,
                   charge=150, allowed=50),
        ]
        report = reprice_claims(claims, sched)
        leverage = payer_leverage_for_bridge(report)
        # Lowercase vocabulary, matching v2 bridge's PayerClass enum.
        expected_keys = {"commercial", "medicare_ffs", "medicare_advantage",
                         "medicaid"}
        self.assertEqual(set(leverage.keys()), expected_keys)
        for v in leverage.values():
            self.assertIsInstance(v, float)
            self.assertGreater(v, 0.0)

    def test_baseline_missing_falls_back_to_recovery_ratio(self):
        """Schedule with no Commercial rate → derived_payer_leverage
        falls back to each payer's recovery_ratio (observed/repriced)
        so the number stays meaningful even without a baseline."""
        sched = ContractSchedule(rates=[
            ContractRate(payer_class="MEDICARE", cpt_code="99213",
                         allowed_amount_usd=75.0),
        ])
        claims = [
            _claim(claim_id="M1", cpt="99213", payer=PayerClass.MEDICARE,
                   charge=150, allowed=60),
        ]
        report = reprice_claims(claims, sched)
        leverage = payer_leverage_for_bridge(report)
        # observed 60, repriced 75 → recovery_ratio 0.80
        self.assertAlmostEqual(leverage["medicare_ffs"], 60 / 75, places=4)


class RepricingReportJSONTests(unittest.TestCase):

    def test_to_dict_shape(self):
        sched = ContractSchedule(rates=[
            ContractRate(payer_class="MEDICARE", cpt_code="99213",
                         allowed_amount_usd=75.0),
        ])
        claims = [_claim(claim_id="X1", cpt="99213",
                         payer=PayerClass.MEDICARE,
                         charge=150, allowed=72)]
        report = reprice_claims(claims, sched)
        d = report.to_dict()
        for k in ("schedule_name", "total_claims", "matched_claims",
                  "total_observed_allowed_usd",
                  "total_repriced_allowed_usd",
                  "by_payer_class", "per_claim_results",
                  "derived_payer_leverage"):
            self.assertIn(k, d)


if __name__ == "__main__":
    unittest.main()
