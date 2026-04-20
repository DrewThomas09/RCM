"""Tests for SeekingChartis home page, market pulse, and insights.

HOME PAGE:
 1. GET / renders SeekingChartis home with market pulse.
 2. Home page has market indicators.
 3. Home page has deal table.
 4. Empty portfolio shows create-deal link.

MARKET PULSE:
 5. compute_market_pulse returns indicators.
 6. Sentiment label computed correctly.

INSIGHTS:
 7. Insights generated for high-denial deals.
 8. Empty portfolio returns empty insights.
"""
from __future__ import annotations

import json
import os
import socket
import tempfile
import threading
import time
import unittest
import urllib.request

from rcm_mc.intelligence.market_pulse import compute_market_pulse
from rcm_mc.intelligence.insights_generator import generate_daily_insights
from rcm_mc.portfolio.store import PortfolioStore


def _start(db_path):
    from rcm_mc.server import build_server
    s = socket.socket(); s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]; s.close()
    server, _ = build_server(port=port, db_path=db_path)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start(); time.sleep(0.05)
    return server, port


class TestHomePage(unittest.TestCase):

    def test_home_renders_caduceus(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/home",
                ) as r:
                    body = r.read().decode()
                self.assertIn("SeekingChartis", body)
                self.assertIn("ck-topbar", body)
                self.assertIn("ck-nav", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_home_with_deals(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="Alpha Hospital",
                              profile={"denial_rate": 18, "days_in_ar": 55,
                                       "net_revenue": 300e6})
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/home",
                ) as r:
                    body = r.read().decode()
                self.assertIn("Alpha Hospital", body)
                self.assertIn("Active Deals", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_empty_portfolio_shows_cta(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/home",
                ) as r:
                    body = r.read().decode()
                self.assertIn("/new-deal", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


class TestMarketPulse(unittest.TestCase):

    def test_returns_indicators(self):
        pulse = compute_market_pulse()
        self.assertGreater(len(pulse.indicators), 0)
        self.assertIsInstance(pulse.healthcare_pe_index, float)
        self.assertIsInstance(pulse.sentiment_score, float)

    def test_sentiment_label(self):
        pulse = compute_market_pulse()
        self.assertIn(pulse.sentiment_label,
                       ("Bullish", "Slightly Positive", "Neutral", "Bearish"))

    def test_to_dict(self):
        pulse = compute_market_pulse()
        d = pulse.to_dict()
        self.assertIn("indicators", d)
        self.assertIn("sentiment_label", d)


class TestInsights(unittest.TestCase):

    def test_high_denial_insight(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="A", profile={"denial_rate": 18})
            store.upsert_deal("d2", name="B", profile={"denial_rate": 20})
            insights = generate_daily_insights(store)
            titles = [i.title for i in insights]
            self.assertTrue(
                any("Denial" in t for t in titles),
                f"Expected denial insight, got: {titles}"
            )
        finally:
            os.unlink(tf.name)

    def test_empty_portfolio(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            insights = generate_daily_insights(store)
            self.assertEqual(insights, [])
        finally:
            os.unlink(tf.name)


if __name__ == "__main__":
    unittest.main()
