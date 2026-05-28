"""Editorial-head + auto-derived meta contract for /day-one (sweep
batch 14).

/day-one is the partner's Monday-morning brief — the curated five-
volume read partners check first thing every week. Pre-sweep, the
page used the legacy date-stamp + ck_section_intro pair (h2 deck),
which the shell then prepended with an auto-injected ck_page_title.
Two title blocks at the masthead.

This sweep replaces both with a single strict Tier-1 5-block head
whose mono meta-line auto-derives the week's at-a-glance counts:
alerts pending, recent activity items, recent analysis packets.

Pins:
  · ONE <h1> per page (#1036 a11y invariant).
  · Eyebrow + 24×1px green-dash glyph + "{WEEKDAY} BRIEF".
  · Mono meta-line carries the live week number + ISO date and,
    when present, real counts of alerts / activity items / recent
    packets — never hard-coded.
  · Italic-first-phrase serif lede: "Where to start your week."
  · 4-bucket status-dot legend.
"""
from __future__ import annotations

import os
import re
import tempfile
import unittest

from rcm_mc.portfolio.store import PortfolioStore


class DayOneEditorialHeadTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        cls._db = path
        store = PortfolioStore(path)
        # Schema-less store is fine — the loaders gracefully return
        # empty lists when tables don't exist yet.
        from rcm_mc.ui.day_one_page import render_day_one
        cls.html = render_day_one(store)

    @classmethod
    def tearDownClass(cls) -> None:
        try:
            os.unlink(cls._db)
        except OSError:
            pass

    def test_one_h1(self) -> None:
        self.assertEqual(len(re.findall(r"<h1[ >]", self.html)), 1)

    def test_head_block(self) -> None:
        self.assertIn('class="do-head"', self.html)

    def test_eyebrow_with_dash_carries_weekday(self) -> None:
        # The eyebrow ends with "BRIEF" — the weekday upper-case
        # prefix is dynamic; just confirm both shape pieces.
        self.assertRegex(
            self.html,
            r'<div class="eyebrow"><span class="dash"></span>\s*'
            r'[A-Z]+\s+BRIEF',
        )

    def test_h1_carries_day_one_and_weekday(self) -> None:
        # H1 reads "Day One — {Weekday}, {Month} {Day}"
        self.assertRegex(
            self.html,
            r'<h1>Day One — [A-Z][a-z]+, [A-Z][a-z]+ \d{1,2}</h1>',
        )

    def test_meta_line_quotes_week_and_date(self) -> None:
        # Meta-line shape: "WEEK NN · YYYY-MM-DD · ..."
        self.assertRegex(
            self.html,
            r'class="meta">[^<]*WEEK\s+\d{2}[^<]*\d{4}-\d{2}-\d{2}',
        )

    def test_lede_italic_first_phrase(self) -> None:
        self.assertIn(
            "<em>Where to start your week.</em>",
            self.html,
        )

    def test_status_dot_legend(self) -> None:
        for cls_name in ("live", "computed", "needs", "illustrative"):
            self.assertRegex(
                self.html,
                rf'<span class="dot {cls_name}"></span>',
            )

    def test_legacy_date_stamp_block_removed(self) -> None:
        # The previous `<div class="do-datestamp">` block has been
        # folded into the mono meta-line. Confirm it no longer
        # renders as a separate top-of-page row.
        self.assertNotIn('class="do-datestamp"', self.html)

    def test_no_legacy_section_intro_at_head(self) -> None:
        # The shell auto-inject path was triggered by the previous
        # ck_section_intro. With the strict head in place, no
        # ck-section-intro should appear in the masthead zone.
        head_zone = self.html[: self.html.find("The Monday brief") + 80]
        self.assertNotIn('class="ck-section-intro"', head_zone)


if __name__ == "__main__":
    unittest.main()
