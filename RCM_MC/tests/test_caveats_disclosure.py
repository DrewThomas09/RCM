"""tests for ``rcm_mc.ui._ui_kit.caveats_disclosure``.

PROMPTS.md Phase 2 / Prompt 18. Tests cover 0/1/5 caveats, default-
closed state, custom label override, and HTML escaping.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._ui_kit import caveats_disclosure


class CountVariants(unittest.TestCase):

    def test_empty_returns_empty_string(self) -> None:
        # No caveats means no disclosure card on the page; the helper
        # short-circuits so callers can include it unconditionally.
        self.assertEqual(caveats_disclosure([]), "")

    def test_one_caveat(self) -> None:
        html = caveats_disclosure(["only one"])
        self.assertEqual(html.count("<li>"), 1)
        self.assertIn("only one", html)

    def test_five_caveats(self) -> None:
        html = caveats_disclosure([f"caveat {i}" for i in range(5)])
        self.assertEqual(html.count("<li>"), 5)


class DefaultClosed(unittest.TestCase):

    def test_no_open_attribute_by_default(self) -> None:
        html = caveats_disclosure(["x"])
        # ``<details open>`` would render expanded. The helper must
        # not emit the attribute by default.
        self.assertNotIn("<details open", html)
        self.assertNotIn("<details class=\"caveats-disclosure\" open", html)

    def test_uses_details_element(self) -> None:
        # Native disclosure works without JS — pin that we use the
        # platform element rather than reinventing it.
        html = caveats_disclosure(["x"])
        self.assertIn("<details", html)
        self.assertIn("<summary>", html)


class LabelHandling(unittest.TestCase):

    def test_default_label(self) -> None:
        html = caveats_disclosure(["x"])
        self.assertIn("<summary>Modeling caveats</summary>", html)

    def test_custom_label(self) -> None:
        html = caveats_disclosure(["x"], label="Known limitations")
        self.assertIn("<summary>Known limitations</summary>", html)


class HtmlEscaping(unittest.TestCase):

    def test_caveats_escaped(self) -> None:
        html = caveats_disclosure(["<script>alert(1)</script>"])
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_label_escaped(self) -> None:
        html = caveats_disclosure(["x"], label="<x>")
        self.assertIn("&lt;x&gt;", html)


class NotYetModeledSubsection(unittest.TestCase):
    """P75: opt-in second list for "not yet modeled" caveats."""

    def test_subsection_renders_when_supplied(self) -> None:
        html = caveats_disclosure(
            ["caveat 1"],
            not_modeled=["cross-lever correlation",
                         "implementation ramp variance"],
        )
        self.assertIn("Not yet modeled", html)
        self.assertIn("caveats-not-modeled", html)
        self.assertIn("cross-lever correlation", html)

    def test_only_not_modeled_still_renders(self) -> None:
        # Caveats list empty but not_modeled present — still renders.
        html = caveats_disclosure(
            [],
            not_modeled=["x", "y"],
        )
        self.assertIn("Not yet modeled", html)

    def test_empty_both_returns_empty_string(self) -> None:
        self.assertEqual(
            caveats_disclosure([], not_modeled=[]),
            "",
        )

    def test_caveats_alone_unchanged_by_extension(self) -> None:
        # The previous-version contract still holds when not_modeled
        # is omitted — no regression on existing callers.
        html = caveats_disclosure(["x"])
        self.assertIn("<details", html)
        self.assertNotIn("Not yet modeled", html)


if __name__ == "__main__":
    unittest.main()
