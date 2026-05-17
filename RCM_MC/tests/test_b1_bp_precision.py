"""B.1 Breusch-Pagan precision verification — D2 follow-through.

D2 specified BP via the Wilson-Hilferty chi-squared survival
approximation (no scipy dependency in runtime). User required a
precision pre-check before code: verify Wilson-Hilferty p-values
through our erf approximation stay within ±0.01 of scipy's exact
chi2.sf across the df values BP actually hits in production
(df ∈ {3, 5, 10}, matching the 3-10 feature count typical for
RCM-MC's per-cohort ridge fits).

Scipy-gated: skipped automatically on environments without scipy
(local dev envs may not have it; CI does). The scipy import is
test-only and never touches production code.
"""
from __future__ import annotations

import unittest

import numpy as np


def _has_scipy() -> bool:
    try:
        import scipy.stats  # noqa: F401
        return True
    except ImportError:
        return False


@unittest.skipUnless(
    _has_scipy(),
    "scipy not installed — BP precision verification skipped (CI runs it)",
)
class TestWilsonHilfertyPrecisionVsScipy(unittest.TestCase):
    """Compare Wilson-Hilferty-through-our-erf vs scipy.stats.chi2.sf
    on the chi-squared survival values BP actually uses. Pass gate:
    max |Δp| < 0.01 across df ∈ {3, 5, 10}."""

    def test_max_error_under_threshold(self):
        import scipy.stats as ss
        from rcm_mc.ml.ridge_predictor import _wilson_hilferty_chi2_sf

        rng = np.random.default_rng(0)
        errors = []
        for df in (3, 5, 10):
            samples = rng.chisquare(df, size=20)
            for x in samples:
                p_wh = _wilson_hilferty_chi2_sf(float(x), df)
                p_scipy = float(ss.chi2.sf(x, df))
                errors.append((df, float(x), p_wh, p_scipy, abs(p_wh - p_scipy)))

        max_err = max(e[4] for e in errors)
        self.assertLess(
            max_err, 0.01,
            f"Wilson-Hilferty error > 0.01 (max={max_err:.4f}) — BP "
            f"p-value reporting is unreliable at this precision. "
            f"Fall back to BP-statistic-only reporting per D2 plan, "
            f"OR improve the erf approximation. "
            f"Sample errors (df, x, p_wh, p_scipy, |Δ|): {errors[:5]}",
        )

    def test_boundary_x_values_match(self):
        """At x values near the chi-squared α=0.05 critical points,
        the WH approximation must agree with scipy to ±0.005 so the
        BP fire/no-fire boundary is correctly placed."""
        import scipy.stats as ss
        from rcm_mc.ml.ridge_predictor import _wilson_hilferty_chi2_sf

        # Critical values for χ²(df) at α=0.05:
        # χ²(3) = 7.81, χ²(5) = 11.07, χ²(10) = 18.31
        critical_points = [(3, 7.815), (5, 11.070), (10, 18.307)]
        for df, x_crit in critical_points:
            p_wh = _wilson_hilferty_chi2_sf(x_crit, df)
            p_scipy = float(ss.chi2.sf(x_crit, df))
            self.assertAlmostEqual(
                p_wh, p_scipy, delta=0.005,
                msg=f"χ²({df}) at critical x={x_crit}: WH={p_wh:.4f}, "
                    f"scipy={p_scipy:.4f} — boundary placement off",
            )


if __name__ == "__main__":
    unittest.main()
