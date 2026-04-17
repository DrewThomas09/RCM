"""Tests for B116: run history page, runs API, peer comparison.

RUNS:
 1. GET /runs returns HTML page.
 2. GET /api/runs returns JSON list.
 3. /api/runs?deal_id= filters by deal.

PEERS:
 4. /api/deals/<id>/peers returns metric comparisons.
 5. Single deal returns empty peers.
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


class TestRunHistory(unittest.TestCase):

    def test_runs_page_renders(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/runs",
                ) as r:
                    body = r.read().decode()
                self.assertIn("Run History", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_api_runs_returns_json(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/runs",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertIn("runs", body)
                self.assertIn("count", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


class TestPeerComparison(unittest.TestCase):

    def test_peers_returns_comparisons(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="Alpha",
                              profile={"bed_count": 200, "denial_rate": 10})
            store.upsert_deal("d2", name="Beta",
                              profile={"bed_count": 300, "denial_rate": 15})
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/deals/d1/peers",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertEqual(body["deal_id"], "d1")
                self.assertIn("peers", body)
                self.assertEqual(len(body["peers"]), 1)
                peer = body["peers"][0]
                self.assertEqual(peer["deal_id"], "d2")
                self.assertIn("metrics", peer)
                if "bed_count" in peer["metrics"]:
                    self.assertEqual(peer["metrics"]["bed_count"]["target"], 200)
                    self.assertEqual(peer["metrics"]["bed_count"]["peer"], 300)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_single_deal_empty_peers(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="Alpha")
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/deals/d1/peers",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertEqual(body["peers"], [])
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


if __name__ == "__main__":
    unittest.main()
