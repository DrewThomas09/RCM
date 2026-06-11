"""Wave-24 visual: Bayesian prior→posterior interval plot.

The calibration page described shrinkage in a table (numbers + an
80px weight bar) but never drew the geometry — how far each posterior
moved from its prior toward the observed value, and how wide the 90%
credible interval remains. Pins the interval SVG: quality tones,
prior ring / observed × / posterior dot, prior-only rows omit the ×,
and the empty state.
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace

from rcm_mc.ui.bayesian_page import _QUALITY_TONES, _posterior_interval_svg


def _est(metric, prior, observed, n, posterior, ci, quality):
    return SimpleNamespace(
        metric=metric, prior_mean=prior, observed_mean=observed,
        observed_n=n, posterior_mean=posterior,
        credible_interval_90=ci, shrinkage_factor=0.4,
        data_quality=quality,
    )


class PosteriorIntervalChartTests(unittest.TestCase):
    def test_renders_rows_with_quality_tones(self):
        svg = _posterior_interval_svg([
            _est("denial_rate", 0.11, 0.14, 200, 0.135,
                 (0.12, 0.15), "strong"),
            _est("ar_days", 48.0, None, 0, 48.0,
                 (40.0, 56.0), "prior_only"),
        ])
        self.assertIn("<svg", svg)
        self.assertIn("ck-bayes-intervals", svg)
        self.assertIn("Denial Rate", svg)
        self.assertIn("Ar Days", svg)
        self.assertIn(_QUALITY_TONES["strong"], svg)
        self.assertIn(_QUALITY_TONES["prior_only"], svg)

    def test_observed_marker_only_when_data_exists(self):
        with_data = _posterior_interval_svg([
            _est("denial_rate", 0.11, 0.14, 200, 0.135,
                 (0.12, 0.15), "strong"),
        ])
        self.assertIn("<path", with_data)  # the × marker
        prior_only = _posterior_interval_svg([
            _est("ar_days", 48.0, None, 0, 48.0,
                 (40.0, 56.0), "prior_only"),
        ])
        self.assertNotIn("<path", prior_only)

    def test_prior_ring_and_posterior_dot_present(self):
        svg = _posterior_interval_svg([
            _est("clean_claim_rate", 0.85, 0.9, 50, 0.88,
                 (0.84, 0.92), "moderate"),
        ])
        self.assertIn('fill="none" stroke="#7a8699"', svg)   # prior ring
        self.assertIn(f'fill="{_QUALITY_TONES["moderate"]}"', svg)

    def test_empty_renders_nothing(self):
        self.assertEqual(_posterior_interval_svg([]), "")


if __name__ == "__main__":
    unittest.main()
