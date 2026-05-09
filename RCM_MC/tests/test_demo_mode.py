"""tests for demo-mode helpers (P91)."""
from __future__ import annotations

import unittest

from rcm_mc.ui._ui_kit import demo_mode_banner, is_demo_mode


class IsDemoModeBranches(unittest.TestCase):

    def test_demo_username_triggers(self) -> None:
        self.assertTrue(is_demo_mode(username="demo"))

    def test_demo_username_case_insensitive(self) -> None:
        self.assertTrue(is_demo_mode(username="Demo"))

    def test_query_param_triggers(self) -> None:
        self.assertTrue(is_demo_mode(query={"demo": "1"}))
        self.assertTrue(is_demo_mode(query={"demo": "true"}))

    def test_query_param_list_form(self) -> None:
        # urllib.parse.parse_qs returns list values.
        self.assertTrue(is_demo_mode(query={"demo": ["1"]}))

    def test_neither_returns_false(self) -> None:
        self.assertFalse(is_demo_mode(username="alice"))
        self.assertFalse(is_demo_mode(query={"other": "1"}))
        self.assertFalse(is_demo_mode())


class BannerRendering(unittest.TestCase):

    def test_banner_emits_eyebrow(self) -> None:
        html = demo_mode_banner()
        self.assertIn("Demo data", html)
        self.assertIn("demo-mode-banner", html)

    def test_banner_warns_about_fictional_names(self) -> None:
        html = demo_mode_banner()
        self.assertIn("fictional", html)

    def test_reset_href_wires_form(self) -> None:
        html = demo_mode_banner(reset_href="/demo/reset")
        self.assertIn('action="/demo/reset"', html)
        self.assertIn("Reset demo data", html)
        self.assertIn("confirm(", html)

    def test_no_reset_href_no_form(self) -> None:
        html = demo_mode_banner()
        self.assertNotIn("Reset demo data", html)


if __name__ == "__main__":
    unittest.main()
