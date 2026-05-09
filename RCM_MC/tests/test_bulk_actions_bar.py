"""tests for the bulk-actions sticky bar.

PROMPTS.md Phase 4 / Prompt 49: multi-select + bulk operations on
list pages. The kit ships a sticky bar component that pages compose
alongside their own checkbox columns. JS is injected globally via
the shell so list pages don't need per-page wiring.
"""
from __future__ import annotations

import os
import sys
import unittest

from rcm_mc.ui._ui_kit import bulk_actions_bar


class HelperShape(unittest.TestCase):

    def test_bar_hidden_by_default(self) -> None:
        html = bulk_actions_bar([
            {"label": "Ack",   "href_template": "/api/alerts/ack?ids={ids}"},
        ])
        self.assertIn("bulk-actions-bar", html)
        self.assertIn("hidden", html)

    def test_count_starts_at_zero(self) -> None:
        html = bulk_actions_bar([
            {"label": "Ack", "href_template": "/api/alerts/ack?ids={ids}"},
        ])
        self.assertIn("bulk-count-n", html)
        self.assertIn(">0<", html)

    def test_each_action_renders_button(self) -> None:
        html = bulk_actions_bar([
            {"label": "Ack",     "href_template": "/api/alerts/ack?ids={ids}"},
            {"label": "Snooze",  "href_template": "/api/alerts/snooze?ids={ids}"},
            {"label": "Delete",  "href_template": "/api/alerts/delete?ids={ids}",
             "confirm": True},
        ])
        # Three action buttons present.
        self.assertEqual(html.count("bulk-action-btn"), 3)
        for label in ("Ack", "Snooze", "Delete"):
            with self.subTest(label=label):
                self.assertIn(label, html)

    def test_confirm_wraps_in_native_confirm(self) -> None:
        html = bulk_actions_bar([
            {"label": "Delete",
             "href_template": "/api/alerts/delete?ids={ids}",
             "confirm": True},
        ])
        self.assertIn("confirm(", html)

    def test_no_confirm_by_default(self) -> None:
        html = bulk_actions_bar([
            {"label": "Ack",
             "href_template": "/api/alerts/ack?ids={ids}"},
        ])
        self.assertNotIn("confirm(", html)

    def test_clear_button_present(self) -> None:
        html = bulk_actions_bar([])
        self.assertIn("bulk-clear", html)


class JSAttachedFromShell(unittest.TestCase):

    def setUp(self) -> None:
        os.environ["CHARTIS_UI_V2"] = "1"
        for name in list(sys.modules):
            if name.startswith("rcm_mc.ui._chartis_kit"):
                sys.modules.pop(name, None)
        from rcm_mc.ui._chartis_kit import chartis_shell
        self.html = chartis_shell("<p>x</p>", "T")

    def test_bulk_select_listener_present(self) -> None:
        self.assertIn("bulk-select", self.html)

    def test_dom_content_loaded_handler(self) -> None:
        # Bind happens on DOMContentLoaded so the bar refreshes
        # accurately when the page first renders.
        self.assertIn("DOMContentLoaded", self.html)


if __name__ == "__main__":
    unittest.main()
