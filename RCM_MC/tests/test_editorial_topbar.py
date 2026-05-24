"""Editorial paper top-bar redesign (2026-05-24) — render contract.

The global top bar was reskinned from the navy two-row shell to a single
76px paper-toned editorial bar (serif nav, green active state, ⌘K search
chip, Guide button, + New deal CTA, green avatar). This is a shell reskin —
class names + JS wiring are preserved, and the bar renders ONLY when
chrome is shown (never on /login). These tests pin the new markup/CSS and,
critically, that login is unaffected.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._chartis_kit import chartis_shell
from rcm_mc.ui.chartis.login_page import render_login_page


def _app_shell() -> str:
    return chartis_shell("<p>body</p>", title="Command center",
                         active_nav="portfolio", show_chrome=True)


class EditorialTopbarTests(unittest.TestCase):
    def setUp(self):
        self.html = _app_shell()

    def test_paper_bar_tokens_and_ink_rule(self):
        # Scoped --tb-* tokens from the handoff, on the .ck-topbar block.
        self.assertIn("--tb-paper:#faf6ec", self.html)
        self.assertIn("--tb-ink:#15202b", self.html)
        self.assertIn("--tb-green:#1f7a5a", self.html)
        self.assertIn("border-bottom:2px solid var(--tb-ink)", self.html)

    def test_brand_wordmark(self):
        self.assertIn('<header class="ck-topbar">', self.html)
        self.assertIn("PE<em>Desk</em>", self.html)

    def test_primary_nav_sections(self):
        for label in (">Home<", ">Pipeline<", ">Diligence<",
                      ">Library<", ">Research<", ">Portfolio<"):
            self.assertIn(label, self.html)

    def test_serif_green_active_nav(self):
        # Serif nav + green italic active underline.
        self.assertIn(".ck-nav a { font-family:var(--sc-serif", self.html)
        self.assertIn(".ck-nav a.active { color:var(--tb-green); font-style:italic;",
                      self.html)

    def test_search_with_cmdk_chip(self):
        self.assertIn('class="ck-search-kbd"', self.html)
        self.assertIn("⌘K", self.html)

    def test_guide_button_preserved(self):
        # Guide button still opens the existing Guide sidebar.
        self.assertIn('class="ck-guide-trigger"', self.html)
        self.assertIn("data-ck-guide-open", self.html)
        self.assertIn('aria-controls="ck-guide-panel"', self.html)

    def test_new_deal_cta_routes_to_real_route(self):
        # CTA exists and points at an existing route (no invented flow).
        self.assertIn('class="ck-newdeal-cta" href="/pipeline"', self.html)
        self.assertIn("+ New deal", self.html)

    def test_avatar_chip_preserved(self):
        self.assertIn('class="ck-user-chip"', self.html)
        self.assertIn("data-ck-user-toggle", self.html)
        # Sign out still posts to the existing endpoint.
        self.assertIn('action="/api/logout"', self.html)

    def test_no_prototype_cdn_in_topbar(self):
        low = self.html.lower()
        for bad in ("unpkg", "babel", "react-dom", "react.development", "top-bar.html"):
            self.assertNotIn(bad, low)

    def test_reduced_motion_respected(self):
        self.assertIn("prefers-reduced-motion", self.html)


class TopbarNotOnLoginTests(unittest.TestCase):
    """The reskin must never leak the app top bar onto /login."""

    def setUp(self):
        self.login = render_login_page()

    def test_login_has_no_topbar_header(self):
        self.assertNotIn('<header class="ck-topbar">', self.login)

    def test_login_has_no_new_deal_cta(self):
        self.assertNotIn('class="ck-newdeal-cta"', self.login)

    def test_login_has_no_guide_trigger(self):
        self.assertNotIn("data-ck-guide-open", self.login)

    def test_login_still_centered_card(self):
        self.assertIn("pd-login-card", self.login)
        self.assertIn("DEAL TEAM LOGIN", self.login)

    def test_login_has_no_basic_auth_challenge(self):
        # Rendered HTML carries no WWW-Authenticate semantics (form mode).
        self.assertNotIn("WWW-Authenticate", self.login)


if __name__ == "__main__":
    unittest.main()
