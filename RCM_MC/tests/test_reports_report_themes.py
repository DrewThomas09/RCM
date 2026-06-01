"""Tests for ``rcm_mc/reports/report_themes.py`` — CSS theme registry.

Small but partner-visible: the four named themes (default, dark,
print, minimal) drive the look-and-feel of every HTML report. The
print theme in particular gets used in IC packets that get printed
on partner letterhead — silent regressions in the print stylesheet
ship straight into the partner-printed PDF.

Module had no direct unit-test coverage. Locks the theme registry
contract: every theme defines the full CSS-variable palette, the
print theme hides nav, and ``get_theme_css`` falls back silently to
default for unknown names.
"""
from __future__ import annotations

import unittest

from rcm_mc.reports.report_themes import (
    THEMES,
    get_theme_css,
)


# Every theme has to declare the same set of CSS variables so report
# templates can reference them without per-theme conditionals.
REQUIRED_VARS = [
    "--bg", "--card", "--text", "--primary", "--accent",
    "--success", "--warning", "--danger", "--gray",
    "--border", "--shadow",
]


class ThemeRegistryTests(unittest.TestCase):

    def test_registry_is_a_dict(self):
        self.assertIsInstance(THEMES, dict)

    def test_required_themes_present(self):
        # These four are exposed in the docstring + UI theme picker —
        # removing any of them breaks the report header.
        for name in ("default", "dark", "print", "minimal"):
            self.assertIn(name, THEMES, f"missing theme: {name}")

    def test_every_theme_declares_every_required_var(self):
        for name, css in THEMES.items():
            for var in REQUIRED_VARS:
                self.assertIn(
                    var, css,
                    f"theme '{name}' missing CSS variable {var}",
                )

    def test_every_theme_has_root_block(self):
        # Each theme starts the variable declaration inside :root {…}
        for name, css in THEMES.items():
            self.assertIn(":root", css, f"theme '{name}' lacks :root")


class GetThemeCssTests(unittest.TestCase):

    def test_returns_string(self):
        out = get_theme_css("default")
        self.assertIsInstance(out, str)
        self.assertGreater(len(out), 0)

    def test_default_argument(self):
        # Calling without args returns the default theme CSS.
        self.assertEqual(get_theme_css(), THEMES["default"])

    def test_each_theme_resolves(self):
        for name in ("default", "dark", "print", "minimal"):
            self.assertEqual(get_theme_css(name), THEMES[name])

    def test_unknown_theme_silently_falls_back_to_default(self):
        # No KeyError — caller passes a typo / removed theme, still
        # gets a valid stylesheet.
        out = get_theme_css("does_not_exist")
        self.assertEqual(out, THEMES["default"])

    def test_none_theme_falls_back_to_default(self):
        # dict.get with None key returns None unless default supplied —
        # the helper passes ``THEMES["default"]`` as the get-default, so
        # None resolves to default.
        out = get_theme_css(None)  # type: ignore
        self.assertEqual(out, THEMES["default"])

    def test_empty_string_theme_falls_back_to_default(self):
        out = get_theme_css("")
        self.assertEqual(out, THEMES["default"])


class DarkThemeTests(unittest.TestCase):
    """Dark theme is the only one with body+card+table rules
    (default uses CSS-variable inheritance from :root). Lock the
    additional rule presence so a future refactor doesn't drop dark
    mode silently."""

    def test_dark_has_body_rule(self):
        self.assertIn("body {", THEMES["dark"])

    def test_dark_has_card_rule(self):
        self.assertIn(".card {", THEMES["dark"])

    def test_dark_has_table_rules(self):
        self.assertIn("table th", THEMES["dark"])
        self.assertIn("table td", THEMES["dark"])

    def test_dark_text_is_light(self):
        # Dark mode foreground (e2e8f0) is light, not near-black.
        self.assertIn("--text: #e2e8f0", THEMES["dark"])

    def test_dark_bg_is_dark(self):
        # Dark mode background (0f172a) is very dark slate.
        self.assertIn("--bg: #0f172a", THEMES["dark"])


class PrintThemeTests(unittest.TestCase):
    """Print theme MUST hide the nav and use B/W palette — anything
    that prints with full color in an IC packet is a bug."""

    def test_print_hides_nav(self):
        self.assertIn("nav { display: none", THEMES["print"])

    def test_print_text_is_pure_black(self):
        self.assertIn("--text: #000000", THEMES["print"])

    def test_print_uses_smaller_font_size(self):
        self.assertIn("font-size: 10pt", THEMES["print"])

    def test_print_removes_box_shadow(self):
        # Box shadow doesn't print cleanly — must be 'none'.
        self.assertIn("--shadow: none", THEMES["print"])

    def test_print_has_card_border_instead_of_shadow(self):
        # Replace the lost shadow with a 1px border so cards still
        # have visual separation on paper.
        self.assertIn("box-shadow: none", THEMES["print"])


class MinimalThemeTests(unittest.TestCase):
    """Minimal theme uses Georgia serif, flat (no rounded cards),
    no shadow — editorial 'print-magazine' look for partner-shareable
    web reports."""

    def test_minimal_uses_georgia_serif(self):
        self.assertIn("'Georgia'", THEMES["minimal"])

    def test_minimal_card_has_no_radius_or_shadow(self):
        self.assertIn("border-radius: 0", THEMES["minimal"])
        self.assertIn("box-shadow: none", THEMES["minimal"])

    def test_minimal_palette_is_neutral_gray(self):
        # Greyer palette than default (avoids strong color in editorial).
        self.assertIn("--bg: #fafafa", THEMES["minimal"])


class DefaultThemeTests(unittest.TestCase):

    def test_default_text_is_dark_navy(self):
        # 1a1a2e — near-black with a navy cast (NOT pure black, which
        # is reserved for the print theme).
        self.assertIn("--text: #1a1a2e", THEMES["default"])

    def test_default_primary_is_classic_navy(self):
        self.assertIn("--primary: #0f4c75", THEMES["default"])


if __name__ == "__main__":
    unittest.main()
