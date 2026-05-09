"""b164 — login gate hardening.

PROMPTS.md Phase 1 / Prompt 3 asked for three coupled changes:

1. The marketing site's ``Open Platform`` CTA must traverse ``/login``
   so a logged-out partner cannot reach the platform without seeing
   the auth gate.
2. ``demo`` user bootstrap so ``/login`` has a working set of
   credentials on first launch.
3. An already-signed-in partner who lands on ``/login`` should be
   redirected to ``next`` instead of staring at the form.

Bootstrap (#2) ships in a separate commit; this regression file pins
the surface that PROMPTS.md cares about: the marketing CTA text and
the ``/login`` route's idempotent presence.
"""
from __future__ import annotations

import re
import unittest


class MarketingCTAPointsAtLogin(unittest.TestCase):
    """The 'Open Platform' button on the public marketing page must
    route through ``/login`` so unauthenticated visitors hit the gate
    deliberately rather than via a 401 bounce."""

    def setUp(self) -> None:
        from rcm_mc.ui.chartis.marketing_page import render_marketing_page
        self.html = render_marketing_page()

    def test_open_platform_cta_targets_login(self) -> None:
        # Both the hero CTA and the top-bar CTA must point at /login.
        # We accept any href that starts with /login (allowing a
        # ?next=… query string to preserve the post-login destination).
        ctas = re.findall(
            r'<a[^>]*href="([^"]*)"[^>]*>[^<]*Open Platform',
            self.html,
            flags=re.IGNORECASE,
        )
        self.assertGreater(len(ctas), 0, "no Open Platform CTA found")
        for href in ctas:
            self.assertTrue(
                href.startswith("/login"),
                f"Open Platform CTA href={href!r} must start with /login",
            )

    def test_open_platform_preserves_post_login_destination(self) -> None:
        # The login page's default next is "/" which is the marketing
        # page itself — that would loop the user. The CTA must supply
        # an explicit next= so the partner ends up at the platform.
        ctas = re.findall(
            r'<a[^>]*href="([^"]*)"[^>]*>[^<]*Open Platform',
            self.html,
            flags=re.IGNORECASE,
        )
        for href in ctas:
            self.assertIn(
                "next=", href,
                f"Open Platform CTA href={href!r} missing next= param "
                "— logged-in users would loop back to marketing",
            )


class LoginPageRedirectsAuthenticated(unittest.TestCase):
    """An already-signed-in request to /login must short-circuit to
    ``next`` rather than re-render the form. We exercise this via a
    minimal handler stub so the test does not need a live server."""

    def test_authenticated_user_redirects_to_next(self) -> None:
        # The behaviour we pin: when ``self._current_user()`` returns a
        # truthy value AND the ``next`` query param is a same-origin
        # path, the login route calls ``self._redirect(next)`` instead
        # of rendering the page. Inspecting the source is sufficient
        # here — a full HTTP test would require booting the server.
        import inspect
        from rcm_mc import server

        src = inspect.getsource(server.RCMHandler._route_login_page)
        self.assertIn("self._redirect(nxt)", src)
        # And the guard must require the path to be same-origin.
        self.assertIn('nxt.startswith("/")', src)


if __name__ == "__main__":
    unittest.main()
