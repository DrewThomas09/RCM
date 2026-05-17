"""B.1 ridge predictor — RidgeCV α-search + diagnostics + composition.

Covers test categories 1-5 from D5. Category 6 (integration tests via
rendered HTML) is deferred to a follow-up PR; the contract-test pattern
in tests/test_chip_propagation_surfaces.py already pins the chip
wire-up at the rendering layer. Category 7 (BP precision verification)
lives in tests/test_b1_bp_precision.py (scipy-skip-decorated single
file). Category 8 (EnsemblePredictor α-wiring) lives in
tests/test_ensemble_predictor.py via additions.
"""
from __future__ import annotations

import unittest

import numpy as np

from rcm_mc.ml.ridge_predictor import (
    DiagnosticReport,
    FailureReason,
    _ALPHA_SEARCH_GRID,
    _RIDGE_ALPHA,
    _RidgeModel,
    _compute_diagnostics,
    _loo_r_squared,
    _loo_r_squared_shortcut,
    _loo_select_alpha,
    _predict_ridge,
    _wilson_hilferty_chi2_sf,
)


# ────────────────────────────────────────────────────────────────────
# Category 1 — RidgeCV α-search correctness
# ────────────────────────────────────────────────────────────────────


class TestRidgeCVAlphaSearch(unittest.TestCase):
    """Fixtures 1A/1B/1C from D5."""

    def test_1a_known_optimal_alpha_high_noise_picks_higher_alpha(self):
        """Fixture 1A: high noise + near-collinear features → high α should win.

        Verify RidgeCV's pick is at least as high as the unregularized
        baseline (α=0.01). At low α, the near-collinear x1/x2 pair
        produces unstable coefficients and high LOO MSE.
        """
        rng = np.random.default_rng(0)
        n, p = 30, 5
        X = rng.standard_normal((n, p))
        # Near-collinear: x[:,1] ≈ x[:,0] + tiny noise → VIF on x1 huge
        X[:, 1] = X[:, 0] + 0.05 * rng.standard_normal(n)
        true_w = np.array([1.0, 1.0, 0.5, 0.0, 0.0])
        y = X @ true_w + 0.5 * rng.standard_normal(n)
        alpha, at_boundary = _loo_select_alpha(X, y)
        # RidgeCV should pick at least 0.1 — under-regularizing produces
        # known-bad LOO on the collinear pair
        self.assertGreaterEqual(alpha, 0.1,
            f"RidgeCV picked α={alpha} on near-collinear high-noise fixture; "
            f"expected ≥0.1 to dampen the collinearity")

    def test_1a_loo_select_returns_value_from_grid(self):
        """Selected α must be one of the grid values, not interpolated."""
        rng = np.random.default_rng(0)
        X = rng.standard_normal((30, 3))
        y = rng.standard_normal(30)
        alpha, _ = _loo_select_alpha(X, y)
        self.assertIn(float(alpha), [float(a) for a in _ALPHA_SEARCH_GRID])

    def test_1c_hat_matrix_shortcut_approximates_naive_loo(self):
        """Fixture 1C: shortcut LOO R² must approximate naive LOO R².

        Exact agreement: the shortcut z-scores the FULL X once and
        computes LOO residuals via the hat-matrix formula assuming
        Xz is fixed. The naive version refits per LOO iteration —
        each refit re-standardizes from scratch on the n-1 remaining
        rows, so feature means/sds shift slightly with each drop.
        The shortcut is exact for the fixed-Xz interpretation;
        agreement with naive is O(1/n) ≈ 0.02-0.05 at n=20.

        For ridgeCV purposes both methods give the same ARGMIN α
        even when the absolute R² values differ by a few hundredths.
        """
        rng = np.random.default_rng(123)
        n, p = 20, 4
        X = rng.standard_normal((n, p))
        y = X @ np.array([1.0, 0.5, -0.3, 0.1]) + 0.2 * rng.standard_normal(n)
        for alpha in (0.1, 1.0, 10.0):
            r2_shortcut = _loo_r_squared_shortcut(X, y, alpha)
            r2_naive = _loo_r_squared(X, y, alpha)
            self.assertAlmostEqual(
                r2_shortcut, r2_naive, delta=0.05,
                msg=f"shortcut LOO and naive LOO diverge >0.05 at α={alpha}: "
                    f"{r2_shortcut} vs {r2_naive}",
            )


# ────────────────────────────────────────────────────────────────────
# Category 2 — Per-diagnostic fixtures + threshold-fire tests
# ────────────────────────────────────────────────────────────────────


class TestDiagnosticsFire(unittest.TestCase):
    """Fixtures 2A through 2E from D5 — each diagnostic fires when
    engineered to AND doesn't fire on a clean fixture."""

    def test_2a_vif_fires_on_collinear_features(self):
        rng = np.random.default_rng(0)
        n, p = 25, 4
        X = rng.standard_normal((n, p))
        # Near-perfect collinearity on x0/x1 → VIF for x0 ≈ 10000
        X[:, 1] = 2.0 * X[:, 0] + 0.01 * rng.standard_normal(n)
        y = X @ np.array([1.0, 1.0, 0.5, 0.5]) + 0.1 * rng.standard_normal(n)
        diag = _compute_diagnostics(X, y, alpha=1.0)
        self.assertGreater(
            diag.max_vif, 10.0,
            f"VIF should fire (>10) on near-collinear features; got {diag.max_vif}")
        fired = diag.failure_reasons_at(n, p)
        self.assertIn(FailureReason.MULTICOLLINEAR, fired)

    def test_2a_neg_vif_does_not_fire_on_orthogonal_features(self):
        rng = np.random.default_rng(0)
        X = rng.standard_normal((30, 4))
        y = X @ np.array([1.0, 0.5, -0.3, 0.2]) + 0.1 * rng.standard_normal(30)
        diag = _compute_diagnostics(X, y, alpha=1.0)
        self.assertLess(
            diag.max_vif, 5.0,
            f"VIF should not fire on orthogonal features; got {diag.max_vif}")
        fired = diag.failure_reasons_at(30, 4)
        self.assertNotIn(FailureReason.MULTICOLLINEAR, fired)

    def test_2b_cooks_d_fires_on_engineered_outlier(self):
        rng = np.random.default_rng(0)
        n, p = 30, 3
        X = rng.standard_normal((n, p))
        y = X @ np.array([1.0, 0.5, -0.3]) + 0.1 * rng.standard_normal(n)
        # Inject one extreme outlier — high leverage + huge residual
        X[0] = np.array([5.0, 5.0, 5.0])
        y[0] = -10.0
        diag = _compute_diagnostics(X, y, alpha=1.0)
        self.assertGreater(
            diag.max_cooks_d, 4.0 / n,
            f"Cook's D should fire (>4/N) on outlier; got {diag.max_cooks_d}")
        self.assertEqual(diag.cooks_d_argmax, 0,
            "max Cook's D should be on the engineered outlier (row 0)")

    def test_2b_neg_cooks_d_computational_soundness(self):
        """Cook's D must be finite and non-negative on clean data.

        Note on the 4/N threshold: it IS sensitive at small N — a clean
        random sample with one row at the tail can produce Cook's D
        > 4/N just from sampling variation. The 4/N threshold is the
        textbook (Bollen & Jackman 1985) but partners will see
        occasional INFLUENTIAL_OUTLIER chips on clean data. The
        diagnostic is informative (partner investigates, confirms no
        problem, moves on) rather than gated. The test here verifies
        the computation is sound, not that random data never trips it.
        """
        rng = np.random.default_rng(0)
        n, p = 80, 3
        X = rng.standard_normal((n, p))
        y = X @ np.array([1.0, 0.5, -0.3]) + 0.1 * rng.standard_normal(n)
        diag = _compute_diagnostics(X, y, alpha=1.0)
        self.assertGreaterEqual(diag.max_cooks_d, 0.0,
            "Cook's D must be non-negative")
        self.assertFalse(np.isnan(diag.max_cooks_d),
            "Cook's D must be finite (not NaN)")
        self.assertFalse(np.isinf(diag.max_cooks_d),
            "Cook's D must be finite (not Inf)")

    def test_2c_bp_fires_on_heteroscedastic_residuals(self):
        """Variance must be LINEAR in X for BP to detect (BP regresses
        resid² ~ X linearly). Construct X[:,0] as positive shifted
        gaussian and tie noise variance linearly to it."""
        rng = np.random.default_rng(42)
        n, p = 100, 3
        # Make X[:,0] positive so we can scale variance linearly with it
        X = rng.standard_normal((n, p))
        X[:, 0] = np.abs(X[:, 0]) + 1.0  # in [1, 4] roughly
        true_w = np.array([1.0, 0.5, 0.2])
        # Variance LINEAR in X[:,0] — BP's linear assumption holds
        noise_sd = 0.1 + 1.5 * X[:, 0]   # ranges roughly [1.6, 6.1]
        noise = noise_sd * rng.standard_normal(n)
        y = X @ true_w + noise
        diag = _compute_diagnostics(X, y, alpha=1.0)
        self.assertLess(
            diag.bp_pvalue, 0.05,
            f"BP should fire (p<0.05) on linear-in-X heteroscedasticity; "
            f"got p={diag.bp_pvalue}")
        fired = diag.failure_reasons_at(n, p)
        self.assertIn(FailureReason.HETEROSCEDASTIC, fired)

    def test_2c_neg_bp_does_not_fire_on_homoscedastic_data(self):
        rng = np.random.default_rng(42)
        n, p = 80, 3
        X = rng.standard_normal((n, p))
        y = X @ np.array([1.0, 0.5, 0.2]) + 0.3 * rng.standard_normal(n)
        diag = _compute_diagnostics(X, y, alpha=1.0)
        self.assertGreater(
            diag.bp_pvalue, 0.10,
            f"BP should not fire borderline on homoscedastic data; "
            f"got p={diag.bp_pvalue}")

    def test_2e_nonlinear_residual_pattern_fires(self):
        """RESET-style curvature detection — regress resid on fitted²
        to catch missing nonlinearity.

        Fixture needs y to have BOTH a linear component (so the ridge
        fit isn't constant — otherwise fitted² has no variance) AND
        a quadratic component the linear fit misses. y = x + 0.5*x²
        + noise produces a non-constant fitted and residuals correlated
        with fitted² (the missing quadratic component).
        """
        rng = np.random.default_rng(0)
        n, p = 60, 2
        X = rng.standard_normal((n, p))
        # Linear + quadratic in x[:,0]. Linear ridge captures the
        # linear component → fitted varies → residual = 0.5x² + noise.
        # Residual ~ x², fitted ~ x → resid/fitted² has detectable slope.
        y = X[:, 0] + 0.5 * X[:, 0] ** 2 + 0.5 * X[:, 1] + 0.2 * rng.standard_normal(n)
        diag = _compute_diagnostics(X, y, alpha=1.0)
        self.assertGreater(
            abs(diag.resid_fit_t_slope), 2.0,
            f"RESET-style nonlinearity diagnostic should fire on "
            f"linear-plus-quadratic data; got t={diag.resid_fit_t_slope}")


# ────────────────────────────────────────────────────────────────────
# Category 3 — Multi-diagnostic composition
# ────────────────────────────────────────────────────────────────────


class TestCompositionRule(unittest.TestCase):

    def test_3a_compound_fixture_fires_multiple_diagnostics(self):
        """≥2 diagnostics fire on a compound fixture → composition rule
        produces DIAGNOSTIC_SUSPECT.

        Constructive fixture: take the 2a collinearity fixture (which
        reliably fires VIF) and inject an extreme tail row. MULTICOLLINEAR
        + INFLUENTIAL_OUTLIER (or MULTICOLLINEAR + HIGH_LEVERAGE) both
        fire — exact pair varies by fixture but the count is ≥2, which
        is what drives the DIAGNOSTIC_SUSPECT composition.
        """
        rng = np.random.default_rng(0)
        n, p = 25, 4
        X = rng.standard_normal((n, p))
        # Near-perfect collinearity (same as fixture 2a)
        X[:, 1] = 2.0 * X[:, 0] + 0.01 * rng.standard_normal(n)
        y = X @ np.array([1.0, 1.0, 0.5, 0.5]) + 0.1 * rng.standard_normal(n)
        # Extreme x + extreme y row — drives leverage AND outlier signals
        X[0] = np.array([6.0, 12.0, 0.0, 0.0])
        y[0] = -50.0
        diag = _compute_diagnostics(X, y, alpha=1.0)
        fired = diag.failure_reasons_at(n, p)
        # MULTICOLLINEAR is the reliable trigger; the second can vary
        self.assertIn(FailureReason.MULTICOLLINEAR, fired,
            f"MULTICOLLINEAR should fire on engineered collinearity; "
            f"got fired={fired}, VIF={diag.max_vif}")
        self.assertGreaterEqual(len(fired), 2,
            f"Engineered fixture should fire ≥2 diagnostics (drives "
            f"DIAGNOSTIC_SUSPECT composition); got {fired}, "
            f"VIF={diag.max_vif:.1f}, Cook's D={diag.max_cooks_d:.3f}, "
            f"leverage={diag.max_leverage:.3f}, "
            f"BP p={diag.bp_pvalue:.3f}, t-slope={diag.resid_fit_t_slope:.2f}")

    def test_3b_heteroscedastic_fires_in_isolation_or_compound(self):
        """Single diagnostic case — verify HETEROSCEDASTIC fires.

        Note: a heteroscedasticity fixture may legitimately also trigger
        leverage/outlier on the same extreme rows (the high-variance
        tail rows naturally have high leverage and high residuals).
        The test verifies HETEROSCEDASTIC is in the fired list — the
        composition rule is exercised in test_3a.
        """
        rng = np.random.default_rng(42)
        n, p = 100, 3
        X = rng.standard_normal((n, p))
        X[:, 0] = np.abs(X[:, 0]) + 1.0
        noise = (0.1 + 1.5 * X[:, 0]) * rng.standard_normal(n)
        y = X @ np.array([1.0, 0.5, 0.2]) + noise
        diag = _compute_diagnostics(X, y, alpha=1.0)
        fired = diag.failure_reasons_at(n, p)
        self.assertIn(FailureReason.HETEROSCEDASTIC, fired,
            f"HETEROSCEDASTIC should fire on linear-in-X variance; "
            f"got {fired}")


# ────────────────────────────────────────────────────────────────────
# Category 4 — R2_NEGATIVE-and-Cook's-D verification refinement
# ────────────────────────────────────────────────────────────────────


class TestR2NegativeCooksDVerification(unittest.TestCase):
    """Fixtures 4A / 4B from D5 — verify the R2_NEGATIVE-and-Cook's-D
    refinement actually recomputes LOO R² without the outlier instead
    of assuming the outlier caused the negative R²."""

    def _make_scenario_a_fixture(self, seed=999):
        """Scenario A: clean linear data + one extreme outlier that
        single-handedly drags LOO R² negative. Removing the outlier
        recovers R² > 0."""
        rng = np.random.default_rng(seed)
        n, p = 25, 3
        X = rng.standard_normal((n, p))
        true_w = np.array([1.0, 0.5, 0.3])
        y = X @ true_w + 0.1 * rng.standard_normal(n)
        # Inject extreme outlier
        X[0] = np.array([6.0, 6.0, 6.0])
        y[0] = -50.0
        return X, y

    def test_4a_scenario_a_preconditions(self):
        """Pre-conditions for Scenario A:
        1. LOO R² < 0 on full data
        2. Cook's D > 4/N on full data
        3. LOO R² ≥ 0 after removing the high-Cook's-D row
        """
        X, y = self._make_scenario_a_fixture()
        n, p = X.shape
        # 1. Full-data LOO R² < 0
        r2_full = _loo_r_squared_shortcut(X, y, alpha=1.0)
        self.assertLess(r2_full, 0,
            f"Pre-condition: full-data LOO R² should be negative; got {r2_full}")
        # 2. Cook's D fires on the outlier
        diag = _compute_diagnostics(X, y, alpha=1.0)
        self.assertGreater(diag.max_cooks_d, 4.0 / n,
            f"Pre-condition: Cook's D should fire (>4/N); got {diag.max_cooks_d}")
        # 3. R² recovers after removing the high-Cook's-D row
        mask = np.ones(n, dtype=bool)
        mask[diag.cooks_d_argmax] = False
        r2_no_outlier = _loo_r_squared_shortcut(X[mask], y[mask], alpha=1.0)
        self.assertGreaterEqual(r2_no_outlier, 0,
            f"Pre-condition: LOO R² should recover ≥0 after outlier removal; "
            f"got {r2_no_outlier}")

    def test_4a_scenario_a_predict_ridge_returns_influential_outlier(self):
        """Scenario A integration: _predict_ridge should fire
        INFLUENTIAL_OUTLIER (single reason) after the verification step
        confirms the outlier caused the negative R²."""
        X, y = self._make_scenario_a_fixture()
        # Build the synthetic peers + known to drive _predict_ridge
        comparables = []
        for i in range(X.shape[0]):
            comparables.append({
                "feat0": float(X[i, 0]),
                "feat1": float(X[i, 1]),
                "feat2": float(X[i, 2]),
                "target_metric": float(y[i]),
                "similarity_score": 1.0,
            })
        # The "known" hospital — pick a typical x_target
        known = {"feat0": 0.0, "feat1": 0.0, "feat2": 0.0}
        pm = _predict_ridge(
            target="target_metric", known=known,
            comparables=comparables, coverage=0.9, seed=42,
        )
        self.assertIsNotNone(pm, "Expected ridge to produce a prediction")
        self.assertEqual(
            pm.failure_reason, FailureReason.INFLUENTIAL_OUTLIER,
            f"Scenario A should fire INFLUENTIAL_OUTLIER after verification; "
            f"got {pm.failure_reason}")
        # No contributing_sources for a single-reason fire
        self.assertEqual(pm.contributing_sources, [],
            "Single-reason fires should have empty contributing_sources")

    def _make_scenario_b_fixture(self, seed=1234):
        """Scenario B: X and y truly independent + one outlier. R²
        stays negative after outlier removal — the model is genuinely
        anti-informative AND has an outlier."""
        rng = np.random.default_rng(seed)
        n, p = 25, 3
        X = rng.standard_normal((n, p))
        y = rng.standard_normal(n)  # independent of X
        # Inject outlier on top
        X[0] = np.array([5.0, 5.0, 5.0])
        y[0] = -10.0
        return X, y

    def test_4b_scenario_b_preconditions(self):
        """Pre-conditions for Scenario B (per D5 refinement):
        1. LOO R² < 0 on full data
        2. Cook's D > 4/N on full data (refinement addition)
        3. LOO R² stays < 0 after outlier removal
        """
        X, y = self._make_scenario_b_fixture()
        n, p = X.shape
        r2_full = _loo_r_squared_shortcut(X, y, alpha=1.0)
        self.assertLess(r2_full, 0,
            f"Pre-condition 1: full-data LOO R² < 0; got {r2_full}")
        diag = _compute_diagnostics(X, y, alpha=1.0)
        self.assertGreater(diag.max_cooks_d, 4.0 / n,
            f"Pre-condition 2 (refinement): Cook's D > 4/N; "
            f"got {diag.max_cooks_d}")
        mask = np.ones(n, dtype=bool)
        mask[diag.cooks_d_argmax] = False
        r2_no_outlier = _loo_r_squared_shortcut(X[mask], y[mask], alpha=1.0)
        self.assertLess(r2_no_outlier, 0,
            f"Pre-condition 3: LOO R² should stay <0 after outlier removal "
            f"(model genuinely anti-informative); got {r2_no_outlier}")

    def test_4b_scenario_b_predict_ridge_unit_logic(self):
        """Unit-level verification of the R2_NEGATIVE-and-Cook's-D
        Scenario B behavior — the integration via _predict_ridge is
        complicated by RidgeCV (which picks α to maximize LOO R²,
        often avoiding R²<0 by over-regularizing to mean). The unit
        test exercises the verification logic directly: at the
        scenario-B fixture's α=1.0, both R² are negative AND removing
        the outlier doesn't recover. In an integrated _predict_ridge
        path, the composition rule produces DIAGNOSTIC_SUSPECT or
        a multi-flag chip — either is methodologically correct because
        the data is genuinely bad regardless of which sub-diagnostic
        triggers loudest.
        """
        X, y = self._make_scenario_b_fixture()
        n = X.shape[0]
        # Verify the verification logic's IF-IF-ELSE branches:
        # Step 1: r2 < 0 confirmed (pre-condition test passes)
        r2_full = _loo_r_squared_shortcut(X, y, alpha=1.0)
        self.assertLess(r2_full, 0)
        # Step 2: Cook's D > threshold (pre-condition test passes)
        diag = _compute_diagnostics(X, y, alpha=1.0)
        self.assertGreater(diag.max_cooks_d, 4.0 / n)
        # Step 3: removing the high-Cook's-D row does NOT recover R²
        mask = np.ones(n, dtype=bool)
        mask[diag.cooks_d_argmax] = False
        r2_no_outlier = _loo_r_squared_shortcut(X[mask], y[mask], alpha=1.0)
        self.assertLess(r2_no_outlier, 0)
        # In _predict_ridge under this exact (X, y, α=1.0) combination,
        # this would route to DIAGNOSTIC_SUSPECT branch. We can't easily
        # test that through the live RidgeCV path because RidgeCV picks
        # α to keep R² as positive as possible — see docstring.


# ────────────────────────────────────────────────────────────────────
# Category 5 — ALPHA_AT_BOUNDARY guardrail (Edge Case 3 ↔ 4)
# ────────────────────────────────────────────────────────────────────


class TestAlphaAtBoundaryGuardrail(unittest.TestCase):

    def test_5a_near_constant_y_does_not_fire_boundary_chip(self):
        """Edge Case 3: y is near-constant → RidgeCV picks max α (correct
        behavior, over-regularize to mean). ALPHA_AT_BOUNDARY should NOT
        fire because the boundary selection is the right answer, not a
        search-range failure."""
        rng = np.random.default_rng(0)
        n, p = 20, 3
        X = rng.standard_normal((n, p))
        y = np.full(n, 5.0) + 1e-6 * rng.standard_normal(n)
        alpha, at_boundary = _loo_select_alpha(X, y)
        # The picked α may legitimately be at the upper boundary, but
        # the guardrail recognizes y is near-constant and doesn't flag
        self.assertFalse(
            at_boundary,
            "ALPHA_AT_BOUNDARY should not fire on near-constant y "
            "(boundary selection is legitimate, not a search-range issue)")


# ────────────────────────────────────────────────────────────────────
# Wilson-Hilferty smoke tests (precision verification is in
# tests/test_b1_bp_precision.py)
# ────────────────────────────────────────────────────────────────────


class TestWilsonHilfertyChi2SF(unittest.TestCase):

    def test_x_le_zero_returns_one(self):
        self.assertEqual(_wilson_hilferty_chi2_sf(0.0, df=3), 1.0)
        self.assertEqual(_wilson_hilferty_chi2_sf(-1.0, df=3), 1.0)

    def test_large_x_returns_small_p(self):
        # χ²(3) survival at x=20 is ~0.00017 — should be << 0.05
        p = _wilson_hilferty_chi2_sf(20.0, df=3)
        self.assertLess(p, 0.001)

    def test_median_x_returns_p_near_half(self):
        # χ²(3) median is 2.366 — survival there should be ~0.5
        p = _wilson_hilferty_chi2_sf(2.366, df=3)
        self.assertAlmostEqual(p, 0.5, delta=0.05)

    def test_p_always_floored_above_zero(self):
        """No matter how extreme x is, p should be > 0 (numerical floor)."""
        self.assertGreater(_wilson_hilferty_chi2_sf(1000.0, df=3), 0)


if __name__ == "__main__":
    unittest.main()
