"""Tests for the EBITDA bridge realization predictor.

`rcm_mc/ml/realization_predictor.py` is a 217-line production module
used by 6 UI surfaces (thesis_card, ebitda_bridge_page, levers,
scenarios, memo_auto, ic_memo) but had no test coverage when this
file was added. The module's contract — risk-adjust the modeled
EBITDA bridge by predicted execution likelihood — directly changes
the investment decision shown to a partner, so its math and edge
cases need locking.
"""
from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from rcm_mc.ml.realization_predictor import (
    RealizationFactor,
    RealizationPrediction,
    predict_realization,
    train_realization_model,
)


def _sample_hcris(n=400, seed=42):
    """HCRIS-shaped fixture with the columns the predictor needs.

    Engineers a mild correlation between operating_margin and
    occupancy_rate / commercial_pct so the logistic model has
    something to learn (otherwise accuracy ~= 0.5 trivially)."""
    rng = np.random.RandomState(seed)
    occupancy = rng.uniform(0.4, 0.95, n)
    commercial_pct = rng.uniform(0.1, 0.6, n)
    beds = rng.randint(20, 800, n).astype(float)
    # Margin correlates positively with occupancy + commercial mix.
    margin = (
        -0.03
        + 0.05 * (occupancy - 0.7)
        + 0.04 * (commercial_pct - 0.35)
        + rng.normal(0, 0.03, n)
    )
    return pd.DataFrame({
        "ccn": [f"{i:06d}" for i in range(1, n + 1)],
        "name": [f"Hospital {i}" for i in range(1, n + 1)],
        "state": rng.choice(["CA", "TX", "NY", "FL", "OH", "PA"], n),
        "beds": beds,
        "occupancy_rate": occupancy,
        "revenue_per_bed": rng.uniform(2e5, 2e6, n),
        "commercial_pct": commercial_pct,
        "net_to_gross_ratio": rng.uniform(0.25, 0.55, n),
        "payer_diversity": rng.uniform(2.0, 4.5, n),
        "operating_margin": margin,
    })


class TrainModelTests(unittest.TestCase):
    """Contract for `train_realization_model`."""

    def test_returns_six_tuple(self):
        df = _sample_hcris()
        out = train_realization_model(df)
        self.assertEqual(len(out), 6,
                         "train_realization_model should return "
                         "(beta, x_mean, x_std, accuracy, n, features)")

    def test_trains_with_sufficient_data(self):
        df = _sample_hcris()
        beta, x_mean, x_std, accuracy, n, feats = (
            train_realization_model(df))
        self.assertGreater(n, 100, "Should train on >100 rows")
        self.assertGreater(len(feats), 3,
                           "Should use >=4 features")
        # Beta has +1 element for intercept
        self.assertEqual(len(beta), len(feats) + 1)
        # Mean/std vectors match feature count
        self.assertEqual(len(x_mean), len(feats))
        self.assertEqual(len(x_std), len(feats))

    def test_accuracy_is_bounded(self):
        df = _sample_hcris()
        _, _, _, accuracy, _, _ = train_realization_model(df)
        # Accuracy is a fraction in [0, 1].
        self.assertGreaterEqual(accuracy, 0.0)
        self.assertLessEqual(accuracy, 1.0)

    def test_accuracy_above_chance_on_correlated_data(self):
        # The fixture builds a real margin↔feature correlation, so the
        # trained model should beat 50/50. Loose floor (0.55) keeps the
        # test stable across small RNG perturbations.
        df = _sample_hcris(n=600, seed=7)
        _, _, _, accuracy, _, _ = train_realization_model(df)
        self.assertGreater(accuracy, 0.55,
                           f"Accuracy {accuracy:.3f} should beat "
                           "chance on correlated training data")

    def test_no_data_returns_safe_zero_model(self):
        # Below the 100-row floor → returns a zero/identity model that
        # downstream code treats as 'no signal'.
        df = _sample_hcris(n=50)
        beta, x_mean, x_std, accuracy, n, feats = (
            train_realization_model(df))
        self.assertEqual(n, 0,
                         "Insufficient data must report n=0 so callers "
                         "know not to trust the model")
        self.assertEqual(accuracy, 0.5)
        # Beta is all zeros; x_std is all ones (safe normalization).
        self.assertTrue(np.allclose(beta, 0))
        self.assertTrue(np.allclose(x_std, 1))

    def test_missing_features_returns_safe_zero_model(self):
        # If <3 features are present (after dropping missing), the model
        # has nothing to learn — returns the same zero model.
        df = _sample_hcris().drop(columns=[
            "occupancy_rate", "revenue_per_bed", "commercial_pct",
            "net_to_gross_ratio", "payer_diversity",
        ])
        _, _, _, accuracy, n, _ = train_realization_model(df)
        self.assertEqual(n, 0)
        self.assertEqual(accuracy, 0.5)

    def test_engineers_log_beds_if_missing(self):
        # The contract: train_realization_model derives log_beds from
        # beds if it isn't already in the df. The fixture has beds but
        # not log_beds — feats should include 'log_beds'.
        df = _sample_hcris()
        _, _, _, _, _, feats = train_realization_model(df)
        self.assertIn("log_beds", feats)


class PredictRealizationTests(unittest.TestCase):
    """Contract for `predict_realization`."""

    def test_returns_prediction_for_known_ccn(self):
        df = _sample_hcris()
        ccn = df["ccn"].iloc[0]
        pred = predict_realization(ccn, df, bridge_uplift=10_000_000)
        self.assertIsNotNone(pred)
        self.assertIsInstance(pred, RealizationPrediction)

    def test_returns_none_for_missing_ccn(self):
        df = _sample_hcris()
        pred = predict_realization("999999", df)
        self.assertIsNone(pred,
                          "Missing CCN must return None, not a stale "
                          "or hallucinated prediction")

    def test_returns_none_when_model_untrained(self):
        # Insufficient rows → train returns n=0 → predict returns None
        # (avoids a 'realization estimate' built on zero training rows).
        df = _sample_hcris(n=50)
        pred = predict_realization(df["ccn"].iloc[0], df)
        self.assertIsNone(pred)

    def test_realization_bounded_30_to_98_pct(self):
        # The realization fraction is mapped to [0.30, 0.98] so the
        # narrative never shows '0% achievable' or '100% achievable'.
        df = _sample_hcris(n=500)
        for ccn in df["ccn"].iloc[:20]:
            pred = predict_realization(ccn, df, bridge_uplift=5_000_000)
            if pred is None:
                continue
            self.assertGreaterEqual(pred.expected_realization, 0.30)
            self.assertLessEqual(pred.expected_realization, 0.98)

    def test_confidence_interval_brackets_point(self):
        df = _sample_hcris(n=500)
        ccn = df["ccn"].iloc[0]
        pred = predict_realization(ccn, df)
        self.assertIsNotNone(pred)
        lo, hi = pred.confidence_interval
        self.assertLessEqual(lo, pred.expected_realization)
        self.assertGreaterEqual(hi, pred.expected_realization)
        # The CI is clipped at 0.20 / 1.00 — the bottom never goes
        # below 0.20 and the top never exceeds 1.0.
        self.assertGreaterEqual(lo, 0.20)
        self.assertLessEqual(hi, 1.0)

    def test_risk_adjusted_uplift_scales_with_realization(self):
        df = _sample_hcris(n=500)
        ccn = df["ccn"].iloc[0]
        pred = predict_realization(ccn, df, bridge_uplift=10_000_000)
        self.assertIsNotNone(pred)
        # risk_adjusted_uplift = raw * realization, computed BEFORE
        # expected_realization is rounded to 3 decimals. So matching
        # against the rounded value drifts by up to 0.0005 × raw =
        # ~5,000 on a 10M bridge. Allow that.
        expected = 10_000_000 * pred.expected_realization
        self.assertAlmostEqual(pred.risk_adjusted_uplift, expected,
                               delta=10_000.0,
                               msg="risk_adjusted_uplift should be "
                               "≈ raw_uplift × expected_realization")
        # discount = raw - risk_adjusted (exact arithmetic identity).
        self.assertAlmostEqual(
            pred.discount,
            pred.raw_uplift - pred.risk_adjusted_uplift,
            delta=1.0,
        )

    def test_zero_bridge_uplift_is_safe(self):
        # Partners view this page even when the bridge hasn't been
        # built yet (uplift=0). The narrative must not crash and the
        # discount must be 0.
        df = _sample_hcris(n=500)
        ccn = df["ccn"].iloc[0]
        pred = predict_realization(ccn, df, bridge_uplift=0)
        self.assertIsNotNone(pred)
        self.assertEqual(pred.raw_uplift, 0)
        self.assertEqual(pred.risk_adjusted_uplift, 0)
        self.assertEqual(pred.discount, 0)
        # The narrative skips the dollar phrasing when uplift=0.
        self.assertNotIn("$", pred.narrative)

    def test_grade_follows_thresholds(self):
        # A: ≥0.85, B: ≥0.70, C: ≥0.55, D: <0.55. The grade is
        # assigned from the UNROUNDED realization, then
        # expected_realization is rounded to 3 decimals — so a
        # rounded value of 0.700 may have been graded C if the
        # unrounded value was 0.6999. Skip boundary predictions
        # (within ±0.001 of any threshold) and assert clean bands
        # only inside-band.
        df = _sample_hcris(n=600)
        results = []
        for ccn in df["ccn"]:
            pred = predict_realization(ccn, df)
            if pred is not None:
                results.append((pred.expected_realization, pred.grade))
        self.assertGreater(len(results), 50,
                           "Need enough predictions to test grade bands")
        bounds = (0.55, 0.70, 0.85)
        eps = 0.002
        for r, g in results:
            self.assertIn(g, {"A", "B", "C", "D"})
            # Skip values too close to a threshold to avoid the
            # rounded-vs-unrounded asymmetry.
            if any(abs(r - b) < eps for b in bounds):
                continue
            if r > 0.85:
                self.assertEqual(g, "A", f"r={r:.3f} should be A")
            elif r > 0.70:
                self.assertEqual(g, "B", f"r={r:.3f} should be B")
            elif r > 0.55:
                self.assertEqual(g, "C", f"r={r:.3f} should be C")
            else:
                self.assertEqual(g, "D", f"r={r:.3f} should be D")

    def test_factors_ranked_by_absolute_effect(self):
        # The UI shows the top factors; the contract is they're sorted
        # by |effect| descending so the strongest signals come first.
        df = _sample_hcris(n=500)
        ccn = df["ccn"].iloc[0]
        pred = predict_realization(ccn, df, bridge_uplift=10_000_000)
        self.assertIsNotNone(pred)
        effects = [abs(f.effect) for f in pred.factors]
        self.assertEqual(effects, sorted(effects, reverse=True),
                         "factors must be sorted by |effect| desc")
        # Capped at 6 factors (the UI shows a tight list).
        self.assertLessEqual(len(pred.factors), 6)

    def test_factor_directions_are_one_of_three_strings(self):
        df = _sample_hcris(n=500)
        ccn = df["ccn"].iloc[0]
        pred = predict_realization(ccn, df)
        self.assertIsNotNone(pred)
        for f in pred.factors:
            self.assertIsInstance(f, RealizationFactor)
            self.assertIn(f.direction, {"supports", "hinders", "neutral"})

    def test_narrative_carries_realization_percentage(self):
        df = _sample_hcris(n=500)
        ccn = df["ccn"].iloc[0]
        pred = predict_realization(ccn, df, bridge_uplift=10_000_000)
        self.assertIsNotNone(pred)
        # Narrative begins with "Expected realization: NN% of modeled bridge."
        self.assertTrue(pred.narrative.startswith("Expected realization:"))
        self.assertIn("%", pred.narrative)

    def test_narrative_includes_dollar_uplift_when_provided(self):
        df = _sample_hcris(n=500)
        ccn = df["ccn"].iloc[0]
        pred = predict_realization(ccn, df, bridge_uplift=25_000_000)
        self.assertIsNotNone(pred)
        self.assertIn("$", pred.narrative)
        self.assertIn("M", pred.narrative,
                      "Dollars are formatted in millions ($XXM)")

    def test_handles_nan_feature_values(self):
        # Robustness: a hospital row with NaN in some features must
        # not crash; missing values map to the trained mean (0 after
        # normalization).
        df = _sample_hcris(n=500)
        df.loc[0, "occupancy_rate"] = np.nan
        df.loc[0, "commercial_pct"] = np.nan
        ccn = df["ccn"].iloc[0]
        pred = predict_realization(ccn, df, bridge_uplift=10_000_000)
        # Even though the row has NaNs, training drops it from the
        # training set; predicting on the same row should still
        # return a Prediction (the NaNs are replaced with 0 in
        # predict_realization's x_raw assembly).
        self.assertIsNotNone(pred)


if __name__ == "__main__":
    unittest.main()
