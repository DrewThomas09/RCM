"""Shadow + decorative-accent purge contract on shared content panels
(sweep batch 12).

The chartis_kit inline-fallback CSS was emitting box-shadows on five
shared content-panel classes that the canonical v3/chartis.css already
renders shadow-free. This drifted the inline fallback from the source
of truth and violated Tier-4 don'ts (no shadows on content panels —
depth is by paper-tone + hairline only).

This sweep batch aligns the inline fallback with the canonical CSS:
  · .ck-panel             — shadow removed (highest-leverage; this
                              container is used on hundreds of pages)
  · .ck-empty-state       — shadow removed; tone-* left-border kept
                              (semantic, not decorative)
  · .ck-severity-panel    — shadow removed; tone-red/amber/teal/
                              positive left-border kept (semantic)
  · .ck-affirm-empty      — shadow AND decorative 4px positive-tone
                              left-border BOTH removed (positive
                              tone conveyed by the h3 color already)
  · .ck-health-mix        — shadow removed

Pins:
  · None of the five content-panel rule BODIES contain box-shadow.
  · .ck-affirm-empty rule body has NO border-left declaration
    (purely decorative pattern was the only one — gone).
  · .ck-severity-panel rule body STILL has border-left (semantic;
    kept) but no box-shadow.
  · .ck-panel border-radius is 2px (not larger).
"""
from __future__ import annotations

import re
import unittest

import pandas as pd


def _render_any_page() -> str:
    # /portfolio empty state pulls in the inline fallback CSS through
    # the shell — gives us the rendered chartis-kit chrome.
    from rcm_mc.ui.portfolio_overview import render_portfolio_overview
    return render_portfolio_overview(pd.DataFrame())


def _rule_body(html: str, selector: str) -> str:
    # Selector must be regex-escaped; we match the rule body BETWEEN
    # the literal opening brace and the matching close brace. Comments
    # in the CSS use /* ... */ and may include the selector name; we
    # search only for the rule pattern `<selector>\s*\{(...)\}`.
    m = re.search(rf"{re.escape(selector)}\s*\{{([^}}]+)\}}", html)
    return m.group(1) if m else ""


class ContentPanelShadowsPurgedTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.html = _render_any_page()

    def test_ck_panel_no_shadow(self) -> None:
        body = _rule_body(self.html, ".ck-panel")
        self.assertTrue(body, "ck-panel rule not found")
        self.assertNotIn("box-shadow", body)

    def test_ck_panel_radius_capped_at_2px(self) -> None:
        body = _rule_body(self.html, ".ck-panel")
        # Tier-0 caps card radius at 2px.
        self.assertRegex(body, r"border-radius:\s*2px")
        self.assertNotIn("border-radius:4px", body)

    def test_ck_empty_state_no_shadow(self) -> None:
        body = _rule_body(self.html, ".ck-empty-state")
        self.assertTrue(body, "ck-empty-state rule not found")
        self.assertNotIn("box-shadow", body)

    def test_ck_severity_panel_no_shadow(self) -> None:
        body = _rule_body(self.html, ".ck-severity-panel")
        self.assertTrue(body, "ck-severity-panel rule not found")
        self.assertNotIn("box-shadow", body)

    def test_ck_severity_panel_retains_semantic_border_left(self) -> None:
        # The 4px colored left-border is SEMANTIC here (severity tone
        # encoding via tone-red / tone-amber / tone-info / tone-positive
        # classes that recolor it). Retained per spec Tier-2 §2.12
        # (badge/tag color carrying category, allowed).
        body = _rule_body(self.html, ".ck-severity-panel")
        self.assertIn("border-left", body)

    def test_ck_affirm_empty_no_shadow(self) -> None:
        body = _rule_body(self.html, ".ck-affirm-empty")
        self.assertTrue(body, "ck-affirm-empty rule not found")
        self.assertNotIn("box-shadow", body)

    def test_ck_affirm_empty_no_decorative_border_left(self) -> None:
        # Decorative 4px positive-tone left-border removed — single-
        # tone class doesn't need a colored bar (the h3 color
        # already conveys "positive" elsewhere in the rule set).
        body = _rule_body(self.html, ".ck-affirm-empty")
        self.assertNotIn("border-left", body)

    def test_ck_health_mix_no_shadow(self) -> None:
        body = _rule_body(self.html, ".ck-health-mix")
        self.assertTrue(body, "ck-health-mix rule not found")
        self.assertNotIn("box-shadow", body)


if __name__ == "__main__":
    unittest.main()
