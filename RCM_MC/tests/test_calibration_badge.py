"""tests for ``calibration_badge`` (P71)."""
from __future__ import annotations

import unittest

from rcm_mc.ui._ui_kit import calibration_badge


class ToneBranches(unittest.TestCase):

    def test_meets_target_positive(self) -> None:
        html = calibration_badge(0.91, target=0.90)
        self.assertIn("tone-positive", html)
        self.assertIn("91%", html)

    def test_within_5pp_warning(self) -> None:
        html = calibration_badge(0.86, target=0.90)
        self.assertIn("tone-warning", html)

    def test_more_than_5pp_below_negative(self) -> None:
        html = calibration_badge(0.82, target=0.90)
        self.assertIn("tone-negative", html)


class TargetAndSamples(unittest.TestCase):

    def test_target_renders_in_output(self) -> None:
        html = calibration_badge(0.91, target=0.90)
        self.assertIn("target 90%", html)

    def test_n_samples_with_thousands_separator(self) -> None:
        html = calibration_badge(0.91, target=0.90, n_samples=1234)
        self.assertIn("over 1,234 held-out samples", html)

    def test_no_samples_omits_detail(self) -> None:
        html = calibration_badge(0.91, target=0.90)
        self.assertNotIn("samples", html)


class MissingInput(unittest.TestCase):

    def test_none_coverage_returns_empty(self) -> None:
        self.assertEqual(calibration_badge(None), "")

    def test_invalid_coverage_returns_empty(self) -> None:
        self.assertEqual(calibration_badge("not-a-number"), "")


if __name__ == "__main__":
    unittest.main()
