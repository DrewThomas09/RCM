"""tests for ``validate_numeric`` + ``inline_validation_pill`` (P87)."""
from __future__ import annotations

import unittest

from rcm_mc.ui._ui_kit import inline_validation_pill, validate_numeric


class ValidationLevels(unittest.TestCase):

    def test_in_range_ok(self) -> None:
        s = validate_numeric(
            0.50, plausible_min=0.30, plausible_max=0.70,
            field_label="Medicare share",
        )
        self.assertEqual(s["level"], "ok")
        self.assertEqual(s["message"], "")

    def test_outside_typical_warning(self) -> None:
        s = validate_numeric(
            0.85, plausible_min=0.30, plausible_max=0.70,
            field_label="Medicare share",
        )
        self.assertEqual(s["level"], "warning")
        self.assertIn("typical range", s["message"])

    def test_below_hard_min_error(self) -> None:
        s = validate_numeric(
            -50, plausible_min=0, plausible_max=100,
            hard_min=0,
            field_label="EBITDA growth",
        )
        self.assertEqual(s["level"], "error")
        self.assertIn("impossible-value", s["message"])

    def test_above_hard_max_error(self) -> None:
        s = validate_numeric(
            500, plausible_min=0, plausible_max=100,
            hard_max=200,
            field_label="Hold years",
        )
        self.assertEqual(s["level"], "error")

    def test_non_numeric_input_error(self) -> None:
        s = validate_numeric(
            "abc", plausible_min=0, plausible_max=1,
        )
        self.assertEqual(s["level"], "error")
        self.assertIn("not a number", s["message"])

    def test_empty_input_ok(self) -> None:
        # Empty string is "no input yet" — ok, not an error.
        s = validate_numeric(
            "", plausible_min=0, plausible_max=1,
        )
        self.assertEqual(s["level"], "ok")


class InlinePillRendering(unittest.TestCase):

    def test_ok_renders_nothing(self) -> None:
        s = validate_numeric(0.5, plausible_min=0, plausible_max=1)
        self.assertEqual(inline_validation_pill(s), "")

    def test_warning_renders_pill(self) -> None:
        s = validate_numeric(2.0, plausible_min=0, plausible_max=1)
        html = inline_validation_pill(s)
        self.assertIn("validation-pill", html)
        self.assertIn("tone-warning", html)

    def test_error_renders_pill(self) -> None:
        s = validate_numeric(
            -1, plausible_min=0, plausible_max=1, hard_min=0,
        )
        html = inline_validation_pill(s)
        self.assertIn("tone-negative", html)


if __name__ == "__main__":
    unittest.main()
