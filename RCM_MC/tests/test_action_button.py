"""tests for ``rcm_mc.ui._ui_kit.action_button``.

PROMPTS.md Phase 2 / Prompt 20. The helper renders a weight-tiered
button with optional duration hint and consequential-action confirm.
Tests cover all weights, with/without duration hint, the
consequential-confirm wrapper, and the link variant.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._ui_kit import action_button


class WeightClasses(unittest.TestCase):

    def test_each_weight_emits_class(self) -> None:
        for weight in ("primary", "secondary", "tertiary"):
            with self.subTest(weight=weight):
                html = action_button(label="X", weight=weight)
                self.assertIn(f"btn-{weight}", html)

    def test_invalid_weight_falls_back_to_primary(self) -> None:
        html = action_button(label="X", weight="purple")
        self.assertIn("btn-primary", html)
        self.assertNotIn("btn-purple", html)


class DurationHint(unittest.TestCase):

    def test_duration_hint_renders_seconds(self) -> None:
        html = action_button(label="Run Monte Carlo", expected_seconds=10)
        self.assertIn("~10s", html)
        self.assertIn("btn-duration", html)
        # Wires the data-attribute the kit JS reads on submit.
        self.assertIn('data-expected-seconds="10"', html)

    def test_no_duration_hint_when_omitted(self) -> None:
        html = action_button(label="Save")
        self.assertNotIn("btn-duration", html)
        self.assertNotIn("data-expected-seconds", html)


class ConsequentialConfirm(unittest.TestCase):

    def test_consequential_wraps_onclick_in_confirm(self) -> None:
        html = action_button(label="Send LP update", consequential=True)
        self.assertIn("confirm", html)
        self.assertIn("btn-consequential", html)

    def test_default_no_confirm(self) -> None:
        html = action_button(label="Filter")
        self.assertNotIn("confirm(", html)


class LinkVariant(unittest.TestCase):

    def test_href_renders_anchor_not_button(self) -> None:
        html = action_button(label="Methodology", weight="tertiary",
                             href="/methodology")
        self.assertTrue(html.startswith("<a "))
        self.assertIn('href="/methodology"', html)

    def test_button_default_when_no_href(self) -> None:
        html = action_button(label="Run")
        self.assertTrue(html.startswith("<button "))


class HtmlEscaping(unittest.TestCase):

    def test_label_escaped(self) -> None:
        html = action_button(label="<x>")
        self.assertIn("&lt;x&gt;", html)

    def test_href_escaped(self) -> None:
        html = action_button(label="L", href='/x"&y')
        # Either escaped to &amp; or properly encoded — pin the
        # absence of a literal ampersand in attribute context.
        self.assertNotIn('"&y', html)


class FormSubmitJSAttachedFromShell(unittest.TestCase):

    def setUp(self) -> None:
        import os
        import sys
        os.environ["CHARTIS_UI_V2"] = "1"
        for name in list(sys.modules):
            if name.startswith("rcm_mc.ui._chartis_kit"):
                sys.modules.pop(name, None)
        from rcm_mc.ui._chartis_kit import chartis_shell
        self.html = chartis_shell("<p>x</p>", "T")

    def test_busy_state_js_present(self) -> None:
        self.assertIn("data-expected-seconds", self.html)
        self.assertIn("Running…", self.html)


if __name__ == "__main__":
    unittest.main()
