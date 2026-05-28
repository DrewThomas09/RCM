"""Editorial head + Today's-Brief contract for /home (sweep batch 5).

Pins the Tier-1 5-block anatomy on /home AND the new Today's-Brief
3-tile auto-derived summary block so the head shape + the value
roll-up can't silently regress.

Pins:
  · ONE <h1> on the page (the #1036 a11y invariant). Pre-sweep, the
    page used the shell's ``editorial_intro=`` kwarg which
    auto-injected a ck_page_title; the rewrite drops that and emits
    the head in-body so the shape matches /portfolio, /pipeline,
    /library, /diligence, regression.
  · Eyebrow + 24×1px green-dash glyph.
  · Mono meta-line quoting REAL deal counts.
  · Italic-first-phrase serif lede in --green-deep.
  · 4-bucket status-dot legend.
  · Today's-Brief block — three tiles:
      · Portfolio NPR    — real sum from the deals frame
      · Health G/A/R     — real bucketing on health_score
      · Stalled · 30d    — real count of deals not updated in 30d
    Each tile carries a real value or "—" with an honest sub-line
    explaining the gap. NEVER editorial filler.
"""
from __future__ import annotations

import re
import unittest

import pandas as pd


class _StubMarketPulse:
    indicators: list = []


def _populated_deals() -> pd.DataFrame:
    # Health scores: 72 (green) / 55 (amber) / 81 (green) / 47 (amber)
    # Updated_at: one row > 30 days ago (stalled).
    return pd.DataFrame({
        "deal_id": ["D1", "D2", "D3", "D4"],
        "name": ["Alpha", "Beta", "Gamma", "Delta"],
        "stage": ["active", "active", "active", "pipeline"],
        "net_revenue": [250e6, 480e6, 120e6, 310e6],
        "denial_rate": [11.5, 14.2, 9.8, 13.1],
        "days_in_ar": [45, 52, 38, 60],
        "health_score": [72, 55, 81, 47],
        "updated_at": [
            "2026-05-28",   # fresh
            "2026-04-01",   # stalled (>30 days)
            "2026-05-15",   # fresh
            "2026-03-10",   # stalled (>30 days)
        ],
    })


class HomeEmptyStateTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        from rcm_mc.ui.home_v2 import render_home
        cls.html = render_home(_StubMarketPulse(), [], pd.DataFrame())

    def test_one_h1(self) -> None:
        self.assertEqual(len(re.findall(r"<h1[ >]", self.html)), 1)

    def test_head_anatomy_present(self) -> None:
        self.assertIn("home-head", self.html)
        self.assertRegex(
            self.html,
            r'<div class="eyebrow"><span class="dash"></span>\s*HOME',
        )
        self.assertIn("<h1>Home</h1>", self.html)
        self.assertIn('class="lede"', self.html)
        self.assertIn(
            "<em>Where the partner reads the market first.</em>",
            self.html,
        )

    def test_status_dot_legend(self) -> None:
        for label in ("Live data", "Computed", "Needs data", "Illustrative"):
            self.assertIn(label, self.html)
        for cls_name in ("live", "computed", "needs", "illustrative"):
            self.assertRegex(
                self.html,
                rf'<span class="dot {cls_name}"></span>',
            )

    def test_brief_block_present_with_honest_dashes(self) -> None:
        # Empty portfolio → every brief tile shows "—" with an honest
        # sub-line. NEVER a fake value.
        self.assertIn("home-brief", self.html)
        self.assertIn("Portfolio NPR", self.html)
        self.assertIn("Health · G / A / R", self.html)
        self.assertIn("Stalled · 30d", self.html)
        self.assertIn("No portfolio deals tracked yet", self.html)


class HomePopulatedTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        from rcm_mc.ui.home_v2 import render_home
        cls.html = render_home(
            _StubMarketPulse(), [], _populated_deals(),
        )

    def test_one_h1(self) -> None:
        self.assertEqual(len(re.findall(r"<h1[ >]", self.html)), 1)

    def test_meta_line_quotes_real_deal_count(self) -> None:
        self.assertIn("4 PORTFOLIO DEALS", self.html)

    def test_brief_npr_quotes_real_sum(self) -> None:
        # 250 + 480 + 120 + 310 = 1160M → $1.16B (or $1.2B / $1,160M
        # depending on format). Accept any leading-dollar amount.
        m = re.search(
            r'class="label">Portfolio NPR</div>\s*'
            r'<div class="val[^"]*">([^<]+)</div>',
            self.html,
        )
        self.assertIsNotNone(m, "Portfolio NPR tile body not found")
        val = m.group(1).strip()
        self.assertRegex(val, r'\$[0-9][0-9,.]*[MB]')

    def test_brief_health_quotes_real_bucketing(self) -> None:
        # 72,55,81,47 → 2 green / 2 amber / 0 red
        m = re.search(
            r'class="label">Health · G / A / R</div>\s*'
            r'<div class="val[^"]*">([^<]+)</div>',
            self.html,
        )
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1).strip(), "2/2/0")

    def test_brief_stalled_quotes_real_count(self) -> None:
        # Two of four rows have updated_at > 30 days back.
        m = re.search(
            r'class="label">Stalled · 30d</div>\s*'
            r'<div class="val[^"]*">([^<]+)</div>',
            self.html,
        )
        self.assertIsNotNone(m)
        # Hard-pin the count rather than allow any number — this is
        # the test's whole job.
        self.assertEqual(m.group(1).strip(), "2")

    def test_brief_stalled_tile_flips_bad_class_when_positive(self) -> None:
        # When stalled > 0 the value cell takes class "val bad" so the
        # coral text color flips on (Tier-2 §2.10 — color the text,
        # never the background).
        self.assertIn(
            'class="val bad"',
            self.html.split("Stalled · 30d")[1][:200],
        )

    def test_no_editorial_intro_double_h1(self) -> None:
        # Pre-sweep the shell's editorial_intro auto-injection AND
        # the in-body head could co-emit two ck-page-title blocks.
        # Confirm the page no longer leans on editorial_intro.
        # (The class="ck-section-intro" wrapper that editorial_intro
        # produces must NOT appear in the rendered head — only the
        # in-body home-head with its single h1.)
        # Allow ck-section-intro elsewhere in the page (some panels
        # may use it); but the first 6000 chars (head zone) shouldn't.
        head_zone = self.html[: self.html.find("home-brief") + 500]
        self.assertNotIn(
            'class="ck-section-intro"',
            head_zone,
            "/home head should no longer use editorial_intro",
        )


if __name__ == "__main__":
    unittest.main()
