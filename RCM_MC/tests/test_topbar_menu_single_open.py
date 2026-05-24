"""Topbar mega-menus must be mutually exclusive and reliably dismissible.

Production bug: multiple mega-menu panels (Portfolio + Research + Diligence)
could be open at once and looked stuck. Root cause: the CSS opened panels on
`:focus-within`, so a focused/clicked menu stayed open alongside a hovered one.
This pins the controlled-open behavior: a JS controller marks the topbar
`[data-menu-js]`, opens exactly one menu via `.is-open`, and closes on
mouseleave / Escape / outside-click / focus-leave.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._chartis_kit import chartis_shell, _topbar


class MenuMarkupTests(unittest.TestCase):
    def setUp(self):
        self.t = _topbar("pipeline")

    def test_no_panel_is_open_by_default(self):
        # No group ships with the open class in server markup.
        self.assertNotIn("is-open", self.t)

    def test_panels_default_hidden_in_css(self):
        css = chartis_shell(body="<main/>", title="x")
        self.assertIn(".ck-nav-menu { position:absolute", css)
        self.assertIn("display:none;", css)


class MenuControllerTests(unittest.TestCase):
    def setUp(self):
        self.h = chartis_shell(body="<main/>", title="x", active_nav="pipeline")

    def test_js_takes_authoritative_open_state(self):
        # Controller marks the topbar so CSS hands open state to .is-open only.
        self.assertIn("setAttribute('data-menu-js'", self.h)
        self.assertIn(".ck-topbar[data-menu-js] .ck-nav-group:hover > .ck-nav-menu { display:none; }",
                      self.h)

    def test_only_one_menu_open_at_a_time(self):
        # openOnly() enforces a single open panel: it clears .is-open from
        # every other group before opening the entered one. (The hardened
        # controller inlines the clear instead of calling closeAll() so a
        # pending open/close timer state is preserved during hover-intent.)
        self.assertIn("function openOnly", self.h)
        self.assertIn("function closeAll", self.h)
        self.assertIn("x.classList.remove('is-open')", self.h)

    def test_dismissal_handlers_present(self):
        self.assertIn("'Escape'", self.h)                 # Escape closes
        self.assertIn("pointerdown", self.h)              # click closes
        # Any click not inside a nav group closes (covers outside-the-bar AND
        # the in-topbar Guide/Search/avatar controls).
        self.assertIn("closest('.ck-nav-group')", self.h)
        self.assertIn("'mouseleave'", self.h)             # leaving nav closes
        self.assertIn("setTimeout(closeAll", self.h)      # with a small delay
        self.assertIn("'focusout'", self.h)               # focus leaving closes

    def test_focus_within_opening_removed(self):
        # The stacking culprit must be gone.
        self.assertNotIn(".ck-nav-group:focus-within > .ck-nav-menu", self.h)

    def test_topbar_chrome_preserved(self):
        for marker in ("ck-guide-trigger", "ck-search", "ck-user-chip",
                       "ck-newdeal-cta", "ck-nav-mega"):
            self.assertIn(marker, self.h)


class LoginUnchangedTests(unittest.TestCase):
    def test_login_has_no_topbar(self):
        # Login must remain topbar-less (controller no-ops without a topbar).
        try:
            from rcm_mc.ui.login_page import render_login_page
        except Exception:
            self.skipTest("login page module not importable in this context")
        html = render_login_page()
        self.assertNotIn("ck-topbar", html)


if __name__ == "__main__":
    unittest.main()
