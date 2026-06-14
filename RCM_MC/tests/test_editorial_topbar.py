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

    def test_modkey_hint_is_platform_aware(self):
        # The ⌘ glyph is hardcoded in markup but a guarded script rewrites it
        # to Ctrl on non-Mac platforms. Both display spots (search kbd + the
        # "All Tools" menu item) are tagged for the rewrite.
        self.assertEqual(self.html.count("data-modkey>"), 2)
        self.assertIn('querySelectorAll("[data-modkey]")', self.html)
        # Bare (chrome-less) pages ship neither the markup nor the script.
        from rcm_mc.ui._chartis_kit import chartis_shell
        bare = chartis_shell("<p>x</p>", "Login", show_chrome=False)
        self.assertNotIn("data-modkey", bare)

    def test_search_input_has_site_search_attributes(self):
        # A site-search box should not autofill or spell-check the query
        # (CCNs, route slugs), and should surface a "search" action key on
        # mobile keyboards.
        self.assertIn('type="search"', self.html)
        self.assertIn('autocomplete="off"', self.html)
        self.assertIn('spellcheck="false"', self.html)
        self.assertIn('enterkeyhint="search"', self.html)

    def test_guide_button_preserved(self):
        # Guide button still opens the existing Guide sidebar.
        self.assertIn('class="ck-guide-trigger"', self.html)
        self.assertIn("data-ck-guide-open", self.html)
        self.assertIn('aria-controls="ck-guide-panel"', self.html)

    def test_new_deal_cta_routes_to_real_route(self):
        # CTA exists and points at the real create wizard (/new-deal step 1),
        # not the Pipeline list it used to dead-end on one click short.
        self.assertIn('class="ck-newdeal-cta" href="/new-deal"', self.html)
        self.assertIn("+ New deal", self.html)

    def test_section_triggers_expose_aria_expanded(self):
        # Each mega-menu section trigger is a disclosure control: it must
        # advertise a starting aria-expanded="false" (flipped by _NAV_MENU_JS
        # on open) so screen readers announce open/collapsed state. No
        # aria-haspopup — the panel is a group of links, not a menu widget.
        # Home (a bare link, no dropdown) carries no aria-expanded. The
        # positive match also proves no aria-haspopup sits on the trigger
        # (the user-chip dropdown keeps its own haspopup — out of scope here).
        self.assertIn('href="/diligence" aria-expanded="false"', self.html)
        self.assertNotIn('href="/home" aria-expanded', self.html)

    def test_section_triggers_control_their_panels(self):
        # Each disclosure trigger must point at the panel it toggles, and that
        # panel must carry the matching id (mirrors the user-chip wiring).
        import re
        controls = set(re.findall(r'aria-controls="(ck-mega-[a-z]+)"', self.html))
        ids = re.findall(r'id="(ck-mega-[a-z]+)"', self.html)
        self.assertGreaterEqual(len(controls), 6)
        self.assertEqual(controls, set(ids))         # every control resolves
        self.assertEqual(len(ids), len(set(ids)))    # ids are unique

    def test_my_dashboard_link_follows_chip_initials(self):
        # The "My Dashboard" link must target the same owner the avatar chip
        # shows — not a hardcoded "/my/AT". Pass real initials and assert both
        # the chip and the dashboard link move together.
        html = chartis_shell("<p>b</p>", title="X", active_nav="portfolio",
                             show_chrome=True, user_initials="JD")
        self.assertIn(">JD</button>", html)            # chip
        self.assertIn('href="/my/JD"', html)           # dashboard link
        self.assertNotIn('href="/my/AT"', html)

    def test_focusable_topbar_elements_have_focus_rings(self):
        # WCAG 2.4.7: every focusable topbar control needs a visible focus
        # indicator. The account dropdown items in particular were rendering
        # no ring for keyboard users navigating the open menu.
        for sel in (".ck-wordmark:focus-visible", ".ck-mode-chip:focus-visible",
                    ".ck-topbar-qpill:focus-visible",
                    ".ck-user-dropdown-item:focus-visible"):
            self.assertIn(sel, self.html, f"missing focus ring: {sel}")

    def test_user_chip_controls_its_dropdown(self):
        # The chip is a disclosure trigger; it must point at the menu it
        # toggles (mirrors the Guide button → #ck-guide-panel wiring) and the
        # menu must carry that id exactly once.
        self.assertIn('aria-controls="ck-user-dropdown"', self.html)
        self.assertIn('id="ck-user-dropdown"', self.html)
        self.assertEqual(self.html.count('id="ck-user-dropdown"'), 1)

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
