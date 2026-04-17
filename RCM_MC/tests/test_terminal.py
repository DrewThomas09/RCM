"""Tests for the stdlib-only terminal styling helpers."""
from __future__ import annotations

import io
import os
import unittest
from unittest.mock import patch

from rcm_mc.infra._terminal import (
    banner,
    completion_box,
    error,
    info,
    paint,
    success,
    supports_color,
    warn,
    wrote,
)


class _FakeTTY(io.StringIO):
    """StringIO subclass that reports as a TTY (to drive supports_color=True)."""
    def isatty(self) -> bool:  # type: ignore[override]
        return True


class TestSupportsColor(unittest.TestCase):
    def test_non_tty_returns_false(self):
        non_tty = io.StringIO()  # isatty() → False
        self.assertFalse(supports_color(stream=non_tty))

    def test_tty_returns_true_by_default(self):
        tty = _FakeTTY()
        # Clean env
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("NO_COLOR", None)
            os.environ.pop("FORCE_COLOR", None)
            os.environ.pop("TERM", None)
            self.assertTrue(supports_color(stream=tty))

    def test_no_color_env_disables(self):
        tty = _FakeTTY()
        with patch.dict(os.environ, {"NO_COLOR": "1"}, clear=False):
            self.assertFalse(supports_color(stream=tty))

    def test_force_color_env_overrides_non_tty(self):
        non_tty = io.StringIO()
        with patch.dict(os.environ, {"FORCE_COLOR": "1"}, clear=False):
            self.assertTrue(supports_color(stream=non_tty))

    def test_dumb_term_disables(self):
        tty = _FakeTTY()
        with patch.dict(os.environ, {"TERM": "dumb"}, clear=False):
            os.environ.pop("NO_COLOR", None)
            os.environ.pop("FORCE_COLOR", None)
            self.assertFalse(supports_color(stream=tty))


class TestPaint(unittest.TestCase):
    def test_paint_plain_when_no_color(self):
        non_tty = io.StringIO()
        self.assertEqual(paint("hello", color="red", stream=non_tty), "hello")

    def test_paint_wraps_with_ansi_when_color(self):
        tty = _FakeTTY()
        with patch.dict(os.environ, {"FORCE_COLOR": "1"}, clear=False):
            result = paint("hello", color="red", stream=tty)
            self.assertIn("\033[", result)
            self.assertIn("hello", result)
            self.assertTrue(result.endswith("\033[0m"))

    def test_paint_no_codes_when_no_styling(self):
        tty = _FakeTTY()
        with patch.dict(os.environ, {"FORCE_COLOR": "1"}, clear=False):
            # No color, bold, dim, italic — should pass through
            self.assertEqual(paint("plain", stream=tty), "plain")

    def test_paint_unknown_color_ignored(self):
        tty = _FakeTTY()
        with patch.dict(os.environ, {"FORCE_COLOR": "1"}, clear=False):
            result = paint("x", color="definitely-not-a-color", stream=tty)
            self.assertEqual(result, "x")


class TestSemanticHelpers(unittest.TestCase):
    """banner / success / warn / error / wrote all render without color in tests."""

    def test_banner_includes_title(self):
        self.assertIn("My Stage", banner("My Stage", stream=io.StringIO()))

    def test_success_has_check_mark(self):
        self.assertIn("✓", success("done", stream=io.StringIO()))
        self.assertIn("done", success("done", stream=io.StringIO()))

    def test_warn_has_warn_mark(self):
        self.assertIn("⚠", warn("careful", stream=io.StringIO()))

    def test_error_has_error_mark(self):
        self.assertIn("✗", error("broken", stream=io.StringIO()))

    def test_info_has_indent(self):
        self.assertTrue(info("hello").startswith("  "))

    def test_wrote_shows_path(self):
        out = wrote("/tmp/outputs/report.html", stream=io.StringIO())
        self.assertIn("/tmp/outputs/report.html", out)
        self.assertIn("✓", out)
        self.assertIn("wrote", out)


class TestCompletionBox(unittest.TestCase):
    def test_box_contains_title(self):
        out = completion_box("RUN COMPLETE", [("Folder:", "/tmp/x")])
        self.assertIn("RUN COMPLETE", out)

    def test_box_contains_label_value(self):
        out = completion_box("done", [("Label:", "value1")])
        self.assertIn("Label:", out)
        self.assertIn("value1", out)

    def test_box_handles_multi_value_list(self):
        out = completion_box("done", [("Tables:", ["/a.csv", "/b.csv"])])
        self.assertIn("/a.csv", out)
        self.assertIn("/b.csv", out)

    def test_box_has_horizontal_rules(self):
        out = completion_box("done", [("x:", "y")])
        # Three rule lines (top, under-title, bottom)
        rule_lines = [line for line in out.splitlines() if "─" in line]
        self.assertGreaterEqual(len(rule_lines), 3)

    def test_box_empty_items_still_renders_title(self):
        out = completion_box("empty", [])
        self.assertIn("empty", out)

    def test_box_label_column_aligns(self):
        """All labels should be same width (padded)."""
        out = completion_box("x", [("A:", "v1"), ("BBBBB:", "v2")])
        lines = [line for line in out.splitlines() if ":" in line and "─" not in line]
        # The 'A:' line should have padding so its value aligns with 'BBBBB:' line's value
        # Easiest check: both value lines should have the value at the same column.
        a_line = next(line for line in lines if "A:" in line)
        b_line = next(line for line in lines if "BBBBB:" in line)
        self.assertEqual(a_line.index("v1"), b_line.index("v2"))


class TestNoAnsiInCapturedOutput(unittest.TestCase):
    """Critical: pytest captures stdout as non-TTY; existing tests greping for
    text should still work because ANSI codes are suppressed."""

    def test_captured_banner_has_no_ansi(self):
        captured = io.StringIO()
        out = banner("test", stream=captured)
        self.assertNotIn("\033[", out)

    def test_captured_completion_box_has_no_ansi(self):
        captured = io.StringIO()
        out = completion_box("test", [("x:", "y")], stream=captured)
        self.assertNotIn("\033[", out)
