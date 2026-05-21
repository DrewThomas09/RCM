"""Pin for the Accuracy-vs-Reliability lead scatter on /model-validation.

The scorecard table keeps the two model-quality axes — accuracy (R²)
and reliability (90%-CI coverage) — in separate columns. The lead
scatter pairs them (R² x, coverage y) with reference lines at the
grade-A R² bar (0.70) and the nominal 90% conformal coverage, so a
partner reads the trustworthy quadrant (accurate AND well-calibrated)
at a glance. Under-covered metrics flag red even at high R² — the
overconfident-interval case that's dangerous for IC.
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace


def _perf(metric, r2, coverage_rate):
    return SimpleNamespace(metric=metric, r2=r2, coverage_rate=coverage_rate)


class AccuracyCoverageScatterTests(unittest.TestCase):
    def _scatter(self, perfs):
        from rcm_mc.ui.model_validation_page import _accuracy_coverage_scatter
        return _accuracy_coverage_scatter(perfs)

    def test_svg_with_quadrant_refs_and_labels(self):
        html = self._scatter([
            _perf("initial_denial_rate", 0.82, 0.91),
            _perf("final_writeoff", 0.55, 0.88),
        ])
        self.assertIn("<svg", html)
        self.assertIn("Accuracy vs Reliability", html)
        self.assertIn("R² (variance explained)", html)
        self.assertIn("90%-CI coverage", html)
        self.assertIn("stroke-dasharray", html)  # R²=0.70 + coverage=0.90 refs

    def test_one_dot_per_metric(self):
        html = self._scatter([
            _perf("a", 0.8, 0.9), _perf("b", 0.6, 0.88), _perf("c", 0.7, 0.92),
        ])
        self.assertEqual(html.count("<circle"), 3)

    def test_tone_flags_undercoverage_and_elite(self):
        # Under-covered (<75%) → negative even though R² is decent;
        # accurate + well-calibrated → positive; over-covered → warning.
        html = self._scatter([
            _perf("elite", 0.78, 0.90),       # positive
            _perf("overconfident", 0.80, 0.68),  # negative (under-covered)
            _perf("conservative", 0.72, 0.98),   # warning (over-covered)
        ])
        self.assertIn("--sc-positive", html)
        self.assertIn("--sc-negative", html)
        self.assertIn("--sc-warning", html)

    def test_empty_below_two_points(self):
        self.assertEqual(self._scatter([_perf("only", 0.8, 0.9)]), "")


if __name__ == "__main__":
    unittest.main()
