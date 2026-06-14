"""Accessibility affordances baked into the shared chartis shell.

A keyboard/screen-reader audit (2026-06) found that only ``.cta-btn``
carried a ``:focus-visible`` ring — tabbing through links, nav items,
generic buttons and form fields produced no visible focus indicator
(a WCAG 2.4.7 failure on every page). There was also no skip-to-content
link (WCAG 2.4.1) and no ``prefers-reduced-motion`` honouring despite
dozens of hover transitions/translateY lifts in the chrome.

This test locks the fixes in so they can't be silently dropped:
  * a global ``:focus-visible`` outline,
  * a ``.ck-skip-link`` that targets ``#ck-main`` (gated on chrome),
  * ``<main id="ck-main">`` as the skip target on every page,
  * a ``prefers-reduced-motion`` reset.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._chartis_kit import chartis_shell

_SKIP_ANCHOR = '<a class="ck-skip-link" href="#ck-main">Skip to content</a>'


class A11yShellTests(unittest.TestCase):
    def test_main_carries_skip_target_id(self):
        # Both chrome'd and bare pages expose the skip target so the
        # anchor (and any in-page #ck-main link) always resolves.
        for show_chrome in (True, False):
            html = chartis_shell("<p>x</p>", title="X", show_chrome=show_chrome)
            self.assertEqual(html.count('id="ck-main"'), 1)

    def test_skip_link_present_with_chrome(self):
        html = chartis_shell("<p>x</p>", title="X")
        self.assertIn(_SKIP_ANCHOR, html)
        # Skip link must precede the main element so it is the first tab stop.
        self.assertLess(html.index(_SKIP_ANCHOR), html.index('<main id="ck-main"'))

    def test_skip_target_is_focusable(self):
        # For the skip link to move keyboard focus (not just scroll), the
        # target must be programmatically focusable.
        html = chartis_shell("<p>x</p>", title="X")
        self.assertIn('<main id="ck-main" tabindex="-1"', html)

    def test_skip_link_absent_on_bare_pages(self):
        # Auth pages (login/forgot) render show_chrome=False — there's no
        # nav to skip, so the anchor must not appear.
        html = chartis_shell("<p>x</p>", title="Login", show_chrome=False)
        self.assertNotIn(_SKIP_ANCHOR, html)

    def test_global_focus_visible_ring(self):
        html = chartis_shell("<p>x</p>", title="X")
        self.assertIn(":focus-visible", html)
        # The ring covers more than just the legacy .cta-btn.
        self.assertIn("a:focus-visible", html)
        self.assertIn("button:focus-visible", html)

    def test_reduced_motion_honoured(self):
        html = chartis_shell("<p>x</p>", title="X")
        self.assertIn("prefers-reduced-motion: reduce", html)

    def test_breadcrumb_nav_is_labelled(self):
        # The primary nav is aria-label="Primary"; the breadcrumb trail
        # must carry its own landmark label so screen readers don't
        # announce two indistinct "navigation" regions.
        html = chartis_shell(
            "<p>x</p>", title="X",
            breadcrumbs=[("Home", "/"), ("Deals", None)],
        )
        self.assertIn('<nav class="ck-breadcrumbs" aria-label="Breadcrumb">', html)


if __name__ == "__main__":
    unittest.main()
