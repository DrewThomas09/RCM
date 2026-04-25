"""Tests for the improvement potential estimator."""
from __future__ import annotations

import unittest


def _profile():
    from rcm_mc.pe.rcm_ebitda_bridge import FinancialProfile
    return FinancialProfile(
        gross_revenue=1_300_000_000,
        net_revenue=400_000_000,
        total_operating_expenses=370_000_000,
        current_ebitda=30_000_000,
        total_claims_volume=300_000,
        payer_mix={"medicare": 0.40, "medicaid": 0.15,
                   "commercial": 0.45},
    )


class TestSignedGap(unittest.TestCase):
    def test_lower_is_better(self):
        from rcm_mc.ml.improvement_potential import _signed_gap
        # current 12, target 7 → 5 of room
        self.assertEqual(
            _signed_gap(12, 7, "lower_is_better"), 5)
        # already-better than target → negative gap
        self.assertEqual(
            _signed_gap(5, 7, "lower_is_better"), -2)

    def test_higher_is_better(self):
        from rcm_mc.ml.improvement_potential import _signed_gap
        self.assertEqual(
            _signed_gap(85, 95, "higher_is_better"), 10)
        self.assertEqual(
            _signed_gap(96, 95, "higher_is_better"), -1)


class TestApplyRealism(unittest.TestCase):
    def test_60pct_closure_lower_better(self):
        from rcm_mc.ml.improvement_potential import _apply_realism
        # 12 → 7 with 0.6 realism = 12 - 0.6*5 = 9.0
        result = _apply_realism(12, 7, 0.6,
                                "lower_is_better")
        self.assertAlmostEqual(result, 9.0)

    def test_higher_better_closes_upward(self):
        from rcm_mc.ml.improvement_potential import _apply_realism
        # 85 → 95 with 0.5 realism = 85 + 0.5*10 = 90
        result = _apply_realism(85, 95, 0.5,
                                "higher_is_better")
        self.assertAlmostEqual(result, 90.0)

    def test_no_room_returns_current(self):
        from rcm_mc.ml.improvement_potential import _apply_realism
        # Already at target → no change
        self.assertEqual(
            _apply_realism(7, 12, 0.6, "lower_is_better"),
            7)


class TestEstimator(unittest.TestCase):
    def test_basic_estimate_produces_uplift(self):
        from rcm_mc.ml.improvement_potential import (
            PeerBenchmarks,
            estimate_improvement_potential,
        )
        bm = PeerBenchmarks(
            denial_rate=7.0,
            days_in_ar=38.0,
            net_collection_rate=97.0,
            clean_claim_rate=96.0,
            cost_to_collect=3.0,
            case_mix_index=1.50,
            target_percentile=75,
        )
        current = {
            "denial_rate": 12.0,
            "days_in_ar": 55.0,
            "net_collection_rate": 92.0,
            "clean_claim_rate": 85.0,
            "cost_to_collect": 5.0,
            "case_mix_index": 1.30,
        }
        result = estimate_improvement_potential(
            _profile(), current, bm)
        # Should produce positive uplift across multiple levers
        self.assertGreater(
            result.realistic_total_ebitda, 1_000_000)
        # On $400M NPR, realistic uplift typically lands $5M-$30M
        self.assertGreater(len(result.levers), 3)
        # Optimistic > realistic > conservative
        self.assertGreater(
            result.optimistic_total_ebitda,
            result.realistic_total_ebitda)
        self.assertGreater(
            result.realistic_total_ebitda,
            result.conservative_total_ebitda)
        # Pct of NPR computed
        self.assertIsNotNone(
            result.realistic_uplift_pct_of_npr)

    def test_already_at_target_skipped(self):
        from rcm_mc.ml.improvement_potential import (
            PeerBenchmarks,
            estimate_improvement_potential,
        )
        bm = PeerBenchmarks(denial_rate=7.0)
        # Hospital already better than peer
        current = {"denial_rate": 5.0}
        result = estimate_improvement_potential(
            _profile(), current, bm)
        self.assertEqual(len(result.levers), 0)
        # Notes mention the lever was skipped
        self.assertEqual(len(result.notes), 1)
        self.assertIn("denial_rate", result.notes[0])

    def test_missing_benchmark_skipped(self):
        """If we don't have a peer target for a lever, skip it
        (we don't make up targets)."""
        from rcm_mc.ml.improvement_potential import (
            PeerBenchmarks,
            estimate_improvement_potential,
        )
        bm = PeerBenchmarks(denial_rate=7.0)
        current = {
            "denial_rate": 12.0,
            "days_in_ar": 55.0,  # no benchmark for this
        }
        result = estimate_improvement_potential(
            _profile(), current, bm)
        levers = {lv.lever for lv in result.levers}
        self.assertIn("denial_rate", levers)
        self.assertNotIn("days_in_ar", levers)

    def test_realism_factor_override(self):
        """Higher realism = higher modeled gap closure → bigger
        EBITDA uplift."""
        from rcm_mc.ml.improvement_potential import (
            PeerBenchmarks,
            estimate_improvement_potential,
        )
        bm = PeerBenchmarks(denial_rate=7.0)
        current = {"denial_rate": 12.0}

        baseline = estimate_improvement_potential(
            _profile(), current, bm)
        aggressive = estimate_improvement_potential(
            _profile(), current, bm,
            realism_factors={"denial_rate": 0.95})

        self.assertGreater(
            aggressive.realistic_total_ebitda,
            baseline.realistic_total_ebitda)

    def test_per_lever_decomposition(self):
        from rcm_mc.ml.improvement_potential import (
            PeerBenchmarks,
            estimate_improvement_potential,
        )
        bm = PeerBenchmarks(
            denial_rate=7.0, days_in_ar=38.0)
        current = {
            "denial_rate": 12.0, "days_in_ar": 55.0}
        result = estimate_improvement_potential(
            _profile(), current, bm)
        # Each lever has full decomposition
        for lv in result.levers:
            self.assertGreater(lv.raw_gap, 0)
            self.assertGreater(lv.realism_factor, 0)
            self.assertEqual(
                lv.lever in ("denial_rate", "days_in_ar"),
                True)
            # realistic_target_value sits between current and target
            if lv.lever == "denial_rate":
                self.assertLess(lv.realistic_target_value,
                                lv.current_value)
                self.assertGreater(
                    lv.realistic_target_value,
                    lv.peer_target_value)

    def test_to_dict_roundtrip(self):
        from rcm_mc.ml.improvement_potential import (
            PeerBenchmarks,
            estimate_improvement_potential,
        )
        bm = PeerBenchmarks(denial_rate=7.0)
        current = {"denial_rate": 12.0}
        result = estimate_improvement_potential(
            _profile(), current, bm)
        d = result.to_dict()
        self.assertIn("levers", d)
        self.assertIn("realistic_total_ebitda", d)
        self.assertIn("conservative_total_ebitda", d)
        self.assertIn("optimistic_total_ebitda", d)


if __name__ == "__main__":
    unittest.main()
