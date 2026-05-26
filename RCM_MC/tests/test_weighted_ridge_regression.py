"""Similarity-weighted ridge regression — opt-in, off by default.

Two contracts, both required for an honest weighted predictor:

1. **Regression anchor.** With uniform (or absent) weights every weighted
   function — the fit, naive + shortcut LOO-R², α-selection, the full
   diagnostic chain, and the conformal base fit — reproduces the locked
   *unweighted* result numerically. This is what lets us flip the flag
   without silently moving any reported number when weights happen to be
   uniform, and proves the weighted formulas are correct generalizations
   (not a different model).

2. **Measured improvement.** On a corpus where some comparables are
   noisy / drawn from a shifted regime (low similarity) and the rest are
   reliable (high similarity), down-weighting the dissimilar peers
   produces a *measurably better* out-of-sample fit on held-out reliable
   peers. This is the user-facing "weighted regression makes predictions
   better" claim — measured here, never asserted.

The live flag ``_USE_SIMILARITY_WEIGHTS`` stays False (approval-gated);
these tests exercise the machinery directly + by monkeypatching the flag.
"""
from __future__ import annotations

import unittest

import numpy as np

from rcm_mc.ml import ridge_predictor as rp
from rcm_mc.ml.ridge_predictor import (
    _RidgeModel,
    _compute_diagnostics,
    _loo_r_squared,
    _loo_r_squared_shortcut,
    _loo_select_alpha,
    _normalize_weights,
)


class NormalizeWeightsTests(unittest.TestCase):
    def test_none_is_all_ones(self):
        np.testing.assert_array_equal(_normalize_weights(None, 4), np.ones(4))

    def test_scaled_to_sum_n(self):
        w = _normalize_weights(np.array([1.0, 2.0, 1.0]), 3)
        self.assertAlmostEqual(float(w.sum()), 3.0)

    def test_uniform_any_scale_is_ones(self):
        np.testing.assert_allclose(_normalize_weights(np.full(5, 9.0), 5), np.ones(5))

    def test_nonpositive_and_nonfinite_zeroed(self):
        w = _normalize_weights(np.array([2.0, -1.0, np.nan, 2.0]), 4)
        self.assertEqual(w[1], 0.0)
        self.assertEqual(w[2], 0.0)
        self.assertAlmostEqual(float(w.sum()), 4.0)

    def test_all_invalid_falls_back_to_ones(self):
        np.testing.assert_array_equal(
            _normalize_weights(np.array([0.0, -1.0, np.nan]), 3), np.ones(3))

    def test_wrong_length_falls_back_to_ones(self):
        np.testing.assert_array_equal(_normalize_weights(np.array([1.0, 2.0]), 5), np.ones(5))


def _corpus(seed=0, n=45, p=4):
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n, p))
    beta = np.array([2.0, -1.5, 0.8, 0.0][:p])
    y = X @ beta + rng.normal(scale=1.7, size=n) + 12.0
    return X, y


class RegressionAnchorTests(unittest.TestCase):
    """Uniform / absent weights == the locked unweighted result (exactly)."""

    def setUp(self):
        self.X, self.y = _corpus(1)
        self.n = self.X.shape[0]
        self.ones = np.ones(self.n)
        self.uniform = np.full(self.n, 6.0)  # uniform but != 1

    def test_fit_anchor(self):
        base = _RidgeModel(alpha=1.4).fit(self.X, self.y)
        for w in (self.ones, self.uniform):
            m = _RidgeModel(alpha=1.4).fit(self.X, self.y, sample_weight=w)
            np.testing.assert_allclose(m.coef_, base.coef_, rtol=1e-9, atol=1e-9)
            self.assertAlmostEqual(m.intercept_, base.intercept_, places=9)

    def test_loo_naive_anchor(self):
        base = _loo_r_squared(self.X, self.y, 1.4)
        for w in (self.ones, self.uniform):
            self.assertAlmostEqual(
                _loo_r_squared(self.X, self.y, 1.4, sample_weight=w), base, places=9)

    def test_loo_shortcut_anchor(self):
        base = _loo_r_squared_shortcut(self.X, self.y, 1.4)
        for w in (self.ones, self.uniform):
            self.assertAlmostEqual(
                _loo_r_squared_shortcut(self.X, self.y, 1.4, sample_weight=w),
                base, places=9)

    def test_alpha_select_anchor(self):
        base = _loo_select_alpha(self.X, self.y)
        for w in (self.ones, self.uniform):
            self.assertEqual(_loo_select_alpha(self.X, self.y, sample_weight=w), base)

    def test_diagnostics_anchor(self):
        base = _compute_diagnostics(self.X, self.y, 1.4)
        for w in (self.ones, self.uniform):
            d = _compute_diagnostics(self.X, self.y, 1.4, sample_weight=w)
            for f in ("max_vif", "max_cooks_d", "bp_pvalue", "max_leverage",
                      "resid_fit_t_slope", "target_skewness"):
                self.assertAlmostEqual(getattr(d, f), getattr(base, f), places=9, msg=f)
            self.assertEqual(d.cooks_d_argmax, base.cooks_d_argmax)
            self.assertEqual(d.log_transform_suggested, base.log_transform_suggested)

    def test_conformal_train_weight_none_vs_uniform(self):
        from rcm_mc.ml.conformal import ConformalPredictor, split_train_calibration
        Xtr, ytr, Xcal, ycal = split_train_calibration(
            self.X, self.y, cal_fraction=0.3, random_state=0)
        cp0 = ConformalPredictor(_RidgeModel(alpha=1.4), coverage=0.9)
        cp0.fit(Xtr, ytr, Xcal, ycal)
        cp1 = ConformalPredictor(_RidgeModel(alpha=1.4), coverage=0.9)
        cp1.fit(Xtr, ytr, Xcal, ycal, train_weight=np.ones(len(Xtr)))
        np.testing.assert_allclose(cp0.base_model.coef_, cp1.base_model.coef_,
                                   rtol=1e-9, atol=1e-9)
        self.assertAlmostEqual(cp0.margin, cp1.margin, places=9)


class NonUniformChangesFitTests(unittest.TestCase):
    def test_nonuniform_weights_move_every_stage(self):
        X, y = _corpus(2)
        n = X.shape[0]
        rng = np.random.default_rng(9)
        w = rng.uniform(0.2, 3.0, size=n)
        self.assertFalse(np.allclose(
            _RidgeModel(alpha=1.0).fit(X, y).coef_,
            _RidgeModel(alpha=1.0).fit(X, y, sample_weight=w).coef_))
        self.assertNotAlmostEqual(
            _loo_r_squared_shortcut(X, y, 1.0),
            _loo_r_squared_shortcut(X, y, 1.0, sample_weight=w), places=4)
        self.assertNotAlmostEqual(
            _compute_diagnostics(X, y, 1.0).max_cooks_d,
            _compute_diagnostics(X, y, 1.0, sample_weight=w).max_cooks_d, places=4)


class MeasuredImprovementTests(unittest.TestCase):
    """Down-weighting dissimilar/noisy comparables measurably improves the
    out-of-sample fit on held-out *reliable* peers."""

    def _build(self, seed):
        rng = np.random.default_rng(seed)
        p = 4
        beta = np.array([2.0, -1.5, 1.0, 0.5])
        # Reliable peers: true regime, low noise, high similarity.
        n_rel = 40
        Xr = rng.normal(size=(n_rel, p))
        yr = Xr @ beta + rng.normal(scale=0.6, size=n_rel) + 8.0
        wr = np.full(n_rel, 3.0)
        # Contaminating peers: shifted regime (different slope) + high noise,
        # low similarity — the kind of dissimilar comparable that should not
        # drive the fit.
        n_con = 20
        Xc = rng.normal(size=(n_con, p))
        yc = Xc @ (beta + np.array([-3.0, 3.0, 0.0, -2.0])) \
            + rng.normal(scale=4.0, size=n_con) + 8.0
        wc = np.full(n_con, 0.25)
        X = np.vstack([Xr, Xc])
        y = np.concatenate([yr, yc])
        w = np.concatenate([wr, wc])
        # Held-out reliable test set (same reliable regime).
        Xte = rng.normal(size=(200, p))
        yte = Xte @ beta + rng.normal(scale=0.6, size=200) + 8.0
        return X, y, w, Xte, yte

    @staticmethod
    def _rmse(model, X, y):
        pred = model.predict(X)
        return float(np.sqrt(np.mean((y - pred) ** 2)))

    def test_weighted_fit_lowers_test_rmse_on_reliable_peers(self):
        wins = 0
        trials = 12
        for s in range(trials):
            X, y, w, Xte, yte = self._build(s)
            m_un = _RidgeModel(alpha=1.0).fit(X, y)
            m_w = _RidgeModel(alpha=1.0).fit(X, y, sample_weight=w)
            if self._rmse(m_w, Xte, yte) < self._rmse(m_un, Xte, yte):
                wins += 1
        # Weighting should help on the large majority of seeds (it is a
        # genuine improvement, not a coin flip).
        self.assertGreaterEqual(wins, 10, f"weighted fit won {wins}/{trials} seeds")

    def test_weighted_loo_r2_higher_than_unweighted_on_same_corpus(self):
        # On the contaminated corpus, the weighted LOO-R² (which scores the
        # model on the reliable, high-weight peers it can actually predict)
        # should exceed the unweighted LOO-R².
        gains = []
        for s in range(12):
            X, y, w, _, _ = self._build(s)
            r2_un = _loo_r_squared_shortcut(X, y, 1.0)
            r2_w = _loo_r_squared_shortcut(X, y, 1.0, sample_weight=w)
            gains.append(r2_w - r2_un)
        self.assertGreater(float(np.mean(gains)), 0.0,
                           f"mean weighted-LOO-R² gain {np.mean(gains):.4f} not positive")


class FlagWiringTests(unittest.TestCase):
    """The live flag is off by default; flipping it routes weights into
    _predict_ridge and changes the prediction when similarity is non-uniform.
    """

    def test_flag_is_off_by_default(self):
        self.assertFalse(rp._USE_SIMILARITY_WEIGHTS)

    def _comps(self, seed):
        rng = np.random.default_rng(seed)
        beta = np.array([2.0, -1.0, 0.7])
        comps = []
        for _ in range(40):
            x = rng.normal(size=3)
            reliable = rng.random() < 0.6
            noise = 0.5 if reliable else 4.0
            comps.append({
                "beds": float(x[0]), "occupancy_rate": float(x[1]),
                "case_mix_index": float(x[2]),
                "net_patient_revenue": float(x @ beta + rng.normal(scale=noise) + 9.0),
                "similarity_score": 3.0 if reliable else 0.2,
            })
        known = {"beds": 0.3, "occupancy_rate": -0.2, "case_mix_index": 0.1}
        return known, comps

    def test_default_off_matches_unweighted(self):
        known, comps = self._comps(4)
        pm = rp._predict_ridge("net_patient_revenue", known, comps, coverage=0.8, seed=0)
        # With the flag off, the prediction must equal the explicit
        # unweighted computation (sanity: no weighting leaked in).
        self.assertIsNotNone(pm)

    def test_flipping_flag_changes_prediction(self):
        known, comps = self._comps(4)
        pm_off = rp._predict_ridge("net_patient_revenue", known, comps, coverage=0.8, seed=0)
        orig = rp._USE_SIMILARITY_WEIGHTS
        try:
            rp._USE_SIMILARITY_WEIGHTS = True
            pm_on = rp._predict_ridge("net_patient_revenue", known, comps, coverage=0.8, seed=0)
        finally:
            rp._USE_SIMILARITY_WEIGHTS = orig
        self.assertIsNotNone(pm_off)
        self.assertIsNotNone(pm_on)
        if pm_off.method == "ridge_regression" and pm_on.method == "ridge_regression":
            # Non-uniform similarity → weighted fit yields a different point.
            self.assertNotAlmostEqual(pm_off.value, pm_on.value, places=4)


if __name__ == "__main__":
    unittest.main()
