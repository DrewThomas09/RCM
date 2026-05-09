"""tests for ``rcm_mc.ui._ui_kit.workbench_cta``.

PROMPTS.md Phase 4 / Prompt 56: the analysis workbench at
``/analysis/<deal_id>`` is the most-engineered page in the codebase
and should be the central artifact. The kit ships a single CTA
helper that deal pages, story pages, and IC packets all use.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._ui_kit import workbench_cta


class CTAStructure(unittest.TestCase):

    def test_renders_primary_button(self) -> None:
        html = workbench_cta("aurora")
        self.assertIn("btn-primary", html)
        self.assertIn('href="/analysis/aurora"', html)
        self.assertIn("Open analysis workbench", html)

    def test_tab_appended_as_query(self) -> None:
        html = workbench_cta("aurora", tab="ebitda-bridge")
        self.assertIn(
            'href="/analysis/aurora?tab=ebitda-bridge"',
            html,
        )

    def test_custom_label(self) -> None:
        html = workbench_cta("aurora", label="Run X-Ray →")
        self.assertIn("Run X-Ray", html)

    def test_empty_deal_id_returns_empty(self) -> None:
        # Defensive: a missing deal context returns no markup so a
        # caller can include the CTA unconditionally.
        self.assertEqual(workbench_cta(""), "")


class HtmlEscaping(unittest.TestCase):

    def test_deal_id_escaped(self) -> None:
        # Deal IDs are user-supplied — special chars must be escaped
        # in the href attribute context.
        html = workbench_cta('aurora"&hack')
        self.assertNotIn('aurora"&hack', html)

    def test_tab_escaped(self) -> None:
        html = workbench_cta("aurora", tab='"><script>')
        self.assertNotIn("<script>", html)


if __name__ == "__main__":
    unittest.main()
