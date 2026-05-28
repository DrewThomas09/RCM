"""Sticky-thead + back-to-top usability contract (sweep batch 18).

Two more reusable usability primitives in the kit, plus two
high-traffic wirings:

  · The .ck-table-sticky-head CSS opt-in (no helper — just a class
    name). Pages add the class to a long table; the thead row
    stays pinned to the topbar while the body scrolls.
  · ck_back_to_top_button — a floating button that fades in after
    the partner scrolls > 600px down, smooth-scrolls to top on
    click.

Wirings:
  · /pipeline — sticky thead on the hospitals table + floating
    back-to-top button.
  · /methodology — floating back-to-top button (catalog can be
    long).

Pins (helpers in isolation):
  · ck_back_to_top_button emits CSS + JS + button with the
    data-rcm-back-to-top attribute the JS binds to. Idempotent
    install guard (__rcmBackToTopInstalled) present. Smooth-scroll
    behavior wired.

Pins (wired into pages):
  · /pipeline hospitals table carries the sticky-head class.
  · /pipeline carries the back-to-top button.
  · /methodology carries the back-to-top button.
"""
from __future__ import annotations

import os
import re
import tempfile
import unittest

from rcm_mc.portfolio.store import PortfolioStore


class BackToTopHelperTests(unittest.TestCase):

    def test_helper_emits_css_js_and_button(self) -> None:
        from rcm_mc.ui._chartis_kit import ck_back_to_top_button
        html = ck_back_to_top_button()
        # Button with the auto-bind attribute the JS reads.
        self.assertIn("data-rcm-back-to-top", html)
        # Editorial button class.
        self.assertIn('class="ck-back-to-top"', html)
        # ARIA label for screen readers.
        self.assertIn('aria-label="Back to top of page"', html)

    def test_helper_idempotent_install_guard(self) -> None:
        from rcm_mc.ui._chartis_kit import ck_back_to_top_button
        html = ck_back_to_top_button()
        # Window-scoped guard prevents double-bind when multiple
        # consumers ship the helper on the same page.
        self.assertIn("__rcmBackToTopInstalled", html)

    def test_helper_smooth_scroll_behavior(self) -> None:
        # Modern smooth-scroll behavior on click.
        from rcm_mc.ui._chartis_kit import ck_back_to_top_button
        html = ck_back_to_top_button()
        self.assertIn("behavior:'smooth'", html)

    def test_helper_accepts_custom_label(self) -> None:
        from rcm_mc.ui._chartis_kit import ck_back_to_top_button
        html = ck_back_to_top_button(label="Top ↑")
        self.assertIn(">Top ↑</button>", html)

    def test_helper_label_is_escaped(self) -> None:
        from rcm_mc.ui._chartis_kit import ck_back_to_top_button
        html = ck_back_to_top_button(label="<script>alert(1)")
        self.assertIn("&lt;script&gt;alert(1)", html)
        # The raw script tag should NOT survive in the button
        # content (it gets escaped before injection).
        self.assertNotIn(">" + "<script>alert(1)</button>", html)

    def test_back_to_top_print_hidden(self) -> None:
        # Print stylesheet hides the button — partners printing IC
        # memos shouldn't see a floating UI control on paper.
        from rcm_mc.ui._chartis_kit import ck_back_to_top_button
        html = ck_back_to_top_button()
        self.assertIn("@media print", html)
        self.assertIn("display:none", html)


class StickyTheadKitContractTests(unittest.TestCase):
    """The ck-table-sticky-head opt-in class is defined in the inline
    fallback CSS that every page inherits via chartis_shell."""

    def test_sticky_head_rule_present_in_shell_css(self) -> None:
        # Render any page that uses chartis_shell; pull the inline
        # CSS and confirm the sticky-head rule is defined.
        import pandas as pd
        from rcm_mc.ui.portfolio_overview import render_portfolio_overview
        html = render_portfolio_overview(pd.DataFrame())
        # The rule body uses `position:sticky` + `top:0` on the
        # sticky-head thead th element.
        self.assertRegex(
            html,
            r"\.ck-table\.ck-table-sticky-head\s+thead\s+th\s*\{[^}]*"
            r"position:sticky[^}]*top:0",
        )


class PipelineWiringTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        from rcm_mc.data.pipeline import _ensure_tables, add_to_pipeline
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        cls._db = path
        store = PortfolioStore(path)
        with store.connect() as con:
            _ensure_tables(con)
            add_to_pipeline(
                con, ccn="050001", hospital_name="Alpha",
                state="AL", beds=200, stage="loi",
            )
            con.commit()
        from rcm_mc.ui.pipeline_page import render_pipeline
        cls.html = render_pipeline(path)

    @classmethod
    def tearDownClass(cls) -> None:
        try:
            os.unlink(cls._db)
        except OSError:
            pass

    def test_hospitals_table_carries_sticky_head_class(self) -> None:
        self.assertIn("ck-table-sticky-head", self.html)

    def test_back_to_top_button_present(self) -> None:
        self.assertIn("data-rcm-back-to-top", self.html)
        self.assertIn('class="ck-back-to-top"', self.html)

    def test_one_h1_with_new_wirings(self) -> None:
        self.assertEqual(len(re.findall(r"<h1[ >]", self.html)), 1)


class MethodologyWiringTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        from rcm_mc.ui.library_page import render_library
        cls.html = render_library()

    def test_back_to_top_button_present(self) -> None:
        self.assertIn("data-rcm-back-to-top", self.html)
        self.assertIn('class="ck-back-to-top"', self.html)

    def test_one_h1_with_new_wirings(self) -> None:
        self.assertEqual(len(re.findall(r"<h1[ >]", self.html)), 1)


if __name__ == "__main__":
    unittest.main()
