"""tests for ``rcm_mc.ui._ui_kit.format_value``.

PROMPTS.md Phase 1 / Prompt 9 introduced this helper to draw an
explicit visual line between *not yet computed* metrics and real
zeros / real numbers. The helper is the seed for a broader migration
across Portfolio overview, My Dashboard, Heatmap, etc.

These tests pin the contract:

* ``None`` and float ``NaN`` always render the missing-label span,
  regardless of ``kind``.
* Real zero renders as ``0`` / ``$0.00`` / ``0.0%`` / ``0.00x`` —
  never the missing-label.
* Each ``kind`` follows the formatting rule from CLAUDE.md.
"""
from __future__ import annotations

import math
import unittest

from rcm_mc.ui._ui_kit import format_value


class MissingValueRendering(unittest.TestCase):

    MISSING_SPAN = '<span class="muted unpopulated">'

    def test_none_renders_missing_label_for_every_kind(self) -> None:
        for kind in ("money", "percent", "count", "multiple", "text"):
            with self.subTest(kind=kind):
                out = format_value(None, kind=kind)
                self.assertIn(self.MISSING_SPAN, out)
                self.assertIn("not yet computed", out)

    def test_nan_float_renders_missing_label(self) -> None:
        for kind in ("money", "percent", "count", "multiple"):
            with self.subTest(kind=kind):
                out = format_value(math.nan, kind=kind)
                self.assertIn(self.MISSING_SPAN, out)

    def test_custom_missing_label_propagates(self) -> None:
        out = format_value(None, kind="money", missing_label="—")
        self.assertIn(">—<", out)

    def test_missing_label_is_html_escaped(self) -> None:
        # Caller-supplied labels could contain user input; the helper
        # must escape them so an injection attempt becomes inert text.
        out = format_value(None, kind="text",
                           missing_label="<script>alert(1)</script>")
        self.assertNotIn("<script>", out)
        self.assertIn("&lt;script&gt;", out)


class RealZeroRendering(unittest.TestCase):
    """Real zeros must render as zero, not as the missing label."""

    def test_zero_money(self) -> None:
        self.assertEqual(format_value(0, kind="money"), "$0.00")

    def test_zero_percent(self) -> None:
        self.assertEqual(format_value(0, kind="percent"), "0.0%")

    def test_zero_count(self) -> None:
        self.assertEqual(format_value(0, kind="count"), "0")

    def test_zero_multiple(self) -> None:
        self.assertEqual(format_value(0, kind="multiple"), "0.00x")


class FormatPerKind(unittest.TestCase):

    def test_money_two_decimals_with_M_suffix(self) -> None:
        # Caller passes raw dollars; helper auto-picks M/B suffix.
        self.assertEqual(format_value(450_250_000, kind="money"),
                         "$450.25M")

    def test_money_two_decimals_with_B_suffix(self) -> None:
        self.assertEqual(format_value(1_204_500_000, kind="money"),
                         "$1.20B")

    def test_money_under_a_million_keeps_full_dollars(self) -> None:
        self.assertEqual(format_value(1_204.50, kind="money"),
                         "$1,204.50")

    def test_percent_one_decimal(self) -> None:
        # Caller passes a 0..1 fraction; helper * 100.
        self.assertEqual(format_value(0.153, kind="percent"), "15.3%")

    def test_percent_negative_keeps_sign(self) -> None:
        self.assertEqual(format_value(-0.041, kind="percent"), "-4.1%")

    def test_count_thousands_separator(self) -> None:
        self.assertEqual(format_value(6024, kind="count"), "6,024")

    def test_multiple_two_decimals(self) -> None:
        self.assertEqual(format_value(2.8, kind="multiple"), "2.80x")

    def test_text_is_html_escaped(self) -> None:
        out = format_value("<b>boom</b>", kind="text")
        self.assertEqual(out, "&lt;b&gt;boom&lt;/b&gt;")


class InvalidKindRaises(unittest.TestCase):

    def test_invalid_kind_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            format_value(1.0, kind="dollars")


if __name__ == "__main__":
    unittest.main()
