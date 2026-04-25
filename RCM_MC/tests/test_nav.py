"""Tests for breadcrumb navigation + keyboard shortcuts."""
from __future__ import annotations

import unittest


class TestBreadcrumb(unittest.TestCase):
    def test_basic_three_level(self):
        from rcm_mc.ui.nav import breadcrumb
        html = breadcrumb([
            ("Dashboard", "/?v3=1"),
            ("Deals", "/?v3=1#deals"),
            ("Aurora", None),
        ])
        # Each label appears
        self.assertIn("Dashboard", html)
        self.assertIn("Deals", html)
        self.assertIn("Aurora", html)
        # Parents are links
        self.assertIn('href="/?v3=1"', html)
        # Current item is non-clickable span
        self.assertIn('bc-current">Aurora</span>', html)
        # Two separator spans between three items
        self.assertEqual(
            html.count('class="bc-sep"'), 2)

    def test_single_item(self):
        from rcm_mc.ui.nav import breadcrumb
        html = breadcrumb([("Home", None)])
        # Renders even with one item
        self.assertIn("Home", html)
        # No separator spans
        self.assertNotIn('class="bc-sep"', html)

    def test_empty(self):
        from rcm_mc.ui.nav import breadcrumb
        self.assertEqual(breadcrumb([]), "")

    def test_html_escape(self):
        from rcm_mc.ui.nav import breadcrumb
        html = breadcrumb([
            ("<script>x</script>", None),
        ])
        self.assertNotIn("<script>x", html)
        self.assertIn("&lt;script&gt;", html)

    def test_inject_css_default(self):
        from rcm_mc.ui.nav import breadcrumb
        html = breadcrumb([("X", None)])
        self.assertIn("<style>", html)

    def test_inject_css_disabled(self):
        from rcm_mc.ui.nav import breadcrumb
        html = breadcrumb(
            [("X", None)], inject_css=False)
        self.assertNotIn("<style>", html)
        self.assertIn("X", html)

    def test_last_item_with_href_still_non_link(self):
        """Even if href is non-None on the last item, it's the
        current page so we render it as the current span."""
        from rcm_mc.ui.nav import breadcrumb
        html = breadcrumb([
            ("Dashboard", "/d"),
            ("Aurora", "/aurora"),  # last → non-clickable
        ])
        # Aurora rendered as current
        self.assertIn('bc-current">Aurora</span>', html)
        # Dashboard rendered as link
        self.assertIn('href="/d"', html)


class TestKeyboardShortcuts(unittest.TestCase):
    def test_default_shortcuts_present(self):
        from rcm_mc.ui.nav import (
            keyboard_shortcuts, SHORTCUTS,
        )
        html = keyboard_shortcuts()
        # Each default shortcut binding appears in the
        # help table
        for binding, _, _ in SHORTCUTS:
            self.assertIn(binding, html)

    def test_help_dialog_structure(self):
        from rcm_mc.ui.nav import keyboard_shortcuts
        html = keyboard_shortcuts()
        # Hidden help dialog
        self.assertIn('id="kbd-help"', html)
        self.assertIn("Keyboard Shortcuts", html)
        # Leader-key indicator
        self.assertIn('id="kbd-leader-ind"', html)
        # JS handler
        self.assertIn("<script>", html)
        # 'keydown' listener
        self.assertIn("keydown", html)

    def test_extra_shortcuts(self):
        from rcm_mc.ui.nav import keyboard_shortcuts
        html = keyboard_shortcuts(extra=[
            ("g x", "Custom binding", "/x"),
        ])
        self.assertIn("g x", html)
        self.assertIn("Custom binding", html)

    def test_inject_css_disabled(self):
        from rcm_mc.ui.nav import keyboard_shortcuts
        html = keyboard_shortcuts(inject_css=False)
        # No stylesheet
        self.assertNotIn("<style>", html)
        # But the JS handler still emits
        self.assertIn("<script>", html)

    def test_shortcut_payload_in_js(self):
        from rcm_mc.ui.nav import keyboard_shortcuts
        html = keyboard_shortcuts()
        # The JS receives a JSON array of shortcuts so it
        # can dispatch on the second key press
        self.assertIn('"binding"', html)
        self.assertIn('"target"', html)
        self.assertIn('/data/catalog', html)
        self.assertIn('/models/quality', html)

    def test_kbd_styling(self):
        from rcm_mc.ui.nav import keyboard_shortcuts
        html = keyboard_shortcuts()
        # <kbd> tags styled monospace
        self.assertIn("<kbd", html)
        self.assertIn("monospace", html)

    def test_isTyping_guard_in_js(self):
        """The JS should not capture shortcuts when the user
        is typing in an input."""
        from rcm_mc.ui.nav import keyboard_shortcuts
        html = keyboard_shortcuts()
        self.assertIn("isTyping", html)


class TestIntegration(unittest.TestCase):
    def test_renders_alongside_breadcrumb(self):
        """Both helpers can coexist on one page."""
        from rcm_mc.ui.nav import (
            breadcrumb, keyboard_shortcuts,
        )
        bc = breadcrumb([
            ("Home", "/"), ("Aurora", None)])
        kb = keyboard_shortcuts()
        page = bc + kb
        # Both sets of structures present
        self.assertIn("bc-current", page)
        self.assertIn("kbd-help", page)


if __name__ == "__main__":
    unittest.main()
