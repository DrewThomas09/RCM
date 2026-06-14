"""Skip-to-content link (WCAG 2.4.1 Bypass Blocks).

Keyboard / screen-reader users must be able to jump past the topbar nav
straight to <main>. The link is the FIRST focusable element in the body,
points at the main landmark, and only appears on chromed pages (bare
login/forgot pages have no nav to bypass).
"""

import unittest

from rcm_mc.ui._chartis_kit import chartis_shell


class SkipLinkTests(unittest.TestCase):
    def setUp(self):
        self.html = chartis_shell("<p>body</p>", "Dash", active_nav="/research")

    def test_skip_link_is_first_focusable_element(self):
        # It must precede the topbar so a single Tab lands on it.
        body = self.html.split("<body>", 1)[1]
        self.assertTrue(
            body.lstrip().startswith('<a class="ck-skip-link" href="#ck-main">'),
            "skip link is not the first element inside <body>",
        )

    def test_skip_link_targets_the_main_landmark(self):
        # Anchor target must exist and be focusable (tabindex=-1 so the
        # programmatic focus move actually lands there).
        self.assertIn('href="#ck-main"', self.html)
        self.assertIn('<main id="ck-main" tabindex="-1"', self.html)

    def test_skip_link_styles_are_inlined(self):
        # Inlined (not in /static) so the bypass works even if the static
        # stylesheet fails to serve.
        self.assertIn(".ck-skip-link", self.html)
        self.assertIn(".ck-skip-link:focus", self.html)

    def test_bare_pages_have_no_skip_link(self):
        # No chrome → no nav to bypass → no link (keeps login DOM minimal).
        bare = chartis_shell("<p>x</p>", "Login", show_chrome=False)
        self.assertNotIn("ck-skip-link", bare)
        # The main landmark still carries its id for in-page anchors.
        self.assertIn('id="ck-main"', bare)


if __name__ == "__main__":
    unittest.main()
