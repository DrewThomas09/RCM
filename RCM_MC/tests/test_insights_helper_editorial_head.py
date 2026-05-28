"""Editorial-head cascade for render_insights_page (sweep batch 9).

The shared insights helper composes the search-hero + filter-rail +
results triplet for /research, /notes, and a handful of corpus pages.
Pre-sweep it called ck_section_intro at the top of the body, which
produces an h2 deck — and the shell auto-injected ck_page_title above
that to provide the h1, stacking two title blocks at the masthead.

This sweep replaces the section_intro path with the strict Tier-1
5-block head built in-body (eyebrow with dash → serif h1 → italic
deck → roman lede → status-dot legend). The new wrapper carries
``class="ip-head ck-page-title"`` so the shell sees an existing
page-title and skips its own auto-inject — exactly one h1.

Pins:
  · /research and /notes both render one h1.
  · The ip-head wrapper carries the ck-page-title marker class.
  · Eyebrow + 24×1px green-dash glyph.
  · Italic deck phrase (uses italic_word OR first-phrase fallback).
  · Status-dot legend in the head block.
  · Page title (from ``title`` kwarg) is the h1 text.
"""
from __future__ import annotations

import os
import re
import tempfile
import unittest

from rcm_mc.portfolio.store import PortfolioStore


class ResearchHeadTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        from rcm_mc.ui.research_page import render_research
        cls.html = render_research()

    def test_one_h1(self) -> None:
        # #1036 a11y invariant. Pre-sweep had two stacked title blocks.
        self.assertEqual(len(re.findall(r"<h1[ >]", self.html)), 1)

    def test_ip_head_wrapper_carries_page_title_marker(self) -> None:
        # The wrapper class must include "ck-page-title" so the shell
        # skips its auto-inject. Without this marker we'd get TWO h1s.
        self.assertIn('class="ip-head ck-page-title"', self.html)

    def test_eyebrow_with_dash(self) -> None:
        self.assertRegex(
            self.html,
            r'<div class="eyebrow"><span class="dash"></span>',
        )

    def test_h1_uses_page_title(self) -> None:
        self.assertIn("<h1>Research</h1>", self.html)

    def test_italic_deck_phrase(self) -> None:
        # The intro's italic_word="thinks" wraps the headline word.
        m = re.search(r'<p class="deck">(.*?)</p>', self.html)
        self.assertIsNotNone(m)
        self.assertIn("<em>thinks</em>", m.group(1))

    def test_lede_body_present(self) -> None:
        # Second roman-serif paragraph carries the intro body.
        self.assertIn(
            "Methodology, frameworks, deep-dives",
            self.html,
        )

    def test_status_dot_legend(self) -> None:
        for cls_name in ("live", "computed", "needs", "illustrative"):
            self.assertRegex(
                self.html,
                rf'<span class="dot {cls_name}"></span>',
            )

    def test_no_legacy_section_intro_at_head(self) -> None:
        # The shell's auto-inject path used to produce
        # `class="ck-section-intro"` here. Confirm it's gone from the
        # head zone (other parts of the page may still use it).
        head_zone = self.html[: self.html.find("ck-rail-layout") + 200]
        self.assertNotIn('class="ck-section-intro"', head_zone)


class NotesHeadTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        from rcm_mc.ui.notes_search_page import render_notes_search
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        cls._db = path
        store = PortfolioStore(path)
        # Initialize tables so notes search doesn't 500 on missing
        # schema; render_notes_search handles empty results.
        with store.connect() as con:
            con.execute(
                "CREATE TABLE IF NOT EXISTS notes ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "ccn TEXT, body TEXT, created_at TEXT)"
            )
            con.commit()
        cls.html = render_notes_search(store=store)

    @classmethod
    def tearDownClass(cls) -> None:
        try:
            os.unlink(cls._db)
        except OSError:
            pass

    def test_one_h1(self) -> None:
        self.assertEqual(len(re.findall(r"<h1[ >]", self.html)), 1)

    def test_ip_head_wrapper(self) -> None:
        self.assertIn('class="ip-head ck-page-title"', self.html)

    def test_h1_uses_page_title(self) -> None:
        # render_notes_search passes title="Notes Search"
        self.assertIn("<h1>Notes Search</h1>", self.html)

    def test_italic_deck_phrase(self) -> None:
        m = re.search(r'<p class="deck">(.*?)</p>', self.html)
        self.assertIsNotNone(m)
        self.assertIn("<em>finds</em>", m.group(1))

    def test_status_dot_legend(self) -> None:
        for cls_name in ("live", "computed", "needs", "illustrative"):
            self.assertRegex(
                self.html,
                rf'<span class="dot {cls_name}"></span>',
            )


if __name__ == "__main__":
    unittest.main()
