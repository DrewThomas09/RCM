"""Editorial head + keyword-search contract for /methodology (sweep batch 3).

Pins:
  · Strict Tier-1 5-block head: eyebrow with 24×1px green-dash, single
    serif h1, mono meta-line quoting real section / entry counts,
    italic-first-phrase serif lede, 4-bucket status-dot legend.
  · ONE <h1> per page (the #1036 a11y invariant) — pre-sweep, the
    page passed BOTH ``editorial_intro=`` (which auto-injects a
    ck_page_title) AND a manual ``ck_page_title(...)`` call, producing
    two title blocks at the masthead. The rewrite drops the auto-
    inject side; only the manual head renders.
  · Keyword-search bar on the masthead — server-side ``?q=`` filter
    on title + description + doc body, case-insensitive, back-button
    safe (no JS).
  · Honest empty state when the keyword matches nothing — coral
    eyebrow + real query in the message + a clear-filter link.
"""
from __future__ import annotations

import re
import unittest


class LibraryEditorialHeadTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        from rcm_mc.ui.library_page import render_library
        cls.html = render_library()

    def test_one_h1_per_page(self) -> None:
        # #1036 a11y invariant. Pre-sweep had TWO (one auto-injected
        # by editorial_intro=, one from manual ck_page_title).
        self.assertEqual(len(re.findall(r"<h1[ >]", self.html)), 1)

    def test_head_block_present(self) -> None:
        self.assertIn('class="lib-head"', self.html)

    def test_eyebrow_has_green_dash(self) -> None:
        self.assertRegex(
            self.html,
            r'<div class="eyebrow"><span class="dash"></span>\s*METHODOLOGY',
        )

    def test_h1_is_research_library(self) -> None:
        self.assertIn("<h1>Research Library</h1>", self.html)

    def test_meta_line_quotes_real_counts(self) -> None:
        # The catalog ships at least one section; meta-line must
        # quote real counts (not a hard-coded placeholder).
        self.assertRegex(
            self.html,
            r'class="meta">\s*\d+\s+SECTIONS\s*·\s*\d+\s+DOCUMENTED ENTRIES',
        )

    def test_lede_italic_first_phrase(self) -> None:
        self.assertIn(
            "<em>Where the platform shows its work.</em>",
            self.html,
        )

    def test_status_dot_legend_present(self) -> None:
        for cls_name in ("live", "computed", "needs", "illustrative"):
            self.assertRegex(
                self.html,
                rf'<span class="dot {cls_name}"></span>',
                f"missing legend dot: {cls_name}",
            )

    def test_no_dual_editorial_intro_h1(self) -> None:
        # The pre-sweep dual head emitted ck-section-intro (auto-h1
        # via the shell) AND ck-page-title. We dropped editorial_intro
        # entirely; only ck-page-title (or our lib-head) survives.
        # Easiest pin: confirm the shell's auto-injected ck-section-
        # intro headline ("Where the platform shows its work.") is
        # NOT also wrapped in an h2 by ck_section_intro — i.e. the
        # phrase only appears inside the italic-first-phrase lede.
        self.assertNotIn(
            '<div class="ck-section-intro"', self.html,
            "library should no longer use ck_section_intro at the head",
        )


class LibrarySearchFunctionalityTests(unittest.TestCase):

    def test_search_bar_renders(self) -> None:
        from rcm_mc.ui.library_page import render_library
        html = render_library()
        # GET form pointing at /methodology with a `q` input.
        self.assertIn('class="lib-search"', html)
        self.assertIn('action="/methodology"', html)
        self.assertIn('name="q"', html)

    def test_keyword_filter_narrows_meta_line(self) -> None:
        # A keyword that matches at least one entry MUST change the
        # meta-line to read "N OF M ENTRIES MATCH ..." and quote the
        # real query.
        from rcm_mc.ui.library_page import render_library
        html = render_library(q="DCF")
        self.assertRegex(
            html,
            r'\d+ OF \d+ ENTRIES MATCH "DCF"',
        )

    def test_clear_link_renders_when_query_active(self) -> None:
        from rcm_mc.ui.library_page import render_library
        html = render_library(q="DCF")
        self.assertIn(
            '<a class="ghost" href="/methodology">Clear</a>',
            html,
        )

    def test_clear_link_absent_when_no_query(self) -> None:
        from rcm_mc.ui.library_page import render_library
        html = render_library()
        self.assertNotIn(
            '<a class="ghost" href="/methodology">Clear</a>',
            html,
        )

    def test_no_results_state_honest(self) -> None:
        # Bogus query → coral eyebrow + real query in the message.
        # Never editorial filler.
        from rcm_mc.ui.library_page import render_library
        html = render_library(q="nonexistent_xyzzy_keyword")
        self.assertIn('class="lib-empty"', html)
        self.assertIn("No results · adjust filters", html)
        self.assertIn("nonexistent_xyzzy_keyword", html)

    def test_query_is_html_escaped(self) -> None:
        # An XSS-shaped query must NOT produce raw script tags.
        from rcm_mc.ui.library_page import render_library
        html = render_library(q='<script>alert(1)</script>')
        self.assertNotIn("<script>alert(1)</script>", html)
        # The escaped form is acceptable.
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)

    def test_search_filter_actually_filters_entries(self) -> None:
        # Quote the real entry count for an unrelated query so the
        # filter narrows the rendered count vs the full catalog.
        from rcm_mc.ui.library_page import render_library
        full = render_library()
        narrow = render_library(q="DCF")
        # Both must render; narrowed page must show "OF" (the count
        # disclaimer) while the full page must not.
        self.assertNotIn(" OF ", full.split("class=\"meta\"")[1][:200])
        self.assertIn(" OF ", narrow.split("class=\"meta\"")[1][:200])


if __name__ == "__main__":
    unittest.main()
