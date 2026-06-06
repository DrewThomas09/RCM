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

from rcm_mc.server import _auto_breadcrumb_chain, _page_has_own_head


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


class PageOwnHeadSuppressionTests(unittest.TestCase):
    """The fallback auto-breadcrumb must be suppressed when the page already
    renders its own top-of-page head, so /app stops stacking a breadcrumb on
    top of its eyebrow head (the "double header")."""

    def test_command_center_grid_head_suppresses(self):
        # Grid /app renders the .cc-crumb eyebrow head.
        body = '<header>...</header><div class="cc-crumb">PORTFOLIO</div>'
        self.assertTrue(_page_has_own_head(body))

    def test_editorial_page_head_suppresses(self):
        # editorial_page_head (flat /app + others) renders .pg-head.
        body = '<header>...</header><div class="pg-head"><h1>X</h1></div>'
        self.assertTrue(_page_has_own_head(body))

    def test_ck_page_title_head_suppresses(self):
        # ck_page_title (the standard head on ~every content page) renders
        # <header class="ck-page-title"> with its own eyebrow + H1.
        body = ('<header class="ck-page-title"><div class="ck-eyebrow">'
                'PIPELINE</div><h1>Deal Pipeline</h1></header>')
        self.assertTrue(_page_has_own_head(body))

    def test_ck_page_title_as_secondary_class_suppresses(self):
        # Some pages add ck-page-title as a 2nd class (Insights pages):
        # class="ip-head ck-page-title". The loose match must still catch it,
        # but must NOT be fooled by the ck-page-title-meta sub-element.
        self.assertTrue(_page_has_own_head('<header class="ip-head ck-page-title">x</header>'))
        self.assertFalse(_page_has_own_head('<div class="ck-page-title-meta">just meta</div>'))

    def test_bespoke_editorial_head_suppresses(self):
        # The per-page heads (pp-head, dp-head, ip-head, cv-head, ...) all
        # open their eyebrow with the dash glyph span.
        body = ('<div class="pp-head"><div class="eyebrow">'
                '<span class="dash"></span> PIPELINE</div><h1>Deal Pipeline</h1></div>')
        self.assertTrue(_page_has_own_head(body))

    def test_explicit_breadcrumbs_suppresses(self):
        body = '<nav class="ck-breadcrumbs"><a>Home</a></nav>'
        self.assertTrue(_page_has_own_head(body))

    def test_plain_page_does_not_suppress(self):
        # A page with no head of its own keeps the fallback breadcrumb.
        body = '<header>topbar</header><main><table>...</table></main>'
        self.assertFalse(_page_has_own_head(body))

    def test_css_rule_text_does_not_falsely_suppress(self):
        # The CSS rules (.cc-crumb { ... }) must not be mistaken for a
        # rendered element — only class="..." attributes count.
        body = '<style>.cc-crumb{color:red;} .pg-head{margin:0;}</style>'
        self.assertFalse(_page_has_own_head(body))


if __name__ == "__main__":
    unittest.main()
