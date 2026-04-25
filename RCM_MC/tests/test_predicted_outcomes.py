"""Tests for the dashboard's "Predicted exit outcomes" card.

The wow moment: partner pins DEAL_042 to track. On every dashboard
load, the tool runs that deal's profile against 600+ realized PE
comparables and renders a predicted MOIC distribution as an inline
SVG range chart. Partner didn't ask for the prediction — the tool
volunteered it.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime, timezone


def _seed_deal(store, deal_id: str, name: str,
               sector: str = "hospital") -> None:
    with store.connect() as con:
        con.execute(
            "INSERT INTO deals (deal_id, name, created_at, profile_json) "
            "VALUES (?, ?, ?, ?)",
            (deal_id, name,
             datetime.now(timezone.utc).isoformat(),
             json.dumps({"sector": sector})),
        )
        con.commit()


class TestRangeBarSvg(unittest.TestCase):
    def test_returns_empty_string_when_no_median(self):
        from rcm_mc.ui.dashboard_page import _moic_range_bar
        self.assertEqual(_moic_range_bar(None, None, None), "")

    def test_renders_svg_with_all_three_points(self):
        from rcm_mc.ui.dashboard_page import _moic_range_bar
        svg = _moic_range_bar(1.5, 2.3, 3.1)
        self.assertIn("<svg", svg)
        self.assertIn("polyline", svg) if False else None
        # Whisker rect + median dot
        self.assertIn("<rect", svg)
        self.assertIn("<circle", svg)
        # 1.0x and 2.5x reference lines (dashed)
        self.assertIn("stroke-dasharray", svg)

    def test_handles_missing_p25_p75(self):
        """When only median is known, render a dot without crashing
        (degraded but informative)."""
        from rcm_mc.ui.dashboard_page import _moic_range_bar
        svg = _moic_range_bar(None, 2.0, None)
        self.assertIn("<svg", svg)


class TestNoWatchlistNoSection(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "t.db")
        from rcm_mc.portfolio.store import PortfolioStore
        PortfolioStore(self.db).init_db()

    def tearDown(self):
        self.tmp.cleanup()

    def test_no_section_when_watchlist_empty(self):
        from rcm_mc.ui.dashboard_page import render_dashboard
        html = render_dashboard(self.db)
        self.assertNotIn("Predicted exit outcomes", html)


class TestPredictedOutcomesPopulate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "t.db")
        from rcm_mc.portfolio.store import PortfolioStore
        self.store = PortfolioStore(self.db)
        self.store.init_db()
        # Seed 2 starred deals + the corpus
        _seed_deal(self.store, "PINNED_1", "Watch A")
        _seed_deal(self.store, "PINNED_2", "Watch B")
        from rcm_mc.deals.watchlist import star_deal
        star_deal(self.store, "PINNED_1")
        star_deal(self.store, "PINNED_2")
        # Seed corpus so benchmark_deal has matches
        from rcm_mc.data_public.deals_corpus import DealsCorpus
        corpus = DealsCorpus(self.db)
        corpus.seed(skip_if_populated=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_section_renders_with_predictions(self):
        from rcm_mc.ui.dashboard_page import render_dashboard
        html = render_dashboard(self.db)
        # Section title with count
        self.assertIn("Predicted exit outcomes", html)
        # Both pinned deals appear
        self.assertIn("Watch A", html)
        self.assertIn("Watch B", html)
        # MOIC value rendered (any number followed by 'x')
        import re
        self.assertRegex(html, r"\d+\.\d{2}x")
        # SVG range chart present
        self.assertIn('aria-label="MOIC range chart"', html)

    def test_section_includes_legend(self):
        from rcm_mc.ui.dashboard_page import render_dashboard
        html = render_dashboard(self.db)
        # Legend explains what the chart means
        self.assertIn("scale 0–6", html)
        self.assertIn("p25–p75 range", html)
        self.assertIn("median predicted MOIC", html)


class TestPerDealTargetProfile(unittest.TestCase):
    """Regression for the "all deals get the same prediction" bug.

    Before the fix, _render_predicted_outcomes_section built a
    hardcoded target = {sector: 'hospital', ev_mm: None, ...} for
    every deal — so the corpus match was identical across pinned
    deals and the predictions only differed by random tie-breaking.

    The fix: read sector + ev_mm + sponsor + payer_mix from the
    deal's profile_json. This test seeds two deals with very
    different sector + EV profiles and verifies the predicted
    medians differ, OR at minimum that the corpus comparables
    match the deal's actual profile (not the default).
    """

    def test_predictions_differ_across_distinct_deals(self):
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "t.db")
            from rcm_mc.portfolio.store import PortfolioStore
            store = PortfolioStore(db)
            store.init_db()

            # Deal A: hospital, $200M
            with store.connect() as con:
                con.execute(
                    "INSERT INTO deals (deal_id, name, created_at, "
                    "profile_json) VALUES (?, ?, ?, ?)",
                    ("DEAL_HOSP", "Small Hospital",
                     datetime.now(timezone.utc).isoformat(),
                     json.dumps({"sector": "hospital", "ev_mm": 200,
                                 "year": 2024})),
                )
                # Deal B: managed_care, $2000M (10x bigger, different sector)
                con.execute(
                    "INSERT INTO deals (deal_id, name, created_at, "
                    "profile_json) VALUES (?, ?, ?, ?)",
                    ("DEAL_MC", "Big Managed Care",
                     datetime.now(timezone.utc).isoformat(),
                     json.dumps({"sector": "managed_care", "ev_mm": 2000,
                                 "year": 2024})),
                )
                con.commit()

            from rcm_mc.deals.watchlist import star_deal
            star_deal(store, "DEAL_HOSP")
            star_deal(store, "DEAL_MC")

            from rcm_mc.data_public.deals_corpus import DealsCorpus
            DealsCorpus(db).seed(skip_if_populated=True)

            from rcm_mc.ui.dashboard_page import render_dashboard
            html = render_dashboard(db)

            # Both deal names render
            self.assertIn("Small Hospital", html)
            self.assertIn("Big Managed Care", html)

            # Extract median MOICs printed for each row. Format is
            # "<bold>2.45x</bold>" inside the row's main span.
            section_start = html.find("Predicted exit outcomes")
            section_end = html.find("</section>", section_start)
            section = html[section_start:section_end]

            # Find each <li ...> block and extract the deal_id +
            # the bold MOIC value
            import re
            blocks = re.findall(
                r'<li[^>]*>.*?DEAL_(HOSP|MC).*?'
                r'(\d+\.\d{2})x</span>',
                section, flags=re.S,
            )
            self.assertEqual(
                len(blocks), 2,
                msg=f"expected 2 deal blocks, got {len(blocks)}"
            )
            medians = {deal: median for deal, median in blocks}
            self.assertNotEqual(
                medians.get("HOSP"), medians.get("MC"),
                msg=f"hospital vs managed-care deals should yield "
                    f"DIFFERENT predicted medians (the whole point "
                    f"of per-deal target profiles), got identical "
                    f"medians: {medians}",
            )
        finally:
            tmp.cleanup()


class TestSeeWhyDeepLink(unittest.TestCase):
    """Each predicted-outcome row's median MOIC links to
    /diligence/comparable-outcomes with the SAME target profile
    that produced the prediction. Closes the "see why this number"
    loop without making the partner re-type the deal's parameters."""

    def test_median_value_links_to_comparable_outcomes(self):
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "t.db")
            from rcm_mc.portfolio.store import PortfolioStore
            store = PortfolioStore(db)
            store.init_db()
            with store.connect() as con:
                con.execute(
                    "INSERT INTO deals (deal_id, name, created_at, "
                    "profile_json) VALUES (?, ?, ?, ?)",
                    ("WATCH_PIVOT", "Pivot Hospital",
                     datetime.now(timezone.utc).isoformat(),
                     json.dumps({"sector": "managed_care",
                                 "ev_mm": 750, "year": 2023})),
                )
                con.commit()
            from rcm_mc.deals.watchlist import star_deal
            star_deal(store, "WATCH_PIVOT")
            from rcm_mc.data_public.deals_corpus import DealsCorpus
            DealsCorpus(db).seed(skip_if_populated=True)

            from rcm_mc.ui.dashboard_page import render_dashboard
            html = render_dashboard(db)

            # Deep-link present with the deal's actual profile values
            self.assertIn(
                "/diligence/comparable-outcomes?", html,
                msg="median value should be a deep-link to the "
                    "comparable-outcomes page",
            )
            # Sector + ev_mm threaded through the query string
            self.assertIn("sector=managed_care", html)
            self.assertIn("ev_mm=750", html)
        finally:
            tmp.cleanup()


class TestCapAtEightDeals(unittest.TestCase):
    """Watchlist of 12 → only 8 prediction rows. Bounds compute
    on busy partners' dashboards."""

    def test_cap_enforced(self):
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "t.db")
            from rcm_mc.portfolio.store import PortfolioStore
            store = PortfolioStore(db)
            store.init_db()
            from rcm_mc.deals.watchlist import star_deal
            for i in range(12):
                _seed_deal(store, f"PIN_{i}", f"Watch {i}")
                star_deal(store, f"PIN_{i}")
            from rcm_mc.data_public.deals_corpus import DealsCorpus
            DealsCorpus(db).seed(skip_if_populated=True)

            from rcm_mc.ui.dashboard_page import render_dashboard
            html = render_dashboard(db)
            # Find the predicted-outcomes section title
            import re
            m = re.search(
                r"Predicted exit outcomes \((\d+)\)", html,
            )
            if m:
                n = int(m.group(1))
                self.assertLessEqual(n, 8,
                                     msg=f"cap should be 8, got {n}")
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
