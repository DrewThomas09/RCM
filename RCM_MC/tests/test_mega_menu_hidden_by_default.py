"""Regression: mega-menu panels are hidden by default (no stacking).

Production bug: the section mega-menus (Portfolio / Research / Library / …)
were ALL visible at once, stacked over the dashboard. Root cause was a
`.ck-nav-mega { display:grid; }` base rule that overrode the
`.ck-nav-menu { display:none }` hidden default (same specificity, later in
source) — so every panel was permanently displayed and the hover / .is-open /
single-open-JS toggles were all moot.

This pins the fix: the base `.ck-nav-mega` rule sets NO `display` (inherits the
hidden default); `display:grid` appears only on the shown (hover / .is-open)
states, and under JS only `.is-open` opens a panel.
"""
from __future__ import annotations

import re
import unittest

from rcm_mc.ui._chartis_kit import chartis_shell, _topbar


class MegaMenuHiddenByDefaultTests(unittest.TestCase):
    def setUp(self):
        self.css = chartis_shell(body="<main/>", title="x", active_nav="/app")

    def test_base_mega_rule_sets_no_display(self):
        # The base `.ck-nav-mega {` rule (not a :hover / .is-open variant) must
        # NOT set display, or it overrides the hidden default and every panel
        # shows at once.
        m = re.search(r"(?<![>\w])\.ck-nav-mega \{[^}]*\}", self.css)
        self.assertIsNotNone(m, ".ck-nav-mega base rule missing")
        self.assertNotIn("display:", m.group(0),
                         "base .ck-nav-mega must not set display (stacking bug)")

    def test_menu_default_is_hidden(self):
        m = re.search(r"\.ck-nav-menu \{[^}]*\}", self.css)
        self.assertIsNotNone(m)
        self.assertIn("display:none", m.group(0))

    def test_open_states_show_the_mega_panel(self):
        # The mega-menu's outer .ck-nav-mega element is shown on the
        # open/hover states; the actual 2fr/3fr grid lives on the inner
        # .ck-mega-inner element (PR #1003 — full-bleed editorial mega).
        # So 'display:block' on the outer is the post-#1003 intent, NOT
        # 'display:grid' (which was the pre-#1003 single-container layout).
        self.assertIn(".ck-nav-group.is-open > .ck-nav-mega { display:block; }",
                      self.css)
        # Under JS control, hover does not open a mega panel; only .is-open does.
        self.assertIn(".ck-topbar[data-menu-js] .ck-nav-group:hover > .ck-nav-mega { display:none; }",
                      self.css)
        self.assertIn(".ck-topbar[data-menu-js] .ck-nav-group.is-open > .ck-nav-mega { display:block; }",
                      self.css)
        # The actual columnar grid is on .ck-mega-inner — assert it's grid
        # so a future regression that drops the columns gets caught.
        self.assertIn("display:grid; grid-template-columns:2fr 3fr;",
                      self.css)

    def test_no_group_open_in_default_markup(self):
        # Server markup never ships a group pre-opened.
        self.assertNotIn("is-open", _topbar("portfolio"))


if __name__ == "__main__":
    unittest.main()
