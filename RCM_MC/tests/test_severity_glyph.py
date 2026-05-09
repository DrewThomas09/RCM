"""tests for ``severity_glyph`` (P98)."""
from __future__ import annotations

import unittest

from rcm_mc.ui._ui_kit import severity_glyph


class GlyphPerSeverity(unittest.TestCase):

    EXPECTATIONS = {
        "safe":     ("●", "tone-positive"),
        "fresh":    ("●", "tone-positive"),
        "green":    ("●", "tone-positive"),
        "amber":    ("◐", "tone-warning"),
        "yellow":   ("◐", "tone-warning"),
        "tight":    ("◐", "tone-warning"),
        "red":      ("▲", "tone-negative"),
        "critical": ("▲", "tone-negative"),
        "tripped":  ("▲", "tone-negative"),
        "cold":     ("○", "tone-muted"),
        "no_data":  ("—", "tone-muted"),
        "zero":     ("—", "tone-muted"),
    }

    def test_each_severity_emits_glyph_and_class(self) -> None:
        for sev, (glyph, cls) in self.EXPECTATIONS.items():
            with self.subTest(severity=sev):
                html = severity_glyph(sev)
                self.assertIn(glyph, html)
                self.assertIn(cls, html)


class CaseInsensitiveAndStripped(unittest.TestCase):

    def test_uppercase_severity(self) -> None:
        html = severity_glyph("CRITICAL")
        self.assertIn("▲", html)

    def test_whitespace_stripped(self) -> None:
        html = severity_glyph("  red  ")
        self.assertIn("▲", html)


class UnknownSeverityFallback(unittest.TestCase):

    def test_unknown_severity_renders_dot(self) -> None:
        html = severity_glyph("nonsense")
        self.assertIn("·", html)
        self.assertIn("tone-muted", html)


class AccessibleLabel(unittest.TestCase):

    def test_aria_label_describes_glyph(self) -> None:
        html = severity_glyph("critical")
        self.assertIn("aria-label=", html)
        self.assertIn("triangle", html)


if __name__ == "__main__":
    unittest.main()
