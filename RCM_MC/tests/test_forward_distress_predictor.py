"""Tests for forward financial distress predictor (12-24mo)."""
from __future__ import annotations

import math
import unittest

import numpy as np


def _synth_panels(n: int = 200, seed: int = 7,
                  horizon: int = 24):
    rng = np.random.default_rng(seed)
    rows = []
    for _ in range(n):
        beds = float(rng.integers(50, 800))
        # Build a 4-year margin history; future margin depends on
        # the trend + liquidity + debt
        m0 = float(rng.normal(0.04, 0.05))
        slope = float(rng.normal(-0.005, 0.01))
        history = [m0 - slope * i + rng.normal(0, 0.01)
                   for i in range(3, 0, -1)]
        history.append(m0)
        days_cash = float(rng.uniform(20, 200))
        debt_to_rev = float(rng.uniform(0.10, 0.80))
        cagr = float(rng.normal(0.01, 0.03))
        occ = float(rng.uniform(0.45, 0.85))
        # Future margin: trend continues + liquidity floor +
        # debt drag + volume growth bonus
        future_margin = (
            m0
            + slope * (horizon / 12)  # extend trend
            + 0.0005 * (days_cash - 100)
            - 0.04 * debt_to_rev
            + 0.5 * cagr
            + rng.normal(0, 0.015)
        )
        future_margin = max(-0.30, min(0.20, future_margin))
        rows.append({
            "operating_margin_t": m0,
            "margin_history": history,
            "cash_on_hand": days_cash * (beds * 50_000) / 365,
            "annual_operating_expenses": beds * 50_000,
            "current_assets": days_cash * 0.6 * beds * 50_000 / 365,
            "current_liabilities": beds * 5_000,
            "long_term_debt":
                debt_to_rev * beds * 4 * 50_000 * 0.30,
            "net_patient_revenue": beds * 4 * 50_000 * 0.30,
            "interest_expense":
                debt_to_rev * beds * 4 * 50_000 * 0.30 * 0.05,
            "ebit": beds * 4 * 50_000 * 0.30 * (m0 + 0.04),
            "discharges_history": [
                beds * 4 * (1 + cagr) ** -i
                for i in range(3, -1, -1)
            ],
            "beds": beds,
            "occupancy_rate": occ,
            "medicare_day_pct": float(rng.uniform(0.30, 0.55)),
            "medicaid_day_pct": float(rng.uniform(0.10, 0.30)),
            "gross_patient_revenue": beds * 4 * 50_000,
            "future_margin": future_margin,
        })
    return rows


class TestFeatureBuilding(unittest.TestCase):
    def test_canonical_feature_set(self):
        from rcm_mc.ml.forward_distress_predictor import (
            FORWARD_DISTRESS_FEATURES,
            build_forward_distress_features,
        )
        f = build_forward_distress_features({})
        # Every canonical feature is present, even on empty input
        for n in FORWARD_DISTRESS_FEATURES:
            self.assertIn(n, f)
        # Defaults are floats
        self.assertIsInstance(f["operating_margin_t"], float)

    def test_margin_slope_negative_when_declining(self):
        from rcm_mc.ml.forward_distress_predictor import (
            build_forward_distress_features,
        )
        f = build_forward_distress_features({
            "margin_history": [0.06, 0.04, 0.02, 0.0],
        })
        self.assertLess(f["margin_3yr_slope"], 0.0)

    def test_days_cash_computed(self):
        from rcm_mc.ml.forward_distress_predictor import (
            build_forward_distress_features,
        )
        f = build_forward_distress_features({
            "cash_on_hand": 1_000_000,
            "annual_operating_expenses": 36_500_000,
        })
        # 1M / (36.5M / 365) = 1M / 100K = 10 days
        self.assertAlmostEqual(
            f["days_cash_on_hand"], 10.0, places=1)

    def test_debt_ratio_clipped(self):
        """Pathological debt ratios capped to keep features
        within the sanity range used at fit time."""
        from rcm_mc.ml.forward_distress_predictor import (
            build_forward_distress_features,
        )
        f = build_forward_distress_features({
            "long_term_debt": 100_000_000,
            "net_patient_revenue": 1_000_000,
        })
        self.assertLessEqual(f["debt_to_revenue"], 5.0)


class TestForwardDistressTraining(unittest.TestCase):
    def test_train_with_skill(self):
        from rcm_mc.ml.forward_distress_predictor import (
            FORWARD_DISTRESS_FEATURES,
            train_forward_distress_predictor,
        )
        rows = _synth_panels(n=200, horizon=24)
        p = train_forward_distress_predictor(
            rows, horizon_months=24)
        self.assertEqual(p.target_metric,
                         "future_margin_24mo")
        self.assertEqual(p.feature_names,
                         FORWARD_DISTRESS_FEATURES)
        self.assertGreater(p.cv_r2_mean, 0.30)

    def test_horizon_validation(self):
        from rcm_mc.ml.forward_distress_predictor import (
            train_forward_distress_predictor,
        )
        rows = _synth_panels(n=50)
        with self.assertRaises(ValueError):
            train_forward_distress_predictor(
                rows, horizon_months=18)

    def test_12_month_horizon_works(self):
        from rcm_mc.ml.forward_distress_predictor import (
            train_forward_distress_predictor,
        )
        rows = _synth_panels(n=100, horizon=12)
        p = train_forward_distress_predictor(
            rows, horizon_months=12)
        self.assertEqual(p.target_metric,
                         "future_margin_12mo")

    def test_empty_panel_rejected(self):
        from rcm_mc.ml.forward_distress_predictor import (
            train_forward_distress_predictor,
        )
        with self.assertRaises(ValueError):
            train_forward_distress_predictor([])


class TestDistressProbability(unittest.TestCase):
    def test_probability_label_and_explanation(self):
        from rcm_mc.ml.forward_distress_predictor import (
            train_forward_distress_predictor,
            predict_distress,
        )
        rows = _synth_panels(n=200, horizon=24)
        p = train_forward_distress_predictor(
            rows, horizon_months=24)

        # Healthy hospital
        healthy_panel = {
            "operating_margin_t": 0.08,
            "margin_history": [0.06, 0.07, 0.075, 0.08],
            "cash_on_hand": 50_000_000,
            "annual_operating_expenses": 100_000_000,
            "long_term_debt": 10_000_000,
            "net_patient_revenue": 100_000_000,
            "discharges_history": [10000, 10500, 11000, 11500],
            "beds": 300,
            "occupancy_rate": 0.78,
        }
        margin_h, prob_h, label_h, color_h, expl_h = (
            predict_distress(p, healthy_panel))
        self.assertGreater(margin_h, -0.10)
        # Healthy → low/moderate distress probability
        self.assertLess(prob_h, 0.40)

        # Distressed hospital
        distressed_panel = {
            "operating_margin_t": -0.08,
            "margin_history": [0.02, 0.0, -0.04, -0.08],
            "cash_on_hand": 1_000_000,
            "annual_operating_expenses": 100_000_000,
            "long_term_debt": 80_000_000,
            "net_patient_revenue": 100_000_000,
            "discharges_history": [11000, 10500, 10000, 9500],
            "beds": 200,
            "occupancy_rate": 0.45,
        }
        margin_d, prob_d, label_d, color_d, expl_d = (
            predict_distress(p, distressed_panel))
        # Distressed predicts lower future margin
        self.assertLess(margin_d, margin_h)
        # Distressed predicts higher distress probability
        self.assertGreater(prob_d, prob_h)

        # Explanations are non-empty + sorted by |contribution|
        self.assertGreater(len(expl_h), 0)
        absvals = [abs(c) for _, c in expl_h]
        self.assertEqual(absvals,
                         sorted(absvals, reverse=True))

    def test_probability_in_unit_interval(self):
        from rcm_mc.ml.forward_distress_predictor import (
            train_forward_distress_predictor,
            predict_distress,
        )
        rows = _synth_panels(n=100, horizon=24)
        p = train_forward_distress_predictor(
            rows, horizon_months=24)
        for panel in rows[:5]:
            _, prob, _, _, _ = predict_distress(p, panel)
            self.assertGreaterEqual(prob, 0.0)
            self.assertLessEqual(prob, 1.0)

    def test_threshold_override(self):
        """Overriding distress_threshold to a more lenient value
        should reduce reported probability."""
        from rcm_mc.ml.forward_distress_predictor import (
            train_forward_distress_predictor,
            predict_distress,
        )
        rows = _synth_panels(n=100, horizon=24)
        p = train_forward_distress_predictor(
            rows, horizon_months=24)
        panel = rows[0]
        _, prob_default, _, _, _ = predict_distress(
            p, panel, distress_threshold=-0.05)
        _, prob_strict, _, _, _ = predict_distress(
            p, panel, distress_threshold=-0.15)
        # More-negative threshold = tighter definition of
        # distress = lower probability of triggering
        self.assertGreaterEqual(prob_default, prob_strict)


class TestRiskLabels(unittest.TestCase):
    def test_label_bands(self):
        from rcm_mc.ml.forward_distress_predictor import (
            _label_for_probability,
        )
        self.assertEqual(_label_for_probability(0.05)[0],
                         "Low")
        self.assertEqual(_label_for_probability(0.20)[0],
                         "Moderate")
        self.assertEqual(_label_for_probability(0.40)[0],
                         "Elevated")
        self.assertEqual(_label_for_probability(0.65)[0],
                         "High")
        self.assertEqual(_label_for_probability(0.90)[0],
                         "Critical")


if __name__ == "__main__":
    unittest.main()
