"""Usability-helper contract for ck_copy_share_link_button +
ck_recently_viewed_rail (sweep batch 17).

Two reusable primitives extracted from #1072 so any page can opt in:

  · ck_copy_share_link_button — a small button that copies
    window.location.href to clipboard via navigator.clipboard.
    Idempotent JS install guarded by
    window.__rcmCopyShareLinkInstalled.

  · ck_recently_viewed_rail — JS-hydrated <section> that paints the
    last 5 deal visits from the rcm_recent_deals localStorage key
    that deal_profile_page already populates on every visit.

Pins (helpers in isolation):
  · The share-link helper emits CSS + JS + the button with the
    data-rcm-share-link attribute that the JS binds to. JS guard
    against duplicate install is present.
  · The recent-rail helper emits the JS-hydration target
    (data-rcm-recent-deals) + a friendly placeholder + a separate
    JS guard against duplicate install.

Pins (wired into pages):
  · /home (populated portfolio) carries the recently-viewed rail.
  · /portfolio (populated) carries the Copy-share-link button.
  · Each page renders exactly one <h1> (the #1036 invariant).
"""
from __future__ import annotations

import re
import unittest

import pandas as pd


class CopyShareLinkButtonTests(unittest.TestCase):

    def test_helper_emits_css_js_and_button(self) -> None:
        from rcm_mc.ui._chartis_kit import ck_copy_share_link_button
        html = ck_copy_share_link_button()
        # Button with the auto-bind attribute the JS reads.
        self.assertIn("data-rcm-share-link", html)
        self.assertIn(">Copy share link</button>", html)
        # Button class for editorial styling.
        self.assertIn('class="ck-share-btn"', html)
        # Idempotent JS install guard.
        self.assertIn("__rcmCopyShareLinkInstalled", html)
        # The clipboard API call is present.
        self.assertIn("navigator.clipboard", html)

    def test_helper_accepts_custom_label(self) -> None:
        from rcm_mc.ui._chartis_kit import ck_copy_share_link_button
        html = ck_copy_share_link_button(label="Share link →")
        self.assertIn(">Share link →</button>", html)

    def test_helper_label_is_escaped(self) -> None:
        from rcm_mc.ui._chartis_kit import ck_copy_share_link_button
        html = ck_copy_share_link_button(label="<script>x")
        self.assertIn("&lt;script&gt;x", html)
        # The unescaped form should NOT appear inside the button.
        self.assertNotIn(">" + "<script>x</button>", html)


class RecentlyViewedRailTests(unittest.TestCase):

    def test_helper_emits_hydration_target_and_js(self) -> None:
        from rcm_mc.ui._chartis_kit import ck_recently_viewed_rail
        html = ck_recently_viewed_rail()
        # JS hydrates this element.
        self.assertIn("data-rcm-recent-deals", html)
        # Wrapper class.
        self.assertIn('class="ck-recent"', html)
        # Idempotent install guard.
        self.assertIn("__rcmRecentlyViewedInstalled", html)
        # Eyebrow + dash.
        self.assertIn('class="eyebrow"', html)
        self.assertIn('class="dash"', html)

    def test_helper_renders_empty_placeholder(self) -> None:
        from rcm_mc.ui._chartis_kit import ck_recently_viewed_rail
        html = ck_recently_viewed_rail()
        # The server-side placeholder is a friendly editorial line
        # the JS replaces on hydration; if JS fails, the partner
        # still sees something deliberate.
        self.assertIn("Loading recent deals", html)

    def test_helper_reads_localstorage_key_partner_already_populates(
        self,
    ) -> None:
        # The JS reads from `rcm_recent_deals` — the same key
        # deal_profile_page already writes to via pushRecent().
        # Pin the contract so a rename on either side gets caught.
        from rcm_mc.ui._chartis_kit import ck_recently_viewed_rail
        html = ck_recently_viewed_rail()
        self.assertIn("rcm_recent_deals", html)


class HomeRecentRailWiredTests(unittest.TestCase):

    def test_home_carries_recently_viewed_rail(self) -> None:
        from rcm_mc.ui.home_v2 import render_home

        class _StubMP:
            indicators: list = []

        html = render_home(_StubMP(), [], pd.DataFrame())
        # Recently-viewed wrapper present right after the masthead.
        self.assertIn('class="ck-recent"', html)
        self.assertIn("data-rcm-recent-deals", html)

    def test_home_one_h1_with_recent_rail(self) -> None:
        from rcm_mc.ui.home_v2 import render_home

        class _StubMP:
            indicators: list = []

        html = render_home(_StubMP(), [], pd.DataFrame())
        self.assertEqual(len(re.findall(r"<h1[ >]", html)), 1)


class PortfolioShareButtonWiredTests(unittest.TestCase):

    def test_portfolio_carries_share_button(self) -> None:
        from rcm_mc.ui.portfolio_overview import render_portfolio_overview
        df = pd.DataFrame({
            "deal_id": ["D1", "D2"],
            "name": ["Alpha", "Beta"],
            "stage": ["active", "active"],
            "sector": ["x", "y"],
            "denial_rate": [10, 12],
            "days_in_ar": [40, 50],
            "net_revenue": [100e6, 200e6],
            "net_collection_rate": [0.95, 0.92],
            "health_score": [70, 60],
        })
        html = render_portfolio_overview(df)
        self.assertIn("data-rcm-share-link", html)
        self.assertIn(">Copy share link</button>", html)

    def test_portfolio_one_h1_with_share_button(self) -> None:
        from rcm_mc.ui.portfolio_overview import render_portfolio_overview
        df = pd.DataFrame({
            "deal_id": ["D1"], "name": ["A"], "stage": ["active"],
            "sector": ["x"], "denial_rate": [10], "days_in_ar": [40],
            "net_revenue": [100e6], "net_collection_rate": [0.95],
            "health_score": [70],
        })
        html = render_portfolio_overview(df)
        # Pre-sweep contract was one h1 (#1036); the new share
        # button is a <button>, not an <h1>, so the invariant holds.
        self.assertEqual(len(re.findall(r"<h1[ >]", html)), 1)


if __name__ == "__main__":
    unittest.main()
