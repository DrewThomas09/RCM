"""tests for ``audit_number_format`` (P94).

Catches rendered numbers that violate the CLAUDE.md compliance
rules. Designed to run on already-rendered HTML strings, so it
catches both new code AND legacy callsites that bypass
``format_value``.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._ui_kit import format_value
from rcm_mc.ui.voice_audit import audit_number_format


class CatchesViolations(unittest.TestCase):

    def test_money_one_decimal(self) -> None:
        issues = audit_number_format("EBITDA $67.5M")
        self.assertTrue(issues)
        self.assertEqual(issues[0]["rule"], "number-format")

    def test_money_no_decimals(self) -> None:
        issues = audit_number_format("Revenue $450M")
        self.assertTrue(issues)

    def test_percent_no_decimals(self) -> None:
        issues = audit_number_format("Denial 9% (peer median)")
        self.assertTrue(issues)

    def test_multiple_one_decimal(self) -> None:
        issues = audit_number_format("MOIC 2.8x")
        self.assertTrue(issues)


class CleanForFormatValueOutput(unittest.TestCase):
    """Output produced by ``format_value`` must pass the audit."""

    def test_money_passes(self) -> None:
        out = format_value(450_250_000, kind="money")  # "$450.25M"
        self.assertEqual(audit_number_format(out), [])

    def test_percent_passes(self) -> None:
        out = format_value(0.153, kind="percent")  # "15.3%"
        self.assertEqual(audit_number_format(out), [])

    def test_multiple_passes(self) -> None:
        out = format_value(2.8, kind="multiple")  # "2.80x"
        self.assertEqual(audit_number_format(out), [])


class GracefulInput(unittest.TestCase):

    def test_empty_returns_empty(self) -> None:
        self.assertEqual(audit_number_format(""), [])

    def test_no_numbers_returns_empty(self) -> None:
        self.assertEqual(
            audit_number_format("Pure prose with no numbers"),
            [],
        )


if __name__ == "__main__":
    unittest.main()
