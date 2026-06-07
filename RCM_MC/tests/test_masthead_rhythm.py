"""Under-title masthead rhythm regression guard (2026-06 rehaul).

The zone under every page title used to render differently on every page: the
title carried a 38px bottom margin, so a thin context strip (source/purpose,
illustrative note, explainer, section intro) that followed it floated far
below, and the gap differed per page. The rehaul made it one rhythm site-wide
in the shared stylesheet (collapse the title onto a following strip, unify the
strip treatments, avoid a doubled hairline above KPI grids).

These guards pin the load-bearing pieces so the rhythm can't silently regress:

  1. ``ck_illustrative_note`` must NOT emit its own inline ``<style>``. It used
     to, and that invisible style block sat between the page title and the note,
     breaking the ``.ck-page-title + .ck-illus-note`` adjacency the collapse
     rule needs (it fired on ~70 data_public pages only once the style moved to
     the global sheet). This is the single easiest piece to regress by "tidying"
     the helper, so it gets a dedicated test.
  2. The shared shell CSS must carry the collapse + unification rules.
  3. End to end, a title followed by a strip must be DOM-adjacent (no inert
     node between) so the CSS actually matches.

Offline: exercises the real helpers + chartis_shell, no server needed.
"""
from __future__ import annotations

import re
import unittest

from rcm_mc.ui._chartis_kit import (
    chartis_shell,
    ck_illustrative_note,
    ck_page_title,
    ck_source_purpose,
)


class IllustrativeNoteIsStyleFree(unittest.TestCase):
    def test_note_emits_markup_only_no_inline_style(self):
        html = ck_illustrative_note("savings figures")
        # The note itself is the divider; its CSS lives in the global sheet.
        self.assertNotIn("<style", html,
                         "ck_illustrative_note must not re-introduce an inline "
                         "<style> (it breaks title+note adjacency)")
        self.assertIn('class="ck-illus-note"', html)
        self.assertIn("Illustrative template", html)
        # The `what` text still rides along for the specific sentence.
        self.assertIn("savings figures", html)


class ShellCarriesMastheadRules(unittest.TestCase):
    def setUp(self):
        # Any chartis page carries the full shared stylesheet in <head>.
        self.head = chartis_shell("<p>body</p>", title="X").split("</head>", 1)[0]

    def test_global_illustrative_note_css_present(self):
        # The CSS the helper used to inline now lives once in the shell sheet.
        self.assertIn(".ck-illus-note { display:flex", self.head)

    def test_title_collapses_onto_a_following_strip(self):
        # The collapse rule fires when a context strip follows the title.
        self.assertIn(".ck-page-title:has(+ .ck-sp)", self.head)
        self.assertIn(".ck-page-title:has(+ .ck-illus-note)", self.head)

    def test_bespoke_explainer_family_is_covered(self):
        # ~30 pages predate ck_page_explainer with their own *-explainer class;
        # the family is caught by attribute-substring, not enumerated.
        self.assertIn('.ck-page-title + [class*="-explainer"]', self.head)

    def test_no_doubled_hairline_above_kpi_grid(self):
        # A strip's bottom rule is dropped above a KPI grid (own top rule).
        self.assertIn(".ck-kpi-grid", self.head)
        self.assertRegex(
            self.head,
            r"\.ck-sp:has\(\+ :is\(\.ck-kpi-grid",
            "missing the KPI-grid doubled-hairline guard",
        )


class TitleStaysAdjacentToStrip(unittest.TestCase):
    """End to end: title-first hoisting must leave the strip as the title's
    immediate sibling, or none of the CSS above can match."""

    def _body_after_head(self, body: str) -> str:
        html = chartis_shell(body, title="T")
        return html.split("</head>", 1)[-1]

    def test_illustrative_note_is_titles_next_sibling(self):
        # Page composes note-before-title (the common data_public shape); the
        # shell hoists the title to the top and the note must land right after.
        body = (
            ck_illustrative_note("figures")
            + ck_page_title("Tracker", eyebrow="DATA")
            + '<div class="ck-kpi-grid">kpis</div>'
        )
        out = self._body_after_head(body)
        m = re.search(r'<header class="ck-page-title".*?</header>\s*(<\w[^>]*>)',
                      out, re.S)
        self.assertIsNotNone(m, "page title header not found in body")
        nxt = m.group(1)
        self.assertNotIn("<style", nxt,
                         "an inert <style> between title and note breaks the "
                         "masthead adjacency")
        self.assertIn("ck-illus-note", nxt,
                      "the illustrative note must be the title's next sibling")

    def test_source_purpose_is_titles_next_sibling(self):
        body = (
            ck_source_purpose(
                purpose="Benchmark the target against peers.",
                universe="hcris", source="CMS HCRIS",
            )
            + ck_page_title("X-Ray", eyebrow="DILIGENCE")
            + "<p>content</p>"
        )
        out = self._body_after_head(body)
        m = re.search(r'<header class="ck-page-title".*?</header>\s*(<\w[^>]*>)',
                      out, re.S)
        self.assertIsNotNone(m)
        self.assertIn("ck-sp", m.group(1),
                      "the source/purpose strip must be the title's next sibling")


if __name__ == "__main__":
    unittest.main()
