"""Conference Intelligence — curated recaps + macro threads.

You asked to make the Conference page actually useful: summarize and visually
present what happened at the big healthcare conferences (JPM, HLTH, …), what
mattered, and the market impact — refreshable. Per the no-runtime-network
architecture, recaps are curated, committed data (conference_recaps.py) that
the page renders above the forward calendar; every recap is source-linked.

Guards:
  - the recap dataset is well-formed (required fields, real sources, valid
    sentiments) and covers the flagship events;
  - the page leads with macro threads + recaps (sentiment, themes,
    announcements, market impact, diligence read) on the default view;
  - the category filter focuses the forward calendar and drops the recaps;
  - the existing calendar (Conference Roadmap) is preserved.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.conference_page import render_conference_roadmap
from rcm_mc.ui.conference_recaps import (
    CONFERENCE_RECAPS,
    MACRO_THREADS,
    SENTIMENT_TONE,
)

_REQUIRED = (
    "id", "name", "edition", "held", "sentiment", "sentiment_note",
    "one_line", "themes", "announcements", "market_impact", "diligence",
    "sources",
)


class RecapDataTests(unittest.TestCase):
    def test_covers_flagship_events(self) -> None:
        names = " ".join(r["name"] for r in CONFERENCE_RECAPS)
        for anchor in ("J.P. Morgan", "HLTH", "HIMSS", "HFMA", "Becker", "AHA"):
            self.assertIn(anchor, names)

    def test_every_recap_is_well_formed(self) -> None:
        self.assertGreaterEqual(len(CONFERENCE_RECAPS), 6)
        ids = set()
        for r in CONFERENCE_RECAPS:
            for k in _REQUIRED:
                self.assertIn(k, r, f"{r.get('id')} missing {k}")
            self.assertNotIn(r["id"], ids, "duplicate id")
            ids.add(r["id"])
            self.assertIn(r["sentiment"], SENTIMENT_TONE)
            self.assertTrue(r["themes"] and r["market_impact"])
            # every recap carries at least one real source URL
            self.assertTrue(r["sources"])
            for _title, url in r["sources"]:
                self.assertTrue(url.startswith("http"))

    def test_macro_threads_present(self) -> None:
        self.assertGreaterEqual(len(MACRO_THREADS), 3)
        for t in MACRO_THREADS:
            self.assertTrue(t["title"] and t["body"])


class RecapRenderTests(unittest.TestCase):
    def test_default_view_leads_with_recaps(self) -> None:
        html = render_conference_roadmap()
        self.assertIn("Conference Intelligence", html)
        self.assertIn("Macro threads", html)
        self.assertIn("What happened — conference recaps", html)
        self.assertIn("Diligence read", html)
        # real sourced content, sentiment badge, a real announcement
        self.assertIn("Cautiously optimistic", html)
        self.assertIn("AbbVie", html)        # JPM26 announcement
        self.assertIn("Optum Real", html)    # HLTH25 announcement

    def test_category_filter_focuses_calendar_drops_recaps(self) -> None:
        html = render_conference_roadmap("Investment")
        # recaps (and the unfiltered AHA recap) are gone on a filtered view
        self.assertNotIn("Macro threads", html)
        self.assertNotIn("AHA Annual", html)
        # but the forward calendar is still there
        self.assertIn("Conference Roadmap", html)
        self.assertIn("J.P. Morgan", html)

    def test_calendar_preserved_on_default(self) -> None:
        html = render_conference_roadmap()
        self.assertIn("Conference Roadmap", html)   # calendar section label
        self.assertIn("Planning Tips", html)
        self.assertIn("2027 Q1", html)


if __name__ == "__main__":
    unittest.main()
