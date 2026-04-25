"""Tests for /diligence/sponsor-detail — single-sponsor drill-down.

When a sponsor pitches "3.5x base case", a partner needs to know
what THIS sponsor has actually realized. Type the name, get the
focused detail view: MOIC distribution, vintage timeline, sector
breakdown, per-deal list with MOIC color-coding.
"""
from __future__ import annotations

import json
import os
import socket
import tempfile
import threading
import unittest
import urllib.parse
import urllib.request
from contextlib import closing


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestSponsorDetailPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db = os.path.join(cls.tmp.name, "t.db")
        cls.port = _free_port()
        from rcm_mc.server import build_server
        cls.server, _ = build_server(
            port=cls.port, host="127.0.0.1",
            db_path=cls.db, auth=None,
        )
        cls.thread = threading.Thread(
            target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        cls.tmp.cleanup()

    def _get(self, path: str) -> str:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{self.port}{path}", timeout=10,
        ) as resp:
            return resp.read().decode()

    def test_initial_load_shows_pitch_form(self):
        html = self._get("/diligence/sponsor-detail")
        self.assertIn("Sponsor track record", html)
        self.assertIn("How to use this", html)
        # Form input present
        self.assertIn('name="sponsor"', html)
        # Type-ahead datalist with sponsor names
        self.assertIn('id="sponsor-suggestions"', html)
        # Deep-link to the league table for partners who want
        # all sponsors at once
        self.assertIn("/sponsor-track-record", html)

    def test_unknown_sponsor_shows_partial_matches(self):
        """A typo or partial spelling should surface candidates,
        not a 404. 'mountain' should match anything containing
        'mountain' (e.g. New Mountain Capital)."""
        params = urllib.parse.urlencode({"sponsor": "mountain"})
        html = self._get(f"/diligence/sponsor-detail?{params}")
        # Look for the partial-match tile UI
        self.assertIn("partial-match", html.lower())

    def test_real_sponsor_renders_detail(self):
        """Pick a sponsor that's likely in the corpus and verify
        the detail view shape."""
        from rcm_mc.data_public.deals_corpus import DealsCorpus
        corpus = DealsCorpus(self.db)
        corpus.seed(skip_if_populated=True)

        # Find a sponsor that DOES exist in the corpus
        from rcm_mc.data_public.sponsor_track_record import (
            build_sponsor_records,
        )
        records = build_sponsor_records(corpus.list(limit=2000))
        # Pick one with at least 2 deals so all sections render
        candidates = [name for name, rec in records.items()
                      if rec.deal_count >= 2 and name != "Unknown"]
        self.assertTrue(candidates, msg="corpus should have ≥1 sponsor "
                                        "with ≥2 deals")
        sponsor_name = candidates[0]

        params = urllib.parse.urlencode({"sponsor": sponsor_name})
        html = self._get(f"/diligence/sponsor-detail?{params}")

        # Sponsor name appears as the H2 header
        self.assertIn(f">{sponsor_name}<", html)
        # Required sections
        self.assertIn("Median MOIC", html)
        self.assertIn("Vintage activity", html)
        self.assertIn("Sector specialization", html)
        # Stat strip carries the deal count
        rec = records[sponsor_name]
        self.assertIn(f">{rec.deal_count}<", html)

    def test_case_insensitive_match(self):
        """'NEW MOUNTAIN CAPITAL' should match the same record as
        'New Mountain Capital'."""
        from rcm_mc.data_public.deals_corpus import DealsCorpus
        from rcm_mc.data_public.sponsor_track_record import (
            build_sponsor_records,
        )
        corpus = DealsCorpus(self.db)
        corpus.seed(skip_if_populated=True)
        records = build_sponsor_records(corpus.list(limit=2000))
        candidates = [n for n, r in records.items() if r.deal_count >= 2]
        if not candidates:
            self.skipTest("no sponsor with ≥2 deals in corpus")
        original = candidates[0]
        upcased = original.upper()

        params = urllib.parse.urlencode({"sponsor": upcased})
        html = self._get(f"/diligence/sponsor-detail?{params}")
        # Resolves to the canonical name, not a "no match" page
        self.assertIn(f">{original}<", html)
        self.assertNotIn("No exact match for", html)


class TestSponsorDetailRobustness(unittest.TestCase):
    """Edge cases: empty input, unknown sponsor with no partial
    matches, sector data missing."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db = os.path.join(cls.tmp.name, "t.db")
        from rcm_mc.portfolio.store import PortfolioStore
        PortfolioStore(cls.db).init_db()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_no_match_no_partials_renders_cleanly(self):
        """A garbage string should render the 'no match' card with
        an empty partial-match list, not a 500."""
        from rcm_mc.ui.sponsor_detail_page import (
            render_sponsor_detail_page,
        )
        html = render_sponsor_detail_page(
            {"sponsor": "ZZZZZZZZZNONSENSE"}, db_path=self.db,
        )
        self.assertIn("No exact match for", html)
        self.assertIn("ZZZZZZZZZNONSENSE", html)


if __name__ == "__main__":
    unittest.main()
