"""Auto-injected breadcrumb must not repeat "Home".

The server post-processes editorial HTML to inject a breadcrumb derived
from the request path (Home -> Section -> Page). Home-section pages
(``/app``, ``/alerts``, ...) resolve their *section* to "Home" too, so the
hardcoded top-level Home crumb plus the resolved Home section crumb were
rendering "Home / Home / Command Center" on the most-trafficked page.

``_auto_breadcrumb_chain`` collapses adjacent duplicate labels so Home-
section pages read "Home / Page" while non-Home sections keep the full
"Home / Section / Page" trail.
"""
from __future__ import annotations

import unittest

from rcm_mc.server import _auto_breadcrumb_chain


class AutoBreadcrumbChainTests(unittest.TestCase):
    def test_app_collapses_double_home(self):
        # /app: section resolves to the Home section, page is Command Center.
        chain = _auto_breadcrumb_chain("Home", "/home", "Command Center", "/app")
        self.assertEqual(
            chain, [("Home", "/home"), ("Command Center", None)]
        )
        # Exactly one "Home" crumb survives.
        self.assertEqual(sum(1 for lbl, _ in chain if lbl == "Home"), 1)

    def test_alerts_collapses_double_home(self):
        chain = _auto_breadcrumb_chain("Home", "/home", "Alerts", "/alerts")
        self.assertEqual(chain, [("Home", "/home"), ("Alerts", None)])

    def test_non_home_section_keeps_full_trail(self):
        chain = _auto_breadcrumb_chain(
            "Pipeline", "/pipeline", "Deal Pipeline", "/pipeline"
        )
        self.assertEqual(
            chain,
            [("Home", "/home"), ("Pipeline", "/pipeline"),
             ("Deal Pipeline", None)],
        )

    def test_home_landing_is_single_crumb(self):
        # The Home landing itself (no distinct page label) → just "Home".
        chain = _auto_breadcrumb_chain("Home", "/home", "", "/home")
        self.assertEqual(chain, [("Home", "/home")])

    def test_section_only_keeps_link_on_surviving_home(self):
        # When the dup is collapsed, the surviving Home crumb keeps its href
        # even if the (dropped) section crumb carried it.
        chain = _auto_breadcrumb_chain("Home", "/home", "", "/anything")
        self.assertEqual(chain, [("Home", "/home")])

    def test_unknown_section_falls_back_to_path(self):
        chain = _auto_breadcrumb_chain("", "", "", "/mystery")
        self.assertEqual(chain, [("Home", "/home"), ("/mystery", None)])

    def test_last_crumb_is_current_page(self):
        # Callers render the final entry as the bold "here" marker, so it
        # must always carry a None href (not a link).
        for args in (
            ("Home", "/home", "Command Center", "/app"),
            ("Pipeline", "/pipeline", "Deal Pipeline", "/pipeline"),
            ("", "", "", "/x"),
        ):
            chain = _auto_breadcrumb_chain(*args)
            self.assertIsNone(chain[-1][1], f"last crumb should be current: {chain}")


if __name__ == "__main__":
    unittest.main()
