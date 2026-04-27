"""Tests for v3 format helpers in rcm_mc.ui._ui_kit (campaign 1C).

Pins CLAUDE.md's number-formatting spec to the helpers so any
future drift (e.g. someone changing decimals from 2 to 1 in the
financial helper) trips a failing test. Renderers that adopt the
helpers inherit this contract automatically.

What's covered:
  - Output string format for the happy path
  - Tabular-nums utility class (.num) on every emitted span
  - Monospace stack (.mono) on financials and multiples per the
    "value should be visually monospaced" intent
  - None / placeholder behavior (em-dash span, never empty string)
  - Negative-value handling for money (sign in front of $)
  - signed=True for percentages forces +/- sign
  - ISO-date acceptance for date / datetime / string forms,
    rejection of US-style "4/15/2026"
"""
from __future__ import annotations

import unittest
from datetime import date, datetime, timezone

from rcm_mc.ui._ui_kit import (
    fmt_iso_date,
    fmt_moic,
    fmt_money,
    fmt_num,
    fmt_pct,
)


class FmtMoneyTests(unittest.TestCase):
    def test_two_decimals_default(self) -> None:
        self.assertEqual(fmt_money(450.25), '<span class="num mono">$450.25</span>')

    def test_thousands_separator(self) -> None:
        self.assertEqual(fmt_money(1234.5), '<span class="num mono">$1,234.50</span>')

    def test_negative_sign_before_dollar(self) -> None:
        self.assertEqual(fmt_money(-99.9), '<span class="num mono">-$99.90</span>')

    def test_suffix_for_millions(self) -> None:
        self.assertEqual(fmt_money(450.25, suffix="M"), '<span class="num mono">$450.25M</span>')

    def test_none_emits_placeholder(self) -> None:
        self.assertEqual(fmt_money(None), '<span class="num">—</span>')

    def test_string_input_coerced(self) -> None:
        self.assertEqual(fmt_money("1,234.5"), '<span class="num mono">$1,234.50</span>')

    def test_bool_rejected(self) -> None:
        # bool is an int subclass — would render as "1.00" without explicit reject.
        self.assertEqual(fmt_money(True), '<span class="num">—</span>')


class FmtPctTests(unittest.TestCase):
    def test_one_decimal_default(self) -> None:
        self.assertEqual(fmt_pct(15.3), '<span class="num">15.3%</span>')

    def test_signed_positive(self) -> None:
        self.assertEqual(fmt_pct(4.1, signed=True), '<span class="num">+4.1%</span>')

    def test_signed_negative(self) -> None:
        self.assertEqual(fmt_pct(-4.1, signed=True), '<span class="num">-4.1%</span>')

    def test_unsigned_negative_keeps_minus(self) -> None:
        self.assertEqual(fmt_pct(-4.1), '<span class="num">-4.1%</span>')

    def test_none_emits_placeholder(self) -> None:
        self.assertEqual(fmt_pct(None), '<span class="num">—</span>')


class FmtMoicTests(unittest.TestCase):
    def test_two_decimals_with_x_suffix(self) -> None:
        self.assertEqual(fmt_moic(2.5), '<span class="num mono">2.50x</span>')

    def test_keeps_mono_for_alignment(self) -> None:
        self.assertIn('mono', fmt_moic(1.234))

    def test_none_emits_placeholder(self) -> None:
        self.assertEqual(fmt_moic(None), '<span class="num">—</span>')


class FmtNumTests(unittest.TestCase):
    def test_default_zero_decimals_for_counts(self) -> None:
        self.assertEqual(fmt_num(42), '<span class="num">42</span>')

    def test_thousands_separator(self) -> None:
        self.assertEqual(fmt_num(123456), '<span class="num">123,456</span>')

    def test_explicit_decimals(self) -> None:
        self.assertEqual(fmt_num(3.14, decimals=2), '<span class="num">3.14</span>')

    def test_none_emits_placeholder(self) -> None:
        self.assertEqual(fmt_num(None), '<span class="num">—</span>')


class FmtIsoDateTests(unittest.TestCase):
    def test_date_object(self) -> None:
        self.assertEqual(
            fmt_iso_date(date(2026, 4, 15)),
            '<span class="num">2026-04-15</span>',
        )

    def test_datetime_strips_time(self) -> None:
        self.assertEqual(
            fmt_iso_date(datetime(2026, 4, 15, 10, 30, tzinfo=timezone.utc)),
            '<span class="num">2026-04-15</span>',
        )

    def test_iso_string_passes_through(self) -> None:
        self.assertEqual(fmt_iso_date("2026-04-15"), '<span class="num">2026-04-15</span>')

    def test_iso_string_with_time_strips(self) -> None:
        self.assertEqual(
            fmt_iso_date("2026-04-15T10:30:00+00:00"),
            '<span class="num">2026-04-15</span>',
        )

    def test_us_format_rejected(self) -> None:
        self.assertEqual(fmt_iso_date("4/15/2026"), '<span class="num">—</span>')

    def test_empty_string_rejected(self) -> None:
        self.assertEqual(fmt_iso_date(""), '<span class="num">—</span>')

    def test_none_placeholder(self) -> None:
        self.assertEqual(fmt_iso_date(None), '<span class="num">—</span>')


class UtilityClassInvariantsTests(unittest.TestCase):
    """The v3 utility classes are the contract every helper must
    honor. If chartis.css ever renames .num or .mono, these tests
    flip and the rename is visible in CI."""

    def test_every_value_path_uses_num_class(self) -> None:
        for out in (
            fmt_money(1.0), fmt_pct(1.0), fmt_moic(1.0), fmt_num(1),
            fmt_iso_date(date(2026, 1, 1)),
        ):
            self.assertIn('class="num', out, f"missing .num class in: {out}")

    def test_money_and_moic_use_mono(self) -> None:
        self.assertIn('mono', fmt_money(1.0))
        self.assertIn('mono', fmt_moic(1.0))

    def test_placeholder_is_consistent_em_dash(self) -> None:
        for out in (
            fmt_money(None), fmt_pct(None), fmt_moic(None),
            fmt_num(None), fmt_iso_date(None),
        ):
            self.assertEqual(out, '<span class="num">—</span>')


if __name__ == "__main__":
    unittest.main()
