"""Tests for cross-deal initiative rollup (Brick 83)."""
from __future__ import annotations

import os
import tempfile
import unittest

from rcm_mc.rcm.initiative_rollup import (
    initiative_deals_detail,
    initiative_portfolio_rollup,
)
from rcm_mc.rcm.initiative_tracking import record_initiative_actual
from rcm_mc.portfolio.store import PortfolioStore


def _store(tmp: str) -> PortfolioStore:
    return PortfolioStore(os.path.join(tmp, "p.db"))


class TestPortfolioRollup(unittest.TestCase):
    def test_empty_store_returns_empty_frame(self):
        with tempfile.TemporaryDirectory() as tmp:
            df = initiative_portfolio_rollup(_store(tmp))
            self.assertTrue(df.empty)
            self.assertIn("initiative_id", df.columns)

    def test_aggregates_across_multiple_deals(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            # Same initiative across 3 deals
            for did, impact in [("ccf", 8000), ("mgh", 5000), ("nyp", 10000)]:
                record_initiative_actual(
                    store, deal_id=did,
                    initiative_id="prior_auth_improvement",
                    quarter="2026Q1", ebitda_impact=impact,
                )
            df = initiative_portfolio_rollup(store)
            row = df[df["initiative_id"] == "prior_auth_improvement"].iloc[0]
            self.assertEqual(row["deal_count"], 3)
            self.assertAlmostEqual(row["cumulative_actual"], 23000, places=1)

    def test_sorts_worst_severity_first(self):
        """Laggards surface at the top so partners see problems first."""
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            # prior_auth_improvement: annual 25k, so Q1 plan = 6.25k.
            # 500 impact → -92% variance → off_track
            record_initiative_actual(
                store, deal_id="ccf", initiative_id="prior_auth_improvement",
                quarter="2026Q1", ebitda_impact=500,
            )
            # coding_cdi_improvement: annual 80k, so Q1 plan = 20k.
            # 22k impact → +10% → on_track
            record_initiative_actual(
                store, deal_id="ccf", initiative_id="coding_cdi_improvement",
                quarter="2026Q1", ebitda_impact=22000,
            )
            df = initiative_portfolio_rollup(store)
            # Off-track comes first
            self.assertEqual(df.iloc[0]["initiative_id"], "prior_auth_improvement")
            self.assertEqual(df.iloc[0]["severity"], "off_track")

    def test_counts_each_deal_only_once_per_initiative(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            # Same deal, same initiative, 3 quarters → deal_count still 1
            for qtr in ("2025Q4", "2026Q1", "2026Q2"):
                record_initiative_actual(
                    store, deal_id="ccf",
                    initiative_id="prior_auth_improvement",
                    quarter=qtr, ebitda_impact=2000,
                )
            df = initiative_portfolio_rollup(store)
            self.assertEqual(df.iloc[0]["deal_count"], 1)


class TestDealsDetail(unittest.TestCase):
    def test_empty_for_unrecorded_initiative(self):
        with tempfile.TemporaryDirectory() as tmp:
            df = initiative_deals_detail(_store(tmp), "prior_auth_improvement")
            self.assertTrue(df.empty)

    def test_returns_every_deal_running_initiative(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            for did in ("ccf", "mgh", "nyp"):
                record_initiative_actual(
                    store, deal_id=did,
                    initiative_id="prior_auth_improvement",
                    quarter="2026Q1", ebitda_impact=5000,
                )
            df = initiative_deals_detail(store, "prior_auth_improvement")
            self.assertEqual(len(df), 3)
            self.assertEqual(
                set(df["deal_id"]),
                {"ccf", "mgh", "nyp"},
            )

    def test_worst_variance_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            # Different impact levels
            record_initiative_actual(
                store, deal_id="bad", initiative_id="prior_auth_improvement",
                quarter="2026Q1", ebitda_impact=100,  # way below 6.25k plan
            )
            record_initiative_actual(
                store, deal_id="good", initiative_id="prior_auth_improvement",
                quarter="2026Q1", ebitda_impact=10000,  # above plan
            )
            df = initiative_deals_detail(store, "prior_auth_improvement")
            self.assertEqual(df.iloc[0]["deal_id"], "bad")


class TestHttpIntegration(unittest.TestCase):
    def _start(self, db_path):
        import socket as _socket
        import threading
        import time as _time
        from rcm_mc.server import build_server
        s = _socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        server, _ = build_server(port=port, db_path=db_path)
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        _time.sleep(0.05)
        return server, port

    def test_initiatives_page_renders_rollup(self):
        import urllib.request as _urlreq
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            record_initiative_actual(
                store, deal_id="ccf",
                initiative_id="prior_auth_improvement",
                quarter="2026Q1", ebitda_impact=500,
            )
            server, port = self._start(os.path.join(tmp, "p.db"))
            try:
                with _urlreq.urlopen(
                    f"http://127.0.0.1:{port}/initiatives"
                ) as r:
                    body = r.read().decode()
                    self.assertIn("Initiative rollup", body)
                    self.assertIn("prior_auth_improvement", body)
                    # Click-through to the drill page
                    self.assertIn('href="/initiative/prior_auth_improvement"', body)
            finally:
                server.shutdown()
                server.server_close()

    def test_initiative_detail_lists_deals(self):
        import urllib.request as _urlreq
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            for did in ("ccf", "mgh"):
                record_initiative_actual(
                    store, deal_id=did,
                    initiative_id="prior_auth_improvement",
                    quarter="2026Q1", ebitda_impact=5000,
                )
            server, port = self._start(os.path.join(tmp, "p.db"))
            try:
                with _urlreq.urlopen(
                    f"http://127.0.0.1:{port}/initiative/prior_auth_improvement"
                ) as r:
                    body = r.read().decode()
                    self.assertIn("Deals running this initiative (2)", body)
                    self.assertIn("ccf", body)
                    self.assertIn("mgh", body)
            finally:
                server.shutdown()
                server.server_close()

    def test_empty_initiatives_page_shows_placeholder(self):
        import urllib.request as _urlreq
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(os.path.join(tmp, "p.db"))
            try:
                with _urlreq.urlopen(
                    f"http://127.0.0.1:{port}/initiatives"
                ) as r:
                    body = r.read().decode()
                    self.assertIn("No initiative actuals recorded yet", body)
            finally:
                server.shutdown()
                server.server_close()
