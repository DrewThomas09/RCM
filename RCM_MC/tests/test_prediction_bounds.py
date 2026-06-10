"""Regression: every predicted value is verified reasonable, across ALL hospitals.

The verification layer (ml.prediction_bounds) holds each model output to a
benchmark band and a coverage sweep cross-references the prediction for EVERY
hospital against that band — so an unreasonable number (80% denial, uplift >
revenue, probability > 1) can never reach a partner unnoticed.
"""
from __future__ import annotations

import math
import unittest

from rcm_mc.ml.prediction_bounds import (
    PREDICTION_BOUNDS, verify_predictions, within_bounds,
)


class BoundTests(unittest.TestCase):
    def test_within_and_outside(self):
        self.assertTrue(within_bounds("est_denial", 0.12))
        self.assertFalse(within_bounds("est_denial", 0.80))    # 80% is nonsense
        self.assertFalse(within_bounds("est_denial", -0.01))

    def test_probability_band(self):
        self.assertTrue(within_bounds("turnaround_probability", 0.0))
        self.assertTrue(within_bounds("turnaround_probability", 1.0))
        self.assertFalse(within_bounds("turnaround_probability", 1.4))

    def test_relative_cap_uses_context(self):
        ctx = {"net_patient_revenue": 1e8}
        self.assertTrue(within_bounds("est_uplift", 1.5e7, ctx))   # = 15% cap
        self.assertFalse(within_bounds("est_uplift", 2e7, ctx))    # 20% > cap

    def test_gaps_and_unknown_metrics_pass(self):
        self.assertTrue(within_bounds("est_denial", None))
        self.assertTrue(within_bounds("est_denial", float("nan")))
        self.assertTrue(within_bounds("not_a_metric", 999))

    def test_rounding_tolerated(self):
        # An integer-rounded uplift may sit $0.40 above a $315,330.60 cap.
        ctx = {"net_patient_revenue": 2102204.0}
        self.assertTrue(within_bounds("est_uplift", 315331.0, ctx))


class CoverageSweepTests(unittest.TestCase):
    def test_all_hospitals_predictions_in_bounds(self):
        from rcm_mc.data.hcris import _get_latest_per_ccn
        from rcm_mc.ui.predictive_screener import _add_features, _predict_rcm_fast
        df = _add_features(_get_latest_per_ccn())
        rows = [r.to_dict() for _, r in df.iterrows()]
        rep = verify_predictions(rows, _predict_rcm_fast)
        # Every prediction for every hospital is reasonable — none escapes.
        self.assertEqual(rep["violations"], [], rep["violations"][:5])
        self.assertGreater(rep["checked"], 1000)  # real coverage, not a no-op

    def test_sweep_reports_a_real_violation(self):
        # A deliberately-broken predictor must be caught.
        def _bad(_row):
            return {"est_denial": 0.80, "turnaround_probability": 1.5}
        rep = verify_predictions([{}, {}], _bad)
        metrics = {v["metric"] for v in rep["violations"]}
        self.assertIn("est_denial", metrics)
        self.assertIn("turnaround_probability", metrics)


if __name__ == "__main__":
    unittest.main()
