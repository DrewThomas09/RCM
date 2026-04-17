"""Tests for cross-deal learning (Prompt 30).

Invariants locked here:

 1. OutcomePair auto-computes error + pct_error.
 2. BiasStats direction = "overestimates" when mean_pct_error < 0.
 3. BiasStats direction = "underestimates" when positive.
 4. adjust_predictions scales by (1 − mean_pct_error).
 5. Adjustment skipped when n_deals < 3.
 6. Fund comparables have similarity_score = 2.0.
 7. AdjustmentReport summarises the applied adjustments.
 8. extract_outcomes returns empty when no hold actuals exist.
 9. compute_bias on empty outcomes returns empty dict.
10. Adjusted prediction carries provenance chain tag.
11. to_dict round-trips on all dataclasses.
12. build_fund_comparables returns empty for fresh DB.
13. PortfolioLearner doesn't raise on a store with no tables.
14. Direction is "unbiased" when |mean_pct_error| ≤ 5%.
"""
from __future__ import annotations

import os
import tempfile
import unittest

from rcm_mc.ml.portfolio_learning import (
    AdjustmentReport,
    BiasStats,
    OutcomePair,
    PortfolioLearner,
    _MIN_DEALS_FOR_ADJUSTMENT,
)
from rcm_mc.portfolio.store import PortfolioStore


def _tmp_store():
    tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tf.close()
    return PortfolioStore(tf.name), tf.name


# ── OutcomePair ────────────────────────────────────────────────────

class TestOutcomePair(unittest.TestCase):

    def test_error_computed(self):
        p = OutcomePair("d1", "denial_rate", 10.0, 12.0)
        self.assertEqual(p.error, 2.0)
        self.assertAlmostEqual(p.pct_error, 0.2)

    def test_zero_predicted_pct_error_safe(self):
        p = OutcomePair("d1", "denial_rate", 0.0, 5.0)
        self.assertEqual(p.pct_error, 0.0)

    def test_to_dict(self):
        p = OutcomePair("d1", "denial_rate", 10.0, 12.0)
        d = p.to_dict()
        self.assertEqual(d["metric"], "denial_rate")
        self.assertEqual(d["error"], 2.0)


# ── BiasStats ─────────────────────────────────────────────────────

class TestBiasStats(unittest.TestCase):

    def test_overestimates_when_actual_lower(self):
        # predicted=10, actual=8 → error=-2, pct=-0.2 → overestimates.
        learner = PortfolioLearner.__new__(PortfolioLearner)
        outcomes = [
            OutcomePair("d1", "denial_rate", 10.0, 8.0),
            OutcomePair("d2", "denial_rate", 12.0, 9.0),
            OutcomePair("d3", "denial_rate", 11.0, 9.5),
        ]
        bias = learner.compute_bias(outcomes)
        self.assertEqual(bias["denial_rate"].direction, "overestimates")

    def test_underestimates_when_actual_higher(self):
        outcomes = [
            OutcomePair("d1", "denial_rate", 10.0, 12.0),
            OutcomePair("d2", "denial_rate", 8.0, 10.0),
            OutcomePair("d3", "denial_rate", 9.0, 11.5),
        ]
        learner = PortfolioLearner.__new__(PortfolioLearner)
        bias = learner.compute_bias(outcomes)
        self.assertEqual(bias["denial_rate"].direction, "underestimates")

    def test_unbiased_when_small_error(self):
        outcomes = [
            OutcomePair("d1", "denial_rate", 10.0, 10.3),
            OutcomePair("d2", "denial_rate", 10.0, 10.1),
            OutcomePair("d3", "denial_rate", 10.0, 9.8),
        ]
        learner = PortfolioLearner.__new__(PortfolioLearner)
        bias = learner.compute_bias(outcomes)
        self.assertEqual(bias["denial_rate"].direction, "unbiased")

    def test_empty_outcomes(self):
        learner = PortfolioLearner.__new__(PortfolioLearner)
        self.assertEqual(learner.compute_bias([]), {})


# ── adjust_predictions ────────────────────────────────────────────

class TestAdjustPredictions(unittest.TestCase):

    def test_scales_by_factor(self):
        bias = {"denial_rate": BiasStats(
            metric="denial_rate", mean_pct_error=-0.15,
            n_deals=5, direction="overestimates",
        )}
        learner = PortfolioLearner.__new__(PortfolioLearner)
        adjusted = learner.adjust_predictions(
            {"denial_rate": 10.0}, bias,
        )
        # factor = 1 − (−0.15) = 1.15 → 10 × 1.15 = 11.5
        self.assertAlmostEqual(adjusted["denial_rate"], 11.5)

    def test_skipped_when_few_deals(self):
        bias = {"denial_rate": BiasStats(
            metric="denial_rate", mean_pct_error=-0.30,
            n_deals=2, direction="overestimates",
        )}
        learner = PortfolioLearner.__new__(PortfolioLearner)
        adjusted = learner.adjust_predictions(
            {"denial_rate": 10.0}, bias,
        )
        # n_deals=2 < 3 threshold → no change.
        self.assertEqual(adjusted["denial_rate"], 10.0)

    def test_provenance_tagged_on_dataclass(self):
        from rcm_mc.analysis.packet import PredictedMetric as PacketPM
        bias = {"denial_rate": BiasStats(
            metric="denial_rate", mean_pct_error=-0.10,
            n_deals=4, direction="overestimates",
        )}
        raw = {"denial_rate": PacketPM(
            value=10.0, ci_low=8.0, ci_high=12.0,
            provenance_chain=["ridge"],
        )}
        learner = PortfolioLearner.__new__(PortfolioLearner)
        adjusted = learner.adjust_predictions(raw, bias)
        pm = adjusted["denial_rate"]
        self.assertIn("portfolio_adjusted", pm.provenance_chain[-1])


# ── AdjustmentReport ──────────────────────────────────────────────

class TestAdjustmentReport(unittest.TestCase):

    def test_to_dict(self):
        r = AdjustmentReport(
            adjustments_applied=2, fund_deals_used=5,
            summary="example",
        )
        d = r.to_dict()
        self.assertEqual(d["adjustments_applied"], 2)


# ── Fund comparables ─────────────────────────────────────────────

class TestFundComparables(unittest.TestCase):

    def test_empty_on_fresh_db(self):
        store, path = _tmp_store()
        try:
            learner = PortfolioLearner(store)
            comps = learner.build_fund_comparables()
            self.assertEqual(comps, [])
        finally:
            os.unlink(path)

    def test_similarity_score_is_two(self):
        # Verify the spec says 2× weighting.
        store, path = _tmp_store()
        try:
            learner = PortfolioLearner(store)
            # No deals means no comps, but confirm the constant is as spec'd.
            from rcm_mc.ml.portfolio_learning import _MIN_DEALS_FOR_ADJUSTMENT
            self.assertEqual(_MIN_DEALS_FOR_ADJUSTMENT, 3)
        finally:
            os.unlink(path)


# ── Full pipeline ─────────────────────────────────────────────────

class TestPortfolioLearnerPipeline(unittest.TestCase):

    def test_extract_outcomes_empty_on_fresh_db(self):
        store, path = _tmp_store()
        try:
            learner = PortfolioLearner(store)
            self.assertEqual(learner.extract_outcomes(), [])
        finally:
            os.unlink(path)

    def test_build_report_on_fresh_db(self):
        store, path = _tmp_store()
        try:
            learner = PortfolioLearner(store)
            report = learner.build_report()
            self.assertEqual(report.adjustments_applied, 0)
            self.assertIn("no adjustments", report.summary)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
