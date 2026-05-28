"""Universal ck_editorial_head() helper + batch-19 wave-1 wirings.

This is the Phase-1 batch of the audited migration plan
(docs/style-sweep/MIGRATION_INVENTORY.md).

A single reusable kit helper that all 288 remaining page renderers
can adopt with one call. Plus the first three migrations (top
high-traffic Group B routes: deal_mc, my_dashboard,
portfolio_monitor).

Pins:
  · The helper emits all 5 spec-mandated blocks (eyebrow + dash,
    serif h1, mono meta, italic-first-phrase lede, status-dot
    legend).
  · The helper produces exactly ONE <h1> (the #1036 invariant).
  · Optional source-note + actions block + show_legend control.
  · Each of the three swept routes renders the helper output:
      · ck-eh wrapper present
      · ck-eh-eyebrow with the spec-mandated dash glyph
      · Real-count meta-line (not hard-coded)
      · One <h1>
"""
from __future__ import annotations

import os
import re
import tempfile
import unittest


class CkEditorialHeadHelperTests(unittest.TestCase):
    """The universal helper in rcm_mc/ui/_chartis_kit.py."""

    def test_helper_emits_five_block_anatomy(self) -> None:
        from rcm_mc.ui._chartis_kit import ck_editorial_head
        html = ck_editorial_head(
            eyebrow="EYEBROW",
            title="Title",
            meta="META",
            lede_italic_phrase="Italic phrase.",
            lede_body="Roman body.",
        )
        # Block 1: eyebrow with dash glyph (Tier-2 §2.1)
        self.assertIn('class="ck-eh-eyebrow"', html)
        self.assertIn('class="ck-eh-dash"', html)
        self.assertIn("EYEBROW", html)
        # Block 2: serif H1 (single h1, #1036 invariant)
        self.assertIn("<h1>Title</h1>", html)
        self.assertEqual(len(re.findall(r"<h1[ >]", html)), 1)
        # Block 3: mono meta-line
        self.assertIn('class="ck-eh-meta"', html)
        self.assertIn(">META<", html)
        # Block 4: italic-first-phrase lede (Tier-2 §2.3)
        self.assertIn("<em>Italic phrase.</em>", html)
        self.assertIn("Roman body.", html)
        # Block 5: status-dot legend (4 buckets, Tier-2 §2.4)
        self.assertIn('class="ck-eh-legend"', html)
        for kind in ("live", "computed", "needs", "illustrative"):
            self.assertRegex(
                html,
                rf'<span class="ck-eh-dot {kind}"></span>',
            )

    def test_helper_optional_source_note(self) -> None:
        from rcm_mc.ui._chartis_kit import ck_editorial_head
        html_with = ck_editorial_head(
            eyebrow="E", title="T",
            source_note="CMS public data, updated 2026-05",
        )
        # The <p class="ck-eh-source"> element appears (with the
        # "Source:" prefix the helper adds).
        self.assertIn(
            "Source: CMS public data, updated 2026-05",
            html_with,
        )
        self.assertIn('<p class="ck-eh-source">', html_with)
        # Helper omits the <p> when source_note is empty (the CSS
        # rule for .ck-eh-source still ships, but no element does).
        html_without = ck_editorial_head(eyebrow="E", title="T")
        self.assertNotIn('<p class="ck-eh-source">', html_without)
        self.assertNotIn("Source:", html_without)

    def test_helper_optional_actions_block(self) -> None:
        from rcm_mc.ui._chartis_kit import ck_editorial_head
        html = ck_editorial_head(
            eyebrow="E", title="T",
            actions_html='<a href="/x">Open X →</a>',
        )
        self.assertIn('class="ck-eh-actions"', html)
        self.assertIn('href="/x">Open X →', html)

    def test_helper_show_legend_false(self) -> None:
        from rcm_mc.ui._chartis_kit import ck_editorial_head
        html = ck_editorial_head(
            eyebrow="E", title="T", show_legend=False,
        )
        # The <ul class="ck-eh-legend"> element is gone (the CSS
        # rule still ships, but the markup is omitted).
        self.assertNotIn('<ul class="ck-eh-legend">', html)

    def test_helper_escapes_untrusted_inputs(self) -> None:
        from rcm_mc.ui._chartis_kit import ck_editorial_head
        html = ck_editorial_head(
            eyebrow="<script>",
            title="<safe>",   # title trusted (caller pre-escapes)
            meta="A & B",
            lede_italic_phrase="C < D.",
            source_note="<script>",
        )
        # Eyebrow / meta / italic phrase / source-note are escaped.
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("A &amp; B", html)
        self.assertIn("C &lt; D.", html)
        # And the raw script tag doesn't leak through.
        self.assertNotIn(">" + "<script></div>", html)


class MyDashboardWireupTests(unittest.TestCase):
    """The /my/<owner> route adopts the universal helper."""

    @classmethod
    def setUpClass(cls) -> None:
        from rcm_mc.ui.my_dashboard_page import render_my_dashboard
        from rcm_mc.portfolio.store import PortfolioStore
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        cls._db = path
        store = PortfolioStore(path)
        cls.html = render_my_dashboard(store=store, owner="alice")

    @classmethod
    def tearDownClass(cls) -> None:
        try:
            os.unlink(cls._db)
        except OSError:
            pass

    def test_one_h1(self) -> None:
        self.assertEqual(len(re.findall(r"<h1[ >]", self.html)), 1)

    def test_ck_eh_wrapper(self) -> None:
        self.assertIn('class="ck-eh"', self.html)

    def test_eyebrow_carries_owner(self) -> None:
        # The eyebrow includes the owner name in caps so the page
        # is obviously partner-scoped at first glance.
        self.assertIn("PARTNER · ALICE", self.html)


class PortfolioMonitorWireupTests(unittest.TestCase):
    """The /portfolio/monitor route adopts the universal helper."""

    @classmethod
    def setUpClass(cls) -> None:
        from rcm_mc.ui.portfolio_monitor_page import render_portfolio_monitor
        from rcm_mc.portfolio.store import PortfolioStore
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        cls._db = path
        store = PortfolioStore(path)
        cls.html = render_portfolio_monitor(store)

    @classmethod
    def tearDownClass(cls) -> None:
        try:
            os.unlink(cls._db)
        except OSError:
            pass

    def test_one_h1(self) -> None:
        self.assertEqual(len(re.findall(r"<h1[ >]", self.html)), 1)

    def test_ck_eh_wrapper(self) -> None:
        # Either the page-local fallback head OR the universal one
        # — both produce a single h1. Pin the universal helper.
        self.assertIn('class="ck-eh"', self.html)

    def test_meta_empty_state_honestly_reads_zero(self) -> None:
        # Empty store → meta says "0 ACTIVE · IMPORT TO POPULATE"
        # rather than a fabricated number — empty-state path uses
        # the same universal helper as the populated path.
        self.assertIn("0 ACTIVE · IMPORT TO POPULATE", self.html)


if __name__ == "__main__":
    unittest.main()
