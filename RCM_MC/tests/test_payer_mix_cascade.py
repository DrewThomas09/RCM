"""Tests for payer mix shift cascade model."""
from __future__ import annotations

import unittest


class TestPayerMix(unittest.TestCase):
    def test_normalization(self):
        from rcm_mc.ml.payer_mix_cascade import PayerMix
        # Slightly-off mix gets renormalized
        mix = PayerMix(medicare=0.4, medicaid=0.15,
                       commercial=0.4, self_pay=0.06)
        normed = mix.normalize()
        total = (normed.medicare + normed.medicaid
                 + normed.commercial + normed.self_pay)
        self.assertAlmostEqual(total, 1.0, places=5)

    def test_zero_mix_rejected(self):
        from rcm_mc.ml.payer_mix_cascade import PayerMix
        mix = PayerMix(medicare=0, medicaid=0,
                       commercial=0, self_pay=0)
        with self.assertRaises(ValueError):
            mix.normalize()

    def test_to_dict(self):
        from rcm_mc.ml.payer_mix_cascade import PayerMix
        mix = PayerMix(medicare=0.5, medicaid=0.1,
                       commercial=0.35, self_pay=0.05)
        d = mix.to_dict()
        self.assertEqual(d["medicare"], 0.5)
        self.assertEqual(d["self_pay"], 0.05)


class TestBaselineMetrics(unittest.TestCase):
    def test_baseline_with_typical_mix(self):
        from rcm_mc.ml.payer_mix_cascade import (
            PayerMix, compute_baseline_metrics,
        )
        mix = PayerMix(medicare=0.40, medicaid=0.15,
                       commercial=0.40, self_pay=0.05)
        metrics = compute_baseline_metrics(
            mix, annual_gross_charges=1_000_000_000)
        # Revenue index should be ~weighted avg
        # 0.4*0.79 + 0.15*0.58 + 0.4*1.0 + 0.05*0.15 = 0.81
        self.assertGreater(
            metrics["revenue_index"], 0.75)
        self.assertLess(metrics["revenue_index"], 0.90)
        # NPR = gross × revenue_index
        self.assertGreater(metrics["npr"], 750_000_000)
        # AR balance = NPR × DSO/365
        self.assertGreater(metrics["ar_balance"], 0)

    def test_pure_commercial_mix_has_baseline_index(self):
        """100% commercial → revenue_index = 1.0."""
        from rcm_mc.ml.payer_mix_cascade import (
            PayerMix, compute_baseline_metrics,
        )
        mix = PayerMix(medicare=0, medicaid=0,
                       commercial=1.0, self_pay=0)
        metrics = compute_baseline_metrics(mix)
        self.assertAlmostEqual(
            metrics["revenue_index"], 1.0)
        self.assertAlmostEqual(
            metrics["denial_rate"], 0.06)


class TestCascade(unittest.TestCase):
    def test_commercial_to_medicaid_shift(self):
        """5pp commercial → medicaid shift compresses everything."""
        from rcm_mc.ml.payer_mix_cascade import (
            PayerMix, cascade_payer_mix_shift,
        )
        baseline = PayerMix(
            medicare=0.40, medicaid=0.10,
            commercial=0.45, self_pay=0.05)
        new = PayerMix(
            medicare=0.40, medicaid=0.15,
            commercial=0.40, self_pay=0.05)
        result = cascade_payer_mix_shift(
            baseline, new,
            annual_gross_charges=1_000_000_000)
        # Mix delta detected
        self.assertAlmostEqual(
            result.mix_delta_pp["commercial"],
            -5.0, places=1)
        self.assertAlmostEqual(
            result.mix_delta_pp["medicaid"], 5.0, places=1)
        # Revenue index goes DOWN (commercial = 1.0,
        # medicaid = 0.58)
        self.assertLess(
            result.new_revenue_index,
            result.baseline_revenue_index)
        # Denial rate goes UP
        self.assertGreater(result.denial_rate_delta_pp, 0)
        # DSO goes UP
        self.assertGreater(result.days_in_ar_delta, 0)
        # Collection rate goes DOWN
        self.assertLess(
            result.collection_rate_delta_pp, 0)
        # NPR goes DOWN (negative dollars)
        self.assertLess(result.npr_delta_dollars, 0)
        # AR balance impact (working capital)
        self.assertNotEqual(
            result.ar_balance_delta_dollars, 0)
        # EBITDA goes DOWN
        self.assertLess(result.ebitda_delta_dollars, 0)
        # Notes mention compression
        self.assertTrue(any(
            "Commercial" in n or "Medicaid" in n
            or "compression" in n
            for n in result.notes))

    def test_no_shift_zero_deltas(self):
        from rcm_mc.ml.payer_mix_cascade import (
            PayerMix, cascade_payer_mix_shift,
        )
        mix = PayerMix(medicare=0.40, medicaid=0.15,
                       commercial=0.40, self_pay=0.05)
        result = cascade_payer_mix_shift(mix, mix)
        self.assertAlmostEqual(
            result.npr_delta_dollars, 0, places=0)
        self.assertAlmostEqual(
            result.ebitda_delta_dollars, 0, places=0)
        self.assertAlmostEqual(
            result.days_in_ar_delta, 0, places=2)

    def test_self_pay_growth_flagged(self):
        """Self-pay >+2pp triggers bad-debt note."""
        from rcm_mc.ml.payer_mix_cascade import (
            PayerMix, cascade_payer_mix_shift,
        )
        baseline = PayerMix(
            medicare=0.40, medicaid=0.15,
            commercial=0.40, self_pay=0.05)
        new = PayerMix(
            medicare=0.40, medicaid=0.15,
            commercial=0.37, self_pay=0.08)
        result = cascade_payer_mix_shift(baseline, new)
        # Bad debt grew
        self.assertGreater(
            result.bad_debt_delta_dollars, 0)
        # Note about self-pay
        self.assertTrue(any(
            "Self-pay" in n for n in result.notes))

    def test_commercial_growth_improves_everything(self):
        """Reverse case: commercial up, others down — should
        improve all metrics."""
        from rcm_mc.ml.payer_mix_cascade import (
            PayerMix, cascade_payer_mix_shift,
        )
        baseline = PayerMix(
            medicare=0.40, medicaid=0.20,
            commercial=0.35, self_pay=0.05)
        new = PayerMix(
            medicare=0.40, medicaid=0.15,
            commercial=0.40, self_pay=0.05)
        result = cascade_payer_mix_shift(baseline, new)
        self.assertGreater(
            result.new_revenue_index,
            result.baseline_revenue_index)
        self.assertLess(result.denial_rate_delta_pp, 0)
        self.assertLess(result.days_in_ar_delta, 0)
        self.assertGreater(
            result.ebitda_delta_dollars, 0)


class TestSensitivitySweep(unittest.TestCase):
    def test_sweep_runs(self):
        from rcm_mc.ml.payer_mix_cascade import (
            PayerMix, sensitivity_sweep,
        )
        baseline = PayerMix(
            medicare=0.40, medicaid=0.15,
            commercial=0.40, self_pay=0.05)
        sweep = sensitivity_sweep(
            baseline, payer="commercial",
            counterparty="medicaid",
            deltas_pp=(-5, -3, -1, 1, 3, 5))
        self.assertEqual(len(sweep), 6)
        # Sorted ascending by delta_pp
        deltas = [d for d, _ in sweep]
        self.assertEqual(deltas, sorted(deltas))
        # EBITDA should be monotonic with commercial-share
        # change
        ebitda_deltas = [
            r.ebitda_delta_dollars for _, r in sweep]
        self.assertEqual(
            ebitda_deltas, sorted(ebitda_deltas))

    def test_unknown_payer_rejected(self):
        from rcm_mc.ml.payer_mix_cascade import (
            PayerMix, sensitivity_sweep,
        )
        with self.assertRaises(ValueError):
            sensitivity_sweep(
                PayerMix(), payer="purple")

    def test_same_payer_counterparty_rejected(self):
        from rcm_mc.ml.payer_mix_cascade import (
            PayerMix, sensitivity_sweep,
        )
        with self.assertRaises(ValueError):
            sensitivity_sweep(
                PayerMix(),
                payer="commercial",
                counterparty="commercial")

    def test_invalid_shifts_skipped(self):
        """Shift that pushes commercial below 0 is skipped."""
        from rcm_mc.ml.payer_mix_cascade import (
            PayerMix, sensitivity_sweep,
        )
        # Only 5% commercial — can't shift -10pp
        baseline = PayerMix(
            medicare=0.55, medicaid=0.30,
            commercial=0.05, self_pay=0.10)
        sweep = sensitivity_sweep(
            baseline, payer="commercial",
            counterparty="medicaid",
            deltas_pp=(-10, -5, -1, 1, 5))
        # -10pp shift skipped (commercial would go to -5%)
        deltas = [d for d, _ in sweep]
        self.assertNotIn(-10, deltas)


if __name__ == "__main__":
    unittest.main()
