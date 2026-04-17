"""Tests for B114: portfolio matrix endpoint.

 1. /api/portfolio/matrix returns deal rows with metrics.
 2. ?metrics= filters to specific columns.
 3. Empty portfolio returns empty.
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


class TestPortfolioMatrix(unittest.TestCase):

    def test_matrix_returns_deals(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="Alpha",
                              profile={"bed_count": 200, "denial_rate": 10})
            store.upsert_deal("d2", name="Beta",
                              profile={"bed_count": 350, "denial_rate": 15})
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/portfolio/matrix",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertEqual(body["deal_count"], 2)
                self.assertIn("metrics", body)
                self.assertIn("bed_count", body["metrics"])
                self.assertIn("denial_rate", body["metrics"])
                self.assertEqual(len(body["deals"]), 2)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_matrix_filters_metrics(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="Alpha",
                              profile={"bed_count": 200, "denial_rate": 10,
                                       "days_in_ar": 45})
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/portfolio/matrix?metrics=bed_count,denial_rate",
                ) as r:
                    body = json.loads(r.read().decode())
                deal = body["deals"][0]
                self.assertIn("bed_count", deal)
                self.assertIn("denial_rate", deal)
                self.assertNotIn("days_in_ar", deal)
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
                    f"http://127.0.0.1:{port}/api/portfolio/matrix",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertEqual(body["deal_count"], 0)
                self.assertEqual(body["deals"], [])
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


if __name__ == "__main__":
    unittest.main()
