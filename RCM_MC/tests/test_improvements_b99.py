"""Tests for improvement pass B99: portfolio summary, portfolio health.

PORTFOLIO SUMMARY:
 1. /api/portfolio/summary returns rollup with alert counts.
 2. Empty portfolio returns zero counts.

PORTFOLIO HEALTH:
 3. /api/portfolio/health returns band distribution.
 4. Empty portfolio returns zero counts.
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

from rcm_mc.portfolio.store import PortfolioStore


def _start(db_path):
    from rcm_mc.server import build_server
    s = socket.socket(); s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]; s.close()
    server, _ = build_server(port=port, db_path=db_path)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start(); time.sleep(0.05)
    return server, port


class TestPortfolioSummary(unittest.TestCase):

    def test_summary_returns_rollup(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/portfolio/summary",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertIn("deal_count", body)
                self.assertIn("stage_funnel", body)
                self.assertIn("active_alerts", body)
                self.assertIn("critical_alerts", body)
                self.assertIn("weighted_moic", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_empty_portfolio(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/portfolio/summary",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertEqual(body["deal_count"], 0)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


class TestPortfolioHealth(unittest.TestCase):

    def test_health_returns_bands(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/portfolio/health",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertIn("bands", body)
                self.assertIn("green", body["bands"])
                self.assertIn("amber", body["bands"])
                self.assertIn("red", body["bands"])
                self.assertIn("average_score", body)
                self.assertIn("deal_count", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_health_with_deals(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="Alpha",
                              profile={"bed_count": 200})
            from rcm_mc.portfolio.portfolio_snapshots import register_snapshot
            register_snapshot(store, "d1", "loi")
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/portfolio/health",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertEqual(body["deal_count"], 1)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


if __name__ == "__main__":
    unittest.main()
