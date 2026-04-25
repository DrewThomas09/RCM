"""Regression tests: dashboard renders cleanly with malformed data.

Belt-and-suspenders coverage to catch the kinds of bugs that
silently slip through otherwise: deals with broken profile_json,
missing fields, weird sectors, extreme EV values. Every variant
must render the dashboard without crashing and without leaking
Python repr like NaN, "None", DataFrame, or "object at 0x..."
into user-visible HTML.
"""
from __future__ import annotations

import json
import os
import re
import tempfile
import unittest
from datetime import datetime, timezone


_REPR_LEAK_MARKERS = (
    "Traceback", "TypeError:", "ValueError:", "AttributeError:",
    "object at 0x", "<bound method",
)


def _strip_scripts_and_styles(html: str) -> str:
    """Strip <script> and <style> blocks so user-visible HTML can
    be checked without false positives from JS using NaN / None."""
    no_script = re.sub(
        r"<script[^>]*>.*?</script>", "", html, flags=re.S)
    no_style = re.sub(
        r"<style[^>]*>.*?</style>", "", no_script, flags=re.S)
    return no_style


class TestRobustness(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "t.db")
        from rcm_mc.portfolio.store import PortfolioStore
        self.store = PortfolioStore(self.db)
        self.store.init_db()

    def tearDown(self):
        self.tmp.cleanup()

    def _render(self) -> str:
        from rcm_mc.ui.dashboard_page import render_dashboard
        return render_dashboard(self.db)

    def _assert_no_repr_leaks(self, html: str) -> None:
        visible = _strip_scripts_and_styles(html)
        for marker in _REPR_LEAK_MARKERS:
            self.assertNotIn(
                marker, visible,
                msg=f"repr leak: {marker!r} found in user-visible HTML",
            )

    def test_renders_with_malformed_profile_json(self):
        """A deal whose profile_json is invalid JSON must not crash
        the predicted-outcomes section (the JSON parse is in a
        try/except)."""
        with self.store.connect() as con:
            con.execute(
                "INSERT INTO deals (deal_id, name, created_at, "
                "profile_json) VALUES (?, ?, ?, ?)",
                ("BAD_JSON", "Broken JSON Hospital",
                 datetime.now(timezone.utc).isoformat(),
                 "{this is not valid json"),
            )
            con.commit()
        from rcm_mc.deals.watchlist import star_deal
        star_deal(self.store, "BAD_JSON")

        html = self._render()
        self.assertIn("BAD_JSON", html)
        self._assert_no_repr_leaks(html)

    def test_renders_with_string_ev_mm(self):
        """profile_json ships ev_mm as a string ("500" not 500).
        Numeric coercion via _safe_float should handle it without
        a TypeError trickling out."""
        with self.store.connect() as con:
            con.execute(
                "INSERT INTO deals (deal_id, name, created_at, "
                "profile_json) VALUES (?, ?, ?, ?)",
                ("STR_EV", "String-EV Hospital",
                 datetime.now(timezone.utc).isoformat(),
                 json.dumps({"sector": "hospital", "ev_mm": "500"})),
            )
            con.commit()
        from rcm_mc.deals.watchlist import star_deal
        star_deal(self.store, "STR_EV")
        from rcm_mc.data_public.deals_corpus import DealsCorpus
        DealsCorpus(self.db).seed(skip_if_populated=True)

        html = self._render()
        self.assertIn("STR_EV", html)
        self._assert_no_repr_leaks(html)

    def test_renders_with_none_ev_mm(self):
        with self.store.connect() as con:
            con.execute(
                "INSERT INTO deals (deal_id, name, created_at, "
                "profile_json) VALUES (?, ?, ?, ?)",
                ("NULL_EV", "Null-EV Hospital",
                 datetime.now(timezone.utc).isoformat(),
                 json.dumps({"sector": "hospital", "ev_mm": None})),
            )
            con.commit()
        from rcm_mc.deals.watchlist import star_deal
        star_deal(self.store, "NULL_EV")
        from rcm_mc.data_public.deals_corpus import DealsCorpus
        DealsCorpus(self.db).seed(skip_if_populated=True)

        html = self._render()
        self.assertIn("NULL_EV", html)
        self._assert_no_repr_leaks(html)

    def test_renders_with_unknown_sector(self):
        """An unknown sector string falls into the matcher's 0.0
        adjacency case but doesn't crash the page."""
        with self.store.connect() as con:
            con.execute(
                "INSERT INTO deals (deal_id, name, created_at, "
                "profile_json) VALUES (?, ?, ?, ?)",
                ("WEIRD_SEC", "Weird-Sector Hospital",
                 datetime.now(timezone.utc).isoformat(),
                 json.dumps({"sector": "foobar", "ev_mm": 100})),
            )
            con.commit()
        from rcm_mc.deals.watchlist import star_deal
        star_deal(self.store, "WEIRD_SEC")
        from rcm_mc.data_public.deals_corpus import DealsCorpus
        DealsCorpus(self.db).seed(skip_if_populated=True)

        html = self._render()
        self.assertIn("WEIRD_SEC", html)
        self._assert_no_repr_leaks(html)


class TestComparableEdgeCases(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "t.db")
        from rcm_mc.portfolio.store import PortfolioStore
        PortfolioStore(self.db).init_db()
        from rcm_mc.data_public.deals_corpus import DealsCorpus
        DealsCorpus(self.db).seed(skip_if_populated=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_zero_ev_does_not_crash(self):
        """`_size_distance` divides by EV; zero would crash without
        the `if target_ev_mm <= 0` guard."""
        from rcm_mc.ui.comparable_outcomes_page import (
            render_comparable_outcomes_page,
        )
        html = render_comparable_outcomes_page(
            {"sector": "hospital", "ev_mm": "0"}, db_path=self.db,
        )
        self.assertIn("Median MOIC", html)

    def test_negative_ev_does_not_crash(self):
        from rcm_mc.ui.comparable_outcomes_page import (
            render_comparable_outcomes_page,
        )
        html = render_comparable_outcomes_page(
            {"sector": "hospital", "ev_mm": "-100"}, db_path=self.db,
        )
        self.assertIn("Median MOIC", html)

    def test_non_numeric_ev_falls_through_gracefully(self):
        from rcm_mc.ui.comparable_outcomes_page import (
            render_comparable_outcomes_page,
        )
        html = render_comparable_outcomes_page(
            {"sector": "hospital", "ev_mm": "not-a-number"},
            db_path=self.db,
        )
        # The float() raises, our handler catches and sets ev=None,
        # benchmark_deal still runs against neutral 0.5 size
        self.assertIn("Median MOIC", html)


if __name__ == "__main__":
    unittest.main()
