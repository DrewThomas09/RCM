"""Title-first contract for ``chartis_shell`` (2026-06 clutter audit).

A page-render audit found that 123 of 178 ``data_public`` surfaces shipped
editorial chrome ABOVE the page's own ``ck_page_title``:

  * the ``editorial_intro=`` section-intro deck (prepended by the shell),
  * a ``ck_source_purpose`` band the renderer composed *before* its title
    (``body = ck_source_purpose(...) + body``),
  * the route-level illustrative-data note.

That "stuff above the title" reads as clutter and breaks the editorial
cadence the gold-standard pages (/command-center, /diligence/hcris-xray)
follow — title first, then the source/purpose band, then content.

Two shell fixes restore the invariant for every page without editing 178
renderers:

  1. ``editorial_intro=`` no longer emits its section-intro deck when the
     body already carries its own ``ck_page_title`` (the deck is redundant
     with the page's own title + source band).
  2. ``_hoist_page_title`` moves the first ``ck_page_title`` header to the
     very top of the body after every injection pass.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._chartis_kit import (
    _hoist_page_title,
    chartis_shell,
    ck_page_title,
    ck_section_intro,
    ck_source_purpose,
)


class HoistPageTitleUnitTests(unittest.TestCase):
    def test_hoists_title_above_prepended_band(self):
        title = ck_page_title("Drug Shortage Tracker", eyebrow="DRUG SHORTAGE")
        band = '<div class="ck-sp"><p>source/purpose</p></div>'
        out = _hoist_page_title(band + title + "<p>content</p>")
        # title now leads, band slid below it
        self.assertLess(out.index('class="ck-page-title"'), out.index('class="ck-sp"'))
        self.assertTrue(out.lstrip().startswith('<header class="ck-page-title">'))
        # nothing duplicated
        self.assertEqual(out.count('class="ck-page-title"'), 1)
        self.assertIn("source/purpose", out)
        self.assertIn("content", out)

    def test_noop_when_title_already_first(self):
        body = ck_page_title("X") + "<p>content</p>"
        self.assertEqual(_hoist_page_title(body), body)

    def test_noop_with_only_leading_style_block(self):
        # hcris_xray opens with a scoped <style> before its title — that
        # still counts as title-first, so the hoist is a no-op.
        body = "<style>.x{color:red}</style>" + ck_page_title("X") + "<p>c</p>"
        self.assertEqual(_hoist_page_title(body), body)

    def test_noop_when_no_title(self):
        body = '<div class="ck-sp">just a band</div><p>content</p>'
        self.assertEqual(_hoist_page_title(body), body)


class ChartisShellTitleFirstTests(unittest.TestCase):
    def test_self_titled_page_with_editorial_intro_drops_deck(self):
        # Case B: the body already has its own ck_page_title AND the page
        # passed editorial_intro=. The redundant section-intro deck must
        # NOT render (it would land above the title).
        body = ck_page_title("Drug Shortage Tracker", eyebrow="DRUG SHORTAGE")
        body += '<div class="ck-kpi-grid">kpis</div>'
        html = chartis_shell(
            body, title="Drug Shortage",
            editorial_intro={
                "eyebrow": "DRUG SHORTAGE",
                "headline": "What the drug shortage page reveals.",
                "italic_word": "reveals",
            },
        )
        self.assertNotIn('class="ck-section-intro"', html)
        # exactly one page title, and it leads the main content
        self.assertEqual(html.count('class="ck-page-title"'), 1)

    def test_titleless_page_with_editorial_intro_keeps_deck(self):
        # Case A is unchanged: a page with no title of its own still gets
        # a shell-injected title + the section-intro deck below it.
        html = chartis_shell(
            "<p>body</p>", title="Some Tool",
            editorial_intro={
                "eyebrow": "TOOL",
                "headline": "The tool finds its voice.",
                "italic_word": "finds",
            },
        )
        self.assertIn('class="ck-section-intro"', html)
        self.assertIn('class="ck-page-title"', html)
        # title leads the section-intro deck
        self.assertLess(
            html.index('class="ck-page-title"'),
            html.index('class="ck-section-intro"'),
        )

    def test_prepended_source_purpose_lands_below_title(self):
        # Reproduces the exact drug_shortage shape: source/purpose band
        # composed BEFORE a body that opens with the page title.
        body = ck_page_title("Drug Shortage Tracker", eyebrow="DRUG SHORTAGE")
        body += "<p>content</p>"
        full = ck_source_purpose(
            purpose="Flag drug-shortage / supply-chain exposure.",
            universe="cms", confidence="derived",
            source="openFDA drug shortages",
            next_action="Search a drug",
        ) + body
        html = chartis_shell(full, title="Drug Shortage")
        body_html = html.split("</head>", 1)[-1]
        self.assertLess(
            body_html.index('class="ck-page-title"'),
            body_html.index('class="ck-sp"'),
            "page title must render above the source/purpose band",
        )

    def test_direct_section_intro_still_below_title(self):
        # A page that calls ck_section_intro DIRECTLY in its body (not via
        # the kwarg) keeps the deck, but the shell-injected title leads it.
        body = ck_section_intro("EYE", "A deck headline.") + "<p>body</p>"
        html = chartis_shell(body, title="Bear Case")
        self.assertIn('class="ck-section-intro"', html)
        self.assertLess(
            html.index('class="ck-page-title"'),
            html.index('class="ck-section-intro"'),
        )


if __name__ == "__main__":
    unittest.main()
