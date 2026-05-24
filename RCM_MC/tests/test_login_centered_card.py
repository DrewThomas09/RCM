"""Centered-card /login redesign (2026-05-24) — render contract.

A skin swap over the working form-login flow: these tests pin the new
centered-card markup + the preserved auth contract (POST /api/login, hidden
next, /forgot, server-side ?tab=request), and assert no external CDN/React/
Babel runtime is shipped on the login page. The end-to-end auth round-trip
(cookie, redirect, invalid-creds, /app gating, Basic-mode fallback, no
loops) is covered by test_basic_auth_login_ux.py + test_ui_rework_contract.py
— this file is the page-render contract.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.chartis.login_page import render_login_page


class CenteredCardRenderTests(unittest.TestCase):
    def setUp(self):
        self.html = render_login_page(next_url="/app")

    def test_centered_card_structure(self):
        self.assertIn("pd-login-page", self.html)
        self.assertIn("pd-login-card", self.html)
        self.assertIn("DEAL TEAM LOGIN", self.html)
        # Headline with the green italic "workspace" brand moment.
        self.assertIn("Sign in to your <em>workspace</em>.", self.html)
        self.assertIn("Use your team credentials", self.html)

    def test_fields_and_submit(self):
        self.assertIn('name="username"', self.html)
        self.assertIn('id="login-email"', self.html)
        self.assertIn('name="password"', self.html)
        self.assertIn('id="login-password"', self.html)
        self.assertIn("Open deal workspace", self.html)
        # Primary CTA class preserved (contract pin).
        self.assertIn('class="cta-btn submit', self.html)

    def test_segmented_control_aria(self):
        self.assertIn('role="tablist"', self.html)
        self.assertIn('role="tab"', self.html)
        self.assertIn('aria-selected="true"', self.html)   # Sign in active
        self.assertIn(">Sign in</a>", self.html)
        self.assertIn(">Request access</a>", self.html)

    def test_show_hide_is_button_not_submit(self):
        self.assertIn("data-pl-show", self.html)
        self.assertIn('type="button"', self.html)
        self.assertIn('aria-pressed="false"', self.html)
        # The toggle JS only flips the input type — no form submit.
        self.assertIn("inp.type=show?'text':'password'", self.html)

    def test_remember_and_forgot(self):
        self.assertIn('name="remember"', self.html)
        self.assertIn('href="/forgot"', self.html)

    def test_sso_is_disabled_not_invented(self):
        # No SSO route exists — the affordance renders disabled, no href/auth.
        self.assertIn("pd-login-sso", self.html)
        self.assertIn("disabled", self.html)
        self.assertIn("not configured", self.html)

    def test_auth_contract_preserved(self):
        self.assertIn('action="/api/login"', self.html)
        # next target echoed into a hidden field for the post-login redirect.
        self.assertIn('name="next" value="/app"', self.html)

    def test_next_preserved_in_segment_links(self):
        # Switching tabs keeps the ?next target.
        self.assertIn("next=/app", self.html)

    def test_no_external_cdn_or_prototype_runtime(self):
        low = self.html.lower()
        for bad in ("unpkg", "babel", "react-dom", "react.development",
                    "login.html", "design-canvas"):
            self.assertNotIn(bad, low)

    def test_chromeless_page(self):
        # show_chrome=False — no top-nav / no PHI banner on the login page.
        # The card is the only surface; assert the full-bleed page wrapper.
        self.assertIn('class="pd-login-page"', self.html)


class ErrorAndRequestTabTests(unittest.TestCase):
    def test_invalid_credentials_error_block(self):
        html = render_login_page(error="Invalid credentials")
        self.assertIn("pd-login-error", html)
        self.assertIn('role="alert"', html)
        self.assertIn("Invalid credentials", html)

    def test_request_tab_renders_request_form(self):
        html = render_login_page(tab="request")
        self.assertIn("Request Access →", html)
        self.assertIn('action="/login?tab=request"', html)
        # Sign-in password field is not shown on the request tab.
        self.assertNotIn('name="password"', html)
        # Active segment flips.
        self.assertIn('aria-selected="true"', html)

    def test_request_success_block(self):
        html = render_login_page(tab="request", request_success=True)
        self.assertIn("pd-login-ok", html)
        self.assertIn("Request received", html)

    def test_error_is_escaped(self):
        html = render_login_page(error="<script>alert(1)</script>")
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)


if __name__ == "__main__":
    unittest.main()
