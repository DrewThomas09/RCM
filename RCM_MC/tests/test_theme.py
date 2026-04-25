"""Tests for the theme toggle + CSS-variables system."""
from __future__ import annotations

import unittest


class TestInitScript(unittest.TestCase):
    def test_renders_script(self):
        from rcm_mc.ui.theme import theme_init_script
        html = theme_init_script()
        self.assertIn("<script>", html)
        self.assertIn("localStorage", html)
        self.assertIn("prefers-color-scheme", html)
        self.assertIn("dataset.theme", html)

    def test_default_dark_fallback(self):
        from rcm_mc.ui.theme import theme_init_script
        html = theme_init_script()
        # Catch block falls back to 'dark'
        self.assertIn('"dark"', html)


class TestStylesheet(unittest.TestCase):
    def test_emits_both_themes(self):
        from rcm_mc.ui.theme import theme_stylesheet
        css = theme_stylesheet()
        # Both theme blocks present
        self.assertIn(':root, [data-theme="dark"]', css)
        self.assertIn('[data-theme="light"]', css)

    def test_required_tokens(self):
        from rcm_mc.ui.theme import theme_stylesheet
        css = theme_stylesheet()
        for token in [
            "--theme-bg-primary",
            "--theme-bg-surface",
            "--theme-text",
            "--theme-text-dim",
            "--theme-border",
            "--theme-accent",
            "--theme-positive",
            "--theme-negative",
            "--theme-watch",
        ]:
            self.assertIn(token, css)

    def test_dark_values(self):
        from rcm_mc.ui.theme import theme_stylesheet
        css = theme_stylesheet()
        # Dark backgrounds
        self.assertIn("#0f172a", css)
        self.assertIn("#1f2937", css)

    def test_light_values(self):
        from rcm_mc.ui.theme import theme_stylesheet
        css = theme_stylesheet()
        # Light backgrounds
        self.assertIn("#f8fafc", css)
        self.assertIn("#ffffff", css)

    def test_html_body_follow_theme(self):
        from rcm_mc.ui.theme import theme_stylesheet
        css = theme_stylesheet()
        # html + body bind to the theme background
        self.assertIn(
            "background: var(--theme-bg-primary)", css)


class TestToggle(unittest.TestCase):
    def test_renders_button(self):
        from rcm_mc.ui.theme import theme_toggle
        html = theme_toggle()
        self.assertIn('id="theme-toggle"', html)
        self.assertIn("Light", html)
        self.assertIn("aria-pressed", html)
        self.assertIn("aria-label", html)

    def test_js_persists_to_localstorage(self):
        from rcm_mc.ui.theme import theme_toggle
        html = theme_toggle()
        self.assertIn("localStorage.setItem", html)
        self.assertIn("rcm_theme", html)

    def test_inject_css_disabled(self):
        from rcm_mc.ui.theme import theme_toggle
        html = theme_toggle(inject_css=False)
        self.assertNotIn("<style>", html)
        # JS still emits
        self.assertIn("<script>", html)

    def test_uses_css_variables(self):
        """Toggle button styles use --theme-* variables so it
        adapts visually when the theme flips."""
        from rcm_mc.ui.theme import theme_toggle
        html = theme_toggle()
        self.assertIn("var(--theme-border", html)
        self.assertIn("var(--theme-text-dim", html)


class TestThemeVars(unittest.TestCase):
    def test_exposes_var_expressions(self):
        from rcm_mc.ui.theme import THEME_VARS
        self.assertEqual(
            THEME_VARS["bg-primary"],
            "var(--theme-bg-primary)")
        self.assertEqual(
            THEME_VARS["text"],
            "var(--theme-text)")

    def test_all_tokens_present(self):
        from rcm_mc.ui.theme import THEME_VARS
        for required in [
            "bg-primary", "bg-surface", "bg-elevated",
            "text", "text-dim", "text-muted",
            "border", "accent",
            "positive", "negative", "watch",
        ]:
            self.assertIn(required, THEME_VARS)


if __name__ == "__main__":
    unittest.main()
